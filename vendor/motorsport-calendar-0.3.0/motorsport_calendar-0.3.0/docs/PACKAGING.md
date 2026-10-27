# PACKAGING.md — Building distributable executables

Sprint 49 (Packaging Alpha). Describes the *official* Flet build
procedure verified against this project's actual structure — every
command below was run for real against this repository, not copied
verbatim from generic documentation. No auto-installer, no auto-update:
`flet build` produces a plain folder/executable the user copies and runs
themselves.

> **⚠ Correction (Sprint 58 — Validation Packaging Beta).** Sprint 49's
> §5 below states the build "reaches the native compilation step... 
> confirming the packaging *configuration* itself... is correct
> end-to-end." That claim was **premature** — the build never actually
> ran to completion in Sprint 49 (missing system toolchain), so the
> resulting binary was never launched. Sprint 58 completed a real build
> and ran the binary for the first time: **it crashed on startup** with
> `ModuleNotFoundError: No module named 'motorsport_calendar'`. Sprint 49's
> asset/icon/path findings (§5) remain accurate — only the "runs
> end-to-end" claim was wrong.
>
> **✅ Fixed (follow-up mission, same day).** See §7 below — a build-only
> `motorsport_calendar/gui/pyproject.toml` now makes `flet build` install
> this project itself (correctly nested, with every real dependency) into
> the compiled bundle. Verified by an actual rebuild + a real launch of
> the resulting binary: no crash, no traceback, the Python app starts.
> §6 below is kept as-is, unedited, as the historical record of what was
> found and how — §7 is the fix.

---

## 1. What gets packaged

The GUI entry point is `motorsport_calendar/gui/app.py::main()` (console
script `motocal-gui`, and `python -m motorsport_calendar.gui`). Flet's
`flet build` command does **not** package an installed Python package the
way `pip`/`hatchling` do — it expects a "Flet app directory" containing an
entry-point module and, next to it, an `assets/` folder. Both already
exist at the right place in this repo:

```
motorsport_calendar/gui/
├── app.py              # entry point — flet build's --module-name app
└── assets/             # bundled automatically, no extra config needed
    ├── icon.png                 # default app icon (all platforms)
    ├── icon_windows.ico         # Windows-specific multi-resolution icon
    ├── favicon-16.png
    ├── favicon-32.png
    ├── logo/
    │   ├── mc-icon.svg
    │   ├── logo-horizontal.svg
    │   └── logo-vertical.svg
    └── championships/           # per-championship logos (none delivered yet)
```

Flet auto-detects the icon convention: `icon.png` (or `.bmp`/`.jpg`/`.webp`)
is the fallback icon for every platform; `icon_windows.ico` overrides it
specifically for the Windows build (a proper multi-resolution `.ico`,
16 through 256px, instead of a single PNG scaled up). No `--icon` CLI flag
exists in this Flet version (0.85.3) — the file-naming convention is the
only mechanism.

`assets_dir` is also passed explicitly to `ft.run()` in `app.py`, for the
*installed-package* launch path (`motocal-gui` invoked directly, not via a
`flet build` bundle) — resolved from `Path(__file__).parent / "assets"`,
**never** a literal absolute path and **never** CWD-relative (Flet's own
`assets_dir` resolves relative strings against the current working
directory at launch time, confirmed by reading `flet/app.py`'s own
source — a CWD-relative string would silently fail to find the assets
once the app is launched from anywhere other than this exact directory).

---

## 2. Building for Linux

### Prerequisites (verified empirically on Ubuntu 24.04)

```bash
sudo apt update
sudo apt install -y binutils clang cmake llvm lld ninja-build pkg-config \
    libgtk-3-dev libunwind-dev
```

Confirmed the hard way: a first `flet build linux` attempt on a machine
missing `clang`/`cmake`/`ninja-build`/`pkg-config` failed at the
"Building Linux application…" step with `flutter doctor` reporting all
four as missing — this is a **system-level** requirement (any Flutter
Linux desktop build needs them), not something this project's own
packaging config can work around. The Flutter SDK itself
(`flet build` installs it automatically on first run, ~1-2 GB download,
interactive confirmation unless `--yes` is passed) does **not** need to be
installed manually.

### Command

```bash
flet build linux motorsport_calendar/gui --module-name app
```

- `linux` — target platform.
- `motorsport_calendar/gui` — the "Flet app directory" (`python_app_path`;
  defaults to `.`, which does **not** work here since this repo's entry
  point is not a top-level `main.py` — must point directly at the
  directory containing `app.py`).
- `--module-name app` — the entry-point module is `app.py`, not the
  default-expected `main.py`.

Add `--yes` to auto-confirm the first-run Flutter SDK install
non-interactively (needed in CI or any non-TTY environment); add
`-v`/`-vv` for verbose/very-verbose build logs when diagnosing a failure.

### Output

```
motorsport_calendar/gui/build/linux/   # default, override with -o
```

A self-contained folder with the compiled executable and every bundled
asset — copy the whole folder to distribute, nothing else required on the
target Linux machine (the Flutter/GTK runtime pieces are bundled, not
system-installed on the target).

---

## 3. Building for Windows

**Must be run on an actual Windows machine — Flet does not support
cross-compiling a Windows build from Linux or macOS** (confirmed against
Flet's own published documentation: "This command can be run on Windows
only"). No WSL workaround exists for this specific step either, since the
Windows build compiles against the native Windows toolchain, not a Linux
one.

### Prerequisites (per Flet's official documentation)

- Visual Studio 2022 or 2026, with the **"Desktop development with C++"**
  workload installed (Visual Studio Installer → Workloads).
- Windows Developer Mode enabled (Settings → Privacy & Security → For
  developers) — Flet's build needs symlink support, which Developer Mode
  grants without requiring an elevated/Administrator shell.

### Command

```powershell
flet build windows motorsport_calendar/gui --module-name app
```

Identical arguments to the Linux command — `flet build`'s CLI contract is
platform-agnostic, only the target platform positional argument and the
underlying native toolchain differ.

### Output

```
motorsport_calendar\gui\build\windows\
```

A folder containing `motocal.exe` (or the configured `--artifact` name)
and its bundled dependencies — `icon_windows.ico` is used automatically
for the executable's own icon, `.ics` files it writes and the taskbar
icon. No installer (`.msi`/NSIS) is produced by this command — that would
be a separate, explicitly out-of-scope step (Sprint 49 brief: "aucune
installation automatique").

### This project's own validation status

The Linux build was validated for real against this repository during
Sprint 49 (Flutter SDK installed, entry point/module-name/assets
resolution all confirmed working — see §5). **The Windows build has now
also been validated for real, on an actual Windows 11 machine — see §8.**
Nothing in this project's own code turned out to be Windows-specific in a
way that made the build fail differently from any other Flet project; the
two blockers hit (§8) were both machine/toolchain-level, not caused by
this repository's own code. The cross-platform path handling from
Sprint 49 (`utils/paths.py`) ensures the *packaged app's own runtime
behavior* (preferences, cache) is correct on Windows — confirmed by the
full test suite passing for real on Windows for the first time (§8).

---

## 4. What is deliberately NOT covered

- **No installer** (`.msi`, NSIS, `.deb`, AppImage, Snap, Flatpak) — the
  brief asks for a buildable executable, not a distribution channel.
- **No auto-update mechanism** — explicitly out of scope
  ("Aucun auto-update").
- **No code signing** — neither Windows Authenticode nor Linux package
  signing; a real distribution would need this, not attempted here.
- **No macOS build** — the Sprint 49 brief scopes this to Linux + Windows
  only.
- **No CI/CD pipeline** for automated builds — this document describes
  the manual, official procedure; wiring it into GitHub Actions is a
  distinct future task (see `docs/TODO.md`).

---

## 5. What was actually verified this sprint

- `flet build linux motorsport_calendar/gui --module-name app` correctly
  locates the entry point, resolves `motorsport_calendar/gui/assets/` as
  the bundled assets folder, downloads and installs the Flutter SDK
  (3.41.7) on first run, resolves all Dart/Flutter package dependencies,
  and reaches the native compilation step ("Building Linux application…")
  — confirming the packaging *configuration* itself (module resolution,
  asset bundling, `pyproject.toml`) is correct end-to-end.
- The **only** blocker hit was the missing system toolchain documented in
  §2 — a machine-level gap, not a project bug. See `docs/JOURNAL.md` for
  the full account, including whether a complete compiled binary was
  produced by the end of the session.
- `page.window.icon`, `_ASSETS_DIR` resolution (CWD-independent), and the
  presence of all 6 files the Sprint 49 brief names explicitly
  (`logo-horizontal.svg`, `logo-vertical.svg`, `mc-icon.svg`,
  `favicon-16.png`, `favicon-32.png`, `icon.ico` → `icon_windows.ico`)
  are covered by `tests/test_packaging.py::TestGuiAssetsBundling`.
- Preferences (`gui/preferences.py`) and HTTP cache
  (`cache/http_cache.py`, `config/models.py::CacheConfig`) now resolve to
  the OS-appropriate user directory (`utils/paths.py`) rather than a
  Linux-only hardcoded path or the current working directory — verified
  by `tests/test_utils_paths.py`, `tests/test_gui_preferences.py`,
  `tests/test_http_cache.py`, `tests/test_config_service.py`. Neither
  ever writes inside this project's own directory.
- ICS export (`exporters/ics.py`) already accepted any caller-supplied
  `Path` with no built-in defaults or repo references — confirmed, not
  changed — by `tests/test_ics_exporter.py::TestExportIsPackagingSafe`.

---

## 6. Sprint 58 — full build output audit (real binary, run for real)

`flet build linux motorsport_calendar/gui --module-name app` was run to
completion for the first time (the missing toolchain from Sprint 49 was
resolved separately) and reported `Successfully built your app for
Linux!`. This section audits the actual output on disk and the actual
running binary — nothing here is inferred from Flet's documentation.

### 6.1 Where Flet puts things

`flet build` produces layered output; only the innermost one is the
redistributable artifact:

```
motorsport_calendar/gui/build/
├── flutter/                          Flet's scratch Flutter project (do not ship)
│   └── build/linux/x64/release/
│       └── bundle/                   ← same content as below, pre-copy
├── site-packages/                    intermediate, not the final artifact
└── linux/                            ← THE REDISTRIBUTABLE FOLDER (copy of bundle/ above)
    ├── gui                           executable (ELF, x86-64, 24 KB, unstripped)
    ├── lib/                          compiled native libraries (88 MB)
    │   ├── libapp.so                 the Flutter/Dart UI (16 MB, statically linked)
    │   ├── libflutter_linux_gtk.so   Flutter engine (42 MB)
    │   ├── libpython3.12.so.1.0      embedded CPython runtime (31 MB)
    │   └── lib*_plugin.so            Flet native plugins (window_manager,
    │                                 url_launcher, screen_retriever,
    │                                 pasteboard, window_to_front,
    │                                 serious_python — the Python↔Dart bridge)
    ├── python3.12/                   embedded CPython stdlib, compiled .pyc (13 MB)
    ├── site-packages/                embedded pip packages (7.3 MB) — see §6.3
    └── data/
        ├── icudtl.dat                Flutter's ICU/i18n data (844 KB)
        └── flutter_assets/
            ├── app/app.zip           the Python APPLICATION code + gui/assets/ (315 KB) — see §6.3
            ├── fonts/                MaterialIcons-Regular.otf (every ft.Icons.* glyph)
            └── packages/             Flutter plugin assets (wakelock_plus, cupertino_icons, flutter_math_fork)
```

**Total size: 112 MB** (`du -sh motorsport_calendar/gui/build/linux`).
Breakdown: `lib/` 88 MB (79 %), `python3.12/` 13 MB (12 %),
`site-packages/` 7.3 MB (6.5 %), `data/` 3.9 MB (3.5 %), executable
24 KB. The two dominant costs (`libflutter_linux_gtk.so` 42 MB,
`libpython3.12.so.1.0` 31 MB) are the Flutter engine and the embedded
Python runtime — both fixed costs of the Flet packaging model, not
specific to this app, and not reducible without switching frameworks.

**Icons**: `assets/icon.png`, `assets/icon_windows.ico`,
`assets/favicon-16.png`, `assets/favicon-32.png`,
`assets/logo/{mc-icon,logo-horizontal,logo-vertical}.svg` are all present
inside `app.zip` (confirmed by listing it), matching `gui/assets/`
exactly — asset bundling itself works correctly (Sprint 49's finding on
this point holds).

### 6.2 Is the compiled app actually standalone? Does it run?

**Python: not required on the target machine.** `libpython3.12.so.1.0`
(the interpreter) and the full stdlib (`python3.12/`, compiled `.pyc`)
are both bundled inside the folder. Confirmed by `ldd gui` and `ldd
lib/libapp.so` — `libapp.so` reports "statically linked", and the
executable's only Python-related link is to the bundled
`libpython3.12.so.1.0`, never a system Python.

**System packages: none beyond what a standard Ubuntu Desktop already
has.** `ldd gui` (and `ldd lib/libflutter_linux_gtk.so`) resolve every
dependency against ordinary desktop libraries already present on a
default Ubuntu install — GTK3, GLib, Pango, Cairo, ATK, X11/Wayland,
fontconfig, D-Bus. All resolved with no "not found" entries on a stock
Ubuntu 24.04 machine. A minimal/server Ubuntu install without a desktop
environment would be missing these and would need
`libgtk-3-0`/`libx11-6`/etc. installed — the same packages any GTK3
desktop app needs, not something specific to this project.

**Can a user just double-click/run the binary? No — it crashes
immediately.** Running `./gui` produces, in
`~/.cache/com.flet.gui/console.log` (the log Flet's own launcher writes
to):

```
Traceback (most recent call last):
  File "/…/flet/app/app.py", line 51, in <module>
    main()
  File "/…/flet/app/app.py", line 41, in main
    from motorsport_calendar.gui.main_view import build_main_view
ModuleNotFoundError: No module named 'motorsport_calendar'
```

**This is the single most important finding of this audit: the built
binary does not work.** The "Successfully built your app for Linux!"
message only confirms the native compilation succeeded — it says nothing
about whether the Python application inside can actually import.

### 6.3 Root cause (found by reading `flet_cli`'s own source, not guessed)

`flet build linux motorsport_calendar/gui --module-name app` passes
`motorsport_calendar/gui` as `python_app_path`. `flet_cli`'s
`BuildCommand` (`flet_cli/commands/build_base.py`) does two things with
that path that matter here:

1. `self.get_pyproject = load_pyproject_toml(self.python_app_path)` —
   it looks for a `pyproject.toml` **inside `python_app_path` itself**
   (i.e. `motorsport_calendar/gui/pyproject.toml`), never the project's
   real root `pyproject.toml`. None exists there, so every
   `tool.flet.*`/`project.*` lookup returns nothing.
2. Only files inside `python_app_path` are bundled into `app.zip`
   (confirmed by listing it — it contains `gui/`'s own `.py` files and
   `gui/assets/`, and *nothing* from `core/`, `providers/`, `config/`,
   `cache/`, `exporters/`, or the root `models.py`/`__init__.py`).

Two independent effects follow from the same root cause:

- **Missing dependencies.** `flet_cli/utils/project_dependencies.py`
  generates the bundled `requirements.txt` from
  `project.dependencies`/`tool.poetry.dependencies` in that same
  (nonexistent) local `pyproject.toml`. With nothing to read, only Flet
  itself and Flet's own transitive dependencies got installed into
  `site-packages/` (`httpx`, `anyio`, `oauthlib`, `certifi`, `h11`,
  `httpcore`, `idna`, `msgpack`, `repath`, `six`,
  `typing_extensions`) — **none of this project's 9 real dependencies**
  (`typer`, `rich`, `pydantic`, `icalendar`, `tzdata`, `pyyaml`,
  `beautifulsoup4`, `lxml` — `httpx` is a coincidental overlap) were
  installed, and neither was `motorsport_calendar` itself.
- **Generic naming/versioning.** With no `project.name`/`tool.flet.product`
  to fall back on, `flet_cli` falls back to `python_app_path.name` — the
  literal directory name `"gui"`. Confirmed in 3 independent places:
  the executable is named `gui` (not `motorsport-calendar` or similar),
  `flutter/linux/CMakeLists.txt` sets `BINARY_NAME "gui"` and
  `APPLICATION_ID "com.flet.gui"`, and the native GTK window title
  compiled into `my_application.cc` is literally
  `gtk_window_set_title(window, "gui")`. The Flutter app metadata
  (`data/flutter_assets/version.json`) reports
  `{"app_name":"gui","version":"1.0.0","package_name":"gui"}` — version
  `1.0.0`, not this project's real `0.2.0`.

**Fix (not applied this sprint — audit/documentation only, per the
sprint brief).** Add a `[tool.flet]` section, either:
- **(a)** a small `pyproject.toml` inside `motorsport_calendar/gui/`
  declaring `[project] name = "motorsport-calendar"` +
  `dependencies = [...]` (mirroring the root one), so `flet build`
  targeting that directory picks it up directly; or
- **(b)** run `flet build` from the project root instead
  (`flet build linux . --module-name motorsport_calendar.gui.app`) with
  `[tool.flet] app.path = "motorsport_calendar/gui"` added to the
  *existing* root `pyproject.toml`, so the build reuses the
  already-correct `project.name`/`version`/`dependencies` that are
  already declared there — no duplication of the dependency list.

Option (b) is very likely the better fit for this project (dependency
list already exists and is already tested/maintained in one place) but
was not attempted or verified this sprint — this audit's scope was
"identify and document," not "fix." See `docs/RELEASE.md` and
`docs/TODO.md` for this tracked as the top blocking item.

> **Update (follow-up mission, same day).** Neither (a) nor (b) exactly
> as described above turned out to be sufficient on its own — see §7 for
> what was actually implemented and why the dependency-list half of this
> diagnosis, while correct, was not the whole story. §7 also explains a
> 2nd, independent problem this section didn't yet name: even with every
> dependency present, `flet build` bundles the *contents* of
> `motorsport_calendar/gui/` flattened, with no `motorsport_calendar.`
> package wrapper — no dependency list, however complete, fixes an
> absolute import (`from motorsport_calendar.gui... import`) resolving
> against a flattened bundle.

### 6.4 Naming, icons, and paths — verified state

*(as first found — before the §7 fix; kept as the historical record. See
§7 for the values after the fix.)*

| Item | Verified value | Source |
|---|---|---|
| Window title (`page.title`) | `STRINGS.app_title` = "Motorsport Calendar" | `main_view.py:163` — set at runtime, *if* the app manages to start |
| Native GTK window title (compiled default) | `"gui"` | `flutter/linux/my_application.cc` — wrong, needs `tool.flet.product` |
| Executable / binary name | `gui` | `flutter/linux/CMakeLists.txt::BINARY_NAME` |
| Application ID | `com.flet.gui` | `CMakeLists.txt::APPLICATION_ID` — generic Flet default |
| App version embedded in the build | `1.0.0` | `data/flutter_assets/version.json` — should be `0.2.0` |
| Window icon (`page.window.icon`) | `"icon.png"`, resolved from `gui/assets/` | `main_view.py:167` — correct, and the file is confirmed present in `app.zip` |
| Favicon | `favicon-16.png`/`favicon-32.png` | present in `app.zip`; only consumed by a future web build, unused by the desktop build |
| Logo (BApps Brand Set) | `logo/{mc-icon,logo-horizontal,logo-vertical}.svg` | present in `app.zip`; not yet wired into any view (`theme.logo_placeholder()` still used, see `docs/AI_CONTEXT.md` debt table) |
| Linux `.desktop` launcher entry | **absent** | no `.desktop` file anywhere in the build output — the binary has no Applications-menu entry, no dock/taskbar grouping icon, until one is written manually or a `.deb`/AppImage/Flatpak step adds it |
| Preferences file | `~/.config/motorsport-calendar/gui_prefs.json` (Linux) / `%APPDATA%\motorsport-calendar\gui_prefs.json` (Windows) | `gui/preferences.py` via `utils/paths.py::user_config_dir("motorsport-calendar")` — confirmed independent of Flet's own `FLET_APP_STORAGE_DATA`/`FLET_APP_STORAGE_TEMP` env vars (which point at a generic, unrelated `~/Documents/flet/gui`/`~/.cache/com.flet.gui` — never used by this app's own code) |
| `config.yaml` lookup | `~/.config/motorsport-calendar/config.yaml` (Linux) / `%APPDATA%\motorsport-calendar\config.yaml` (Windows) | `config/service.py` via the same `user_config_dir()` |
| HTTP cache | `~/.cache/motorsport-calendar/` (Linux) / `%LOCALAPPDATA%\motorsport-calendar\` (Windows) | `cache/http_cache.py`/`config/models.py` via `utils/paths.py::user_cache_dir("motorsport-calendar")` |

The last 3 rows are the good news of this audit: the Sprint 49
cross-platform path work (`utils/paths.py`) is correct and entirely
independent of Flet's own storage variables — preferences/cache/config
would land in the right OS-appropriate place *if* the app could start.

### 6.5 What is still missing for a real distributable Beta

*(as first found — see §7 for what's been resolved since.)*

1. ~~**The `ModuleNotFoundError` blocker (§6.3)**~~ — **✅ fixed, see §7.**
2. **App identity mostly configured, one gap remains** — binary name
   (`motorsport-calendar`), application ID (`com.flet.motorsport-
   calendar`), and window title are all fixed by §7's change (they read
   `project.name` from the same manifest). The embedded build version
   (`data/flutter_assets/version.json`) still reads `1.0.0` instead of
   `0.2.0` despite `project.version = "0.2.0"` being set — not yet root
   -caused, see §7's own note on this.
3. **No Linux desktop integration** — no `.desktop` file, so the app
   never appears in an Applications menu/launcher by just unpacking the
   folder; a user must run the `motorsport-calendar` executable directly
   from a file manager or terminal.
4. **No compression/archive step** — the 148 MB folder (grew from 112 MB
   once real dependencies were added, see §7) is distributed as-is; a
   release should ship a `.tar.gz` (Linux) / `.zip` (Windows), not a raw
   folder (see `docs/RELEASE.md`).
5. **No checksums** — a real release should publish a `SHA256SUMS.txt`
  alongside each archive so a user can verify a download wasn't
  corrupted/tampered with.
6. **Windows build still unverified** — `flet build windows` (§3 above)
   has never been run for real (no Windows machine in this environment,
   unchanged since Sprint 49) — everything in §3 remains transcribed
   from Flet's documentation, not independently confirmed the way the
   Linux build now has been. The fix in §7 should apply identically
   (same manifest, same mechanism, platform-agnostic), but this is
   unverified until run on a real Windows machine.
7. **No CI-driven build** — still manual per §4's scope note; a GitHub
   Actions workflow that runs the build command on tag push would remove
   the "did the packager remember every step" risk entirely, but is a
   distinct future task (see `docs/TODO.md`).

---

## 7. The fix (follow-up mission, same day) — verified by an actual rebuild and a real launch

Two independent problems, not one — §6.3 correctly diagnosed the first
but a naive fix for it alone was proven insufficient by literally trying
it and re-launching the binary:

1. **Missing dependencies** — real, but fixing only this (a duplicated
   `[project.dependencies]` list in a new `motorsport_calendar/gui/
   pyproject.toml`) still crashed with the exact same
   `ModuleNotFoundError` after a full rebuild. Confirmed by checking
   `site-packages/` after that rebuild: `pydantic`/`icalendar`/`typer`/
   `rich`/`tzdata`/`pyyaml`/`beautifulsoup4`/`lxml` were all present —
   dependencies were never the whole story.
2. **The `motorsport_calendar` package itself was never bundled in a
   correctly nested (importable) shape** — `flet build` zips the
   *contents* of whichever directory `python_app_path` points at
   (`motorsport_calendar/gui/`), flattened, with no `motorsport_calendar.`
   package wrapper (confirmed by listing `app.zip`: `main_view.py`,
   `strings.py`, etc. sit at the zip root, never under a `gui/` or
   `motorsport_calendar/` prefix). Every file in `gui/` uses **absolute**
   imports (`from motorsport_calendar.gui.controller import ...`) — no
   dependency list, however complete, makes an absolute import resolve
   against a flattened bundle with no such package to import.

### The fix

`motorsport_calendar/gui/pyproject.toml` (new file, committed to the
repo) declares only 2 dependencies:

```toml
[project]
name = "motorsport-calendar"
version = "0.2.0"
dependencies = [
    "flet>=0.80",
    "motorsport-calendar",
]

[tool.flet.app]
module = "app"

[tool.flet.dev_packages]
motorsport-calendar = "../.."
```

`tool.flet.dev_packages` is Flet's own mechanism for "a dependency I'm
developing locally, not (yet) on PyPI" (confirmed by reading
`flet_cli/commands/build_base.py`'s handling of it): it rewrites the
`motorsport-calendar` requirement into
`motorsport-calendar @ file:///…/motorsport-calendar` (resolved relative
to `motorsport_calendar/gui/`, i.e. `../..` = the repo root) before
handing the requirements list to `serious_python`'s packaging step. This
triggers a genuine, isolated `pip install` of the project **from its
real root**, using the **existing** root `pyproject.toml` +
`hatchling` build backend (`packages = ["motorsport_calendar"]`) —
exactly the same wheel a developer's own `pip install -e .[gui]` already
builds from, nothing new to maintain. Installing it this way also
resolves its own declared dependencies (typer/rich/pydantic/icalendar/
httpx/tzdata/pyyaml/beautifulsoup4/lxml) transitively, straight from the
one place they're actually declared — the build manifest never lists them
a second time.

The build command itself, and its output location, are **unchanged**:

```bash
flet build linux motorsport_calendar/gui --module-name app
```

(`--module-name app` is now technically redundant — `tool.flet.app.module`
in the new manifest already says so — but kept in the documented command
for clarity/backward-compatibility; the two never conflict.)

### Verified, not assumed

- Rebuilt for real (`flet build linux motorsport_calendar/gui
  --module-name app`), ~25 seconds (the existing Flutter scaffold at
  `motorsport_calendar/gui/build/flutter/` was reused — this fix never
  changes `python_app_path`, so nothing about the native/Flutter side of
  the build was invalidated).
- `site-packages/motorsport_calendar/` now exists, correctly nested
  (`__init__.py`, `core/`, `providers/`, `config/`, `cache/`,
  `exporters/`, `gui/`, `cli.py`, `models/`), version `0.2.0` (confirmed
  via `motorsport_calendar-0.2.0.dist-info`).
- **The binary was launched twice** (`./motorsport-calendar`, the new,
  correctly-named executable). Both times: no `ModuleNotFoundError`, no
  traceback of any kind in `~/.cache/motorsport-calendar/console.log`
  (empty both times — previously this file always contained the crash
  traceback). The process stayed alive past the point the broken build
  always crashed at (confirmed via `ps` — running, multi-threaded state
  — at a 6-second mark, well past instant-crash territory).
- **Not verified**: an actual rendered GTK window was not visually
  confirmed — this environment has no real display compositor to
  screenshot against, the same limitation noted for every GUI sprint
  throughout this project's history. The Python-level startup crash —
  the specific, concrete bug this mission was asked to fix — is
  definitively resolved; final pixel-level confirmation is a "run it on
  a real desktop" step for whoever ships the next Beta build.
- Executable/app ID/window title (compiled default) are now
  `motorsport-calendar`/`com.flet.motorsport-calendar`/
  `"motorsport-calendar"` — all read from `project.name` in the same
  manifest, no separate fix needed (§6.5 point 2 above).
- **Resolved — MC-002 (P0-5).** Root-caused by reading Flet's actual
  installed source (`flet_cli/commands/build.py`/`build_base.py`), not
  guessed: `project.version` genuinely is passed as `--build-name` to
  `flutter build`, and that flag correctly stamps the final native
  package's own version metadata — but it never rewrites the Flutter
  scaffold's `pubspec.yaml` on disk, and Flutter's own build step
  generates `data/flutter_assets/version.json` by reading that file's
  `version:` line directly, which `flet create`'s cookiecutter template
  seeds with a generic `1.0.0+1` that nothing was overriding.
  `motorsport_calendar/gui/pyproject.toml` now sets
  `[tool.flet.flutter.pubspec] version = "0.3.0+1"` — Flet's own
  supported extension point for patching generated `pubspec.yaml` keys
  — guarded by `tests/test_packaging.py::
  test_gui_manifest_pins_flutter_pubspec_version_to_root`.
  **Caveat carried into the release process** (see `docs/RELEASE.md`):
  this merge only runs when the Flutter scaffold is actually
  regenerated — Flet skips it when reusing an existing
  `motorsport_calendar/gui/build/` cache, which is exactly how `1.0.0`
  shipped in the first place (this same Sprint 59 rebuild reused the
  scaffold for speed). A real release build must start from a
  deleted/absent `build/` directory every time.
- Bundle size grew from 112 MB to **148 MB** — expected and correct: the
  9 real dependencies (`pydantic`+`pydantic_core`, `icalendar`, `typer`,
  `rich`, `tzdata`, `pyyaml`, `beautifulsoup4`+`bs4`+`soupsieve`, `lxml`,
  `python-dateutil`) are now genuinely present, where before the build
  silently shipped without them (and would have crashed on every one of
  their use sites even if the top-level import had somehow succeeded).
- Full test suite (2041 passed, 1 skipped — Windows-only), ruff, and
  mypy (41 source / 176 tests, both unchanged from before this fix) all
  confirmed green — no application source file was touched, only the new
  build manifest and its safety-net tests
  (`tests/test_packaging.py::TestFletBuildManifest`).
- The root `pyproject.toml`, the `motocal`/`motocal-gui` console-script
  entry points, and `pip install -e .[gui]` are **completely untouched**
  — confirmed by re-importing `motorsport_calendar.gui.app`/
  `motorsport_calendar.cli` directly from the dev virtualenv after the
  fix. The new manifest is read *only* by `flet build`; nothing in the
  normal development workflow ever looks at
  `motorsport_calendar/gui/pyproject.toml`.

### Safety net against future drift

`tests/test_packaging.py::TestFletBuildManifest` (8 tests) locks in the
shape of the fix: the build manifest declares `flet` + the project
itself (never a second copy of the 9-item dependency list — a test
fails if one is ever reintroduced), `project.name`/`version` stay in
sync with the root manifest, the `tool.flet.dev_packages` redirect
resolves to a real, installable project root, and the declared entry
module (`app`) actually exists on disk.

---

## 8. Sprint RC-01 — Windows build, validated for real on Windows 11

The Windows build (§3) had never been executed on an actual Windows
machine until this sprint. Run on a real Windows 11 24H2/25H2 machine,
from a fresh environment with none of Flet's prerequisites pre-installed
— every gap below was hit and fixed for real, not anticipated from
documentation.

### Machine-level prerequisites, confirmed the hard way

1. **Visual Studio Build Tools 2022, "Desktop development with C++"
   workload** — absent on this machine, installed via `winget install
   --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait
   --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`.
   Confirmed by Flutter's own `flutter doctor` afterward: `[√] Visual
   Studio - develop Windows apps`.
2. **Windows Developer Mode** — disabled by default
   (`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock`),
   required for the symlink support `flet build` needs; enabling it
   requires Administrator privileges, not something a normal user-level
   shell can do unattended.
3. **`rich`'s legacy Windows console renderer crashes on a non-UTF-8
   codepage.** `flet build`'s progress UI (via `rich.Live`) raised
   `UnicodeEncodeError: 'charmap' codec can't encode character '●'`
   immediately on first run, before any real build work started, on a
   terminal using the default `cp1252`/`850` codepage rather than UTF-8.
   Fix: set `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` (and/or `chcp 65001`)
   before invoking `flet build` — an environment-level fix, no project
   code touched. Not specific to this project; any `flet build windows`
   invocation from a non-UTF-8 Windows console hits this.
4. **The Visual Studio-bundled `cmake.exe` used by Flutter's Windows
   toolchain is a 32-bit (`i386`) binary**, confirmed via `file
   cmake.exe`. CMake's generated `cmake_install.cmake` tries to copy
   `C:/WINDOWS/System32/vcruntime140_1.dll` (a genuinely x64-only DLL —
   it has no 32-bit build at all) into the release bundle as part of
   `InstallRequiredSystemLibraries`. Being a 32-bit process, this
   `cmake.exe` is transparently WOW64-redirected to
   `C:\WINDOWS\SysWOW64\` for that path — where the file can never exist,
   since no 32-bit version of it is ever produced by any Microsoft
   installer. Result: `CMake Error ... file INSTALL cannot find
   "C:/WINDOWS/System32/vcruntime140_1.dll"`, failing the whole
   `INSTALL.vcxproj` target (MSBuild surfaces this as a wall of generic
   `MSB3073` batch-echo noise, not the real error — the actual cause only
   showed up by re-running the failing `cmake -P cmake_install.cmake`
   command directly, bypassing MSBuild's non-verbose logger). **Fix**
   (community-documented workaround for this known Flutter/Windows/CMake
   interaction, confirmed working here): copy the real
   `C:\WINDOWS\System32\vcruntime140_1.dll` to
   `C:\WINDOWS\SysWOW64\vcruntime140_1.dll` (Administrator privileges
   required) — an additive, easily-reversible file copy, never an
   overwrite. This satisfies the WOW64-redirected read; the byte content
   copied into the app's own bundle is still the correct real x64 DLL.
   Installing both the x64 *and* x86 Microsoft Visual C++ Redistributable
   via winget was necessary but **not sufficient** on its own — the x86
   redistributable never ships this specific file, by design.

None of the four items above are caused by this project's own code or
build manifest (§7) — all are properties of the Windows machine/toolchain
that any Flet Windows-desktop build hits the first time it's run in a
fresh environment.

### Result, verified not assumed

- `flet build windows motorsport_calendar/gui --module-name app`
  completed with `Successfully built your Windows app!`.
- Output: `motorsport_calendar\gui\build\windows\motorsport-calendar.exe`
  (314 KB), full bundle **105 MB**. `site-packages/motorsport_calendar/`
  confirmed correctly nested (same shape as the Linux build, §7),
  `motorsport_calendar-0.2.0.dist-info` confirms the right version was
  installed.
- **Binary launched for real, window rendered and visually inspected —
  the first time in this project's history** (every prior GUI sprint
  noted no display compositor was available to confirm rendering). Native
  window title read `"gui"` at first paint (compiled default, expected —
  see §7), then correctly updated to `"Motorsport Calendar"` once Python
  startup finished setting `page.title`. No console.log traceback at any
  point (`%LOCALAPPDATA%\motorsport-calendar\console.log` stayed absent —
  the same healthy signal already established for Linux). Closed cleanly
  via the window's own close button, process exited on its own (no forced
  kill needed).
- All 8 pages visually walked through with real screenshots (Dashboard,
  Ce week-end, Mon calendrier, Recherche, Mes favoris, Préférences, À
  propos, Soutenir le projet) — real data rendered correctly in every
  one (e.g. Dashboard: 17 championnats, 180 événements, 865 sessions;
  Mon calendrier: category tree with live counts; Recherche: 108 live
  results). No crash, no broken widget, no theme issue on any page.
- Two real, pre-existing test bugs surfaced by running the suite on
  Windows for the first time (both in test assumptions, not application
  code — see `tests/test_config_service.py` and
  `tests/test_utils_paths.py`): a `.cache`-in-path assertion that's
  Linux-only by the code's own documented design, and two `Path.home()`
  fallback tests that cleared the *entire* environment (`clear=True`),
  which only coincidentally worked on Linux (`pwd` database fallback,
  environment-independent) and legitimately can't work on Windows
  (`Path.home()` has no non-environment fallback there). Fixed by
  correcting the test assumptions to match each platform's real
  behavior — no application code changed. Full suite: **2042 passed, 0
  skipped** (the 1 previously-Windows-only-skipped test now runs for
  real and passes).
- ~~One pre-existing cosmetic UI bug found during the visual walkthrough:
  the "Année par défaut" dropdown on the Préférences page renders
  truncated~~ — **fixed, MC-002 (P0-8)**: `width` widened from 160 to
  190 (`gui/main_view.py::_build_preferences_controls`) — every other
  option in that dropdown is a bare 4-digit year, only the "Année en
  cours" sentinel label needed the extra room.

### Not yet covered

- This was one real Windows 11 machine, one Windows build/Visual Studio
  version combination. A different Windows edition/VS version could
  plausibly hit the same `vcruntime140_1.dll`/WOW64 issue (it is a
  property of Flet/Flutter's toolchain, not this specific machine) —
  worth confirming again the next time a Beta is actually cut on a
  different machine.
- No installer, no code signing, no CI-driven build — unchanged from §4's
  scope note and `docs/RELEASE.md` §8's known gaps.

See `docs/RELEASE.md` for the proposed `Release/` folder layout and the
step-by-step procedure to generate and publish a Beta build.
