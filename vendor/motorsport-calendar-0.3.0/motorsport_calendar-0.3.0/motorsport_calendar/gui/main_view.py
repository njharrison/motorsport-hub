"""Main view — Flet navigation shell for Motorsport Calendar.

Requires flet>=0.80:  pip install motorsport-calendar[gui]

Responsibilities:
- Page setup, services, window sizing
- NavigationRail (8 destinations)
- Shared state + handlers for "Mon calendrier"
- Delegates layout to motorsport_calendar.gui.views.*
- Delegates visual tokens (colors, spacing, radii) to motorsport_calendar.gui.theme

Design rules:
- All user-visible text comes from strings.py (STRINGS singleton).
- All colors/spacing/radii come from theme.py — nothing hardcoded here.
- Championship labels come from display_names.py (get_display_name).
- Championship groups come from categories.py (get_groups_for).
- Preferences file I/O uses preferences.py.
- Each view is an independent ft.Control; swapped on nav change without rebuilding.
- "Mon calendrier" is one exception (Sprint 43 — no more wizard steps,
  but still a single page rebuilt in place): its container's `.content` is
  rebuilt on every selection/year/category-expand change (see
  `_refresh_calendar_view`), since the championships/summary/explorer all
  derive from the same mutable state.
- Ce week-end is the other exception (Sprint 29): it starts in the loading
  state and its container's `.content` is replaced once when the background
  fetch (`_load_weekend`) resolves — never re-fetched on every tab visit.

Sprint 54 (Beta UX recette) — visual-consistency-only cleanups, no
behavior change: the success dialog's title now uses a themed
``ft.Icon(CHECK_CIRCLE)`` instead of a hardcoded "✅" emoji (every other
dialog/page title in this app uses Material icons via ``ft.Icon``, never
inline emoji); 2 dialog content columns' ``spacing=4`` now read
``theme.Spacing.XXS`` (same value, no longer a bare number bypassing the
Design System scale); the "5 destinations" comment above was stale
(7 since Sprint 45's Recherche/Sprint 44's Favoris).

Sprint 55 (Recherche interactive) — "Recherche" results become
clickable, resolved through 2 new shared helpers extracted from
existing per-dialog closures rather than duplicated at a second call
site: ``_open_event_details(championship_id, event_uid)`` (used by both
the season explorer's row click, Sprint 42, and a search event result
click) and ``_open_circuit_details(circuit_key)`` (used by both the
event details dialog's circuit-name click, Sprint 47, and a search
circuit result click). A search championship result click navigates to
"Mon calendrier" (``_navigate_to("calendar")``, Sprint 53's own
navigation) — the closest existing destination, since no dedicated
per-championship page exists; it never mutates ``state.
selected_championships``, so clicking a search result to *look at* a
championship never silently changes what the user has picked for
generation.

Sprint 56 (Notifications natives) — ``_prepare_system_notifications()``
calls ``controller.prepare_notifications(year_events, favorite_ids=...)``
once at launch and again on every year_events refresh (same trigger as the
search/circuit index rebuilds it sits next to in ``_load_year_events``).
main_view.py never imports ``gui/system_notifications.py`` directly, nor
does it read the ``notifications_enabled`` preference for this purpose —
both live in ``controller.prepare_notifications`` (same "controller wires
business logic to preferences, main_view.py only calls the result" split
as ``check_for_update``), so main_view.py stays exactly what it already
is: a Flet shell, never a second place gate/dispatch logic could drift
from the tested one.

Sprint 57 (Préparation Beta — nettoyage) — the local ``_make_release_opener``
factory (Sprint 51/53's "open a release URL, with a Windows subprocess
fallback") is gone: it was the 2nd independent copy of the exact same
logic ``views/about.py``'s GitHub link already had since Sprint 26. Both
call sites now use the shared ``gui/url_opener.py::make_url_opener``
instead, alongside a 3rd real call site added this sprint ("Soutenir le
projet"'s GitHub Discussions/Issues buttons) — one implementation, three
callers, never independently reimplemented again.

Sprint 57 also adds the 8th nav destination, "Soutenir le projet"
(``views/support.py``) — purely informative (no vote/donation system,
per the brief), and IMSA/WorldSBK no longer appear in ``championships``
(``controller.list_championships()`` now filters them — see that
function's own docstring) since neither has a reliable source yet; both
remain fully registered in ``ProviderRegistry``, this is a GUI-exposure
decision only.
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING

import flet as ft

from motorsport_calendar.gui import theme
from motorsport_calendar.gui.calendar_selection import build_selection_summary
from motorsport_calendar.gui.categories import get_groups_for
from motorsport_calendar.gui.circuit_service import CircuitService
from motorsport_calendar.gui.components.championship_card import build_championship_card
from motorsport_calendar.gui.components.championship_selector import (
    ChampionshipButtonData,
    ChampionshipCategoryData,
)
from motorsport_calendar.gui.controller import (
    check_for_update,
    generate_calendar,
    get_calendar_year_events,
    get_dashboard_data,
    get_upcoming_weekend,
    list_championships,
    prepare_notifications,
)
from motorsport_calendar.gui.display_names import DEFAULT_SELECTED, get_display_name
from motorsport_calendar.gui.event_details import build_event_details
from motorsport_calendar.gui.favorites_service import FavoritesService
from motorsport_calendar.gui.models import (
    DEFAULT_YEAR_SENTINEL,
    GenerateState,
    resolve_default_year,
)
from motorsport_calendar.gui.preferences import load_preferences, save_preferences
from motorsport_calendar.gui.search_service import SearchService
from motorsport_calendar.gui.season_explorer import build_season_explorer
from motorsport_calendar.gui.strings import STRINGS, plural
from motorsport_calendar.gui.url_opener import make_url_opener
from motorsport_calendar.gui.views.about import build_about_view
from motorsport_calendar.gui.views.calendar import CalendarViewControls, build_calendar_view
from motorsport_calendar.gui.views.dashboard import build_dashboard_view
from motorsport_calendar.gui.views.favorites import build_favorites_view
from motorsport_calendar.gui.views.preferences import (
    PreferencesViewControls,
    build_preferences_view,
)
from motorsport_calendar.gui.views.search import build_search_view
from motorsport_calendar.gui.views.support import build_support_view
from motorsport_calendar.gui.views.weekend import build_weekend_view

if TYPE_CHECKING:
    from motorsport_calendar.gui.calendar_selection import SelectionSummary
    from motorsport_calendar.gui.circuit_service import CircuitProfile
    from motorsport_calendar.gui.event_details import EventDetails
    from motorsport_calendar.gui.search_service import SearchResultItem
    from motorsport_calendar.gui.season_explorer import SeasonEventRow, SeasonMonthGroup
    from motorsport_calendar.gui.update_service import UpdateCheckResult
    from motorsport_calendar.models import Event


def _open_folder(path: str) -> None:
    """Open the folder containing *path* in the system file manager."""
    folder = str(Path(path).parent)
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", folder])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except OSError:
        pass


async def build_main_view(page: ft.Page) -> None:
    """Build and attach the navigation shell + all views to the Flet page."""
    page.title = STRINGS.app_title
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = theme.Colors.BACKGROUND
    page.padding = 0
    page.window.icon = "icon.png"  # Sprint 49 — Brand Set v1.0, served from gui/assets/
    page.window.min_width = 560
    page.window.min_height = 580
    page.window.width = 700
    page.window.height = 720

    # =========================================================================
    # SERVICES
    # =========================================================================

    file_picker = ft.FilePicker()
    url_launcher = ft.UrlLauncher()
    page.services.extend([file_picker, url_launcher])

    # =========================================================================
    # PREFERENCES + STATE
    # =========================================================================

    prefs = load_preferences()
    favorites_service = FavoritesService()
    search_service = SearchService()
    circuit_service = CircuitService()

    def _save_prefs() -> None:
        # Sprint 44: read-modify-write, never a fresh literal — this file
        # is centralized (gui/preferences.py's own docstring) and shared
        # with FavoritesService's own "favorite_championships" key; a
        # fresh literal here would silently wipe whatever favorites were
        # last saved.
        current = load_preferences()
        current["selected_championships"] = list(state.selected_championships)
        current["last_output_dir"] = prefs.get("last_output_dir", "")
        save_preferences(current)

    # "Mon calendrier" pre-selects favorites automatically (Sprint 44) —
    # falls back to the previously remembered selection (or the hardcoded
    # first-launch default) only when the user has no favorites yet.
    initial_selection = favorites_service.list() or list(
        prefs.get("selected_championships", DEFAULT_SELECTED)
    )

    state = GenerateState(
        # Sprint 52 — "année par défaut" preference: "current" (default)
        # always resolves to today's year (never goes stale), or a
        # literal year the user pinned on the Préférences page.
        year=resolve_default_year(prefs.get("default_year", DEFAULT_YEAR_SENTINEL)),
        selected_championships=initial_selection,
    )

    # =========================================================================
    # CALENDAR CONTROLS (state + handlers stay here; layout in views/)
    # =========================================================================

    calendar_container = ft.Container(expand=True)

    # --- Selection summary (Sprint 40) — events/sessions/period for the
    # current year + championship selection. `None` = still fetching the
    # current year's events; any dict (even empty) = ready to summarize.
    # Toggling a championship button never re-fetches — only picking a
    # different year does (see `on_year_change`/`_load_year_events`).
    year_events: dict[str, list[Event]] | None = None

    def _current_selection_summary() -> SelectionSummary | None:
        # Sprint 43: nothing selected -> the zeroed summary immediately,
        # no need to wait for year_events (build_selection_summary already
        # returns the same zeroed result regardless of its content when
        # selected_championships is empty).
        if not state.selected_championships:
            return build_selection_summary({}, [])
        if year_events is None:
            return None
        return build_selection_summary(year_events, state.selected_championships)

    def _current_season_groups() -> tuple[SeasonMonthGroup, ...] | None:
        # Sprint 43: the season explorer is only shown once >= 1
        # championship is selected — go straight to the EmptyState (an
        # empty tuple) rather than a loading spinner for nothing to wait on.
        if not state.selected_championships:
            return ()
        if year_events is None:
            return None
        return build_season_explorer(year_events, state.selected_championships)

    def _open_event_details(championship_id: str, event_uid: str) -> None:
        """Look an event's identity back up in year_events and open its
        "fiche événement" (Sprint 42) — the one place that resolves
        identity-only data (``SeasonEventRow``, Sprint 42; ``SearchResultItem``,
        Sprint 55) back into a real ``Event``, so the season explorer's own
        row click and a "Recherche" event result click never each implement
        this lookup separately."""
        if year_events is None:
            return  # stale click from a view built before the fetch resolved
        for event in year_events.get(championship_id, []):
            if event.event_uid == event_uid:
                _show_event_details_dialog(build_event_details(championship_id, event))
                return

    def _on_event_row_click(row: SeasonEventRow) -> None:
        _open_event_details(row.championship_id, row.event_uid)

    def _prepare_system_notifications() -> None:
        """Sprint 56 — "au démarrage, si les notifications sont activées,
        préparer les prochaines notifications". Called once at launch and
        again whenever year_events refreshes (year change), same trigger
        as the search/circuit index rebuilds right above. All the actual
        logic (the ``notifications_enabled`` gate, computing, dispatching)
        lives in ``controller.prepare_notifications`` — same "controller
        wires business logic to preferences, main_view.py only calls the
        result" split as ``_check_for_update``/``check_for_update``; this
        function only supplies the data main_view.py alone holds
        (year_events, the favorites list)."""
        if year_events is None:
            return
        prepare_notifications(year_events, favorite_ids=frozenset(favorites_service.list()))

    async def _load_year_events(year: int, *, refresh: bool = False) -> None:
        nonlocal year_events
        try:
            fetched = await get_calendar_year_events(year, refresh=refresh)
        except Exception:  # never crash the app on this background fetch
            return
        if year != state.year:
            return  # stale response for a year the user has since left
        year_events = fetched
        _refresh_calendar_view()
        # Sprint 45: the search index is only as fresh as year_events —
        # rebuild it whenever a new year resolves, then re-render any
        # search currently on screen so results never point at stale data.
        search_service.build_index(championships, year_events)
        _refresh_search_view()
        # Sprint 47: same rationale — the circuit database is only as
        # fresh as year_events, rebuilt every time a new year resolves.
        circuit_service.build_index(year_events)
        # Sprint 56: same rationale again — notifications are only as
        # fresh as year_events.
        _prepare_system_notifications()

    # --- Year selector — secondary, top-right control (Sprint 43) ---
    current_year = date.today().year

    def on_year_change(e: ft.ControlEvent) -> None:
        nonlocal year_events
        state.year = int(e.control.value)
        year_events = None  # show the loading state immediately
        _refresh_calendar_view()
        page.calendar_year_load_task = asyncio.create_task(_load_year_events(state.year))

    year_dropdown = ft.Dropdown(
        label=STRINGS.season_label,
        value=str(current_year),
        options=[ft.dropdown.Option(str(y)) for y in range(current_year - 5, current_year + 6)],
        width=160,
        dense=True,
        on_select=on_year_change,
    )

    async def _on_calendar_refresh_click(e: ft.ControlEvent) -> None:
        # MC-002 (P0-7) — bypass the HTTP cache for the currently browsed
        # year; same loading-state pattern as on_year_change above, so the
        # user gets the same immediate feedback for either action.
        nonlocal year_events
        year_events = None
        _refresh_calendar_view()
        await _load_year_events(state.year, refresh=True)

    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip=STRINGS.refresh_tooltip,
        on_click=_on_calendar_refresh_click,
    )

    # --- Championships — entry point of the page (Sprint 43) ---
    championships = list_championships()

    # Which category accordions are expanded — persisted here (main_view.py
    # rebuilds CalendarViewControls from scratch on every change, so this
    # can't live on the ExpansionTile controls themselves). Seeded with any
    # category that already has a selected championship (e.g. the
    # DEFAULT_SELECTED preselection), so the user's own selection is
    # visible without an extra click on first launch.
    expanded_categories: set[str] = set()
    for _group, _ids in get_groups_for(championships):
        if any(cid in state.selected_championships for cid in _ids):
            expanded_categories.add(_group.category.value)

    def _on_championship_click(cid: str) -> None:
        if cid in state.selected_championships:
            state.selected_championships.remove(cid)
        else:
            state.selected_championships.append(cid)
        _save_prefs()
        _refresh_calendar_view()

    def _on_category_toggle(category_id: str, expanded: bool) -> None:
        if expanded:
            expanded_categories.add(category_id)
        else:
            expanded_categories.discard(category_id)

    def _current_category_groups() -> list[ChampionshipCategoryData]:
        return [
            ChampionshipCategoryData(
                category_id=group.category.value,
                label=f"{group.emoji}  {group.label}",
                expanded=group.category.value in expanded_categories,
                options=tuple(
                    ChampionshipButtonData(
                        championship_id=cid,
                        display_name=get_display_name(cid),
                        selected=cid in state.selected_championships,
                    )
                    for cid in ids
                ),
            )
            for group, ids in get_groups_for(championships)
        ]

    # --- Output path (fixed footer) ---
    output_field = ft.TextField(
        label=STRINGS.output_label,
        hint_text=STRINGS.output_hint,
        read_only=True,
        expand=True,
        dense=True,
    )

    async def on_browse_click(e: ft.ControlEvent) -> None:
        last_dir = prefs.get("last_output_dir") or None
        result = await file_picker.save_file(
            dialog_title=STRINGS.save_dialog_title,
            file_name=f"motorsport-calendar-{state.year}.ics",
            initial_directory=last_dir,
            allowed_extensions=["ics"],
        )
        if result:
            path = result if result.endswith(".ics") else f"{result}.ics"
            state.output_path = path
            output_field.value = path
            prefs["last_output_dir"] = str(Path(path).parent)
            _save_prefs()
            _refresh_calendar_view()

    browse_btn = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        tooltip=STRINGS.browse_tooltip,
        on_click=on_browse_click,
    )

    # --- Generate button & progress (step 4) ---
    progress_ring = ft.ProgressRing(width=22, height=22, visible=False)
    error_text = ft.Text(
        value="", size=theme.FontSize.BODY, color=theme.Colors.ERROR, selectable=True
    )

    generate_btn = ft.Button(
        content=STRINGS.generate_btn,
        icon=ft.Icons.CALENDAR_MONTH,
        disabled=True,
        on_click=None,
        style=theme.button_style("cta"),
    )

    def _refresh_generate_btn() -> None:
        generate_btn.disabled = not state.is_ready()

    def _current_calendar_controls() -> CalendarViewControls:
        return CalendarViewControls(
            year_dropdown=year_dropdown,
            refresh_btn=refresh_btn,
            output_field=output_field,
            browse_btn=browse_btn,
            generate_btn=generate_btn,
            progress_ring=progress_ring,
            error_text=error_text,
            category_groups=_current_category_groups(),
            on_championship_click=_on_championship_click,
            on_category_toggle=_on_category_toggle,
            selection_summary=_current_selection_summary(),
            selected_count=len(state.selected_championships),
            season_groups=_current_season_groups(),
            on_event_click=_on_event_row_click,
        )

    def _refresh_calendar_view() -> None:
        _refresh_generate_btn()
        calendar_container.content = build_calendar_view(_current_calendar_controls())
        page.update()

    # =========================================================================
    # FAVORITES CONTROLS (Sprint 44 — state + handlers stay here; layout in views/)
    # =========================================================================

    favorites_container = ft.Container(expand=True)

    # Same "remember expanded categories across rebuilds" pattern as the
    # calendar's own `expanded_categories` — a separate tracker, since
    # "Mon calendrier" and "Mes favoris" are independent pages that may
    # reasonably have different categories open at once.
    favorites_expanded_categories: set[str] = set()
    for _group, _ids in get_groups_for(championships):
        if any(cid in favorites_service.list() for cid in _ids):
            favorites_expanded_categories.add(_group.category.value)

    def _current_favorites_groups() -> list[ChampionshipCategoryData]:
        favorite_ids = favorites_service.list()
        return [
            ChampionshipCategoryData(
                category_id=group.category.value,
                label=f"{group.emoji}  {group.label}",
                expanded=group.category.value in favorites_expanded_categories,
                options=tuple(
                    ChampionshipButtonData(
                        championship_id=cid,
                        display_name=get_display_name(cid),
                        selected=cid in favorite_ids,
                    )
                    for cid in ids
                ),
            )
            for group, ids in get_groups_for(championships)
        ]

    def _refresh_favorites_view() -> None:
        favorites_container.content = build_favorites_view(
            _current_favorites_groups(),
            len(favorites_service.list()),
            _on_favorite_click,
            _on_favorites_category_toggle,
        )
        page.update()

    def _on_favorite_click(cid: str) -> None:
        favorites_service.toggle(cid)
        _refresh_favorites_view()
        # Dashboard/"Ce week-end" show favorites first (Sprint 44) — both
        # already-loaded pages need to re-render with the new order. This
        # re-fetches rather than re-sorting the already-fetched data
        # locally, so there is exactly one "favorites first" implementation
        # (upcoming_weekend.py) — the existing HttpCache TTL means this is
        # a cache hit, not a real network round-trip.
        page.weekend_reload_task = asyncio.create_task(_load_weekend())
        page.dashboard_reload_task = asyncio.create_task(_load_dashboard())

    def _on_favorites_category_toggle(category_id: str, expanded: bool) -> None:
        if expanded:
            favorites_expanded_categories.add(category_id)
        else:
            favorites_expanded_categories.discard(category_id)

    # =========================================================================
    # SEARCH CONTROLS (Sprint 45 — state + handlers stay here; layout in views/)
    # =========================================================================

    search_container = ft.Container(expand=True)
    current_search_query = ""

    def _on_search_championship_click(item: SearchResultItem) -> None:
        """Sprint 55: no dedicated per-championship page exists — "Mon
        calendrier" is the closest existing destination (browse a
        championship's own events), same reuse-only navigation as the
        Dashboard's "Accès rapides" cards (Sprint 53) — never a new page,
        never a selection side-effect on the user's generation choices."""
        if item.championship_id is not None:
            _navigate_to("calendar")

    def _on_search_event_click(item: SearchResultItem) -> None:
        """Sprint 55: reuses the exact same identity -> Event resolution
        as the season explorer's own row click (Sprint 42)."""
        if item.championship_id is not None and item.event_uid is not None:
            _open_event_details(item.championship_id, item.event_uid)

    def _on_search_circuit_click(item: SearchResultItem) -> None:
        """Sprint 55: reuses the exact same key -> CircuitProfile
        resolution as the event details dialog's own circuit link
        (Sprint 47)."""
        if item.circuit_key is not None:
            _open_circuit_details(item.circuit_key)

    def _refresh_search_view() -> None:
        results = search_service.search(current_search_query)
        search_container.content = build_search_view(
            search_field,
            results,
            bool(current_search_query.strip()),
            on_championship_click=_on_search_championship_click,
            on_event_click=_on_search_event_click,
            on_circuit_click=_on_search_circuit_click,
        )
        page.update()

    def _on_search_query_change(e: ft.ControlEvent) -> None:
        nonlocal current_search_query
        current_search_query = e.control.value or ""
        _refresh_search_view()

    search_field = ft.TextField(
        hint_text=STRINGS.search_hint,
        dense=True,
        on_change=_on_search_query_change,
    )

    def _open_circuit_details(circuit_key: str) -> None:
        """Resolve a circuit key through CircuitService and open its
        "fiche Circuit" (Sprint 47) — the one place that turns a bare key
        into a dialog, so the event details dialog's own circuit-name
        click and a "Recherche" circuit result click (Sprint 55) never
        each implement this lookup separately. A stale/unknown key (index
        not yet rebuilt) is a silent no-op, never a crash."""
        profile = circuit_service.get_circuit(circuit_key)
        if profile is not None:
            _show_circuit_details_dialog(profile)

    # --- Event details dialog (Sprint 42 — "fiche événement") ---
    def _show_event_details_dialog(details: EventDetails) -> None:
        def on_close(e: ft.ControlEvent) -> None:
            page.pop_dialog()

        def on_circuit_click() -> None:
            """Sprint 47: the circuit name on the reused ChampionshipCard
            becomes clickable — ``details.circuit_key`` is ``None`` in
            lockstep with the card's own ``circuit_name`` (nothing to
            click when that line is hidden), so this is only ever wired
            when there is something to open."""
            if details.circuit_key is not None:
                _open_circuit_details(details.circuit_key)

        content_controls: list[ft.Control] = []
        if details.date_label is not None:
            content_controls.append(
                ft.Text(
                    details.date_label,
                    size=theme.FontSize.BODY,
                    weight=ft.FontWeight.W_500,
                    color=theme.Colors.TEXT_SECONDARY,
                )
            )
        # Reuses ChampionshipCard as-is (Sprint 30) for
        # championship/event/circuit/country/sessions — this dialog adds
        # only the date_label line above it, never redraws the card itself.
        # Sprint 47: on_circuit_click is only wired here — every other
        # ChampionshipCard consumer (Ce week-end, Dashboard, Favoris)
        # keeps its plain, non-interactive circuit line unchanged.
        content_controls.append(
            build_championship_card(details.card, on_circuit_click=on_circuit_click)
        )

        dialog = ft.AlertDialog(
            title=ft.Text(
                STRINGS.event_details_title,
                size=theme.FontSize.HEADLINE,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=content_controls,
                    spacing=theme.Spacing.SM,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
            ),
            actions=[ft.Button(content=STRINGS.close_btn, on_click=on_close)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    # --- Circuit details dialog (Sprint 47 — "fiche Circuit") ---
    def _show_circuit_details_dialog(profile: CircuitProfile) -> None:
        def on_close(e: ft.ControlEvent) -> None:
            page.pop_dialog()

        content_controls: list[ft.Control] = [
            ft.Text(profile.name, size=theme.FontSize.HEADLINE, weight=ft.FontWeight.BOLD),
        ]
        if profile.country is not None:
            content_controls.append(
                ft.Text(
                    profile.country,
                    size=theme.FontSize.BODY,
                    color=theme.Colors.TEXT_SECONDARY,
                )
            )
        content_controls.append(ft.Divider(height=theme.Spacing.SM))

        content_controls.append(
            ft.Text(
                STRINGS.circuit_championships_count.format(
                    n=profile.championship_count, s=plural(profile.championship_count)
                ),
                size=theme.FontSize.LABEL,
                weight=ft.FontWeight.BOLD,
            )
        )
        content_controls.append(
            ft.Row(
                [theme.chip(name) for name in profile.championship_names],
                spacing=theme.Spacing.XXS,
                wrap=True,
            )
        )
        content_controls.append(ft.Divider(height=theme.Spacing.SM))

        content_controls.append(
            ft.Text(
                STRINGS.circuit_section_history,
                size=theme.FontSize.LABEL,
                weight=ft.FontWeight.BOLD,
            )
        )
        for entry in profile.events:
            content_controls.append(
                ft.Row(
                    [
                        ft.Text(f"{entry.season} — {entry.event_name}", size=theme.FontSize.SMALL),
                        ft.Text(
                            entry.championship_name,
                            size=theme.FontSize.SMALL,
                            color=theme.Colors.TEXT_MUTED,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        content_controls.append(ft.Divider(height=theme.Spacing.SM))

        content_controls.append(
            ft.Text(
                STRINGS.circuit_events_count.format(
                    n=profile.total_events, s=plural(profile.total_events)
                ),
                size=theme.FontSize.BODY,
                weight=ft.FontWeight.W_500,
            )
        )

        dialog = ft.AlertDialog(
            title=ft.Text(
                STRINGS.circuit_details_title,
                size=theme.FontSize.HEADLINE,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=content_controls,
                    spacing=theme.Spacing.SM,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=400,
            ),
            actions=[ft.Button(content=STRINGS.close_btn, on_click=on_close)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    # --- Success dialog ---
    def _show_success_dialog(
        total_events: int,
        total_sessions: int,
        output_path: str,
        details: list[str],
    ) -> None:
        ev_s = plural(total_events)
        sess_s = plural(total_sessions)

        def on_open_folder(e: ft.ControlEvent) -> None:
            _open_folder(output_path)

        def on_close(e: ft.ControlEvent) -> None:
            page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE, size=theme.IconSize.LG, color=theme.Colors.SUCCESS
                    ),
                    ft.Text(
                        STRINGS.success_title,
                        size=theme.FontSize.HEADLINE,
                        weight=ft.FontWeight.BOLD,
                        color=theme.Colors.SUCCESS,
                    ),
                ],
                spacing=theme.Spacing.XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"{total_events} événement{ev_s}  ·  {total_sessions} session{sess_s}",
                            size=theme.FontSize.SUBTITLE,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Divider(height=theme.Spacing.XS),
                        ft.Text(
                            STRINGS.success_saved_at,
                            size=theme.FontSize.SMALL,
                            color=theme.Colors.TEXT_SECONDARY,
                        ),
                        ft.Text(
                            output_path,
                            size=theme.FontSize.CAPTION,
                            selectable=True,
                            color=theme.Colors.TEXT_MUTED,
                        ),
                        ft.Divider(height=theme.Spacing.XS),
                        ft.Text(
                            "\n".join(details),
                            size=theme.FontSize.SMALL,
                            color=theme.Colors.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=theme.Spacing.XXS,
                ),
                width=400,
            ),
            actions=[
                ft.Button(
                    content=STRINGS.open_folder_btn,
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=on_open_folder,
                ),
                ft.Button(content=STRINGS.close_btn, on_click=on_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    # --- Update available dialog (Sprint 51) ---
    def _show_update_dialog(result: UpdateCheckResult) -> None:
        """Render an ``UpdateCheckResult`` the view never built itself —
        all fetching/parsing/version-comparison logic lives in
        ``gui/update_service.py``/``gui/controller.py::check_for_update``;
        this function only displays the result it's handed. Never
        downloads, installs, or restarts anything — the single action
        available is opening the release URL in the system browser."""
        manifest = result.manifest
        if manifest is None:  # defensive — callers only reach here when set
            return

        on_view_release = make_url_opener(url_launcher, manifest.url)

        def on_close(e: ft.ControlEvent) -> None:
            page.pop_dialog()

        content_controls: list[ft.Control] = [
            ft.Text(manifest.title, size=theme.FontSize.SUBTITLE, weight=ft.FontWeight.W_500),
            ft.Divider(height=theme.Spacing.XS),
            ft.Row(
                [
                    ft.Text(
                        STRINGS.update_current_version,
                        size=theme.FontSize.SMALL,
                        color=theme.Colors.TEXT_SECONDARY,
                    ),
                    ft.Text(result.current_version, size=theme.FontSize.SMALL),
                ],
                spacing=theme.Spacing.XXS,
            ),
            ft.Row(
                [
                    ft.Text(
                        STRINGS.update_new_version,
                        size=theme.FontSize.SMALL,
                        color=theme.Colors.TEXT_SECONDARY,
                    ),
                    ft.Text(
                        manifest.version,
                        size=theme.FontSize.SMALL,
                        weight=ft.FontWeight.BOLD,
                        color=theme.Colors.PRIMARY,
                    ),
                ],
                spacing=theme.Spacing.XXS,
            ),
            ft.Divider(height=theme.Spacing.XS),
            ft.Text(
                manifest.summary,
                size=theme.FontSize.SMALL,
                color=theme.Colors.TEXT_SECONDARY,
            ),
        ]
        if manifest.mandatory:
            content_controls.append(
                ft.Text(
                    STRINGS.update_mandatory_badge,
                    size=theme.FontSize.CAPTION,
                    weight=ft.FontWeight.BOLD,
                    color=theme.Colors.WARNING,
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text(
                STRINGS.update_title,
                size=theme.FontSize.HEADLINE,
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Container(
                content=ft.Column(controls=content_controls, spacing=theme.Spacing.XXS),
                width=400,
            ),
            actions=[
                ft.Button(
                    content=STRINGS.update_view_btn,
                    icon=ft.Icons.OPEN_IN_NEW,
                    on_click=on_view_release,
                ),
                ft.Button(content=STRINGS.close_btn, on_click=on_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    async def _check_for_update() -> None:
        """Fetch once per app launch — same "background task, never
        blocks the UI" pattern as ``_load_weekend``/``_load_dashboard``.
        Silently does nothing if disabled, unconfigured, or unreachable
        (``UpdateService.check_for_update`` never raises); this wrapper's
        own ``except`` is only a last-resort safety net."""
        try:
            result = await check_for_update()
        except Exception:  # never crash the app on this background fetch
            return
        if result.update_available and result.manifest is not None:
            _show_update_dialog(result)

    # --- Generate handler ---
    async def on_generate_click(e: ft.ControlEvent) -> None:
        if not state.is_ready():
            return

        state.is_generating = True
        generate_btn.disabled = True
        progress_ring.visible = True
        error_text.value = STRINGS.generating_status
        error_text.color = theme.Colors.TEXT_SECONDARY
        page.update()

        try:
            results = await generate_calendar(
                year=state.year,
                championship_ids=list(state.selected_championships),
                output_path=state.output_path,
                refresh=False,
            )

            total_events = 0
            total_sessions = 0
            details: list[str] = []
            has_success = False

            for cid, val in results.items():
                name = get_display_name(cid)
                if isinstance(val, tuple):
                    n_ev, n_sess = val
                    total_events += n_ev
                    total_sessions += n_sess
                    details.append(STRINGS.summary_ok.format(name=name, n=n_ev, s=plural(n_ev)))
                    has_success = True
                else:
                    details.append(STRINGS.summary_error.format(name=name, err=val))

            error_text.value = ""
            page.update()

            if has_success:
                _show_success_dialog(total_events, total_sessions, state.output_path, details)
            else:
                error_text.value = STRINGS.error_no_events + "\n" + "\n".join(details)
                error_text.color = theme.Colors.ERROR

        except Exception as exc:
            error_text.value = STRINGS.error_unexpected.format(msg=exc)
            error_text.color = theme.Colors.ERROR
        finally:
            state.is_generating = False
            generate_btn.disabled = not state.is_ready()
            progress_ring.visible = False
            page.update()

    generate_btn.on_click = on_generate_click

    # =========================================================================
    # PRÉFÉRENCES PAGE (Sprint 52) — real configuration center
    # =========================================================================
    # Reuses FavoritesService (already constructed above) and the raw
    # preferences dict for update_check_enabled/default_year/
    # ics_alarm_minutes (no dedicated service for these three — a single
    # flag/value each needs none, same "read-modify-write directly" style
    # already used by _save_prefs above). No business logic in
    # views/preferences.py itself: every control below is built here,
    # fully wired, and handed to build_preferences_view() only to be laid
    # out.
    #
    # MC-002 (P0-2): the Notifications section's 3 controls (enabled,
    # favorites-only, lead time) were removed from here — Flet ships no
    # OS notification service on any platform (see
    # gui/system_notifications.py's module docstring), so the switches
    # looked fully functional while never producing a visible
    # notification, with no indication to the user. NotificationService
    # itself (gui/notification_service.py) is untouched and still reads
    # its persisted preferences directly — only the GUI's illusion of a
    # working toggle is gone, replaced by the same ComingSoonRow already
    # used for the Application section, until a real OS backend exists.

    _ics_alarm_minutes_options: list[tuple[int, str]] = [
        (0, STRINGS.prefs_reminder_none),
        (15, STRINGS.prefs_duration_15min),
        (30, STRINGS.prefs_duration_30min),
        (60, STRINGS.prefs_duration_1h),
    ]
    # Same year-range convention as year_dropdown above, plus the
    # "current" sentinel first (recommended default, never goes stale).
    _default_year_options: list[tuple[str, str]] = [
        (DEFAULT_YEAR_SENTINEL, STRINGS.prefs_default_year_current),
        *((str(y), str(y)) for y in range(current_year - 5, current_year + 6)),
    ]

    preferences_container = ft.Container(expand=True)

    def _refresh_preferences_view() -> None:
        preferences_container.content = build_preferences_view(_build_preferences_controls())
        page.update()

    def _on_update_check_enabled_change(e: ft.ControlEvent) -> None:
        current = load_preferences()
        current["update_check_enabled"] = e.control.value
        save_preferences(current)
        _refresh_preferences_view()

    def _on_default_year_change(e: ft.ControlEvent) -> None:
        current = load_preferences()
        current["default_year"] = e.control.value
        save_preferences(current)
        _refresh_preferences_view()

    def _on_ics_alarm_minutes_change(e: ft.ControlEvent) -> None:
        current = load_preferences()
        current["ics_alarm_minutes"] = int(e.control.value)
        save_preferences(current)
        _refresh_preferences_view()

    def _build_preferences_controls() -> PreferencesViewControls:
        prefs_now = load_preferences()
        return PreferencesViewControls(
            update_check_enabled_switch=ft.Switch(
                value=bool(prefs_now.get("update_check_enabled", True)),
                active_color=theme.Colors.PRIMARY,
                on_change=_on_update_check_enabled_change,
            ),
            default_year_dropdown=ft.Dropdown(
                value=str(prefs_now.get("default_year", DEFAULT_YEAR_SENTINEL)),
                options=[
                    ft.dropdown.Option(value, label) for value, label in _default_year_options
                ],
                dense=True,
                # MC-002 (P0-8): 160 truncated the "Année en cours" sentinel
                # label to "Année en co" (found Sprint RC-01's visual
                # walkthrough) — every other option here is a bare 4-digit
                # year, so only this one label needs the extra room.
                width=190,
                on_select=_on_default_year_change,
            ),
            ics_alarm_minutes_dropdown=ft.Dropdown(
                value=str(prefs_now.get("ics_alarm_minutes", 30)),
                options=[
                    ft.dropdown.Option(str(minutes), label)
                    for minutes, label in _ics_alarm_minutes_options
                ],
                dense=True,
                width=160,
                on_select=_on_ics_alarm_minutes_change,
            ),
        )

    # =========================================================================
    # BUILD ALL VIEWS
    # =========================================================================

    _refresh_generate_btn()
    calendar_container.content = build_calendar_view(_current_calendar_controls())

    # Kick off the initial year-events fetch (Sprint 40) — same "fetch once at
    # launch" pattern as _load_weekend/_load_dashboard below.
    page.calendar_year_load_task = asyncio.create_task(_load_year_events(state.year))

    favorites_container.content = build_favorites_view(
        _current_favorites_groups(),
        len(favorites_service.list()),
        _on_favorite_click,
        _on_favorites_category_toggle,
    )

    # Championships are searchable immediately; events/circuits populate
    # once the background year-events fetch resolves (rebuilt again in
    # _load_year_events) — same "eventually consistent" pattern as every
    # other background-loaded page in this app.
    search_service.build_index(championships, year_events or {})
    search_container.content = build_search_view(
        search_field,
        search_service.search(""),
        False,
        on_championship_click=_on_search_championship_click,
        on_event_click=_on_search_event_click,
        on_circuit_click=_on_search_circuit_click,
    )
    # Sprint 47: the circuit database is empty until the first
    # year-events fetch resolves — rebuilt again in _load_year_events,
    # same "eventually consistent" pattern as search above.
    circuit_service.build_index(year_events or {})

    weekend_container = ft.Container(content=build_weekend_view(None), expand=True)

    async def _load_weekend(*, refresh: bool = False) -> None:
        """Fetch once per app launch — never on every tab visit, unless
        the user clicks the manual-refresh button (MC-002 P0-7).

        The existing HttpCache TTL (see controller.get_upcoming_weekend)
        already prevents redundant network calls; this background task
        just means the fetch starts immediately at launch instead of
        waiting for the user to click the Ce week-end tab.
        """
        try:
            result = await get_upcoming_weekend(refresh=refresh)
        except Exception:  # never crash the app on this background fetch
            return
        weekend_container.content = build_weekend_view(result, on_refresh=_on_weekend_refresh_click)
        page.update()

    async def _on_weekend_refresh_click(e: ft.ControlEvent) -> None:
        # Same immediate-loading-state feedback as the initial launch fetch.
        weekend_container.content = build_weekend_view(None)
        page.update()
        await _load_weekend(refresh=True)

    # Keep a reference on `page` for the app's lifetime — an unreferenced
    # asyncio.Task can be garbage-collected mid-flight.
    page.weekend_load_task = asyncio.create_task(_load_weekend())

    dashboard_container = ft.Container(content=build_dashboard_view(None), expand=True)

    async def _load_dashboard(*, refresh: bool = False) -> None:
        """Fetch once per app launch — same pattern as ``_load_weekend``,
        including the manual-refresh path (MC-002 P0-7).

        Reuses the exact same fetch pipeline (``controller.
        _fetch_weekend_entries``) as "Ce week-end" — the HttpCache already
        in play there means this second background task mostly hits cache,
        not a second round of network calls.
        """
        try:
            result = await get_dashboard_data(refresh=refresh)
        except Exception:  # never crash the app on this background fetch
            return
        on_view_release = (
            make_url_opener(url_launcher, result.update.manifest.url)
            if result.update is not None and result.update.manifest is not None
            else None
        )
        dashboard_container.content = build_dashboard_view(
            result,
            on_navigate=_navigate_to,
            on_view_release=on_view_release,
            on_refresh=_on_dashboard_refresh_click,
        )
        page.update()

    async def _on_dashboard_refresh_click(e: ft.ControlEvent) -> None:
        dashboard_container.content = build_dashboard_view(None)
        page.update()
        await _load_dashboard(refresh=True)

    page.dashboard_load_task = asyncio.create_task(_load_dashboard())

    # Sprint 51 — checked once per app launch, same background-task pattern
    # as the fetches above; a no-op (no dialog, no network call) whenever
    # the "update_check_enabled" preference is off or no manifest URL is
    # configured (see gui/controller.py::check_for_update).
    page.update_check_task = asyncio.create_task(_check_for_update())

    preferences_container.content = build_preferences_view(_build_preferences_controls())

    all_views: list[ft.Control] = [
        dashboard_container,
        weekend_container,
        calendar_container,
        search_container,
        favorites_container,
        preferences_container,
        build_about_view(url_launcher),
        build_support_view(url_launcher),
    ]

    # =========================================================================
    # NAVIGATION SHELL
    # =========================================================================

    def on_nav_change(e: ft.ControlEvent) -> None:
        content_area.content = all_views[int(e.control.selected_index)]
        page.update()

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=72,
        extended=False,
        bgcolor=theme.Colors.SURFACE,
        indicator_color=theme.Colors.PRIMARY,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.SPACE_DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.SPACE_DASHBOARD,
                label=STRINGS.nav_dashboard,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SPORTS_MOTORSPORTS_OUTLINED,
                selected_icon=ft.Icons.SPORTS_MOTORSPORTS,
                label=STRINGS.nav_weekend,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                selected_icon=ft.Icons.CALENDAR_MONTH,
                label=STRINGS.nav_my_calendar,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SEARCH_OUTLINED,
                selected_icon=ft.Icons.SEARCH,
                label=STRINGS.nav_search,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.STAR_OUTLINE,
                selected_icon=ft.Icons.STAR,
                label=STRINGS.nav_favorites,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label=STRINGS.nav_preferences,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INFO_OUTLINED,
                selected_icon=ft.Icons.INFO,
                label=STRINGS.nav_about,
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.VOLUNTEER_ACTIVISM_OUTLINED,
                selected_icon=ft.Icons.VOLUNTEER_ACTIVISM,
                label=STRINGS.nav_support,
            ),
        ],
        on_change=on_nav_change,
    )

    def on_page_resize(e: ft.ControlEvent) -> None:
        # page.width is int | float | None per Flet's own type — None before
        # the page has ever been laid out, which never happens once an
        # on_resize event has actually fired, but the type stub allows it;
        # (page.width or 0) keeps the rail collapsed rather than crashing
        # in that theoretical case.
        extended = (page.width or 0) > 900
        if nav_rail.extended != extended:
            nav_rail.extended = extended
            page.update()

    page.on_resize = on_page_resize

    content_area = ft.Container(
        content=all_views[0],  # start on Tableau de bord (Sprint 39 — page d'accueil)
        expand=True,
    )

    # Sprint 53 — Dashboard "Accès rapides" cards call this with a string
    # key (never a raw nav index — the view has no business knowing
    # nav_rail's internal ordering); only this function translates a key
    # into "which tab is selected", the exact same switch on_nav_change
    # already performs for a real NavigationRail click.
    _quick_access_nav_index: dict[str, int] = {
        "weekend": 1,
        "calendar": 2,
        "search": 3,
        "favorites": 4,
    }

    def _navigate_to(key: str) -> None:
        index = _quick_access_nav_index.get(key)
        if index is None:
            return
        nav_rail.selected_index = index
        content_area.content = all_views[index]
        page.update()

    page.add(
        ft.Row(
            controls=[
                nav_rail,
                ft.VerticalDivider(width=1, color=theme.Colors.BORDER),
                content_area,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )
