<p align="center">
  <img src="assets/branding/Banner.png" alt="Motorsport Calendar — by BApps" width="100%">
</p>

# motorsport-calendar

> Generate motorsport race calendars in ICS format — subscribe once, stay updated automatically.

[![CI](https://github.com/naviss29/motorsport-calendar/actions/workflows/ci.yml/badge.svg)](https://github.com/naviss29/motorsport-calendar/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

---

## Overview

**motorsport-calendar** fetches race calendars from public APIs and exports them as `.ics` files
you can subscribe to in Google Calendar, Apple Calendar, Outlook, or any iCalendar-compatible app.
It ships as a CLI and as a native desktop app (Alpha — Beta packaging and positioning
already validated, see [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md)).

```bash
# Formula 1 — 2026 season
motocal generate-f1 2026 f1-2026.ics

# WEC — FIA World Endurance Championship
motocal generate-wec 2026 wec-2026.ics

# All enabled championships in one file
motocal generate 2026 motorsport-2026.ics

# Desktop app
motocal-gui
```

Import the `.ics` file into your calendar app — every race, qualifying session, and
practice appears automatically with the correct local time.

---

## Features

- **ICS export** — one VEVENT per session, compatible with every major calendar app
- **16 working championships** across single-seater, endurance, GT and motorcycle racing — see the table below
- **Desktop app (Alpha)** — Dashboard, upcoming weekend, personal calendar builder, search,
  favorites, and preferences, all built on Flet
- **Extensible architecture** — add a new series in a few files, zero changes elsewhere
- **HTTP cache** — disk-based JSON cache with configurable TTL; skip with `--refresh`
- **YAML configuration** — sources, cache path, alarm reminders, opt-out per championship
- **CLI** — `motocal` powered by Typer + Rich, with coloured output and progress feedback

---

## Installation

### CLI only (recommended)

```bash
pip install motorsport-calendar
```

### CLI + Desktop app

```bash
pip install "motorsport-calendar[gui]"
```

### With uv

```bash
uv tool install motorsport-calendar
# With the desktop app:
uv tool install "motorsport-calendar[gui]"
```

### From source

```bash
git clone https://github.com/naviss29/motorsport-calendar.git
cd motorsport-calendar
uv sync --all-extras
```

> Building a standalone desktop binary (no Python required on the target machine) is
> documented in [`docs/PACKAGING.md`](docs/PACKAGING.md) and
> [`docs/RELEASE.md`](docs/RELEASE.md).

---

## Running the CLI

After installation, the `motocal` command is available in your terminal:

```bash
motocal --help
```

> **Windows note:** If `motocal` is not found after `pip install`, your Python `Scripts`
> directory may not be in `PATH`. As a fallback, use:
> ```
> python -m motorsport_calendar --help
> ```
> To add the Scripts directory to PATH permanently, see
> [Python on Windows FAQ](https://docs.python.org/3/using/windows.html#finding-the-python-executable).

---

## Usage

### One championship at a time

Every working championship has its own `generate-<id>` command:

```bash
motocal generate-f1            2026 f1-2026.ics
motocal generate-f2            2026 f2-2026.ics
motocal generate-f3            2026 f3-2026.ics
motocal generate-f1-academy    2025 f1a-2025.ics
motocal generate-formula-e     2026 formula-e-2026.ics
motocal generate-wec           2026 wec-2026.ics
motocal generate-elms          2026 elms-2026.ics
motocal generate-mlmc          2026 mlmc-2026.ics
motocal generate-gtwc-europe   2026 gtwc-europe-2026.ics
motocal generate-gtwc-america  2026 gtwc-america-2026.ics
motocal generate-gtwc-asia     2026 gtwc-asia-2026.ics
motocal generate-igtc          2026 igtc-2026.ics
motocal generate-motogp        2026 motogp-2026.ics
motocal generate-moto2         2026 moto2-2026.ics
motocal generate-moto3         2026 moto3-2026.ics

# Force re-download from the source instead of using the cache
motocal generate-f1 2026 f1-2026.ics --refresh
```

> `generate-imsa` and `generate-worldsbk` also exist (full provider architecture, wired
> into the CLI and config) but currently exit with "source non implémentée" — no public,
> structured schedule source was found for either championship. See
> [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the investigation. They are hidden
> from the desktop app's selectors until a real source is found.

### All enabled championships

```bash
# Fetches every enabled provider and merges them into one ICS file
motocal generate 2026 motorsport-2026.ics
```

If one provider fails (network error, unimplemented source…), the others continue.
A per-provider summary is displayed:

```
Génération calendrier 2026 — 16 providers activés…
  ✓ formula1 : 24 événements
  ✓ formula2 : 14 événements
  ✓ wec : 8 événements
  ✗ imsa : source non implémentée

Export terminé : motorsport-2026.ics (…)
```

### Other commands

```bash
# List all registered providers
motocal providers

# Show version
motocal version
```

---

## Desktop app (Alpha)

A native desktop window is available as an optional extra, built with [Flet](https://flet.dev):

```bash
pip install "motorsport-calendar[gui]"
motocal-gui
# or
python -m motorsport_calendar.gui
```

The app is organized around 8 pages:

- **Tableau de bord** — quick overview: next race, weekend at a glance, what's new
- **Ce week-end** — every session happening this weekend, across all championships
- **Mon calendrier** — pick a season and championships, generate an `.ics` file with a native save dialog
- **Recherche** — find a championship, event, or circuit; results open the matching page directly
- **Favoris** — star championships to prioritize them across the app
- **Préférences** — startup update check, default season, export reminder delay;
  notifications and theme/language are prepared but not wired to a real backend yet
- **À propos** — project presentation, tech stack, links
- **Soutenir le projet** — how to support the project (donations, roadmap voting, feedback)

> The desktop app uses exactly the same pipeline as the CLI — same providers, same cache,
> same `config.yaml`, same ICS exporter. No business logic is duplicated.

Tableau de bord, Ce week-end, and Mon calendrier each have a refresh button (top-right of
the page) to bypass the HTTP cache and re-fetch immediately — the same effect as the CLI's
`--refresh` flag, without editing `config.yaml` or deleting the cache by hand.

A notification-computation engine (`NotificationService`) exists internally and is fully
tested, but isn't exposed in the app yet — Flet ships no OS notification service on any
platform, so the Préférences page doesn't offer a notifications toggle until a real native
backend exists; see [`docs/DECISIONS.md`](docs/DECISIONS.md) for the investigation.

To build a standalone desktop binary, see [`docs/PACKAGING.md`](docs/PACKAGING.md).

---

## Configuration

Create `config.yaml` in your working directory (or `~/.config/motorsport-calendar/config.yaml`).
All keys are optional — sensible defaults apply when absent.

```yaml
# Timezone for display (IANA format)
timezone: Europe/Paris

cache:
  enabled: true
  path: ~/.cache/motorsport-calendar
  ttl_hours: 24        # re-download after 24 h

ics:
  alarm_minutes: 30    # VALARM reminder before each session (0 = disabled)

providers:
  formula1:
    enabled: true
    source: openf1     # openf1.org API — covers 2023 onwards
    # source: jolpica  # api.jolpi.ca (Ergast successor) — covers 1950 onwards
  wec:
    enabled: true
    source: official   # fiawec.com
  # Disable a championship:
  # imsa:
  #   enabled: false
```

Every other championship (`f2`, `f3`, `f1-academy`, `formula-e`, `elms`, `mlmc`,
`gtwc-europe`, `gtwc-america`, `gtwc-asia`, `igtc`, `motogp`, `moto2`, `moto3`…) can be
configured the same way — see `motocal providers` for the full, currently registered list.

---

## Architecture

```
config.yaml
     │
     ▼ registry.enabled()
  ┌──────────┬──────────┬──────────┐
  │Formula 1 │   WEC    │  MotoGP  │  …more (auto-discovered)
  │ Provider │ Provider │ Provider │
  └────┬─────┴────┬─────┴────┬─────┘
       │          │          │
  OpenF1     fiawec.com   Pulselive
  Source      Source       Source
       │          │          │
       ▼          ▼          ▼
     Events     Events     Events
          └──────┬──────┘
                 ▼
           IcsExporter
                 ▼
           calendar.ics
```

Each provider package **auto-registers** itself at import time via `ProviderRegistry`.
Each source auto-registers via `SourceRegistry`. The CLI calls `registry.discover()` once —
no hardcoded lists anywhere. The desktop app's controller (`gui/controller.py`) calls into
the exact same registry — no separate data path.

### Key concepts

| Concept | Role |
|---|---|
| `Provider` | Fetches data from one source and maps it to `list[Event]` |
| `Source` | Encapsulates the HTTP/scraping logic for one data endpoint |
| `F1CalendarBaseSource` | Shared base for F2, F3, Academy, Formula E — one class to subclass |
| `AcoSportsEventSource` | Shared base for WEC, ELMS, MLMC (same ACO CMS, JSON-LD) |
| `PulseliveBase` | Shared base for MotoGP, Moto2, Moto3 (Dorna's official API) |
| `SroTimetableBase` | Shared base for GTWC Europe/America/Asia and IGTC (SRO's HTML tables) |
| `ProviderRegistry` | Auto-discovers and holds all registered provider factories |
| `SourceRegistry` | Auto-discovers and holds all registered source factories |
| `IcsExporter` | Serialises a `list[Event]` to an RFC 5545 `.ics` file |
| `HttpCache` | Disk-based JSON cache keyed by SHA-256(url + params) |
| `ConfigService` | Reads `config.yaml` and merges with Pydantic defaults |

---

## Championships

| Championship | Status | Source | Availability |
|---|---|---|---|
| Formula 1 (recent) | ✅ Available | [openf1.org](https://openf1.org) | 2023 → present |
| Formula 1 (historical) | ✅ Available | [jolpi.ca](https://jolpi.ca) (Ergast successor) | 1950 → present |
| Formula 2 | ✅ Available | [f1calendar dataset](https://github.com/sportstimes/f1) (MIT) | Recent seasons |
| Formula 3 | ✅ Available | [f1calendar dataset](https://github.com/sportstimes/f1) (MIT) | 2022 → present |
| F1 Academy | ✅ Available | [f1calendar dataset](https://github.com/sportstimes/f1) (MIT) | 2023 → present |
| Formula E | ✅ Available | [f1calendar dataset](https://github.com/sportstimes/f1) (MIT) | Recent seasons |
| WEC — FIA World Endurance Championship | ✅ Available | fiawec.com (JSON-LD) | Recent seasons |
| ELMS — European Le Mans Series | ✅ Available | europeanlemansseries.com (JSON-LD) | Recent seasons |
| Michelin Le Mans Cup | ✅ Available | lemanscup.com (JSON-LD) | Recent seasons |
| GT World Challenge Europe | ✅ Available | gt-world-challenge-europe.com (HTML) | Recent seasons |
| GT World Challenge America | ✅ Available | gt-world-challenge-america.com (HTML) | Recent seasons |
| GT World Challenge Asia | ✅ Available | gt-world-challenge-asia.com (HTML) | Recent seasons |
| Intercontinental GT Challenge (IGTC) | ✅ Available | intercontinentalgtchallenge.com (HTML) | Recent seasons |
| MotoGP | ✅ Available | api.pulselive.motogp.com (official Dorna API) | Recent seasons |
| Moto2 | ✅ Available | api.pulselive.motogp.com (official Dorna API) | Recent seasons |
| Moto3 | ✅ Available | api.pulselive.motogp.com (official Dorna API) | Recent seasons |
| IMSA WeatherTech SportsCar Championship | 🔴 Architecture ready, no source found | — | Hidden from the desktop app |
| World Superbike (WorldSBK) | 🔴 Architecture ready, no source found | — | Hidden from the desktop app |

See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the full per-championship
investigation, including why IMSA and WorldSBK don't have a working source yet.

---

## Roadmap

The project is currently **Alpha**, with Beta preparation work done — the desktop app,
all 16 working providers, and standalone Linux + Windows packaging are in place and
validated; see [`docs/ROADMAP.md`](docs/ROADMAP.md) for the detailed, per-sprint
breakdown, and [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) for a running log of every
sprint.

| Milestone | Status |
|---|---|
| Multi-provider CLI, cache, config, ICS export | ✅ |
| 16 working championships across single-seater, endurance, GT and motorcycle racing | ✅ |
| Desktop app — Dashboard, weekend, calendar builder, search, favorites, preferences | ✅ Alpha |
| Standalone desktop packaging (no Python required) | ✅ Linux, ✅ Windows |
| PyPI release, stable public API | 🚧 |

---

## Contribution

### Run the tests

```bash
# All tests with coverage
uv run pytest

# A specific file
uv run pytest tests/test_cli_generate.py -v

# Packaging integrity
uv run pytest tests/test_packaging.py -v

# Lint + type check
uv run ruff check motorsport_calendar tests
uv run mypy motorsport_calendar
```

### Add a support series sharing the f1calendar dataset (F2, F3, Academy, Formula E…)

Subclass `F1CalendarBaseSource` — only four overrides needed:

```python
# providers/formula3/sources/f1calendar.py  ← already implemented
from motorsport_calendar.providers.support_series.f1calendar_base import F1CalendarBaseSource
from motorsport_calendar.providers.formula3.source import Formula3Source
from motorsport_calendar.models import Championship, ChampionshipCategory, SessionType

_SESSION_MAP = {
    "practice":   (SessionType.FP1,        45, "Free Practice"),
    "qualifying": (SessionType.QUALIFYING, 30, "Qualifying"),
    "sprint":     (SessionType.SPRINT,     30, "Sprint Race"),
    "feature":    (SessionType.RACE,       40, "Feature Race"),
}
_CIRCUIT_DATA = { ... }  # slug → (country, IANA timezone)

class F1CalendarSource(F1CalendarBaseSource, Formula3Source):
    @property
    def _series_key(self) -> str: return "f3"

    @property
    def _session_map(self): return _SESSION_MAP

    @property
    def _circuit_data(self): return _CIRCUIT_DATA

    def _make_championship(self, year: int) -> Championship:
        return Championship(id=f"formula3-{year}", name="FIA Formula 3 Championship",
                            category=ChampionshipCategory.SINGLE_SEATER)
```

Then register in `sources/__init__.py` — one line. That's all.

The same pattern applies to the other shared bases: `AcoSportsEventSource` (WEC, ELMS,
MLMC), `PulseliveBase` (MotoGP, Moto2, Moto3), `SroTimetableBase` (GTWC \*, IGTC).

### Add any other provider

1. Create `motorsport_calendar/providers/mychampionship/`
2. Add `source.py` (abstract `Source` class) and `provider.py` (concrete `Provider`)
3. Add `sources/mysource.py` with the HTTP/scraping implementation
4. Register in `__init__.py` and `sources/__init__.py` — two lines total

`motocal generate` picks it up automatically.

---

## License

[MIT](LICENSE) © 2026 Alan Yvenou
