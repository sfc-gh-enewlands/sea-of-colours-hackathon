"""Single-orbit purchase evidence, carried through observable inventory histories."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from sea_of_colours.game.weapons import BLUE_COST_BY_KIND, CHAFF_DURATION_HOURS
from sea_of_colours.orchestrator_2.harnesses.aiml_toastie import (
    agency, counter_chaff as counter, packager, weapon_forge, weapon_plays,
)


def board(blue=0, *, day=1, launches=None, own_stock=1, mine=True, prices=None):
    return {
        "meta": {"rules": {"weapon_blue_costs": dict(prices or BLUE_COST_BY_KIND)}},
        "orbit": {"weapon_stock": {"chaff": own_stock}, "probes": 4},
        "redsign": [{"id": "redsign-0", "day": 1, "hour": 5,
                     "mine": mine, "center": [10, 10], "cells": [[10, 10]]}],
        "grid": {"width": 32, "height": 32},
        "red_tiles": [{"x": 10, "y": 10, "purity": 255}],
        "station_intel": {
            "night_day": day - 1,
            "opponents": [{
                "seat": "P2", "arms": {"blue": blue, "cap": 600},
                "activity": {"emps": 0, "snaps": 0, "chaff": 0, **(launches or {})},
            }],
        },
    }


def observe(view, previous=None, *, day=1, session="game", viewer="P1"):
    return counter.observe(view, previous, day=day, session_id=session, viewer=viewer)


def eligible(state):
    return counter.rival_could_hold_chaff({counter.EVIDENCE_KEY: state})


def qualified():
    initial = observe(board())
    return observe(board(300, day=2), initial, day=2)


@pytest.mark.parametrize("blue", [0, 100, 200, 300, 600])
def test_first_observation_is_not_purchase(blue):
    assert not eligible(observe(board(blue)))


def test_split_purchases_never_qualify():
    state = observe(board())
    state = observe(board(100, day=2), state, day=2)
    state = observe(board(300, day=3), state, day=3)
    assert state["opponents"]["P2"]["purchase_blue"] == 200
    assert not eligible(state)


@pytest.mark.parametrize("purchase, expected", [(100, False), (200, False), (300, True), (400, False), (600, False)])
def test_only_exact_chaff_priced_single_orbit_qualifies(purchase, expected):
    state = observe(board(purchase, day=2), observe(board()), day=2)
    assert eligible(state) is expected


def test_mixed_purchase_is_preserved_as_an_alternative():
    hypotheses = qualified()["opponents"]["P2"]["hypotheses"]
    assert any(hypothesis["qualifying_days"] == [2] for hypothesis in hypotheses)
    assert any(hypothesis["rack"]["chaff"] == 0 for hypothesis in hypotheses)


def test_unchanged_nights_carry_evidence():
    state = qualified()
    for day in range(3, 8):
        state = observe(board(300, day=day), state, day=day)
        assert eligible(state)
    assert counter.rival_blue_summary({counter.EVIDENCE_KEY: state}).startswith(
        "P2: inferred 300-blue purchase in a single orbit on day(s) 2;"
    )


def test_public_chaff_launch_consumes_evidence():
    state = observe(board(0, day=3, launches={"chaff": 1}), qualified(), day=3)
    assert not eligible(state)


def test_snap_launch_rules_out_the_only_chaff_hypothesis():
    state = observe(board(200, day=3, launches={"snaps": 1}), qualified(), day=3)
    assert not eligible(state)


def test_launch_compensation_detects_replenishment():
    state = observe(board(200))
    state = observe(board(300, day=2, launches={"emps": 1}), state, day=2)
    assert state["opponents"]["P2"]["purchase_blue"] == 300
    assert eligible(state)


def test_chaff_replenishment_records_new_purchase_day():
    state = observe(board(300, day=3, launches={"chaff": 1}), qualified(), day=3)
    tagged = [hypothesis["qualifying_days"] for hypothesis in state["opponents"]["P2"]["hypotheses"]]
    assert [3] in tagged
    assert [2] not in tagged


def test_preexisting_chaff_may_be_spent_before_qualifying_chaff():
    state = observe(board(300))
    state = observe(board(600, day=2), state, day=2)
    state = observe(board(300, day=3, launches={"chaff": 1}), state, day=3)
    assert eligible(state)
    state = observe(board(0, day=4, launches={"chaff": 1}), state, day=4)
    assert not eligible(state)


@pytest.mark.parametrize("change", ["day_gap", "activity_day", "missing_launches", "prices", "session", "viewer"])
def test_uncertain_continuity_discards_evidence(change):
    view = board(300, day=3)
    kwargs = {"day": 3}
    if change == "day_gap":
        view = board(300, day=4)
        kwargs["day"] = 4
    elif change == "activity_day":
        view["station_intel"]["night_day"] = 1
    elif change == "missing_launches":
        del view["station_intel"]["opponents"][0]["activity"]["snaps"]
    elif change == "prices":
        view["meta"]["rules"]["weapon_blue_costs"]["chaff"] = 250
    else:
        kwargs[change] = "different"
    assert not eligible(observe(view, qualified(), **kwargs))


@pytest.mark.parametrize("blue", [None, -1, True, "300", "?", 700, 301])
def test_invalid_totals_do_not_qualify(blue):
    assert not eligible(observe(board(blue, day=2), observe(board()), day=2))


def test_missing_prices_do_not_infer_using_current_defaults():
    view = board(300, day=2)
    view.pop("meta")
    assert not eligible(observe(view, observe(board()), day=2))


def test_season_prices_are_used():
    prices = {"emp": 200, "chaff": 255}
    state = observe(board(prices=prices))
    state = observe(board(255, day=2, prices=prices), state, day=2)
    assert eligible(state)


def test_repeated_planning_uses_same_prior_without_mutation():
    prior = {counter.EVIDENCE_KEY: observe(board())}
    original = deepcopy(prior)
    first = counter.prepare(board(300, day=2), prior, day=2, session_id="game", viewer="P1")
    second = counter.prepare(board(300, day=2), prior, day=2, session_id="game", viewer="P1")
    assert first == second
    assert prior == original
    restored = json.loads(json.dumps({counter.EVIDENCE_KEY: first}))
    state = counter.prepare(board(300, day=3), restored, day=3, session_id="game", viewer="P1")
    assert eligible(state)


def test_real_registry_and_compiler_place_chaff_at_h4():
    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    registry = agency.build_registry(agent_view=view)
    option = registry[counter.PLAY_ID]
    assert option.payload["at_hour"] == 1 + CHAFF_DURATION_HOURS
    assert "hour 4" in option.detail
    assert "hour 4" in option.execute_lines[0]
    assert "hour 2" not in option.detail + " ".join(option.execute_lines)
    compiled = packager._Packer(view)
    packager._DISPATCH[option.kind](compiled, option.payload)
    assert compiled.moves == [
        {"a": "wait"}, {"a": "wait"}, {"a": "wait"},
        {"a": "chaff_flare"}, {"a": "wait"}, {"a": "wait"},
    ]


@pytest.mark.parametrize("case", ["no_evidence", "no_stock", "rival_redsign", "no_redsign"])
def test_registry_requires_all_three_gates(case):
    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    if case == "no_evidence":
        view.pop(counter.EVIDENCE_KEY)
    elif case == "no_stock":
        view["orbit"]["weapon_stock"]["chaff"] = 0
    elif case == "rival_redsign":
        view["redsign"][0]["mine"] = False
    else:
        view["redsign"] = []
    assert counter.PLAY_ID not in agency.build_registry(agent_view=view)


def test_declaration_valid_and_honest():
    assert weapon_forge.validate_all() == []
    assert weapon_plays.PLAYS[0].when == "always"
    assert "SYMMETRIC" in weapon_plays.PLAYS[0].rationale
    assert "EMP plus SNAP bought together" in weapon_plays.PLAYS[0].rationale


def test_invalid_partial_price_table_cannot_create_evidence():
    view = board(300, day=2)
    view["meta"]["rules"]["weapon_blue_costs"]["snap"] = "?"
    assert not eligible(observe(view, observe(board()), day=2))


def test_existing_memory_roundtrip_and_resolve_preserve_evidence(monkeypatch):
    from sea_of_colours.orchestrator_2.harnesses.aiml_toastie._v7 import memory
    from sea_of_colours.snowpark import backend

    monkeypatch.setattr(memory, "_IN_MEMORY_STORE", {})
    monkeypatch.setattr(backend, "snowpark_session_for", lambda store: None)
    first = memory.new_entry(1)
    first[counter.EVIDENCE_KEY] = observe(board())
    memory.save_entry("game", "P1", first)
    prior = memory.read_recent("game", "P1")[-1]
    view = board(300, day=2)
    second = memory.new_entry(2)
    second[counter.EVIDENCE_KEY] = counter.prepare(
        view, prior, day=2, session_id="game", viewer="P1",
    )
    memory.save_entry("game", "P1", second)
    memory.update_after_resolve("game", "P1", 2, actual_banked=10)
    restored = memory.read_recent("game", "P1")[-1]
    assert eligible(restored[counter.EVIDENCE_KEY])
    assert memory.read_recent("other", "P1") == []
    assert memory.read_recent("game", "P2") == []


def test_rival_histories_do_not_mix():
    first = board(0)
    first["station_intel"]["opponents"].append({
        "seat": "P3", "arms": {"blue": 100, "cap": 600},
        "activity": {"emps": 0, "snaps": 0, "chaff": 0},
    })
    second = board(300, day=2)
    second["station_intel"]["opponents"].append({
        "seat": "P3", "arms": {"blue": 300, "cap": 600},
        "activity": {"emps": 0, "snaps": 0, "chaff": 0},
    })
    state = observe(second, observe(first), day=2)
    assert any(hypothesis["qualifying_days"] for hypothesis in state["opponents"]["P2"]["hypotheses"])
    assert not any(hypothesis["qualifying_days"] for hypothesis in state["opponents"]["P3"]["hypotheses"])


@pytest.mark.parametrize("field,value", [
    ("mine", False), ("mine", None), ("mine", "true"), ("mine", 1),
    ("id", ""), ("day", None), ("day", -1), ("hour", None), ("hour", 0),
    ("live", False),
])
def test_invalid_discovery_withholds_despite_visible_pure(field, value):
    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    view["redsign"][0][field] = value
    assert counter.PLAY_ID not in agency.build_registry(agent_view=view)
    assert counter.format_discovery_block(view) == ""


def probe_memory(*, day=1, hour=5, seat="P1", kind="own", outcome="ok", tag="probe"):
    return {"day": day, "execution_log": [
        {"hour": hour, "seat": seat, "kind": kind, "outcome": outcome, "tag": tag},
    ]}


@pytest.mark.parametrize("override,corroborated", [
    ({}, True), ({"day": 2}, False), ({"hour": 6}, False),
    ({"seat": "P2"}, False), ({"kind": "orbital"}, False),
    ({"outcome": "failed"}, False), ({"tag": "drop"}, False),
])
def test_probe_event_is_optional_corroboration(override, corroborated):
    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    counter.prepare_discovery(view, probe_memory(**override), viewer="P1")
    assert counter.discovery_records(view)[0]["probe_corroborated"] is corroborated
    assert counter.PLAY_ID in agency.build_registry(agent_view=view)


def test_discovery_evidence_reaches_actual_prompt_and_menu():
    from sea_of_colours.orchestrator_2.harnesses.aiml_toastie import prompt

    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    counter.prepare_discovery(view, probe_memory(), viewer="P1")
    registry = agency.build_registry(agent_view=view)
    detail = registry[counter.PLAY_ID].detail
    assert "discovery/co-discovery on day 1, hour 5" in detail
    assert "corroboration only" in detail
    assembled = prompt.build_prompt(
        agent_view=view, day=2, day_cap=7, vault_score=0,
        memory_replay="", chain_hints=[],
    )
    assert "OUR PURE-RED DISCOVERY" in assembled
    assert "does not prove we were uniquely first" in assembled
    assert "anonymous fuzzy beacon" in assembled


def test_attributed_discovery_without_probe_event_is_still_known():
    view = board(300, day=2)
    counter.prepare_discovery(view, {"day": 1, "execution_log": []}, viewer="P1")
    assert len(counter.discovery_records(view)) == 1
    assert "no matching successful probe event available" in counter.format_discovery_block(view)


def test_seam_pattern_alone_cannot_manufacture_discovery_credit():
    from types import SimpleNamespace

    view = board(300, day=2)
    view[counter.EVIDENCE_KEY] = qualified()
    view["redsign"] = []
    registry = agency.build_registry(
        agent_view=view, seam_patterns=[SimpleNamespace(mine=True, waves=[])],
    )
    assert counter.PLAY_ID not in registry
