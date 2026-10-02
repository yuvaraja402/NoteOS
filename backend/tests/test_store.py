import json
import unittest
from types import SimpleNamespace

from botocore.exceptions import ClientError

from app.store import DIRTY_QUEUE, NoteStore, flush_due
from fakes import DynamoDouble, RedisDouble


class BufferTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.redis = RedisDouble()
        self.table = DynamoDouble()
        self.settings = SimpleNamespace(flush_idle_seconds=60, flush_max_seconds=300, cache_ttl_seconds=86400, max_notes=100)
        self.store = NoteStore(self.redis, self.table, self.settings, clock=lambda: self.now)
        self.note = {"title": "Draft", "content": "", "tags": [], "color": "sea", "is_pinned": False}

    def write(self, title="Draft"):
        return self.store.save_note("device-a", "note-1", {**self.note, "title": title})

    def test_edit_is_buffered_without_a_dynamodb_write_or_expiry(self):
        self.write()
        self.assertEqual(self.table.writes, [])
        self.assertIsNone(self.redis.expiries[self.store.key("device-a")])
        self.assertEqual(self.redis.sorted_sets[DIRTY_QUEUE]["device-a"], 1060)

    def test_idle_flush_persists_and_only_then_expires_clean_cache(self):
        self.write()
        self.now = 1030
        self.assertFalse(self.store.flush_one("device-a"))
        self.now = 1059
        self.assertFalse(self.store.flush_one("device-a"))
        self.now = 1060
        self.assertTrue(self.store.flush_one("device-a"))
        self.assertEqual(self.table.items["device-a"]["notes"][0]["title"], "Draft")
        self.assertFalse(self.store.snapshot("device-a")["dirty"])
        self.assertEqual(self.redis.expiries[self.store.key("device-a")], 86400)
        self.assertNotIn("device-a", self.redis.sorted_sets[DIRTY_QUEUE])

    def test_continuous_edits_cannot_postpone_beyond_maximum(self):
        self.write()
        for seconds in range(20, 301, 20):
            self.now = 1000 + seconds
            self.write(str(seconds))
        self.assertEqual(self.store.snapshot("device-a")["due_at"], 1300)
        self.assertTrue(self.store.flush_one("device-a"))
        self.assertEqual(self.table.items["device-a"]["notes"][0]["title"], "300")

    def test_dynamodb_failure_keeps_pending_data_and_retries(self):
        self.write()
        self.now = 1060
        self.table.fail = True
        with self.assertLogs("app.store", level="ERROR"):
            self.store.flush_due_workspaces()
        self.assertTrue(self.store.snapshot("device-a")["dirty"])
        self.assertIn("device-a", self.redis.sorted_sets[DIRTY_QUEUE])
        self.table.fail = False
        self.store.flush_due_workspaces()
        self.assertFalse(self.store.snapshot("device-a")["dirty"])

    def test_edit_during_flush_is_not_acknowledged_as_persisted(self):
        self.write("Old")
        self.now = 1060
        self.table.before_put = lambda: self.write("Latest")
        self.store.flush_one("device-a")
        current = self.store.snapshot("device-a")
        self.assertTrue(current["dirty"])
        self.assertEqual(current["notes"][0]["title"], "Latest")
        self.assertEqual(current["persisted_revision"], 1)
        self.assertIsNone(self.redis.expiries[self.store.key("device-a")])
        self.now = 1120
        self.store.flush_one("device-a")
        self.assertEqual(self.table.items["device-a"]["notes"][0]["title"], "Latest")

    def test_device_workspaces_are_isolated(self):
        self.write()
        self.assertEqual(self.store.snapshot("device-b")["notes"], [])
        self.store.delete_note("device-b", "note-1")
        self.assertEqual(len(self.store.snapshot("device-a")["notes"]), 1)

    def test_deletion_persists_empty_workspace_after_cache_is_removed(self):
        self.write()
        self.store.delete_note("device-a", "note-1")
        self.now = 1060
        self.store.flush_one("device-a")
        self.redis.values.pop(self.store.key("device-a"))
        self.assertEqual(self.store.snapshot("device-a")["notes"], [])
        self.assertGreater(self.store.snapshot("device-a")["revision"], 0)

    def test_pending_queue_survives_api_process_restart(self):
        self.write()
        restarted = NoteStore(self.redis, self.table, self.settings, clock=lambda: self.now)
        self.now = 1060
        restarted.flush_due_workspaces()
        self.assertEqual(len(self.table.writes), 1)

    def test_stale_flush_cannot_overwrite_newer_dynamodb_document(self):
        self.write("Old")
        self.table.items["device-a"] = {"workspace_id": "device-a", "notes": [], "revision": 5}
        self.now = 1060
        with self.assertRaises(ClientError):
            self.store.flush_one("device-a")
        self.assertEqual(self.table.items["device-a"]["revision"], 5)
        self.assertTrue(self.store.snapshot("device-a")["dirty"])

    def test_workspace_limit_rejects_edit_before_committing_redis(self):
        self.write()
        with self.assertRaises(ValueError):
            self.store.save_note("device-a", "note-1", {**self.note, "content": "x" * (210 * 1024)})
        self.assertEqual(self.store.snapshot("device-a")["notes"][0]["content"], "")

    def test_lease_prevents_two_workers_flushing_same_workspace(self):
        self.write()
        self.now = 1060
        self.redis.set("noteos:flush-lock:device-a", "another-worker")
        self.assertFalse(self.store.flush_one("device-a"))
        self.assertEqual(self.table.writes, [])

    def test_due_time_uses_idle_window_and_hard_maximum(self):
        self.assertEqual(flush_due(100, 90, 60, 300), 160)
        self.assertEqual(flush_due(380, 90, 60, 300), 390)


if __name__ == "__main__":
    unittest.main()
