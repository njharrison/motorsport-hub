"""UpdateService — checks a remote manifest for a newer app version (Sprint 51).

Completely independent of Flet: no ``flet`` import anywhere in this module,
same "usable standalone" contract as ``FavoritesService``/
``NotificationService``/``SearchService``. Never downloads, installs, or
restarts anything — the only side effect of ``check_for_update()`` is a
single HTTP GET against a caller-supplied manifest URL. The manifest is a
small, generic JSON document (see ``_parse_manifest``); this module has no
knowledge of GitHub, any specific hosting platform, or any release API —
``manifest_url`` is entirely caller-supplied (``gui/controller.py::
check_for_update`` resolves it from ``config.yaml``'s
``update.manifest_url``, see ``config/models.py::UpdateConfig``).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_REQUIRED_MANIFEST_FIELDS = ("version", "release_date", "title", "summary", "url")


@dataclass(frozen=True)
class UpdateManifest:
    """One remote release, as published in the JSON manifest.

    Field names match the manifest's JSON keys 1:1 (see the Sprint 51
    brief's example) — no renaming/remapping between wire format and
    this structure.
    """

    version: str
    release_date: str
    title: str
    summary: str
    url: str
    mandatory: bool = False


@dataclass(frozen=True)
class UpdateCheckResult:
    """Everything ``main_view.py`` needs to render — the view never parses
    the manifest or compares versions itself, only this result.

    ``error`` is set whenever the check could not be completed (no URL
    configured, network unreachable, invalid JSON, incomplete manifest,
    unparseable version) — always alongside ``update_available=False``,
    never raised as an exception. A failed check must never crash
    application startup.
    """

    update_available: bool
    current_version: str
    manifest: UpdateManifest | None = None
    error: str | None = None


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a dotted numeric version string into a comparable tuple.

    Args:
        version: e.g. ``"0.4.10"`` -> ``(0, 4, 10)``.

    Raises:
        ValueError: *version* is not a non-empty dotted sequence of
            non-negative integers (covers empty strings, non-numeric
            components, and stray whitespace).
    """
    parts = version.strip().split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Invalid version string: {version!r}")
    return tuple(int(part) for part in parts)


def is_newer(current: str, candidate: str) -> bool:
    """True if *candidate* is a strictly newer version than *current*.

    Numeric, component-by-component comparison — never lexicographic —
    so ``0.4.9 < 0.4.10 < 0.5.0 < 1.0.0`` is ordered correctly. A plain
    string comparison would rank ``"0.4.9"`` above ``"0.4.10"`` (since
    ``'9' > '1'`` at the first differing character), exactly the bug this
    function exists to avoid. Differing lengths are padded with zeros
    before comparing, so ``"0.5"`` and ``"0.5.0"`` compare equal rather
    than the longer form being considered newer.

    Raises:
        ValueError: either *current* or *candidate* is not a valid
            dotted-numeric version string (propagated from
            :func:`parse_version`).
    """
    current_parts = parse_version(current)
    candidate_parts = parse_version(candidate)
    length = max(len(current_parts), len(candidate_parts))
    current_padded = current_parts + (0,) * (length - len(current_parts))
    candidate_padded = candidate_parts + (0,) * (length - len(candidate_parts))
    return candidate_padded > current_padded


def _parse_manifest(data: object) -> UpdateManifest:
    """Build an :class:`UpdateManifest` from decoded JSON, or raise.

    Raises:
        ValueError: *data* isn't a JSON object, or is missing one of the
            required fields (``version``/``release_date``/``title``/
            ``summary``/``url`` — everything except ``mandatory``, which
            defaults to ``False`` when absent).
    """
    if not isinstance(data, dict):
        raise ValueError("Le manifeste n'est pas un objet JSON.")
    missing = [field for field in _REQUIRED_MANIFEST_FIELDS if field not in data]
    if missing:
        raise ValueError(f"Champ(s) manquant(s) dans le manifeste : {', '.join(missing)}.")
    return UpdateManifest(
        version=str(data["version"]),
        release_date=str(data["release_date"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        url=str(data["url"]),
        mandatory=bool(data.get("mandatory", False)),
    )


class UpdateService:
    """Checks whether a newer Motorsport Calendar version is available.

    Never downloads, installs, or restarts anything — the only side
    effect of :meth:`check_for_update` is one HTTP GET to *manifest_url*.

    Args:
        manifest_url: Absolute URL of the JSON manifest. Any host works;
            this class has no knowledge of GitHub or any other platform.
        current_version: The running app's version (e.g.
            ``motorsport_calendar.__version__``) — never read internally,
            always caller-supplied, so this stays fully deterministic and
            testable (same "no hidden global state" convention as
            ``NotificationService.compute_notifications``'s explicit
            ``now`` parameter).
        client: Optional ``httpx.AsyncClient`` to inject (useful in
            tests). When omitted, a short-lived client is created per call.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        manifest_url: str,
        current_version: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._manifest_url = manifest_url
        self._current_version = current_version
        self._client = client
        self._timeout = timeout

    async def check_for_update(self) -> UpdateCheckResult:
        """Fetch the manifest and compare it to the current version.

        Returns:
            An :class:`UpdateCheckResult` — always, never raises.
            ``update_available`` is ``False`` whenever no URL is
            configured, the manifest can't be fetched/parsed, or the
            remote version isn't strictly newer than *current_version*.
        """
        if not self._manifest_url:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                error="Aucune URL de manifeste configurée.",
            )

        try:
            raw = await self._fetch_json()
        except (httpx.HTTPError, ValueError) as exc:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                error=str(exc),
            )

        try:
            manifest = _parse_manifest(raw)
        except ValueError as exc:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                error=str(exc),
            )

        try:
            available = is_newer(self._current_version, manifest.version)
        except ValueError as exc:
            return UpdateCheckResult(
                update_available=False,
                current_version=self._current_version,
                manifest=manifest,
                error=str(exc),
            )

        return UpdateCheckResult(
            update_available=available,
            current_version=self._current_version,
            manifest=manifest,
        )

    async def _fetch_json(self) -> object:
        """GET ``self._manifest_url`` and return its decoded JSON body."""
        if self._client is not None:
            response = await self._client.get(self._manifest_url, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        async with httpx.AsyncClient() as client:
            response = await client.get(self._manifest_url, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
