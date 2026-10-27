"""Tests for utils.paths — cross-platform user directories (Sprint 49).

No filesystem I/O: these functions only compute a Path, they never create
directories or touch disk (that remains the caller's job, e.g.
``HttpCache.__init__``'s own ``mkdir``). ``sys.platform``/env vars are
patched to exercise both the Windows and the Linux/XDG branch regardless
of which OS actually runs the test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from motorsport_calendar.utils.paths import user_cache_dir, user_config_dir


class TestUserConfigDirLinux:
    def test_uses_xdg_config_home_when_set(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch.dict("os.environ", {"XDG_CONFIG_HOME": "/tmp/xdg-config"}, clear=False),
        ):
            assert user_config_dir("motorsport-calendar") == Path(
                "/tmp/xdg-config/motorsport-calendar"
            )

    def test_falls_back_to_dot_config_when_xdg_unset(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch.dict("os.environ", {}, clear=False),
        ):
            import os

            os.environ.pop("XDG_CONFIG_HOME", None)
            assert user_config_dir("motorsport-calendar") == (
                Path.home() / ".config" / "motorsport-calendar"
            )

    def test_falls_back_when_xdg_config_home_is_empty_string(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch.dict("os.environ", {"XDG_CONFIG_HOME": ""}, clear=False),
        ):
            assert user_config_dir("motorsport-calendar") == (
                Path.home() / ".config" / "motorsport-calendar"
            )

    def test_app_name_is_the_last_path_component(self) -> None:
        with patch("sys.platform", "linux"):
            assert user_config_dir("my-app").name == "my-app"


class TestUserConfigDirWindows:
    def test_uses_appdata_when_set(self) -> None:
        with (
            patch("sys.platform", "win32"),
            patch.dict("os.environ", {"APPDATA": r"C:\Users\Alice\AppData\Roaming"}),
        ):
            result = user_config_dir("motorsport-calendar")
        assert result.name == "motorsport-calendar"
        assert "AppData" in str(result.parent)

    def test_falls_back_to_home_appdata_roaming_when_appdata_unset(self) -> None:
        # Only APPDATA is missing — USERPROFILE (which Path.home() needs on
        # Windows to resolve at all) is realistically always set by the OS,
        # unlike on Linux where a fully-cleared environ still resolves via
        # the pwd database. clear=True here would make Path.home() itself
        # raise, testing an environment that cannot occur in practice.
        with (
            patch("sys.platform", "win32"),
            patch.dict("os.environ", {}, clear=False),
        ):
            import os

            os.environ.pop("APPDATA", None)
            result = user_config_dir("motorsport-calendar")
        assert result == Path.home() / "AppData" / "Roaming" / "motorsport-calendar"


class TestUserCacheDirLinux:
    def test_uses_xdg_cache_home_when_set(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch.dict("os.environ", {"XDG_CACHE_HOME": "/tmp/xdg-cache"}, clear=False),
        ):
            assert user_cache_dir("motorsport-calendar") == Path(
                "/tmp/xdg-cache/motorsport-calendar"
            )

    def test_falls_back_to_dot_cache_when_xdg_unset(self) -> None:
        with (
            patch("sys.platform", "linux"),
            patch.dict("os.environ", {}, clear=False),
        ):
            import os

            os.environ.pop("XDG_CACHE_HOME", None)
            assert user_cache_dir("motorsport-calendar") == (
                Path.home() / ".cache" / "motorsport-calendar"
            )


class TestUserCacheDirWindows:
    def test_uses_localappdata_when_set(self) -> None:
        with (
            patch("sys.platform", "win32"),
            patch.dict("os.environ", {"LOCALAPPDATA": r"C:\Users\Alice\AppData\Local"}),
        ):
            result = user_cache_dir("motorsport-calendar")
        assert result.name == "motorsport-calendar"
        assert "AppData" in str(result.parent)

    def test_falls_back_to_home_appdata_local_when_localappdata_unset(self) -> None:
        # See the analogous APPDATA test above — only LOCALAPPDATA is
        # missing, USERPROFILE stays set.
        with (
            patch("sys.platform", "win32"),
            patch.dict("os.environ", {}, clear=False),
        ):
            import os

            os.environ.pop("LOCALAPPDATA", None)
            result = user_cache_dir("motorsport-calendar")
        assert result == Path.home() / "AppData" / "Local" / "motorsport-calendar"


class TestConfigAndCacheDirsAreDistinct:
    """Sprint 49 brief: config = roaming/persisted settings, cache = local,
    disposable data — never the same directory, on either platform."""

    def test_distinct_on_linux(self) -> None:
        with patch("sys.platform", "linux"):
            assert user_config_dir("motorsport-calendar") != user_cache_dir("motorsport-calendar")

    def test_distinct_on_windows(self) -> None:
        with (
            patch("sys.platform", "win32"),
            patch.dict(
                "os.environ",
                {
                    "APPDATA": r"C:\Users\Alice\AppData\Roaming",
                    "LOCALAPPDATA": r"C:\Users\Alice\AppData\Local",
                },
            ),
        ):
            assert user_config_dir("motorsport-calendar") != user_cache_dir("motorsport-calendar")
