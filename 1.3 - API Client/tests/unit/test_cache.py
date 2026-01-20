"""Unit tests for the cache module."""

from __future__ import annotations

import time

from github_client.utils.cache import CacheEntry, ResponseCache, make_cache_key


class TestMakeCacheKey:
    """Tests for make_cache_key function."""

    def test_basic_key(self):
        """Should create key from method and endpoint."""
        key = make_cache_key("GET", "/users/octocat")
        assert "GET" in key
        assert "/users/octocat" in key

    def test_different_methods_different_keys(self):
        """Different methods should produce different keys."""
        get_key = make_cache_key("GET", "/repos")
        post_key = make_cache_key("POST", "/repos")
        assert get_key != post_key

    def test_with_auth_true(self):
        """Key with auth should differ from key without auth."""
        key_auth = make_cache_key("GET", "/user", is_authenticated=True)
        key_no_auth = make_cache_key("GET", "/user", is_authenticated=False)
        assert key_auth != key_no_auth
        assert "auth" in key_auth
        assert "anon" in key_no_auth

    def test_with_params(self):
        """Key with params should include param info."""
        key_no_params = make_cache_key("GET", "/repos")
        key_with_params = make_cache_key("GET", "/repos", params={"page": "1"})
        assert key_no_params != key_with_params

    def test_params_order_independent(self):
        """Param order should not affect key."""
        key1 = make_cache_key("GET", "/repos", params={"a": "1", "b": "2"})
        key2 = make_cache_key("GET", "/repos", params={"b": "2", "a": "1"})
        assert key1 == key2


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_is_expired_fresh(self):
        """Fresh entry should not be expired."""
        entry = CacheEntry(
            data={"test": "data"},
            etag=None,
            expires_at=time.time() + 60,
        )
        assert entry.is_expired is False

    def test_is_expired_old(self):
        """Old entry should be expired."""
        entry = CacheEntry(
            data={"test": "data"},
            etag=None,
            expires_at=time.time() - 60,  # Expired
        )
        assert entry.is_expired is True

    def test_ttl_remaining_fresh(self):
        """Fresh entry should have positive TTL remaining."""
        entry = CacheEntry(
            data={"test": "data"},
            etag=None,
            expires_at=time.time() + 60,
        )
        assert entry.ttl_remaining > 0


class TestResponseCache:
    """Tests for ResponseCache class."""

    def test_default_settings(self):
        """Should have sensible defaults."""
        cache = ResponseCache()
        assert cache._default_ttl == 300  # 5 minutes

    def test_custom_settings(self):
        """Should accept custom TTL."""
        cache = ResponseCache(default_ttl=120)
        assert cache._default_ttl == 120

    def test_set_and_get(self):
        """Should store and retrieve entries."""
        cache = ResponseCache()
        data = {"login": "octocat"}

        cache.set("key1", data)
        entry = cache.get("key1")

        assert entry is not None
        assert entry.data == data

    def test_get_miss(self):
        """Should return None for missing key."""
        cache = ResponseCache()
        assert cache.get("nonexistent") is None

    def test_get_expired_returns_none(self):
        """Should return None for expired entries."""
        cache = ResponseCache(default_ttl=1)
        cache.set("key1", {"test": "data"})

        # Let it expire
        time.sleep(1.1)

        entry = cache.get("key1")
        assert entry is None

    def test_set_with_etag(self):
        """Should store ETag when provided."""
        cache = ResponseCache()
        cache.set("key1", {"test": "data"}, etag='"etag-value"')
        entry = cache.get("key1")

        assert entry is not None
        assert entry.etag == '"etag-value"'

    def test_refresh_ttl(self):
        """Should extend TTL on refresh."""
        cache = ResponseCache(default_ttl=10)
        cache.set("key1", {"test": "data"})

        entry_before = cache.get("key1")
        original_expires = entry_before.expires_at

        # Refresh with longer TTL
        result = cache.refresh_ttl("key1", ttl=60)

        assert result is True
        entry_after = cache.get("key1")
        assert entry_after.expires_at > original_expires

    def test_refresh_ttl_nonexistent(self):
        """Refresh of nonexistent key should return False."""
        cache = ResponseCache()
        result = cache.refresh_ttl("nonexistent")
        assert result is False

    def test_invalidate(self):
        """Should remove entry on invalidate."""
        cache = ResponseCache()
        cache.set("key1", {"test": "data"})
        result = cache.invalidate("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_invalidate_nonexistent(self):
        """Invalidate of nonexistent key should return False."""
        cache = ResponseCache()
        result = cache.invalidate("nonexistent")
        assert result is False

    def test_clear(self):
        """Should remove all entries."""
        cache = ResponseCache()
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})

        count = cache.clear()

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_size(self):
        """Should report correct size."""
        cache = ResponseCache()

        assert cache.size == 0
        cache.set("key1", {"a": 1})
        assert cache.size == 1
        cache.set("key2", {"b": 2})
        assert cache.size == 2

    def test_get_etag(self):
        """Should return stored ETag."""
        cache = ResponseCache()
        cache.set("key1", {"test": "data"}, etag='"my-etag"')

        assert cache.get_etag("key1") == '"my-etag"'

    def test_get_etag_missing(self):
        """Should return None for missing key."""
        cache = ResponseCache()
        assert cache.get_etag("nonexistent") is None

    def test_get_etag_expired(self):
        """Should return ETag even for expired entries."""
        cache = ResponseCache(default_ttl=1)
        cache.set("key1", {"test": "data"}, etag='"stale-etag"')

        time.sleep(1.1)  # Let it expire

        # Even expired, we should be able to get the ETag for conditional requests
        etag = cache.get_etag("key1")
        assert etag == '"stale-etag"'
