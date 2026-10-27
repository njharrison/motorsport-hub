"""GUI controller — bridges the view to the existing engine.

No Flet import here: this module is testable in isolation.
Never duplicates providers, registry, exporter, or cache.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from motorsport_calendar.cache import HttpCache
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.gui.dashboard import DashboardData
    from motorsport_calendar.gui.upcoming_weekend import WeekendEntry, WeekendResult
    from motorsport_calendar.gui.update_service import UpdateCheckResult
    from motorsport_calendar.models import Event


# Sprint 57 (Préparation Beta — positionnement) — championships hidden
# from the GUI's own championship pickers ("Mon calendrier"/"Mes
# favoris"/"Recherche") until they have a reliable source. Both remain
# fully registered in ProviderRegistry (``registry.list_all()``,
# unfiltered, still returns them) — this is a UI-exposure decision only,
# never a code removal: `cli.py generate-imsa`/`generate-worldsbk` and
# `registry.enabled(...)` (the Dashboard's "championnats actifs" stat)
# are untouched, since those describe the architecture, not what the GUI
# offers to pick from. Revisit (remove from this tuple) once
# ``OfficialImsaSource``/``OfficialWorldSbkSource`` have a real
# implementation (see ADR-027/ADR-029, `docs/DATA_SOURCES.md`).
_HIDDEN_FROM_GUI: frozenset[str] = frozenset({"imsa", "worldsbk"})


def list_championships() -> list[str]:
    """Return sorted list of championship IDs offered by the GUI.

    Excludes ``_HIDDEN_FROM_GUI`` — championships still fully registered
    in ``ProviderRegistry`` but not yet proposed to the user (Sprint 57).
    """
    from motorsport_calendar.core.registry import registry

    registry.discover()
    return [cid for cid in registry.list_all() if cid not in _HIDDEN_FROM_GUI]


def _resolve_source_and_provider_factories(
    cid: str, config: ConfigService
) -> tuple[Callable[..., Any], Callable[..., Any]] | None:
    """Return (make_source, make_provider) factories for *cid*, or ``None``
    when no source is registered / the provider can't be resolved.

    Shared behind ``_fetch_weekend_entries`` and ``get_calendar_year_events``
    (Sprint 40) — extracted once a second caller needed the exact same
    championship-config-source-provider resolution, rather than duplicated.
    Returns factories, not an already-constructed provider: callers decide
    how many times (and with which cache/refresh) to instantiate — e.g.
    ``_fetch_weekend_entries`` constructs a fresh one per year fetched.
    """
    from motorsport_calendar.config.models import ProviderConfig
    from motorsport_calendar.core.registry import registry
    from motorsport_calendar.core.source_registry import source_registry

    available = source_registry.list_for(cid)
    if not available:
        return None

    provider_cfg = config.providers.get(cid) or ProviderConfig()
    source_name = provider_cfg.source or available[0]

    try:
        make_source = source_registry.get(cid, source_name)
        make_provider = registry.get(cid)
    except KeyError:
        return None

    return make_source, make_provider


async def _fetch_weekend_entries(
    reference_now: datetime, *, refresh: bool = False
) -> list[WeekendEntry]:
    """Fetch every "Ce week-end" championship's events for *reference_now*'s
    year and the following one.

    Shared fetch pipeline behind both ``get_upcoming_weekend`` (Sprint 29)
    and ``get_dashboard_data`` (Sprint 39) — extracted once a second caller
    needed the exact same raw material, rather than duplicated. Same
    registries, same HttpCache as ``generate_calendar``. ``refresh=False``
    by default: relies on the existing cache TTL so opening these pages
    repeatedly does not hit the network every time — set ``refresh=True``
    (MC-002 P0-7) to force a re-download, bypassing the cache, e.g. from a
    manual "refresh" action in the GUI. Never raises — a failing
    championship/year is skipped, matching the CLI's partial-failure
    resilience rule.
    """
    from motorsport_calendar.cache import HttpCache
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.core.registry import registry
    from motorsport_calendar.core.source_registry import source_registry
    from motorsport_calendar.gui.upcoming_weekend import WEEKEND_CHAMPIONSHIP_IDS, WeekendEntry

    config = ConfigService()
    cache: HttpCache | None = None
    if config.cache.enabled:
        cache = HttpCache(cache_dir=config.cache.resolved_path, ttl=config.cache.ttl_seconds)

    registry.discover()
    source_registry.discover()

    entries: list[WeekendEntry] = []

    for cid in WEEKEND_CHAMPIONSHIP_IDS:
        resolved = _resolve_source_and_provider_factories(cid, config)
        if resolved is None:
            continue
        make_source, make_provider = resolved

        for year in (reference_now.year, reference_now.year + 1):
            source = make_source(cache, refresh)
            provider = make_provider(source)
            try:
                events = await provider.fetch_events(cid, year)
                entries.extend(WeekendEntry(championship_id=cid, event=e) for e in events)
            except Exception:  # one championship/year failing must not break the rest
                continue

    return entries


async def get_calendar_year_events(year: int, *, refresh: bool = False) -> dict[str, list[Event]]:
    """Fetch every registered championship's events for *year* — "Mon
    calendrier" (Sprint 40), turning the wizard's year/championship filters
    into a browsable calendar.

    Unlike ``_fetch_weekend_entries``, this is scoped to exactly one year
    (no year+1 lookahead — the user picked this year deliberately) and
    covers every registered championship (``registry.list_all()``), not
    only the "Ce week-end" subset, since the wizard's championship
    checkboxes already list every registered id.

    Never raises — a failing championship is simply absent from the
    result, matching the CLI's partial-failure resilience rule. Callers
    filter this dict locally per the user's checkbox selection (see
    ``gui/calendar_selection.py``) — toggling a checkbox never triggers a
    new fetch, only picking a different year does.

    Args:
        refresh: bypass the HTTP cache and re-download (MC-002 P0-7) —
            set from a manual "refresh" action in the GUI, ``False`` on
            every ordinary year-change fetch.
    """
    from motorsport_calendar.cache import HttpCache
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.core.registry import registry
    from motorsport_calendar.core.source_registry import source_registry

    config = ConfigService()
    cache: HttpCache | None = None
    if config.cache.enabled:
        cache = HttpCache(cache_dir=config.cache.resolved_path, ttl=config.cache.ttl_seconds)

    registry.discover()
    source_registry.discover()

    result: dict[str, list[Event]] = {}
    for cid in registry.list_all():
        resolved = _resolve_source_and_provider_factories(cid, config)
        if resolved is None:
            continue
        make_source, make_provider = resolved

        source = make_source(cache, refresh)
        provider = make_provider(source)
        try:
            events = await provider.fetch_events(cid, year)
            result[cid] = list(events)
        except Exception:  # one championship failing must not break the rest
            continue

    return result


async def get_upcoming_weekend(
    *, now: datetime | None = None, refresh: bool = False
) -> WeekendResult:
    """Find the next race weekend across the 17 "Ce week-end" championships.

    Never raises — a failing championship/year is skipped, matching the
    CLI's partial-failure resilience rule.

    Returns a ``upcoming_weekend.WeekendResult`` (found + display-ready
    cards, or not-found + a hint date for the next available weekend).
    Favorited championships (Sprint 44, ``FavoritesService``) are shown
    first among the returned cards.

    Args:
        refresh: bypass the HTTP cache and re-download (MC-002 P0-7) —
            forwarded to ``_fetch_weekend_entries``.
    """
    from motorsport_calendar.gui.favorites_service import FavoritesService
    from motorsport_calendar.gui.upcoming_weekend import find_upcoming_weekend

    reference_now = now or datetime.now(UTC)
    entries = await _fetch_weekend_entries(reference_now, refresh=refresh)
    favorite_ids = frozenset(FavoritesService().list())
    return find_upcoming_weekend(entries, now=reference_now, favorite_ids=favorite_ids)


async def get_dashboard_data(
    *, now: datetime | None = None, refresh: bool = False
) -> DashboardData:
    """Aggregate everything the Dashboard (Sprint 39, home page since
    Sprint 53) needs in one fetch pass.

    Reuses the exact same fetch pipeline as ``get_upcoming_weekend`` — no
    second, separate network round-trip for the season-wide stats; season
    totals are derived from the very same fetched events used to find the
    next weekend. Favorited championships (Sprint 44) are shown first
    within ``weekend.cards`` — same source, same sort as
    ``get_upcoming_weekend``.

    Sprint 53: also resolves the "État de Motorsport Calendar"/
    "Nouveautés" sections' data — every value comes from an existing
    service (``ProviderRegistry``, ``ConfigService``, ``FavoritesService``,
    ``check_for_update`` itself, ``motorsport_calendar.__version__``), no
    new service created. The update check runs concurrently with the
    weekend/season fetch (``asyncio.gather``, same "independent I/O, no
    reason to serialize" reasoning as Sprint 50's provider fetch) — it is
    also independently triggered by ``main_view.py``'s own startup dialog
    (Sprint 51, unchanged); calling the same stateless, side-effect-free
    ``check_for_update()`` from two call sites is reuse, not duplicated
    logic.

    Args:
        refresh: bypass the HTTP cache and re-download (MC-002 P0-7) —
            forwarded to ``_fetch_weekend_entries``. Never applies to
            ``check_for_update``, which has its own, unrelated cache-free
            manifest fetch.
    """
    import asyncio

    from motorsport_calendar import __version__
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.core.registry import registry
    from motorsport_calendar.gui.dashboard import build_dashboard_data
    from motorsport_calendar.gui.favorites_service import FavoritesService

    reference_now = now or datetime.now(UTC)
    entries, update = await asyncio.gather(
        _fetch_weekend_entries(reference_now, refresh=refresh),
        check_for_update(),
    )
    total_championships = len(registry.list_all())
    active_championships = len(registry.enabled(ConfigService().providers))
    favorite_ids = frozenset(FavoritesService().list())
    return build_dashboard_data(
        entries,
        total_championships=total_championships,
        now=reference_now,
        favorite_ids=favorite_ids,
        active_championships=active_championships,
        favorite_count=len(favorite_ids),
        current_version=__version__,
        update=update,
    )


async def generate_calendar(
    year: int,
    championship_ids: list[str],
    output_path: str,
    *,
    refresh: bool = False,
) -> dict[str, tuple[int, int] | str]:
    """Generate an ICS file for the selected championships.

    Mirrors the CLI ``generate`` pipeline without duplicating any logic.
    Returns a dict mapping each championship_id to either:
    - a tuple (event_count, session_count) on success
    - a str (error message) on failure

    Does NOT call asyncio.run() — intended to be awaited directly.
    """
    if not championship_ids:
        return {}

    import asyncio

    import httpx

    from motorsport_calendar.cache import HttpCache
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.config.models import ProviderConfig
    from motorsport_calendar.core.registry import registry
    from motorsport_calendar.core.source_registry import source_registry
    from motorsport_calendar.exporters.ics import IcsExporter

    config = ConfigService()

    cache: HttpCache | None = None
    if config.cache.enabled:
        cache = HttpCache(
            cache_dir=config.cache.resolved_path,
            ttl=config.cache.ttl_seconds,
        )

    registry.discover()
    source_registry.discover()

    provider_list: list[tuple[str, Any]] = []
    results: dict[str, tuple[int, int] | str] = {}

    for cid in championship_ids:
        provider_cfg = config.providers.get(cid) or ProviderConfig()
        source_name = provider_cfg.source
        if not source_name:
            available = source_registry.list_for(cid)
            source_name = available[0] if available else ""

        if not source_name:
            results[cid] = "aucune source disponible"
            continue

        try:
            make_source = source_registry.get(cid, source_name)
            make_provider = registry.get(cid)
        except KeyError as exc:
            results[cid] = str(exc)
            continue

        source = make_source(cache, refresh)
        provider_list.append((cid, make_provider(source)))

    async def _fetch_one(cid: str, provider: Any) -> tuple[str, list[Any], str | None]:
        try:
            events = await provider.fetch_events(cid, year)
            return (cid, list(events), None)
        except NotImplementedError:
            return (cid, [], "source non implémentée")
        except httpx.HTTPStatusError as exc:
            return (cid, [], f"HTTP {exc.response.status_code}")
        except httpx.TimeoutException:
            return (cid, [], "timeout")
        except Exception as exc:
            return (cid, [], str(exc))

    # Sprint 50 — même optimisation que cli.py::generate : chaque provider
    # interroge une API distante indépendante, les récupérer en parallèle
    # (asyncio.gather, qui préserve l'ordre de provider_list) réduit le temps
    # total au provider le plus lent plutôt qu'à leur somme, sans changer les
    # résultats ni l'ordre des événements dans le fichier ICS final.
    all_events: list[Any] = []
    fetch_results = await asyncio.gather(
        *(_fetch_one(cid, provider) for cid, provider in provider_list)
    )
    for cid, events, error in fetch_results:
        if error is not None:
            results[cid] = error
            continue
        all_events.extend(events)
        session_count = sum(len(e.sessions) for e in events)
        results[cid] = (len(events), session_count)

    if all_events:
        all_events.sort(
            key=lambda e: min(
                (s.start_datetime for s in e.sessions),
                default=datetime.max.replace(tzinfo=UTC),
            )
        )
        # Sprint 52 — the Préférences page lets a GUI user override the
        # VALARM reminder without touching config.yaml; falls back to
        # config.ics.alarm_minutes when the preference was never saved
        # (fresh install) or explicitly reset. The CLI (cli.py::generate)
        # has no such preferences file and is intentionally unaffected —
        # it always reads only config.yaml, as before.
        from motorsport_calendar.gui.preferences import load_preferences

        alarm_minutes = load_preferences().get("ics_alarm_minutes", config.ics.alarm_minutes)
        IcsExporter(alarm_minutes=alarm_minutes).export(all_events, Path(output_path))

    return results


async def check_for_update(
    *,
    current_version: str | None = None,
    manifest_url: str | None = None,
) -> UpdateCheckResult:
    """Check whether a newer Motorsport Calendar version is available.

    All the network/comparison logic lives in
    ``gui/update_service.py::UpdateService`` — this function only resolves
    the two inputs it needs (current version, manifest URL) from their
    respective sources before delegating, same "controller wires business
    logic to config/preferences, main_view.py only renders the result"
    role as ``generate_calendar``/``get_dashboard_data``.

    Args:
        current_version: Overrides ``motorsport_calendar.__version__`` —
            for tests only; ``main_view.py`` never passes this.
        manifest_url: Overrides ``ConfigService().update.manifest_url`` —
            for tests only; ``main_view.py`` never passes this.

    Returns:
        ``UpdateCheckResult(update_available=False, ...)`` without any
        network call when the ``update_check_enabled`` preference is off
        or no manifest URL is configured — checking is opt-out, not
        forced, and never crashes app startup either way (see
        ``UpdateService.check_for_update``, which never raises).
    """
    from motorsport_calendar import __version__
    from motorsport_calendar.config import ConfigService
    from motorsport_calendar.gui.preferences import load_preferences
    from motorsport_calendar.gui.update_service import UpdateCheckResult, UpdateService

    resolved_version = current_version if current_version is not None else __version__

    if not load_preferences().get("update_check_enabled", True):
        return UpdateCheckResult(update_available=False, current_version=resolved_version)

    resolved_url = manifest_url if manifest_url is not None else ConfigService().update.manifest_url
    if not resolved_url:
        return UpdateCheckResult(update_available=False, current_version=resolved_version)

    return await UpdateService(resolved_url, resolved_version).check_for_update()


def prepare_notifications(
    year_events: dict[str, list[Event]],
    *,
    now: datetime | None = None,
    favorite_ids: frozenset[str] = frozenset(),
) -> int:
    """ "Au démarrage, si les notifications sont activées, préparer les
    prochaines notifications" (Sprint 56 brief, verbatim). Same
    "controller wires business logic to config/preferences, main_view.py
    only calls the result" role as ``check_for_update`` — the
    ``notifications_enabled`` preference gate lives here, exactly where
    ``update_check_enabled``'s gate already lives for updates, not
    duplicated inline in ``main_view.py``.

    Args:
        year_events: registry championship id -> its events for the
            currently loaded year — the same dict ``main_view.py`` already
            holds (``controller.get_calendar_year_events``).
        now: reference instant — defaults to ``datetime.now(UTC)``; only
            ever overridden by tests, same convention as
            ``get_dashboard_data``/``get_upcoming_weekend``.
        favorite_ids: forwarded to ``NotificationService.
            compute_notifications`` for its "favoris uniquement" filter —
            ``main_view.py`` passes ``FavoritesService().list()``.

    Returns:
        How many notifications were actually shown by the system layer —
        always ``0`` today, since no ``SystemNotifier`` implementation
        exists yet (see ``gui/system_notifications.py``). Never raises:
        an empty ``year_events``, a disabled preference, and an
        unavailable system notifier are all ordinary, silently-handled
        outcomes, never errors.
    """
    from motorsport_calendar.gui.notification_service import NotificationService
    from motorsport_calendar.gui.system_notifications import notify_all

    service = NotificationService()
    if not service.enabled:
        return 0

    notifications = service.compute_notifications(
        year_events, now=now or datetime.now(UTC), favorite_ids=favorite_ids
    )
    return notify_all(notifications)
