"""Tests for PreferencesModel.

Sprint 52: repurposed to hold exactly the 3 "Application" fields the
brief asks to be prepared, not implemented (theme/language/time_format)
— the previous fields (timezone/first_day_of_week/favorite_championships/
preferred_calendar/bapps_sync_enabled) were all decorative and never
bound to anything real; retired in favor of this smaller, sprint-scoped
shape. See gui/models.py::PreferencesModel's own docstring.
"""

from __future__ import annotations

import pytest

from motorsport_calendar.gui.models import PreferencesModel


class TestPreferencesModelDefaults:
    def test_default_theme(self):
        assert PreferencesModel().theme == "dark"

    def test_default_language(self):
        assert PreferencesModel().language == "fr"

    def test_default_time_format(self):
        assert PreferencesModel().time_format == "24h"


class TestPreferencesModelFrozen:
    def test_frozen_cannot_set_theme(self):
        model = PreferencesModel()
        with pytest.raises((AttributeError, TypeError)):
            model.theme = "light"

    def test_frozen_cannot_set_language(self):
        model = PreferencesModel()
        with pytest.raises((AttributeError, TypeError)):
            model.language = "en"

    def test_frozen_cannot_set_time_format(self):
        model = PreferencesModel()
        with pytest.raises((AttributeError, TypeError)):
            model.time_format = "12h"


class TestPreferencesModelCustomValues:
    def test_custom_theme(self):
        model = PreferencesModel(theme="light")
        assert model.theme == "light"

    def test_custom_language(self):
        model = PreferencesModel(language="en")
        assert model.language == "en"

    def test_custom_time_format(self):
        model = PreferencesModel(time_format="12h")
        assert model.time_format == "12h"


class TestPreferencesModelEquality:
    def test_two_defaults_are_equal(self):
        assert PreferencesModel() == PreferencesModel()

    def test_different_language_not_equal(self):
        assert PreferencesModel(language="fr") != PreferencesModel(language="en")

    def test_different_theme_not_equal(self):
        a = PreferencesModel(theme="dark")
        b = PreferencesModel(theme="light")
        assert a != b


class TestPreferencesModelTypes:
    def test_theme_is_str(self):
        assert isinstance(PreferencesModel().theme, str)

    def test_language_is_str(self):
        assert isinstance(PreferencesModel().language, str)

    def test_time_format_is_str(self):
        assert isinstance(PreferencesModel().time_format, str)
