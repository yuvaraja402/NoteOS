"""Redis write buffer and conditional DynamoDB document persistence."""

import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError
from redis.exceptions import WatchError

logger = logging.getLogger(__name__)
DIRTY_QUEUE = "noteos:dirty"
MAX_DOCUMENT_BYTES = 200 * 1024


def flush_due(now: int, first_dirty: int, idle: int, maximum: int) -> int:
    return min(now + idle, first_dirty + maximum)


class BusyWorkspace(Exception):
    pass


class NoteStore:
    def __init__(self, redis_client, table, settings, clock=time.time):
        self.redis = redis_client
        self.table = table
        self.settings = settings
        self.clock = clock

    @staticmethod
    def key(workspace):
        return f"noteos:workspace:{workspace}"

    def _load_document(self, workspace):
        item = self.table.get_item(Key={"workspace_id": workspace}, ConsistentRead=True).get("Item")
        return {
            "notes": item.get("notes", []) if item else [],
            "revision": int(item.get("revision", 0)) if item else 0,
            "persisted_revision": int(item.get("revision", 0)) if item else 0,
            "persisted_at": item.get("persisted_at") if item else None,
            "dirty": False,
            "first_dirty_at": None,
            "due_at": None,
        }

    def snapshot(self, workspace):
        key = self.key(workspace)
        cached = self.redis.get(key)
        if cached is not None:
            return json.loads(cached)
        document = self._load_document(workspace)
        self.redis.set(key, json.dumps(document), nx=True, ex=self.settings.cache_ttl_seconds)
        # Another request may have populated and edited this workspace while we read AWS.
        return json.loads(self.redis.get(key))

    def mutate(self, workspace, operation):
        key = self.key(workspace)
        for _ in range(8):
            self.snapshot(workspace)
            with self.redis.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if raw is None:
                        continue
                    document = json.loads(raw)
                    result = operation(document["notes"])
                    if len(document["notes"]) > self.settings.max_notes:
                        raise ValueError("This workspace has reached its note limit.")
                    if len(json.dumps(document["notes"]).encode()) > MAX_DOCUMENT_BYTES:
                        raise ValueError("This workspace has reached its storage limit.")
                    now = int(self.clock())
                    first_dirty = document["first_dirty_at"] if document["dirty"] else now
                    document.update(
                        revision=document["revision"] + 1,
                        dirty=True,
                        first_dirty_at=first_dirty,
                        due_at=flush_due(now, first_dirty, self.settings.flush_idle_seconds, self.settings.flush_max_seconds),
                    )
                    pipe.multi()
                    # SET removes the clean-cache TTL. Dirty data never expires before persistence.
                    pipe.set(key, json.dumps(document))
                    pipe.zadd(DIRTY_QUEUE, {workspace: document["due_at"]})
                    pipe.execute()
                    return result, document["revision"]
                except WatchError:
                    continue
        raise BusyWorkspace("Workspace changed concurrently; retry the request.")

    def save_note(self, workspace, note_id, payload, patch=False):
        now = datetime.now(timezone.utc).isoformat()

        def update(notes):
            current = next((note for note in notes if note["id"] == note_id), None)
            if patch and current is None:
                raise KeyError(note_id)
            if current is None:
                current = {"id": note_id, "created_at": now}
                notes.append(current)
            current.update(payload)
            current["updated_at"] = now
            return dict(current)

        return self.mutate(workspace, update)

    def delete_note(self, workspace, note_id):
        def delete(notes):
            notes[:] = [note for note in notes if note["id"] != note_id]
        return self.mutate(workspace, delete)

    def rate_limit(self, identity, limit):
        bucket = int(self.clock()) // 60
        key = f"noteos:rate:{identity}:{bucket}"
        with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120, nx=True)
            count, _ = pipe.execute()
        return count <= limit

    def flush_one(self, workspace):
        token = str(uuid4())
        lock_key = f"noteos:flush-lock:{workspace}"
        if not self.redis.set(lock_key, token, nx=True, ex=60):
            return False
        try:
            raw = self.redis.get(self.key(workspace))
            if raw is None:
                logger.error("Missing buffered workspace; cache recovery is required")
                return False
            document = json.loads(raw)
            if not document["dirty"] or document["due_at"] > int(self.clock()):
                return False
            persisted_at = datetime.now(timezone.utc).isoformat()
            self.table.put_item(
                Item={
                    "workspace_id": workspace,
                    "notes": document["notes"],
                    "revision": document["revision"],
                    "persisted_at": persisted_at,
                },
                ConditionExpression="attribute_not_exists(#rev) OR #rev <= :revision",
                ExpressionAttributeNames={"#rev": "revision"},
                ExpressionAttributeValues={":revision": document["revision"]},
            )
            self._acknowledge(workspace, document["revision"], persisted_at)
            return True
        finally:
            # Never release another task's lease after this one's lease expires.
            self.redis.eval(
                "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0",
                1, lock_key, token,
            )

    def _acknowledge(self, workspace, revision, persisted_at):
        key = self.key(workspace)
        for _ in range(8):
            with self.redis.pipeline() as pipe:
                try:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if raw is None:
                        return
                    current = json.loads(raw)
                    current["persisted_revision"] = max(current["persisted_revision"], revision)
                    current["persisted_at"] = persisted_at
                    clean = current["revision"] == revision
                    if clean:
                        current.update(dirty=False, first_dirty_at=None, due_at=None)
                    pipe.multi()
                    pipe.set(key, json.dumps(current))
                    if clean:
                        pipe.expire(key, self.settings.cache_ttl_seconds)
                        pipe.zrem(DIRTY_QUEUE, workspace)
                    pipe.execute()
                    return
                except WatchError:
                    continue
        raise BusyWorkspace("Persistence acknowledgement will be retried.")

    def flush_due_workspaces(self):
        workspaces = self.redis.zrangebyscore(DIRTY_QUEUE, "-inf", int(self.clock()), start=0, num=100)
        for workspace in workspaces:
            try:
                self.flush_one(workspace)
            except (ClientError, BusyWorkspace, OSError):
                logger.error("DynamoDB flush failed; buffered changes remain queued")
