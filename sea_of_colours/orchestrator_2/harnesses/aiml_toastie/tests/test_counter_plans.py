from copy import deepcopy

import pytest

from sea_of_colours.orchestrator_2.harnesses.aiml_toastie import (
    agency, counter_plans, early_economy, packager, prompt,
)
from sea_of_colours.orchestrator_2.harnesses.aiml_toastie._v7 import move_sanitizer


def scenario():
    view = {
        "meta": {"day": 3},
        "world": {"width": 40, "height": 28, "live": [
            {"x": 16, "y": 2, "tile": "RED", "purity": 255},
        ]},
        "red_tiles": [{"x": 16, "y": 2, "purity": 255, "freshness": "fresh"}],
        "my_assets": [{"id": "harvester_p2", "kind": "harvester", "state": "orbit"}],
        "entities": {"mine": [{"type": "probe", "pos": [15, 2], "nights_remaining": 2}]},
        "orbit": {"weapon_stock": {"chaff": 1}, "probe_stock": 1},
        "probe_stock": 1,
    }
    counter = agency.Option("TOASTIE_JAM", "chaff", "counter", "", payload={
        "weapon": "chaff", "at_hour": 4, "play_id": "TOASTIE_JAM", "stock": 1,
    })
    harvest = agency.Option("SMASH_GRAB", "seam", "grab", "", payload={"waves": [{
        "wave": 1, "earliest_hour": 1, "drop_at": [16, 2], "comb_path": [],
    }]})
    return view, counter, harvest


def test_pair_advertises_actual_compiled_and_sanitized_timeline():
    view, counter, harvest = scenario()
    original = deepcopy(view)
    result = counter_plans.preview(counter, harvest, view, day=3, day_cap=7)
    assert result is not None
    assert result["drop_hours"] == [7]
    assert result["pickup_hours"] == [8]
    moves, _ = packager.pack_recipe([counter, harvest], view, complete=False)
    actual, _ = move_sanitizer.sanitize_moves(
        moves, view, blue_is_loot=True, deploy_idle=False, release_vacated_cells=True,
    )
    assert result["moves"] == actual
    assert view == original


@pytest.mark.parametrize("failure", ["no_chaff", "no_harvester", "no_vision", "too_long", "hazard"])
def test_invalid_pair_not_advertised(failure):
    view, counter, harvest = scenario()
    hazards = set()
    if failure == "no_chaff":
        view["orbit"]["weapon_stock"]["chaff"] = 0
    elif failure == "no_harvester":
        view["my_assets"] = []
    elif failure == "no_vision":
        view["entities"]["mine"] = []
        view["world"]["live"] = []
    elif failure == "too_long":
        harvest.payload["waves"][0]["comb_path"] = [[coordinate, 2] for coordinate in range(17, 38)]
    elif failure == "hazard":
        hazards.add((16, 2))
    assert counter_plans.preview(counter, harvest, view, day=3, day_cap=7, hazard_cells=hazards) is None


def test_probe_route_and_budget():
    view, counter, harvest = scenario()
    view["entities"]["mine"] = []
    view["world"]["live"] = []
    harvest.payload["waves"][0]["probe_at"] = [15, 2]
    result = counter_plans.preview(counter, harvest, view, day=3, day_cap=7)
    assert result is not None
    assert result["drop_hours"] == [8]
    assert result["pickup_hours"] == [9]
    view["orbit"]["probe_stock"] = 0
    assert counter_plans.preview(counter, harvest, view, day=3, day_cap=7) is None


def test_comparison_overrides_economic_priority_in_actual_prompt():
    view, counter, harvest = scenario()
    registry = {counter.option_id: counter, harvest.option_id: harvest}
    menu = agency.format_menu_block(registry, agent_view=view, day=3, day_cap=7, probe_stock=1)
    assert menu.index("OPENING-CHAFF COMPARISON") < menu.index("EARLY ECONOMY")
    assert "VALIDATED PAIR ['TOASTIE_JAM', 'SMASH_GRAB']" in menu
    assert "drops [7]; pickups [8]" in menu
    assert "always execute" not in menu
    assert "potential, not secured" in menu
    assembled = prompt.build_prompt(
        agent_view=view, day=3, day_cap=7, vault_score=0, memory_replay="",
        chain_hints=[], option_menu_block=menu,
    )
    for false_claim in ("the CERTAIN play", "for CERTAIN", "ONLY CERTAINTY", "(sure)"):
        assert false_claim not in assembled
    assert "chaff_react does not schedule protection" in assembled


def test_no_threat_preserves_normal_priority():
    view, _, harvest = scenario()
    registry = {harvest.option_id: harvest}
    assert counter_plans.comparison(registry, view, day=3, day_cap=7) == ""
    assert "Opening-chaff comparison takes precedence" not in early_economy.directive(registry, view)


def test_no_valid_pair_is_explicit():
    view, counter, harvest = scenario()
    view["my_assets"] = []
    text = counter_plans.comparison({counter.option_id: counter, harvest.option_id: harvest}, view, day=3, day_cap=7)
    assert "No counter-plus-harvest pair passed validation" in text
    assert "VALIDATED PAIR" not in text


def test_overlapping_two_wave_harvest_is_not_recommended():
    view, counter, harvest = scenario()
    view["my_assets"].append({"id": "harvester_p2_2", "kind": "harvester", "state": "orbit"})
    harvest.payload["waves"].append(deepcopy(harvest.payload["waves"][0]))
    assert counter_plans.preview(counter, harvest, view, day=3, day_cap=7) is None


def test_preview_does_not_extend_beyond_move_cap(monkeypatch):
    view, counter, harvest = scenario()
    monkeypatch.setattr(counter_plans, "MAX_MOVES", 8)
    result = counter_plans.preview(counter, harvest, view, day=3, day_cap=7)
    assert result is not None and result["pickup_hours"] == [8]
    monkeypatch.setattr(counter_plans, "MAX_MOVES", 7)
    assert counter_plans.preview(counter, harvest, view, day=3, day_cap=7) is None
