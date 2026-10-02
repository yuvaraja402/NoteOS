"""Service doubles used only by tests; never loaded by the API runtime."""

from copy import deepcopy

from botocore.exceptions import ClientError
from redis.exceptions import WatchError


class RedisDouble:
    def __init__(self):
        self.values = {}
        self.expiries = {}
        self.versions = {}
        self.sorted_sets = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expiries[key] = ex
        self.versions[key] = self.versions.get(key, 0) + 1
        return True

    def expire(self, key, seconds, nx=False):
        if nx and self.expiries.get(key) is not None:
            return False
        self.expiries[key] = seconds
        return True

    def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.set(key, value)
        return value

    def zadd(self, key, mapping):
        self.sorted_sets.setdefault(key, {}).update(mapping)

    def zrem(self, key, member):
        self.sorted_sets.get(key, {}).pop(member, None)

    def zrangebyscore(self, key, lower, upper, start=0, num=100):
        items = sorted(self.sorted_sets.get(key, {}).items(), key=lambda pair: pair[1])
        return [member for member, score in items if score <= upper][start:start + num]

    def eval(self, script, count, key, token):
        if self.get(key) == token:
            self.values.pop(key, None)
            return 1
        return 0

    def pipeline(self, transaction=True):
        return PipelineDouble(self)

    def ping(self):
        return True


class PipelineDouble:
    def __init__(self, redis):
        self.redis = redis
        self.collecting = True
        self.calls = []
        self.watched = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def watch(self, key):
        self.watched[key] = self.redis.versions.get(key, 0)
        self.collecting = False

    def multi(self):
        self.collecting = True

    def execute(self):
        if any(self.redis.versions.get(key, 0) != version for key, version in self.watched.items()):
            raise WatchError()
        return [getattr(self.redis, name)(*args, **kwargs) for name, args, kwargs in self.calls]

    def __getattr__(self, name):
        def call(*args, **kwargs):
            if not self.collecting:
                return getattr(self.redis, name)(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            return self
        return call


class DynamoDouble:
    def __init__(self):
        self.items = {}
        self.writes = []
        self.fail = False
        self.before_put = None

    def get_item(self, Key, **kwargs):
        item = self.items.get(Key["workspace_id"])
        return {"Item": deepcopy(item)} if item else {}

    def put_item(self, Item, **kwargs):
        if self.before_put:
            hook, self.before_put = self.before_put, None
            hook()
        current = self.items.get(Item["workspace_id"])
        if self.fail or current and current["revision"] > Item["revision"]:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[Item["workspace_id"]] = deepcopy(Item)
        self.writes.append(deepcopy(Item))
