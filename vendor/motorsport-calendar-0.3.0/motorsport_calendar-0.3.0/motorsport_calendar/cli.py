"""CLI entry point — no business logic, only presentation and delegation."""

from datetime import UTC
from pathlib import Path
from typing import Annotated, Any

from rich.console import Console
from rich.table import Table
import typer

app = typer.Typer(
    name="motocal",
    help="[bold green]motorsport-calendar[/] — Generate motorsport calendars in ICS format.",
    add_completion=True,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True, style="red")


def _version_callback(value: bool) -> None:
    if value:
        from motorsport_calendar import __version__

        console.print(f"motocal [bold green]v{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """motorsport-calendar — Generate motorsport race calendars in ICS format."""


@app.command()
def version() -> None:
    """Show the current version."""
    from motorsport_calendar import __version__

    console.print(f"motocal [bold green]v{__version__}[/]")


@app.command()
def providers() -> None:
    """List all registered data providers."""
    from motorsport_calendar.core.registry import registry

    registry.discover()
    all_ids = registry.list_all()

    table = Table(title="Registered Providers", show_header=True, header_style="bold cyan")
    table.add_column("Championship ID", style="green")

    if not all_ids:
        console.print(table)
        console.print("[yellow]No providers registered.[/]")
        return

    for cid in all_ids:
        table.add_row(cid)
    console.print(table)


def _run_generate_command(
    *,
    championship_id: str,
    year: int,
    output: Path,
    refresh: bool,
    fetch_label: str,
    default_source: str,
    error_prefix: str,
    not_implemented_message: str | None = None,
) -> None:
    """Shared body for every single-championship ``generate-*`` command.

    Each ``generate-*`` Typer command stays a thin wrapper (own docstring/
    help text, since Typer introspects the function signature for
    ``--help``) that only forwards its arguments here — this is the only
    place the fetch/error-handling/export logic lives. Introduced Sprint 34
    when adding Formula E made a 6th near-identical copy impossible to
    justify; the five pre-existing commands were refactored onto this same
    helper with byte-identical output (locked down by their existing tests).

    Args:
        championship_id: Registry id, e.g. "formula1", "wec".
        fetch_label: Display label in "Fetching {label} {year} calendar…".
        default_source: Source name used when config.yaml has no override.
        error_prefix: Prefix in "{prefix} error {code}: {url}" / "{prefix}
            timeout (10 s). Try again later.".
        not_implemented_message: When set, a stub source raising
            NotImplementedError is reported with this message (formatted
            with ``source_name=``) instead of propagating — used by WEC.
    """
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

    # Découverte automatique — la CLI ne connaît ni les providers ni les sources
    registry.discover()
    source_registry.discover()

    provider_cfg = config.providers.get(championship_id)
    if provider_cfg is None:
        provider_cfg = ProviderConfig(source=default_source)

    source_name = provider_cfg.source or default_source

    try:
        make_source = source_registry.get(championship_id, source_name)
    except KeyError as exc:
        err_console.print(str(exc))
        raise typer.Exit(code=1) from exc

    source = make_source(cache, refresh)

    try:
        make_provider = registry.get(championship_id)
    except KeyError as exc:
        err_console.print(str(exc))
        raise typer.Exit(code=1) from exc

    provider = make_provider(source)

    async def _fetch() -> list[Any]:
        return await provider.fetch_events(championship_id, year)  # type: ignore[no-any-return]

    cache_note = " [yellow](--refresh)[/]" if refresh else ""
    console.print(
        f"Fetching {fetch_label} [bold cyan]{year}[/] calendar "
        f"via [green]{source_name}[/]…{cache_note}"
    )

    try:
        events = asyncio.run(_fetch())
    except NotImplementedError as exc:
        if not_implemented_message is None:
            raise
        err_console.print(not_implemented_message.format(source_name=source_name))
        raise typer.Exit(code=1) from exc
    except httpx.HTTPStatusError as exc:
        err_console.print(f"{error_prefix} error {exc.response.status_code}: {exc.request.url}")
        raise typer.Exit(code=1) from exc
    except httpx.TimeoutException as exc:
        err_console.print(f"{error_prefix} timeout (10 s). Try again later.")
        raise typer.Exit(code=1) from exc

    IcsExporter(alarm_minutes=config.ics.alarm_minutes).export(events, output)

    count = len(events)
    sessions_count = sum(len(e.sessions) for e in events)
    console.print(
        f"[green]✓[/] {count} event{'s' if count != 1 else ''}, "
        f"{sessions_count} session{'s' if sessions_count != 1 else ''} → [bold]{output}[/]"
    )


@app.command("generate-f1")
def generate_f1(
    year: Annotated[int, typer.Argument(help="Formula 1 season year (e.g. 2024)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Formula 1 calendar via OpenF1 and export it as an ICS file."""
    _run_generate_command(
        championship_id="formula1",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="F1",
        default_source="openf1",
        error_prefix="OpenF1 API",
    )


@app.command("generate-f2")
def generate_f2(
    year: Annotated[int, typer.Argument(help="Formula 2 season year (e.g. 2025)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Formula 2 calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="formula2",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="F2",
        default_source="f1calendar",
        error_prefix="F2 source",
    )


@app.command("generate-f3")
def generate_f3(
    year: Annotated[int, typer.Argument(help="Formula 3 season year (e.g. 2025)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the FIA Formula 3 calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="formula3",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="F3",
        default_source="f1calendar",
        error_prefix="F3 source",
    )


@app.command("generate-f1-academy")
def generate_f1_academy(
    year: Annotated[int, typer.Argument(help="F1 Academy season year (e.g. 2025)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the F1 Academy calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="f1-academy",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="F1 Academy",
        default_source="f1calendar",
        error_prefix="F1 Academy source",
    )


@app.command("generate-formula-e")
def generate_formula_e(
    year: Annotated[int, typer.Argument(help="Formula E season year (e.g. 2025)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Formula E calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="formula-e",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="Formula E",
        default_source="f1calendar",
        error_prefix="Formula E source",
    )


@app.command("generate-elms")
def generate_elms(
    year: Annotated[int, typer.Argument(help="ELMS season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the European Le Mans Series calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="elms",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="ELMS",
        default_source="aco_scraper",
        error_prefix="ELMS source",
    )


@app.command("generate-mlmc")
def generate_mlmc(
    year: Annotated[int, typer.Argument(help="MLMC season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Michelin Le Mans Cup calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="mlmc",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="MLMC",
        default_source="aco_scraper",
        error_prefix="MLMC source",
    )


@app.command("generate-wec")
def generate_wec(
    year: Annotated[int, typer.Argument(help="WEC season year (e.g. 2024)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the FIA WEC calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="wec",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="WEC",
        default_source="official",
        error_prefix="WEC API",
        not_implemented_message=(
            "La source WEC '[bold]{source_name}[/]' n'est pas encore implémentée. "
            "Consulter le backlog pour l'état d'avancement."
        ),
    )


@app.command("generate-imsa")
def generate_imsa(
    year: Annotated[int, typer.Argument(help="IMSA season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the IMSA WeatherTech SportsCar Championship calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="imsa",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="IMSA",
        default_source="official",
        error_prefix="IMSA API",
        not_implemented_message=(
            "La source IMSA '[bold]{source_name}[/]' n'est pas encore implémentée. "
            "Consulter le backlog pour l'état d'avancement."
        ),
    )


@app.command("generate-gtwc-europe")
def generate_gtwc_europe(
    year: Annotated[int, typer.Argument(help="GT World Challenge Europe season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the GT World Challenge Europe calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="gtwc-europe",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="GT World Challenge Europe",
        default_source="sro_scraper",
        error_prefix="GT World Challenge Europe source",
    )


@app.command("generate-gtwc-america")
def generate_gtwc_america(
    year: Annotated[int, typer.Argument(help="GT World Challenge America season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the GT World Challenge America calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="gtwc-america",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="GT World Challenge America",
        default_source="sro_scraper",
        error_prefix="GT World Challenge America source",
    )


@app.command("generate-gtwc-asia")
def generate_gtwc_asia(
    year: Annotated[int, typer.Argument(help="GT World Challenge Asia season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the GT World Challenge Asia calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="gtwc-asia",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="GT World Challenge Asia",
        default_source="sro_scraper",
        error_prefix="GT World Challenge Asia source",
    )


@app.command("generate-igtc")
def generate_igtc(
    year: Annotated[
        int, typer.Argument(help="Intercontinental GT Challenge season year (e.g. 2026)")
    ],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Intercontinental GT Challenge calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="igtc",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="IGTC",
        default_source="sro_scraper",
        error_prefix="IGTC source",
    )


@app.command("generate-motogp")
def generate_motogp(
    year: Annotated[int, typer.Argument(help="MotoGP season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the MotoGP calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="motogp",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="MotoGP",
        default_source="pulselive",
        error_prefix="MotoGP source",
    )


@app.command("generate-moto2")
def generate_moto2(
    year: Annotated[int, typer.Argument(help="Moto2 season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Moto2 calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="moto2",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="Moto2",
        default_source="pulselive",
        error_prefix="Moto2 source",
    )


@app.command("generate-moto3")
def generate_moto3(
    year: Annotated[int, typer.Argument(help="Moto3 season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the Moto3 calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="moto3",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="Moto3",
        default_source="pulselive",
        error_prefix="Moto3 source",
    )


@app.command("generate-worldsbk")
def generate_worldsbk(
    year: Annotated[int, typer.Argument(help="WorldSBK season year (e.g. 2026)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch the World Superbike (WorldSBK) calendar and export it as an ICS file."""
    _run_generate_command(
        championship_id="worldsbk",
        year=year,
        output=output,
        refresh=refresh,
        fetch_label="WorldSBK",
        default_source="official",
        error_prefix="WorldSBK API",
        not_implemented_message=(
            "La source WorldSBK '[bold]{source_name}[/]' n'est pas encore implémentée. "
            "Consulter le backlog pour l'état d'avancement."
        ),
    )


@app.command("generate")
def generate(
    year: Annotated[int, typer.Argument(help="Season year (e.g. 2024)")],
    output: Annotated[Path, typer.Argument(help="Destination .ics file")],
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignorer le cache et re-télécharger les données."),
    ] = False,
) -> None:
    """Fetch all enabled championships and export them as a single ICS file."""
    import asyncio
    from datetime import datetime
    from typing import Any

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

    enabled_ids = registry.enabled(config.providers)

    if not enabled_ids:
        err_console.print("Aucun provider activé dans la configuration.")
        raise typer.Exit(code=1)

    n = len(enabled_ids)
    cache_note = " [yellow](--refresh)[/]" if refresh else ""
    console.print(
        f"Génération calendrier [bold cyan]{year}[/] — "
        f"{n} provider{'s' if n != 1 else ''} activé{'s' if n != 1 else ''}…{cache_note}"
    )

    provider_list: list[tuple[str, Any]] = []
    results: list[tuple[str, list[Any], str | None]] = []

    for championship_id in enabled_ids:
        provider_cfg = config.providers.get(championship_id) or ProviderConfig()
        source_name = provider_cfg.source
        if not source_name:
            available = source_registry.list_for(championship_id)
            source_name = available[0] if available else ""

        if not source_name:
            results.append((championship_id, [], "aucune source disponible"))
            continue

        try:
            make_source = source_registry.get(championship_id, source_name)
            make_provider = registry.get(championship_id)
        except KeyError as exc:
            results.append((championship_id, [], str(exc)))
            continue

        source = make_source(cache, refresh)
        provider_list.append((championship_id, make_provider(source)))

    async def _fetch_one(cid: str, prov: Any) -> tuple[str, list[Any], str | None]:
        try:
            events = await prov.fetch_events(cid, year)
            return (cid, list(events), None)
        except NotImplementedError:
            return (cid, [], "source non implémentée")
        except httpx.HTTPStatusError as exc:
            return (cid, [], f"HTTP {exc.response.status_code}")
        except httpx.TimeoutException:
            return (cid, [], "timeout")
        except Exception as exc:
            return (cid, [], str(exc))

    async def _fetch_all() -> list[tuple[str, list[Any], str | None]]:
        # Sprint 50 — chaque provider interroge une API distante indépendante ;
        # les récupérer en parallèle (au lieu d'un for/await séquentiel) réduit
        # le temps total à celui du provider le plus lent, pas la somme de tous
        # (mesuré ~10x sur 10 providers simulés à latence égale). asyncio.gather
        # préserve l'ordre de provider_list dans le résultat, donc le fichier
        # ICS final et les résumés affichés restent strictement identiques.
        return list(await asyncio.gather(*(_fetch_one(cid, prov) for cid, prov in provider_list)))

    results.extend(asyncio.run(_fetch_all()))

    all_events: list[Any] = []
    for cid, events, error in results:
        if error is None:
            count = len(events)
            console.print(f"  [green]✓[/] {cid} : {count} événement{'s' if count != 1 else ''}")
            all_events.extend(events)
        else:
            console.print(f"  [red]✗[/] {cid} : {error}")

    if not any(error is None for _, _, error in results):
        err_console.print("\nAucun championnat n'a pu être exporté.")
        raise typer.Exit(code=1)

    all_events.sort(
        key=lambda e: min(
            (s.start_datetime for s in e.sessions),
            default=datetime.max.replace(tzinfo=UTC),
        )
    )

    IcsExporter(alarm_minutes=config.ics.alarm_minutes).export(all_events, output)

    total_sessions = sum(len(e.sessions) for e in all_events)
    console.print(
        f"\nExport terminé : [bold]{output}[/] "
        f"({len(all_events)} événement{'s' if len(all_events) != 1 else ''}, "
        f"{total_sessions} session{'s' if total_sessions != 1 else ''})"
    )
