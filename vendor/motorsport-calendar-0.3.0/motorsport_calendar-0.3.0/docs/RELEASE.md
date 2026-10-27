# RELEASE.md — Building and publishing a Motorsport Calendar release

Sprint 58 (Validation Packaging Beta). This document is the step-by-step
release procedure — generate the Linux/Windows builds, assemble them into
a local `Release/` folder, and publish a GitHub Release. For the deep
technical detail behind each build command (what Flet actually produces,
file sizes, dependency verification, known issues), see
`docs/PACKAGING.md` — this document assumes that one and does not repeat
its content.

> **✅ The blocker documented here previously is fixed.** `docs/
> PACKAGING.md` §6 originally found the Linux build crashing on startup
> (`ModuleNotFoundError: No module named 'motorsport_calendar'`) —
> `docs/PACKAGING.md` §7 documents the fix (a build-only
> `motorsport_calendar/gui/pyproject.toml`), verified by an actual
> rebuild and a real launch of the resulting binary (no crash, no
> traceback). The build command below is unchanged by the fix.
>
> **✅ The embedded build version is also fixed (MC-002 P0-5)** — see
> `docs/PACKAGING.md` §7's own note for the root cause. **Load-bearing
> for every release build:** the fix only takes effect when the Flutter
> scaffold is actually regenerated — §2 and §3 below now say so
> explicitly (delete `motorsport_calendar/gui/build/` before each real
> release build). Skipping that step silently brings back the stale
> `1.0.0` in `data/flutter_assets/version.json`.

---

## 1. Release checklist (overview)

1. Decide the version number and update `pyproject.toml` (`version =
   "..."`, this is the single source of truth for the version — the CLI
   (`motocal --version`), the GUI ("À propos" page), and this checklist
   all read from it).
2. Move the relevant `CHANGELOG.md` section from `## [Unreleased] — Sprint
   N — ...` to a dated, versioned heading (`## [0.2.0-beta.1] —
   2026-07-14`), following the file's existing Keep a Changelog format.
3. Run the full test suite, ruff, and mypy — a release is never built
   from a red or unverified tree (see §5, "Pre-release verification").
4. Generate the Linux build (§2).
5. Generate the Windows build on a Windows machine (§3) — cannot be
   cross-compiled from Linux/macOS (see `docs/PACKAGING.md` §3).
6. Assemble both builds, checksums, and the top-level project files into
   the local `Release/` folder (§4).
7. Tag the commit and push it — this alone also triggers the automatic
   PyPI publish (§6.1 prerequisites first, only once) — then publish a
   GitHub Release with the assembled archives attached (§6).

---

## 2. Generating the Linux build

**Delete any existing `motorsport_calendar/gui/build/` first** — for a
real release, never reuse a cached scaffold from a previous dev-cycle
build. Flet only re-applies `motorsport_calendar/gui/pyproject.toml`'s
`[tool.flet.flutter.pubspec]` override (which stamps the correct app
version into `data/flutter_assets/version.json`, MC-002 P0-5) when the
Flutter scaffold is actually regenerated — reusing an existing `build/`
silently skips that and ships the previous build's stale version again:

```bash
rm -rf motorsport_calendar/gui/build

# From the project root, with the project's own venv active
# (flet-cli is a `gui` extra dependency — pip install motorsport-calendar[gui])
flet build linux motorsport_calendar/gui --module-name app
```

Output: `motorsport_calendar/gui/build/linux/` — see
`docs/PACKAGING.md` §6.1 for exactly what this folder contains
(executable, `lib/`, `python3.12/`, `site-packages/`, `data/`) and §6.2
for what it does/doesn't require on the target machine.

Prerequisites (system toolchain, Flutter SDK) are documented in
`docs/PACKAGING.md` §2 — not repeated here.

**Before packaging any output for release**, always smoke-test the
compiled binary directly — never assume a successful `flet build` means
a working app (see `docs/PACKAGING.md` §6 for exactly this mistake, the
first time this project's own Linux build was actually launched):

```bash
cd motorsport_calendar/gui/build/linux
./motorsport-calendar
```

The window must actually open (not just "the command exits 0"). If it
doesn't, check `~/.cache/motorsport-calendar/console.log` for a Python
traceback — an empty file with the process still running past a few
seconds is the expected, healthy signal (confirmed against this exact
project — see `docs/PACKAGING.md` §7).

### Packaging the Linux build for distribution

```bash
cd motorsport_calendar/gui/build
VERSION="0.2.0-beta.1"   # match pyproject.toml
tar -czf "motorsport-calendar-${VERSION}-linux-x64.tar.gz" -C linux .
sha256sum "motorsport-calendar-${VERSION}-linux-x64.tar.gz" \
    > "motorsport-calendar-${VERSION}-linux-x64.tar.gz.sha256"
```

A `.tar.gz` (not a raw folder) is the distributable unit — see §4 for
where it lands in `Release/`.

---

## 3. Generating the Windows build

Must be run on an actual Windows machine — Flet does not support
cross-compiling a Windows build from Linux or macOS (see
`docs/PACKAGING.md` §3 for the prerequisites: Visual Studio 2022/2026
with the "Desktop development with C++" workload, Developer Mode
enabled).

**Delete any existing `motorsport_calendar\gui\build\` first** — same
reason as the Linux build above (§2): the embedded-version fix (MC-002
P0-5) only applies when the Flutter scaffold is regenerated.

```powershell
Remove-Item -Recurse -Force motorsport_calendar\gui\build -ErrorAction SilentlyContinue
flet build windows motorsport_calendar/gui --module-name app
```

Output: `motorsport_calendar\gui\build\windows\` — a folder containing
the compiled `.exe` and its bundled dependencies, `icon_windows.ico`
used automatically for the executable/taskbar icon. **Validated for real
on a Windows 11 machine, Sprint RC-01** — see `docs/PACKAGING.md` §8 for
the full account, including two machine-level gaps hit and fixed on a
fresh environment (`rich`'s console renderer needs `PYTHONUTF8=1` on a
non-UTF-8 codepage; the VS-bundled 32-bit `cmake.exe` needs
`vcruntime140_1.dll` mirrored into `SysWOW64` due to WOW64 redirection —
neither caused by this project's own code).

### Packaging the Windows build for distribution

```powershell
$VERSION = "0.2.0-beta.1"   # match pyproject.toml
Compress-Archive -Path "motorsport_calendar\gui\build\windows\*" `
    -DestinationPath "motorsport-calendar-$VERSION-windows-x64.zip"
Get-FileHash "motorsport-calendar-$VERSION-windows-x64.zip" -Algorithm SHA256 |
    Select-Object Hash | Out-File "motorsport-calendar-$VERSION-windows-x64.zip.sha256"
```

---

## 4. Assembling the `Release/` folder

Proposed local staging layout — never committed (see §7, add `Release/`
to `.gitignore`), regenerated fresh for each release rather than
accumulated:

```
Release/
├── Linux/
│   ├── motorsport-calendar-0.2.0-beta.1-linux-x64.tar.gz
│   └── motorsport-calendar-0.2.0-beta.1-linux-x64.tar.gz.sha256
├── Windows/
│   ├── motorsport-calendar-0.2.0-beta.1-windows-x64.zip
│   └── motorsport-calendar-0.2.0-beta.1-windows-x64.zip.sha256
├── Source/
│   └── motorsport-calendar-0.2.0-beta.1-source.tar.gz
├── CHANGELOG.md
├── LICENSE
└── README.md
```

Notes on each entry:

- **`Linux/`/`Windows/`** — one archive + one checksum file each, from
  §2/§3. Never the raw uncompressed build folders (148 MB of loose files
  is not something to hand a user or attach to a GitHub Release
  comfortably).
- **`Source/`** — a plain source archive (`git archive` output, or
  `python -m build --sdist`). Partially redundant with GitHub's own
  auto-generated "Source code (tar.gz/zip)" links on every Release page
  — kept here mainly for a user who wants a single download location
  covering every artifact without relying on GitHub's auto-generated
  links, not because GitHub requires it.
- **`CHANGELOG.md`/`LICENSE`/`README.md`** — plain copies of the
  project-root files at release time, so `Release/` is self-describing
  even if extracted and shared standalone, away from the repository.

```bash
# From the project root
VERSION="0.2.0-beta.1"
mkdir -p "Release/Linux" "Release/Windows" "Release/Source"

cp motorsport_calendar/gui/build/motorsport-calendar-${VERSION}-linux-x64.tar.gz* Release/Linux/
cp motorsport_calendar/gui/build/motorsport-calendar-${VERSION}-windows-x64.zip* Release/Windows/   # copied from the Windows machine
git archive --format=tar.gz -o "Release/Source/motorsport-calendar-${VERSION}-source.tar.gz" HEAD
cp CHANGELOG.md LICENSE README.md Release/
```

---

## 5. Pre-release verification

Never build a release from an unverified tree:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/mypy motorsport_calendar
```

All three must be clean (or only carry the already-documented, accepted
mypy Flet-stub debt — see `docs/AI_CONTEXT.md`'s debt table) before
tagging. This is a repeat of the same gate every sprint in this project
already runs before considering its own work done — a release is not
exempt.

---

## 6. Publishing a GitHub Release

> **⚠️ MC-002 (P0-9): the tag push below has a second, automatic side
> effect this doc previously never mentioned.** `.github/workflows/
> publish.yml` triggers on any `v*.*.*` tag push — the same
> `git push origin vX.Y.Z` that makes the tag visible on GitHub also
> builds the package and publishes it to **PyPI**, via OIDC trusted
> publishing, with no further confirmation step and no way to unpublish
> a version once PyPI has accepted it. Read §6.1 (PyPI prerequisites)
> **before** running this step for the first time — not after.

```bash
# 1. Tag the commit the release is built from
git tag -a v0.2.0-beta.1 -m "Motorsport Calendar 0.2.0-beta.1"
git push origin v0.2.0-beta.1   # ← also triggers the PyPI publish, see §6.1

# 2. Create the Release and attach every archive + checksum from Release/
gh release create v0.2.0-beta.1 \
    Release/Linux/*.tar.gz Release/Linux/*.sha256 \
    Release/Windows/*.zip Release/Windows/*.sha256 \
    Release/Source/*.tar.gz \
    --title "Motorsport Calendar 0.2.0-beta.1" \
    --notes-file <(sed -n '/## \[0.2.0-beta.1\]/,/## \[/p' CHANGELOG.md | sed '$d') \
    --prerelease
```

Notes:

- `--prerelease` marks it as a Beta on GitHub's own UI (grey "Pre-release"
  badge instead of the green "Latest") — remove once the project reaches
  a real `1.0.0`.
- `--notes-file` extracts the just-published `CHANGELOG.md` section for
  this version as the Release description, instead of writing release
  notes twice — the `sed` range prints from this version's heading up to
  (excluding) the next `## [` heading.
- `gh release create` also auto-generates GitHub's own "Source code
  (tar.gz)"/"(zip)" links regardless of whether `Release/Source/` is
  attached — this is expected, not a duplicate to remove (see §4's note
  on `Source/`).
- Both the tag push (→ PyPI, automatic) and `gh release create` (→ GitHub
  Release, explicit) publish something externally, irreversibly —
  confirm §5 passed and the Linux binary was smoke-tested (§2) before
  running either. Nothing before this point is visible outside the
  local machine.

### 6.1 PyPI — prerequisites, verified once (MC-002 P0-9)

`.github/workflows/publish.yml` already exists, is tag-triggered, and
uses PyPI's OIDC trusted publishing (no stored token in this repo) — it
had simply never been exercised. Checked once, ahead of the first real
release, without publishing anything:

- **Package name availability** — confirmed free:
  `curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/motorsport-calendar/json`
  returns `404` (PyPI's "no such project" response), not `200`.
- **Metadata validity** — `uv build && uvx twine check dist/*` (or
  `python -m build && python -m twine check dist/*`) reports `PASSED`
  for both the sdist and the wheel: `pyproject.toml`'s `[project]`
  table (description, README rendering, license, classifiers, URLs) is
  what PyPI will actually display.
- **Trusted publisher registration — not yet done, blocks the first
  publish.** PyPI's OIDC trusted publishing requires the project owner
  to register this exact GitHub repo + workflow file
  (`naviss29/motorsport-calendar`, `publish.yml`, environment `pypi`)
  on PyPI's own side *before* the first tag push — there is nothing to
  configure in this repo for that half, it happens on
  [pypi.org](https://pypi.org) under "Publishing" for a new project (or
  an already-owned one). Skipping this makes the `publish` job fail at
  the `id-token` exchange step, not silently no-op.
- **`Development Status :: 3 - Alpha` classifier** — still accurate for
  the current state; revisit only when the CTO actually calls this
  build a Beta/RC/stable release, not automatically at the first PyPI
  upload.

None of the above was executed as a real publish — this section is
preparation, confirmed safe to re-check any time without side effects,
not a substitute for the actual go-ahead to tag and push.

---

## 7. Housekeeping

- `Release/` should be added to `.gitignore` (same reasoning as `build/`
  — a regenerated local staging area, never a tracked directory).
- Re-run this entire procedure for every release; there is no
  incremental/partial release flow documented here on purpose — each
  Release folder is produced fresh from a clean, verified tree (§5).

---

## 8. Known gaps (tracked, not blocking this document)

- ~~The Linux build's `ModuleNotFoundError` blocker~~ — **fixed**, see
  `docs/PACKAGING.md` §7.
- ~~The Windows build fix is unverified~~ — **fixed and verified for
  real on a Windows 11 machine, Sprint RC-01**, see `docs/PACKAGING.md`
  §8 (build succeeded, binary launched, all 8 GUI pages visually
  confirmed rendering correctly, clean shutdown).
- ~~The embedded build version still reads `1.0.0` instead of the real
  version~~ — **fixed, MC-002 P0-5**, see `docs/PACKAGING.md` §7's own
  note. Only takes effect on a freshly-regenerated scaffold — §2/§3
  above now say to delete `build/` before every release build.
- ~~A pre-existing cosmetic UI bug found during the Sprint RC-01 visual
  walkthrough: the "Année par défaut" dropdown truncates its text~~ —
  **fixed, MC-002 (P0-8)**.
- No CI workflow runs any of this automatically yet — every step above
  is manual. A future GitHub Actions workflow triggered on tag push
  could run §2/§5/§6 (Linux) and, with a Windows runner, §3 — tracked in
  `docs/TODO.md`, not attempted this sprint.
- No code signing (Windows Authenticode, Linux package signing) — a
  Beta distributed to a small/trusted audience can reasonably skip this;
  a wider public release should not.
