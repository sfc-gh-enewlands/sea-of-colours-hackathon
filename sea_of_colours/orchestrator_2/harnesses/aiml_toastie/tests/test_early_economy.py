from __future__ import annotations

from copy import deepcopy

import pytest

from sea_of_colours.orchestrator_2.harnesses.aiml_toastie import (
    agency, early_economy, orbit_policy, packager, prompt, value_pyramid,
)


def view(day=1, red=100, blue=100):
    return {
        "meta": {"day": day},
        "world": {"width": 40, "height": 40, "live": [
            {"x": 35, "y": 20, "tile": "BLUE", "purity": blue},
            {"x": 37, "y": 20, "tile": "RED", "purity": red},
        ]},
        "blue_tiles": [{"x": 35, "y": 20, "purity": blue, "freshness": "fresh"}],
        "red_tiles": [{"x": 37, "y": 20, "purity": red, "freshness": "fresh"}],
        "entities": {"mine": [{"type": "probe", "pos": [36, 20], "nights_remaining": 2}]},
        "my_assets": [{"kind": "harvester", "state": "orbit", "id": "harvester_p1"}],
        "orbit": {"weapon_stock": {"chaff": 1}},
        "probe_stock": 1,
        "last_night": {"incoming_attacks": [], "emp_scars": []},
    }


@pytest.mark.parametrize("day,expected", [(0, False), (1, True), (4, True), (5, False), (7, False)])
def test_day_boundary(day, expected):
    assert early_economy.active(view(day)) is expected


def test_single_harvester_requests_blue_even_when_armed():
    assert prompt.blue_is_requested(view())
    assert not prompt.blue_is_requested(view(5))


def test_blue_request_includes_fogged_bluesign():
    board = view()
    board["blue_tiles"] = []
    board["blue_sign"] = [{"cells": [[20, 20, 1.0]]}]
    assert prompt.blue_is_requested(board)
    board["my_assets"] = []
    assert not prompt.blue_is_requested(board)


def test_early_lower_purity_blue_but_not_friendly_probe_crush():
    assert (35, 20) in value_pyramid._rich_blue(view())
    assert not value_pyramid._rich_blue(view(5))
    board = view()
    board["entities"]["mine"][0]["pos"] = [35, 20]
    assert not value_pyramid._rich_blue(board)


def test_final_registry_rejects_vein_and_keeps_blue():
    board = view()
    registry = agency.build_registry(agent_view=board, harvesters_alive=1)
    assert any(option.kind == "blue_grab" for option in registry.values())
    assert all(early_economy.category(option, board) != "low_red" for option in registry.values())
    assert "No executable premium-red option" in early_economy.directive(registry, board)
    menu = agency.format_menu_block(registry, agent_view=board, day=1, day_cap=7)
    assert "BLUE FUNDING ROUTES" in menu
    assert "otherwise prioritise these, even with one harvester" in menu


@pytest.mark.parametrize("red", [151, 255])
def test_premium_red_before_blue(red):
    board = view(red=red)
    registry = agency.build_registry(agent_view=board, harvesters_alive=1)
    groups = [option.payload.get("early_priority") for option in registry.values()]
    assert "premium" in groups
    assert "blue" in groups
    assert groups.index("premium") < groups.index("blue")
    assert "Premium red first" in early_economy.directive(registry, board)


def test_day_five_filter_is_noop():
    registry = {"LOW": agency.Option("LOW", "chain", "", "", payload={"drop_at": [37, 20], "cells": []})}
    original = deepcopy(registry)
    early_economy.apply(registry, view(5))
    assert registry == original
    assert early_economy.directive(registry, view(5)) == ""


def test_unreachable_premium_does_not_win_over_blue():
    board = view(red=255)
    unreachable = agency.Option("REMOTE", "hotdrop", "", "", payload={
        "probe_at": [37, 19], "drop_at": [37, 20], "signal_type": "redsign",
    })
    blue = agency.Option("BLUE", "blue_grab", "", "", payload={"drop_at": [35, 20], "cells": []})
    board["probe_stock"] = 0
    registry = {"REMOTE": unreachable, "BLUE": blue}
    early_economy.apply(registry, board)
    assert "REMOTE" not in registry
    assert "BLUE" in registry


def test_completion_does_not_restore_low_red():
    board = view()
    compiler = packager._Packer(board)
    packager._complete_utilization(
        compiler, board, chain_hints=[{"drop_at": [37, 20], "cells": []}],
        probe_hints=[], supersede_hints=[],
    )
    assert not compiler.moves


def test_no_resources_retains_probe_exploration():
    board = view()
    board["red_tiles"] = []
    board["blue_tiles"] = []
    registry = {"SCOUT": agency.Option("SCOUT", "probe", "", "", payload={"at": [20, 20]})}
    early_economy.apply(registry, board)
    assert "SCOUT" in registry


def test_chaff_buying_keeps_existing_cap():
    board = {"orbit": {"credits": 6000, "blue_purity_total": 3000,
                      "weapon_stock": {"chaff": 1}, "probes": 4,
                      "harvesters": [{"id": "h1"}, {"id": "h2"}]},
             "my_assets": [], "blue_tiles": [], "red_tiles": []}
    actions, _ = orbit_policy.plan_orbit_actions(board, weapons_enabled=True)
    assert not any(action["a"] == "build_chaff" for action in actions)
    board["orbit"]["weapon_stock"] = {}
    actions, _ = orbit_policy.plan_orbit_actions(board, weapons_enabled=True)
    assert any(action["a"] == "build_chaff" for action in actions)


def test_priority_is_present_in_assembled_prompt():
    board = view()
    registry = agency.build_registry(agent_view=board, harvesters_alive=1)
    menu = agency.format_menu_block(registry, agent_view=board, day=1, day_cap=7)
    assembled = prompt.build_prompt(
        agent_view=board, day=1, day_cap=7, vault_score=0,
        memory_replay="", chain_hints=[], option_menu_block=menu,
    )
    assert "EARLY ECONOMY (days 1-4)" in assembled
    assert "Do not pursue vein/trace-only red" in assembled


def test_depleted_blue_does_not_surface_as_a_grab():
    board = view(blue=0)
    registry = agency.build_registry(agent_view=board, harvesters_alive=1)
    assert not any(option.kind == "blue_grab" for option in registry.values())


def test_incidental_vein_on_premium_route_is_preserved():
    board = view(red=255)
    board["red_tiles"].append({"x": 37, "y": 21, "purity": 100, "freshness": "fresh"})
    option = agency.Option("MIXED", "chain", "", "", payload={
        "drop_at": [37, 20], "cells": [[37, 21]],
    })
    registry = {"MIXED": option}
    early_economy.apply(registry, board)
    assert registry["MIXED"].payload["cells"] == [[37, 21]]
