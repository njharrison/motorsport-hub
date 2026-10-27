"""Tests unitaires pour HttpCache — cache disque JSON avec TTL."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import time
from unittest.mock import AsyncMock, patch

from motorsport_calendar.cache import HttpCache
from motorsport_calendar.utils.paths import user_cache_dir

_URL = "https://api.example.com/data"
_PARAMS: dict = {"year": 2024}
_DATA: list = [{"id": 1, "name": "Bahrain"}]
_DATA_ALT: list = [{"id": 2, "name": "Melbourne"}]


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestHttpCacheDefaultCacheDir:
    """Sprint 49 — the implicit default (used when a caller constructs
    ``HttpCache()`` without an explicit ``cache_dir``, e.g. the CLI/GUI's
    own cache-disabled edge case) must be a user cache directory, never the
    current working directory. Inspects the *default parameter value*
    only — never constructs an instance with it, which would create a real
    directory at the developer/CI machine's actual user cache location."""

    def test_default_is_not_relative_to_cwd(self) -> None:
        default = inspect.signature(HttpCache.__init__).parameters["cache_dir"].default
        assert default != Path(".cache")
        assert default.is_absolute()

    def test_default_matches_user_cache_dir(self) -> None:
        default = inspect.signature(HttpCache.__init__).parameters["cache_dir"].default
        assert default == user_cache_dir("motorsport-calendar")


class TestHttpCacheInit:
    def test_creates_cache_dir_if_missing(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "sub" / ".cache"
        HttpCache(cache_dir=cache_dir)
        assert cache_dir.is_dir()

    def test_accepts_existing_dir(self, tmp_path: Path) -> None:
        HttpCache(cache_dir=tmp_path)  # ne doit pas lever d'exception

    def test_default_ttl_is_24h(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        assert cache._ttl == 86400

    def test_custom_ttl_is_stored(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path, ttl=3600)
        assert cache._ttl == 3600


# ---------------------------------------------------------------------------
# get_json — comportement du cache
# ---------------------------------------------------------------------------


class TestGetJsonCacheMiss:
    async def test_calls_fetch_on_miss(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        result = await cache.get_json(_URL, _PARAMS, fetch)
        fetch.assert_called_once_with(_URL, _PARAMS)
        assert result == _DATA

    async def test_creates_cache_file_on_miss(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)
        assert any(tmp_path.glob("*.json"))

    async def test_cache_file_contains_data_and_metadata(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        await cache.get_json(_URL, _PARAMS, AsyncMock(return_value=_DATA))
        (cache_file,) = list(tmp_path.glob("*.json"))
        entry = json.loads(cache_file.read_text(encoding="utf-8"))
        assert entry["data"] == _DATA
        assert entry["url"] == _URL
        assert entry["params"] == _PARAMS
        assert "cached_at" in entry


class TestGetJsonCacheHit:
    async def test_does_not_call_fetch_on_hit(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)  # peuplement
        fetch.reset_mock()
        await cache.get_json(_URL, _PARAMS, fetch)  # hit
        fetch.assert_not_called()

    async def test_returns_cached_data_on_hit(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        await cache.get_json(_URL, _PARAMS, AsyncMock(return_value=_DATA))
        result = await cache.get_json(_URL, _PARAMS, AsyncMock(return_value=_DATA_ALT))
        assert result == _DATA  # données originales, pas _DATA_ALT


class TestGetJsonExpiry:
    async def test_expired_entry_triggers_refetch(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)  # peuplement

        fetch.reset_mock()
        fetch.return_value = _DATA_ALT

        # Simuler un temps futur dépassant le TTL
        target = "motorsport_calendar.cache.http_cache.time.time"
        with patch(target, return_value=time.time() + 86401):
            result = await cache.get_json(_URL, _PARAMS, fetch)

        fetch.assert_called_once()
        assert result == _DATA_ALT

    async def test_valid_entry_not_refetched_just_before_expiry(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path, ttl=3600)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)
        fetch.reset_mock()

        # Juste avant expiration : le cache doit rester valide
        target = "motorsport_calendar.cache.http_cache.time.time"
        with patch(target, return_value=time.time() + 3599):
            await cache.get_json(_URL, _PARAMS, fetch)

        fetch.assert_not_called()


class TestGetJsonRefresh:
    async def test_refresh_bypasses_valid_cache(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)  # peuplement
        fetch.reset_mock()
        await cache.get_json(_URL, _PARAMS, fetch, refresh=True)
        fetch.assert_called_once()

    async def test_refresh_updates_cache_entry(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        await cache.get_json(_URL, _PARAMS, AsyncMock(return_value=_DATA))
        result = await cache.get_json(
            _URL, _PARAMS, AsyncMock(return_value=_DATA_ALT), refresh=True
        )
        assert result == _DATA_ALT
        # La prochaine lecture sans refresh doit retourner les nouvelles données
        result2 = await cache.get_json(_URL, _PARAMS, AsyncMock(return_value=[]))
        assert result2 == _DATA_ALT


# ---------------------------------------------------------------------------
# Unicité des clés
# ---------------------------------------------------------------------------


class TestCacheKeyUniqueness:
    async def test_different_params_produce_different_entries(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(side_effect=[_DATA, _DATA_ALT])
        await cache.get_json(_URL, {"year": 2024}, fetch)
        await cache.get_json(_URL, {"year": 2025}, fetch)
        assert fetch.call_count == 2
        assert len(list(tmp_path.glob("*.json"))) == 2

    async def test_different_urls_produce_different_entries(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(side_effect=[_DATA, _DATA_ALT])
        await cache.get_json("https://api.example.com/a", _PARAMS, fetch)
        await cache.get_json("https://api.example.com/b", _PARAMS, fetch)
        assert fetch.call_count == 2

    async def test_same_params_different_order_use_same_key(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, {"a": 1, "b": 2}, fetch)
        fetch.reset_mock()
        await cache.get_json(_URL, {"b": 2, "a": 1}, fetch)
        fetch.assert_not_called()  # même clé, cache hit


# ---------------------------------------------------------------------------
# Robustesse — données corrompues
# ---------------------------------------------------------------------------


class TestCorruption:
    async def test_corrupted_json_treated_as_miss(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        key = cache._make_key(_URL, _PARAMS)
        (tmp_path / f"{key}.json").write_text("not valid json", encoding="utf-8")
        fetch = AsyncMock(return_value=_DATA)
        result = await cache.get_json(_URL, _PARAMS, fetch)
        fetch.assert_called_once()
        assert result == _DATA

    async def test_missing_cached_at_field_treated_as_miss(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        key = cache._make_key(_URL, _PARAMS)
        (tmp_path / f"{key}.json").write_text(
            json.dumps({"data": _DATA}),
            encoding="utf-8",
        )
        fetch = AsyncMock(return_value=_DATA)
        result = await cache.get_json(_URL, _PARAMS, fetch)
        fetch.assert_called_once()
        assert result == _DATA

    async def test_missing_data_field_treated_as_miss(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        key = cache._make_key(_URL, _PARAMS)
        (tmp_path / f"{key}.json").write_text(
            json.dumps({"cached_at": time.time()}),
            encoding="utf-8",
        )
        fetch = AsyncMock(return_value=_DATA)
        result = await cache.get_json(_URL, _PARAMS, fetch)
        fetch.assert_called_once()
        assert result == _DATA


# ---------------------------------------------------------------------------
# invalidate / clear
# ---------------------------------------------------------------------------


class TestInvalidate:
    async def test_invalidate_forces_next_fetch(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, _PARAMS, fetch)  # peuplement
        cache.invalidate(_URL, _PARAMS)
        fetch.reset_mock()
        await cache.get_json(_URL, _PARAMS, fetch)
        fetch.assert_called_once()

    def test_invalidate_returns_true_when_entry_existed(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        key = cache._make_key(_URL, _PARAMS)
        (tmp_path / f"{key}.json").write_text("{}", encoding="utf-8")
        assert cache.invalidate(_URL, _PARAMS) is True

    def test_invalidate_returns_false_when_entry_missing(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        assert cache.invalidate(_URL, _PARAMS) is False


class TestClear:
    async def test_clear_removes_all_entries(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        fetch = AsyncMock(return_value=_DATA)
        await cache.get_json(_URL, {"year": 2024}, fetch)
        await cache.get_json(_URL, {"year": 2025}, fetch)
        count = cache.clear()
        assert count == 2
        assert not any(tmp_path.glob("*.json"))

    def test_clear_empty_cache_returns_zero(self, tmp_path: Path) -> None:
        cache = HttpCache(cache_dir=tmp_path)
        assert cache.clear() == 0
