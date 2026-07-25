import time

from app.cache.memory_cache import TTLCache


def test_set_and_get_returns_value():
    cache = TTLCache()
    cache.set("key1", {"foo": "bar"}, ttl_seconds=60)
    assert cache.get("key1") == {"foo": "bar"}


def test_get_missing_key_returns_none():
    cache = TTLCache()
    assert cache.get("does-not-exist") is None


def test_expired_entry_returns_none():
    cache = TTLCache()
    cache.set("key1", "value", ttl_seconds=0.05)
    time.sleep(0.1)
    assert cache.get("key1") is None


def test_expired_entry_is_evicted_from_store():
    cache = TTLCache()
    cache.set("key1", "value", ttl_seconds=0.05)
    time.sleep(0.1)
    cache.get("key1")  # triggers lazy eviction
    assert "key1" not in cache._store


def test_different_keys_are_independent():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    cache.set("key2", "value2", ttl_seconds=60)
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"


def test_overwrite_existing_key():
    cache = TTLCache()
    cache.set("key1", "old", ttl_seconds=60)
    cache.set("key1", "new", ttl_seconds=60)
    assert cache.get("key1") == "new"
