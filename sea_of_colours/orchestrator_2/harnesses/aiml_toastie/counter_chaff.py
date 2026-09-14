"""Public, per-orbit purchase evidence for the H4 counter-chaff play.

Hypotheses retain both inventory and the purchase days of possibly unspent
qualifying chaff. A same-orbit mixed purchase remains an alternative; neither
a current arsenal total nor a missing observation establishes a purchase.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping, MutableMapping

from sea_of_colours.game.weapons import CHAFF_DURATION_HOURS
from sea_of_colours.game import weapons

from ._v7.opponent_weapons import _published_prices, decode_rack

COUNTER_HOUR = 1 + int(CHAFF_DURATION_HOURS)
PLAY_ID = "TOASTIE_JAM"
OFFENCE_ID = "ITS_MY_GRILL_NOW"
EVIDENCE_KEY = "toastie_purchase_evidence"
DISCOVERY_EVENTS_KEY = "toastie_discovery_events"
_ACTIVITY_KEYS = {"emp": "emps", "snap": "snaps", "chaff": "chaff"}


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _hypotheses(blue: int, prices: Mapping[str, int]) -> list[dict]:
    return [
        {"rack": rack, "qualifying_days": []}
        for rack in decode_rack(blue, prices) or []
    ]


def _advance(
    hypotheses: list[dict], launches: Mapping[str, int],
    purchases: list[dict], *, qualifies: bool, day: int,
) -> list[dict]:
    survivors = {}
    for hypothesis in hypotheses:
        rack = hypothesis["rack"]
        if any(rack.get(kind, 0) < count for kind, count in launches.items()):
            continue
        remaining = {
            kind: count - launches.get(kind, 0) for kind, count in rack.items()
        }
        tagged = hypothesis["qualifying_days"]
        fired = launches.get("chaff", 0)
        untagged = rack.get("chaff", 0) - len(tagged)
        minimum = max(0, fired - untagged)
        maximum = min(fired, len(tagged))
        for consumed in range(minimum, maximum + 1):
            for kept in set(combinations(tagged, len(tagged) - consumed)):
                for purchase in purchases:
                    updated = {
                        kind: remaining.get(kind, 0) + count
                        for kind, count in purchase.items()
                    }
                    days = tuple(sorted(
                        kept + ((day,) * purchase.get("chaff", 0) if qualifies else ())
                    ))
                    key = (tuple(sorted(updated.items())), days)
                    survivors[key] = {"rack": updated, "qualifying_days": list(days)}
    return list(survivors.values())


def observe(
    agent_view: Mapping[str, Any], previous: Mapping[str, Any] | None,
    *, day: int, session_id: str, viewer: str,
) -> dict:
    """Pure transition from the previous submitted day's public observation."""
    prices = _published_prices(agent_view) or {}
    raw_prices = ((agent_view.get("meta") or {}).get("rules") or {}).get("weapon_blue_costs")
    valid_prices = (
        bool(prices) and prices.get("chaff", 0) > 0
        and isinstance(raw_prices, Mapping) and set(raw_prices) == set(prices)
        and all(_integer(value) is not None and value > 0 for value in raw_prices.values())
        and all(kind in _ACTIVITY_KEYS and cost > 0 for kind, cost in prices.items())
    )
    state = {
        "version": 1, "day": day, "session_id": session_id, "viewer": viewer,
        "prices": prices, "opponents": {},
    }
    if not valid_prices:
        return state
    prior = previous or {}
    contiguous = (
        prior.get("version") == 1 and prior.get("day") == day - 1
        and prior.get("session_id") == session_id and prior.get("viewer") == viewer
        and prior.get("prices") == prices
    )
    intel = agent_view.get("station_intel") or {}
    activity_current = _integer(intel.get("night_day")) == day - 1
    for opponent in intel.get("opponents") or []:
        if not isinstance(opponent, Mapping):
            continue
        seat = str(opponent.get("seat") or "")
        if not seat or seat == viewer:
            continue
        arms = opponent.get("arms") or {}
        blue = _integer(arms.get("blue"))
        cap = _integer(arms.get("cap"))
        if blue is None or cap is None or blue > cap:
            continue
        initial = _hypotheses(blue, prices)
        if not initial:
            continue
        observation = {"blue": blue, "hypotheses": initial, "purchase_blue": None}
        state["opponents"][seat] = observation
        old = (prior.get("opponents") or {}).get(seat)
        if not contiguous or not activity_current or not old:
            continue
        activity = opponent.get("activity") or {}
        launches = {
            kind: _integer(activity.get(_ACTIVITY_KEYS[kind])) for kind in prices
        }
        if any(count is None for count in launches.values()):
            continue
        purchase_blue = blue - old["blue"] + sum(
            count * prices[kind] for kind, count in launches.items()
        )
        if not 0 <= purchase_blue <= cap:
            continue
        purchases = decode_rack(purchase_blue, prices) or []
        updated = _advance(
            old["hypotheses"], launches, purchases,
            qualifies=purchase_blue >= prices["chaff"], day=day,
        )
        if updated:
            observation.update(hypotheses=updated, purchase_blue=purchase_blue)
    return state


def prepare(
    agent_view: MutableMapping[str, Any], prior_entry: Mapping[str, Any] | None,
    *, day: int, session_id: str, viewer: str,
) -> dict:
    """Attach evidence before registry construction; caller persists on submit."""
    state = observe(
        agent_view, (prior_entry or {}).get(EVIDENCE_KEY),
        day=day, session_id=session_id, viewer=viewer,
    )
    agent_view[EVIDENCE_KEY] = state
    return state


def rival_blue_summary(agent_view: Mapping[str, Any]) -> str:
    state = agent_view.get(EVIDENCE_KEY) or {}
    parts = []
    for seat, observation in (state.get("opponents") or {}).items():
        days = sorted({
            day for hypothesis in observation.get("hypotheses", [])
            for day in hypothesis.get("qualifying_days", [])
            if hypothesis.get("rack", {}).get("chaff", 0) > 0
        })
        if days:
            amount = (state.get("prices") or {}).get("chaff")
            parts.append(
                f"{seat}: inferred at least {amount}-blue purchase in a single orbit "
                f"on day(s) {', '.join(map(str, days))}; a qualifying chaff "
                "could remain unspent (same-orbit mixed purchases also fit)"
            )
    return "; ".join(parts)


def rival_could_hold_chaff(agent_view: Mapping[str, Any]) -> bool:
    """Does an unspent, single-orbit qualifying purchase hypothesis survive?"""
    return bool(rival_blue_summary(agent_view))


def prepare_discovery(
    agent_view: MutableMapping[str, Any], last_night: Mapping[str, Any], *, viewer: str,
) -> None:
    """Keep only observer-filtered, successful own probe events as corroboration."""
    agent_view[DISCOVERY_EVENTS_KEY] = {
        "day": last_night.get("day"),
        "hours": sorted({
            event["hour"] for event in last_night.get("execution_log", [])
            if isinstance(event, Mapping)
            and event.get("kind") == "own" and event.get("seat") == viewer
            and event.get("tag") == "probe" and event.get("outcome") == "ok"
            and _integer(event.get("hour")) is not None and event["hour"] > 0
        }),
    }


def discovery_records(agent_view: Mapping[str, Any], *, mine: bool = True) -> list[dict]:
    """Live first-discovery credit, not just a currently visible pure square."""
    records = {}
    events = agent_view.get(DISCOVERY_EVENTS_KEY) or {}
    for beacon in agent_view.get("redsign") or []:
        if not isinstance(beacon, Mapping) or beacon.get("mine") is not mine:
            continue
        if "live" in beacon and beacon["live"] is not True:
            continue
        identifier = beacon.get("id")
        day = _integer(beacon.get("day"))
        hour = _integer(beacon.get("hour"))
        if not isinstance(identifier, str) or not identifier.strip():
            continue
        if day is None or day < 1 or hour is None or hour < 1:
            continue
        records[identifier] = {
            "id": identifier, "day": day, "hour": hour,
            "probe_corroborated": events.get("day") == day and hour in events.get("hours", []),
        }
    return [records[identifier] for identifier in sorted(records)]


def discovery_summary(agent_view: Mapping[str, Any]) -> str:
    return "; ".join(
        f"{record['id']}: engine credits us with discovery/co-discovery on "
        f"day {record['day']}, hour {record['hour']}; "
        + ("successful own probe event at the same time (corroboration only)"
           if record["probe_corroborated"] else "no matching successful probe event available")
        for record in discovery_records(agent_view)
    )


def format_discovery_block(agent_view: Mapping[str, Any]) -> str:
    evidence = discovery_summary(agent_view)
    if not evidence:
        return ""
    return (
        "OUR PURE-RED DISCOVERY\n" + evidence + ".\n"
        "This does not prove we were uniquely first. Rivals receive an anonymous "
        "fuzzy beacon, not our identity or the exact pure coordinates. "
        "TOASTIE_JAM requires discovery on the previous turn, our chaff and surviving rival purchase evidence; "
        "discovery alone does not authorise an offer.\n"
    )


def chaff_window(start: int) -> tuple[int, int]:
    return start, start + weapons.CHAFF_DURATION_HOURS - 1


def previous_turn_discovery(agent_view: Mapping[str, Any], *, mine: bool = True) -> bool:
    day = _integer((agent_view.get("meta") or {}).get("day"))
    if day is None:
        day = _integer((agent_view.get(EVIDENCE_KEY) or {}).get("day"))
    return day is not None and any(record["day"] == day - 1 for record in discovery_records(agent_view, mine=mine))


def chaff_guidance(agent_view: Mapping[str, Any]) -> str:
    start = 1 + weapons.CHAFF_DURATION_HOURS
    _, end = chaff_window(start)
    return (
        "OVERALL STRATEGY: bank blue to buy chaff in orbit for offence "
        "(ITS_MY_GRILL_NOW) and defence (TOASTIE_JAM). Orbit buys automatically "
        "when affordable and below the one-charge cap; both plays spend the SAME "
        "rack, not separate charges. Before day 5, premium red first, otherwise "
        "pursue blue/bluesign.\n"
        "OFFENCE: if ITS_MY_GRILL_NOW is offered, a rival discovered a live "
        "redsign on the previous turn and we hold chaff. Select H1 chaff to "
        f"cancel their anticipated opening drop across H1-H{start - 1}. "
        f"Pair it with an offered seam/hot-drop route starting at H{start} or "
        "later (a new probe may delay the actual landing). Their drop cancellation "
        "can invalidate follow-up steps. This creates an opportunity, not certain "
        "uncontested red: rivals also resume, and a fuzzy beacon hides exact pures.\n"
        f"CHAFF TIMING: a flare at H1 cancels opponents' actions at H1-H{start - 1}, "
        "including drops, probes, steps, pickups and weapon launches. No early hour "
        "is inherently safe. If the initial drop is cancelled, subsequent steps "
        "and pickup cannot work: the harvester never landed. Shortening a route "
        "does not protect its H1 drop. chaff_react reports a belief only; it does "
        "not shorten, delay, repair or counterfire a plan.\n"
        "COUNTER POLICY: when our live pure was discovered/co-discovered on the "
        "previous turn and a surviving rival hypothesis comes from at least one "
        "chaff's blue cost spent in a single orbit, treat enemy H1 chaff as HIGHLY "
        "LIKELY. This is our strategic prediction, not confirmed enemy orders. "
        f"If TOASTIE_JAM is offered, select this COUNTER at H{start}, cancelling "
        f"their H{start}-H{end} opening follow-up, rather than calling an H1 grab "
        "safe. It does not rescue actions already cancelled by their flare. "
        "The launcher spends the launch slot and is also jammed during carry-over "
        f"hours; plan our follow-up from H{end + 1}. Do not infer free harvest time "
        "inside our own chaff window. Retain recovery orders outside suspected "
        "windows. Weapon ownership remains ambiguous: same-orbit mixed purchases fit."
    )


def chaff_rack_block(agent_view: Mapping[str, Any]) -> str:
    stock = ((agent_view.get("orbit") or {}).get("weapon_stock") or {}).get("chaff", 0)
    if not stock:
        return ""
    cost = (_published_prices(agent_view) or weapons.BLUE_COST_BY_KIND)["chaff"]
    return (
        f"OUR CHAFF: {stock} charge(s), {cost} blue per charge. A flare cancels "
        f"opponents' actions for {weapons.CHAFF_DURATION_HOURS} consecutive hours "
        "starting at launch. The launch consumes one slot; carry-over hours "
        "also jam our own moves. Aim at a time window, not a cell.\n"
    )


def gate_menu(
    registry: MutableMapping[str, Any], agent_view: Mapping[str, Any],
) -> dict[str, str]:
    attack = registry.get(OFFENCE_ID)
    own_stock = ((agent_view.get("orbit") or {}).get("weapon_stock") or {}).get("chaff")
    if attack is not None:
        if not (_integer(own_stock) or 0) or not previous_turn_discovery(agent_view, mine=False):
            registry.pop(OFFENCE_ID)
        else:
            _, end = chaff_window(1)
            attack.payload["at_hour"] = 1
            attack.detail = (
                f"OFFENCE: rival discovery last turn; chaff at H1 denies H1-H{end}. "
                f"Pair with an offered harvest route from H{end + 1} onward. "
                "Shared chaff stock; the opening drop is predicted, not known."
            )
            attack.payload["denial_yield"] = (
                f"yield: OFFENSIVE DENIAL H1-H{end}: cancels opponents' opening "
                "probe/drop/step/pickup/launch actions and may invalidate dependent "
                "moves. WE BANK 0 directly; score denied is unknown. "
                "Our own carry-over hours are jammed too."
            )
            attack.execute_lines = [
                f"{OFFENCE_ID}: chaff_flare (H1, denies H1-H{end}, NO target cell); "
                f"follow-up starts no earlier than H{end + 1}"
            ]
    option = registry.get(PLAY_ID)
    if option is None:
        return {}
    stock = ((agent_view.get("orbit") or {}).get("weapon_stock") or {}).get("chaff")
    discovery = discovery_summary(agent_view)
    if not (_integer(stock) or 0) or not discovery or not previous_turn_discovery(agent_view):
        registry.pop(PLAY_ID)
        return {PLAY_ID: "withheld: own chaff and a live discovery attributed to us on the previous turn are required"}
    evidence = rival_blue_summary(agent_view)
    if not evidence:
        registry.pop(PLAY_ID)
        return {PLAY_ID: "withheld: no surviving single-orbit chaff purchase evidence"}
    was = option.payload.get("at_hour")
    start = 1 + weapons.CHAFF_DURATION_HOURS
    _, end = chaff_window(start)
    option.payload["at_hour"] = start
    option.payload["denial_yield"] = (
        f"yield: COUNTER DENIAL at H{start}-H{end}: cancels opponents' probe/drop/step/"
        "pickup/launch actions in that window. A cancelled enabling action may "
        "invalidate later actions. Score denied is unknown without their plan; "
        "WE BANK 0 directly. Our carry-over moves are jammed too."
    )
    option.detail = f"COUNTER: select for highly likely enemy H1 chaff. Fire at hour {start}, deny H{start}-H{end}. {discovery}. {evidence}."
    option.execute_lines = [
        f"{PLAY_ID}: chaff_flare (ONE launch move, hour {start}, denies H{start}-H{end}, NO target cell)"
    ]
    return {PLAY_ID: f"retimed from hour {was} to hour {start}"} if was != start else {}
