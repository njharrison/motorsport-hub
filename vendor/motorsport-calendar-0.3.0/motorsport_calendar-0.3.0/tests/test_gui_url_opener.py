"""Tests for gui.url_opener — Sprint 57 shared "open this URL" helper.

Promoted from 2 independent copies (``views/about.py``'s GitHub link,
``main_view.py``'s release-URL opener) once a 3rd real call site
("Soutenir le projet"'s GitHub Discussions/Issues buttons) made the
duplication concrete. No Flet page needed: ``url_launcher`` is a stub
with an ``AsyncMock``-style ``launch_url``, never a real
``ft.UrlLauncher()`` (which requires a live page/session to do anything).
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, patch

import pytest

from motorsport_calendar.gui.url_opener import make_url_opener


class _StubLauncher:
    def __init__(self, *, raises: bool = False) -> None:
        self.launch_url = AsyncMock(side_effect=RuntimeError("boom") if raises else None)


class TestMakeUrlOpener:
    async def test_success_calls_launch_url_with_the_given_url(self) -> None:
        launcher = _StubLauncher()
        opener = make_url_opener(launcher, "https://example.test/page")
        await opener(None)
        launcher.launch_url.assert_awaited_once_with("https://example.test/page")

    async def test_success_never_falls_back_to_subprocess(self) -> None:
        launcher = _StubLauncher()
        opener = make_url_opener(launcher, "https://example.test/page")
        with patch("subprocess.Popen") as mock_popen:
            await opener(None)
        mock_popen.assert_not_called()

    async def test_failure_never_raises(self) -> None:
        launcher = _StubLauncher(raises=True)
        opener = make_url_opener(launcher, "https://example.test/page")
        await opener(None)  # must not raise

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only fallback")
    async def test_failure_on_windows_falls_back_to_subprocess(self) -> None:
        launcher = _StubLauncher(raises=True)
        opener = make_url_opener(launcher, "https://example.test/page")
        with patch("subprocess.Popen") as mock_popen:
            await opener(None)
        mock_popen.assert_called_once()

    async def test_failure_on_non_windows_never_calls_subprocess(self) -> None:
        launcher = _StubLauncher(raises=True)
        opener = make_url_opener(launcher, "https://example.test/page")
        with patch("sys.platform", "linux"), patch("subprocess.Popen") as mock_popen:
            await opener(None)
        mock_popen.assert_not_called()

    async def test_windows_fallback_uses_the_given_url(self) -> None:
        launcher = _StubLauncher(raises=True)
        opener = make_url_opener(launcher, "https://example.test/specific-page")
        with patch("sys.platform", "win32"), patch("subprocess.Popen") as mock_popen:
            await opener(None)
        (command,), kwargs = mock_popen.call_args
        assert "https://example.test/specific-page" in command
        assert kwargs.get("shell") is True

    async def test_different_urls_produce_independent_openers(self) -> None:
        launcher = _StubLauncher()
        opener_a = make_url_opener(launcher, "https://example.test/a")
        opener_b = make_url_opener(launcher, "https://example.test/b")
        await opener_a(None)
        await opener_b(None)
        assert launcher.launch_url.await_args_list[0].args == ("https://example.test/a",)
        assert launcher.launch_url.await_args_list[1].args == ("https://example.test/b",)
