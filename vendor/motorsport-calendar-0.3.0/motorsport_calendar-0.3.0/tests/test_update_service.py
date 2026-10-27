"""Tests for UpdateService — no Flet dependency, no real network calls."""

from __future__ import annotations

import inspect

import httpx
import pytest

from motorsport_calendar.gui import update_service
from motorsport_calendar.gui.update_service import (
    UpdateCheckResult,
    UpdateManifest,
    UpdateService,
    _parse_manifest,
    is_newer,
    parse_version,
)


class TestNoFletDependency:
    """Sprint 51 brief: 'Le service doit être totalement indépendant de
    Flet.' Source inspection rather than checking ``sys.modules`` after
    import — this project's own test suite imports ``flet`` indirectly
    all over the place (via ``main_view.py`` fixtures elsewhere), so
    ``flet`` being importable at all doesn't prove this module imports it
    itself."""

    def test_module_source_never_mentions_flet(self) -> None:
        source = inspect.getsource(update_service)
        # allow the word in the module's own docstring (explaining the
        # constraint), forbid any actual "import flet" statement
        assert "import flet" not in source


_MANIFEST_JSON = {
    "version": "0.5.1",
    "release_date": "2026-07-12",
    "title": "Motorsport Calendar 0.5.1",
    "summary": "Correctifs et améliorations de stabilité.",
    "url": "https://example.test/releases/0.5.1",
    "mandatory": False,
}


def _transport(handler: object) -> httpx.MockTransport:
    return httpx.MockTransport(handler)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_three_components(self) -> None:
        assert parse_version("0.4.10") == (0, 4, 10)

    def test_single_component(self) -> None:
        assert parse_version("1") == (1,)

    def test_two_components(self) -> None:
        assert parse_version("0.5") == (0, 5)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_version("")

    def test_non_numeric_component_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_version("0.4.9-beta")

    def test_letters_raise(self) -> None:
        with pytest.raises(ValueError):
            parse_version("abc")

    def test_trailing_dot_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_version("0.4.")

    def test_whitespace_is_stripped(self) -> None:
        assert parse_version("  0.4.9  ") == (0, 4, 9)


# ---------------------------------------------------------------------------
# is_newer — the core "no lexicographic comparison" requirement
# ---------------------------------------------------------------------------


class TestIsNewer:
    def test_same_version_is_not_newer(self) -> None:
        assert is_newer("0.4.9", "0.4.9") is False

    def test_patch_bump_is_newer(self) -> None:
        assert is_newer("0.4.9", "0.4.10") is True

    def test_lexicographic_trap_is_avoided(self) -> None:
        """The exact case named in the brief: a naive string comparison
        would rank "0.4.9" above "0.4.10" (since '9' > '1' at the first
        differing character) — numeric comparison must not."""
        assert is_newer("0.4.9", "0.4.10") is True
        assert "0.4.9" > "0.4.10"  # sanity check: string comparison IS backwards here

    def test_minor_bump_is_newer(self) -> None:
        assert is_newer("0.4.10", "0.5.0") is True

    def test_major_bump_is_newer(self) -> None:
        assert is_newer("0.5.0", "1.0.0") is True

    def test_older_version_is_not_newer(self) -> None:
        assert is_newer("0.5.0", "0.4.9") is False

    def test_much_older_major_is_not_newer(self) -> None:
        assert is_newer("1.0.0", "0.9.9") is False

    def test_shorter_form_equal_to_longer_zero_padded_form(self) -> None:
        """ "0.5" and "0.5.0" are the same version — the shorter form must
        not be considered older just because it has fewer components."""
        assert is_newer("0.5", "0.5.0") is False
        assert is_newer("0.5.0", "0.5") is False

    def test_shorter_form_older_than_real_bump(self) -> None:
        assert is_newer("0.5", "0.5.1") is True

    def test_invalid_current_version_raises(self) -> None:
        with pytest.raises(ValueError):
            is_newer("not-a-version", "0.5.0")

    def test_invalid_candidate_version_raises(self) -> None:
        with pytest.raises(ValueError):
            is_newer("0.5.0", "not-a-version")


# ---------------------------------------------------------------------------
# _parse_manifest
# ---------------------------------------------------------------------------


class TestParseManifest:
    def test_valid_manifest(self) -> None:
        manifest = _parse_manifest(_MANIFEST_JSON)
        assert manifest == UpdateManifest(
            version="0.5.1",
            release_date="2026-07-12",
            title="Motorsport Calendar 0.5.1",
            summary="Correctifs et améliorations de stabilité.",
            url="https://example.test/releases/0.5.1",
            mandatory=False,
        )

    def test_mandatory_defaults_to_false_when_absent(self) -> None:
        data = {k: v for k, v in _MANIFEST_JSON.items() if k != "mandatory"}
        manifest = _parse_manifest(data)
        assert manifest.mandatory is False

    def test_mandatory_true_is_preserved(self) -> None:
        data = {**_MANIFEST_JSON, "mandatory": True}
        manifest = _parse_manifest(data)
        assert manifest.mandatory is True

    def test_not_a_dict_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_manifest(["not", "a", "dict"])

    def test_missing_version_raises(self) -> None:
        data = {k: v for k, v in _MANIFEST_JSON.items() if k != "version"}
        with pytest.raises(ValueError, match="version"):
            _parse_manifest(data)

    def test_missing_url_raises(self) -> None:
        data = {k: v for k, v in _MANIFEST_JSON.items() if k != "url"}
        with pytest.raises(ValueError, match="url"):
            _parse_manifest(data)

    def test_missing_multiple_fields_lists_all_of_them(self) -> None:
        data = {"version": "0.5.1"}
        with pytest.raises(ValueError, match="release_date"):
            _parse_manifest(data)

    def test_empty_dict_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_manifest({})


# ---------------------------------------------------------------------------
# UpdateService.check_for_update — end-to-end through a real httpx client
# (httpx.MockTransport, no real network call)
# ---------------------------------------------------------------------------


class TestUpdateServiceNoUrlConfigured:
    async def test_empty_manifest_url_returns_no_update_without_network(self) -> None:
        service = UpdateService("", "0.4.9")
        result = await service.check_for_update()
        assert result == UpdateCheckResult(
            update_available=False,
            current_version="0.4.9",
            error="Aucune URL de manifeste configurée.",
        )


class TestUpdateServiceUpdateAvailable:
    async def test_newer_version_available(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_MANIFEST_JSON)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is True
        assert result.current_version == "0.4.9"
        assert result.error is None
        assert result.manifest is not None
        assert result.manifest.version == "0.5.1"
        assert result.manifest.title == "Motorsport Calendar 0.5.1"

    async def test_major_version_bump_detected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "version": "1.0.0"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.5.0", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is True
        assert result.manifest is not None
        assert result.manifest.version == "1.0.0"

    async def test_minor_version_bump_detected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "version": "0.5.0"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.10", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is True
        assert result.manifest is not None
        assert result.manifest.version == "0.5.0"

    async def test_mandatory_flag_is_passed_through(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "mandatory": True})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.manifest is not None
        assert result.manifest.mandatory is True


class TestUpdateServiceSameVersion:
    async def test_same_version_reports_no_update(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "version": "0.5.1"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.5.1", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is None
        # the manifest is still returned — the view may want to display
        # "you are up to date" details even when no update is available
        assert result.manifest is not None

    async def test_current_version_ahead_of_manifest_reports_no_update(self) -> None:
        """A dev build running ahead of the published manifest must never
        be told to 'update' to an older version."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "version": "0.4.0"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.5.1", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False


class TestUpdateServiceInvalidManifest:
    async def test_manifest_missing_required_fields(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"version": "0.5.1"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.manifest is None
        assert result.error is not None

    async def test_manifest_is_a_json_array_not_an_object(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=["not", "an", "object"])

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None

    async def test_manifest_body_is_not_valid_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"NOT JSON {{{{")

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None

    async def test_manifest_version_is_unparseable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={**_MANIFEST_JSON, "version": "not-a-version"})

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None
        # the manifest itself parsed fine — only the version comparison failed
        assert result.manifest is not None


class TestUpdateServiceNoNetwork:
    async def test_connection_error_is_caught(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.manifest is None
        assert result.error is not None

    async def test_timeout_is_caught(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None

    async def test_http_404_is_caught(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None

    async def test_http_500_is_caught(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        result = await service.check_for_update()
        await client.aclose()

        assert result.update_available is False
        assert result.error is not None

    async def test_never_raises(self) -> None:
        """The brief's core safety requirement: a failed check must never
        crash application startup."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("unreachable", request=request)

        client = httpx.AsyncClient(transport=_transport(handler))
        service = UpdateService("https://example.test/manifest.json", "0.4.9", client=client)
        try:
            await service.check_for_update()
        except Exception as exc:  # pragma: no cover - failure path
            pytest.fail(f"check_for_update() raised {exc!r} instead of returning a result")
        finally:
            await client.aclose()


class TestUpdateServiceWithoutInjectedClient:
    async def test_creates_its_own_client_when_none_given(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No client passed to the constructor — the service must build
        and tear down its own short-lived one rather than fail."""
        calls: list[str] = []

        class _FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return dict(_MANIFEST_JSON)

        class _FakeClient:
            async def __aenter__(self) -> _FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def get(self, url: str, timeout: float) -> _FakeResponse:
                calls.append(url)
                return _FakeResponse()

        monkeypatch.setattr(
            "motorsport_calendar.gui.update_service.httpx.AsyncClient",
            lambda: _FakeClient(),
        )

        service = UpdateService("https://example.test/manifest.json", "0.4.9")
        result = await service.check_for_update()

        assert calls == ["https://example.test/manifest.json"]
        assert result.update_available is True
