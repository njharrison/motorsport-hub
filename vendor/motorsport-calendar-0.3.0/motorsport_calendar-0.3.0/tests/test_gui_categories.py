"""Tests for motorsport_calendar.gui.categories."""

from __future__ import annotations

import pytest

from motorsport_calendar.gui.categories import (
    GROUPS,
    Category,
    ChampionshipGroup,
    get_groups_for,
)

# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


class TestCategory:
    def test_values_are_strings(self):
        assert Category.FORMULA == "formula"
        assert Category.ENDURANCE == "endurance"
        assert Category.MOTO == "moto"
        assert Category.RALLY == "rally"
        assert Category.AMERICA == "america"

    def test_is_str_subclass(self):
        assert isinstance(Category.FORMULA, str)

    def test_all_six_categories_defined(self):
        names = {c.name for c in Category}
        assert names == {"FORMULA", "ENDURANCE", "GT", "MOTO", "RALLY", "AMERICA"}

    def test_iteration_yields_all_members(self):
        assert len(list(Category)) == 6


# ---------------------------------------------------------------------------
# ChampionshipGroup
# ---------------------------------------------------------------------------


class TestChampionshipGroup:
    def test_frozen(self):
        group = ChampionshipGroup(
            category=Category.FORMULA,
            label="Formula",
            emoji="🏎",
            championship_ids=("formula1",),
        )
        with pytest.raises((AttributeError, TypeError)):
            group.label = "changed"

    def test_championship_ids_is_tuple(self):
        group = ChampionshipGroup(
            category=Category.ENDURANCE,
            label="Endurance",
            emoji="🏁",
            championship_ids=("wec", "elms"),
        )
        assert isinstance(group.championship_ids, tuple)
        assert group.championship_ids == ("wec", "elms")

    def test_equality(self):
        g1 = ChampionshipGroup(
            category=Category.FORMULA,
            label="Formula",
            emoji="🏎",
            championship_ids=("formula1",),
        )
        g2 = ChampionshipGroup(
            category=Category.FORMULA,
            label="Formula",
            emoji="🏎",
            championship_ids=("formula1",),
        )
        assert g1 == g2


# ---------------------------------------------------------------------------
# GROUPS registry
# ---------------------------------------------------------------------------


class TestGroups:
    def test_groups_is_non_empty_list(self):
        assert isinstance(GROUPS, list)
        assert len(GROUPS) >= 2

    def test_formula_group_present(self):
        formulas = [g for g in GROUPS if g.category == Category.FORMULA]
        assert len(formulas) >= 1

    def test_endurance_group_present(self):
        endurances = [g for g in GROUPS if g.category == Category.ENDURANCE]
        assert len(endurances) >= 1

    def test_formula_group_contains_formula1(self):
        formula_group = next(g for g in GROUPS if g.category == Category.FORMULA)
        assert "formula1" in formula_group.championship_ids

    def test_endurance_group_contains_wec(self):
        endurance_group = next(g for g in GROUPS if g.category == Category.ENDURANCE)
        assert "wec" in endurance_group.championship_ids

    def test_no_duplicate_championship_ids(self):
        all_ids: list[str] = []
        for group in GROUPS:
            all_ids.extend(group.championship_ids)
        assert len(all_ids) == len(set(all_ids)), "Duplicate IDs across groups"

    def test_all_groups_have_emoji(self):
        for group in GROUPS:
            assert group.emoji, f"{group.label} has empty emoji"

    def test_all_groups_have_label(self):
        for group in GROUPS:
            assert group.label, f"Group with category {group.category} has empty label"


# ---------------------------------------------------------------------------
# get_groups_for
# ---------------------------------------------------------------------------


class TestGetGroupsFor:
    def test_empty_input_returns_empty(self):
        result = get_groups_for([])
        assert result == []

    def test_formula1_only(self):
        result = get_groups_for(["formula1"])
        assert len(result) == 1
        group, ids = result[0]
        assert group.category == Category.FORMULA
        assert ids == ["formula1"]

    def test_groups_formula_and_endurance(self):
        result = get_groups_for(["formula1", "formula2", "wec"])
        categories = [g.category for g, _ in result]
        assert Category.FORMULA in categories
        assert Category.ENDURANCE in categories

    def test_formula_ids_in_declared_order(self):
        # IDs returned per group must follow the order declared in GROUPS
        result = get_groups_for(["formula2", "formula1", "formula3"])
        formula_result = next(r for r in result if r[0].category == Category.FORMULA)
        _, ids = formula_result
        formula_group = next(g for g in GROUPS if g.category == Category.FORMULA)
        expected_order = [cid for cid in formula_group.championship_ids if cid in ids]
        assert ids == expected_order

    def test_unknown_ids_collected_in_fallback(self):
        result = get_groups_for(["formula1", "unknown-series"])
        all_ids = [cid for _, ids in result for cid in ids]
        assert "unknown-series" in all_ids

    def test_unknown_ids_only_fallback(self):
        result = get_groups_for(["unknown-series"])
        assert len(result) == 1
        group, ids = result[0]
        assert group.label == "Autres"
        assert ids == ["unknown-series"]

    def test_no_empty_groups_returned(self):
        # If none of the available IDs belong to a registered group, that group is omitted
        result = get_groups_for(["wec"])
        for _group, ids in result:
            assert len(ids) > 0

    def test_all_available_ids_are_returned(self):
        available = ["formula1", "formula2", "wec", "unknown"]
        result = get_groups_for(available)
        returned = {cid for _, ids in result for cid in ids}
        assert returned == set(available)

    def test_full_registry(self):
        available = ["formula1", "formula2", "formula3", "f1-academy", "wec"]
        result = get_groups_for(available)
        returned = {cid for _, ids in result for cid in ids}
        assert returned == set(available)
        # Two groups expected (Formula + Endurance) — no fallback
        assert len(result) == 2

    def test_returns_list_of_tuples(self):
        result = get_groups_for(["formula1"])
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
        group, ids = result[0]
        assert isinstance(group, ChampionshipGroup)
        assert isinstance(ids, list)
