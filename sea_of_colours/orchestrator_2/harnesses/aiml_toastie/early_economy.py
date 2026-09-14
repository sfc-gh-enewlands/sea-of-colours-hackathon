"""Days 1-4: premium red first, otherwise blue rather than low-value red."""

from __future__ import annotations

from typing import Any, Mapping


def active(view: Mapping[str, Any], day: int | None = None) -> bool:
    if day is None:
        day = view.get("toastie_day", (view.get("meta") or {}).get("day", (view.get("hud") or {}).get("day")))
    return isinstance(day, int) and not isinstance(day, bool) and 1 <= day < 5


def category(option: Any, view: Mapping[str, Any]) -> str:
    from . import packager, value_pyramid

    payload = option.payload or {}
    if option.kind in ("probe", "supersede", "chaff", "emp", "snap"):
        return "support"
    if option.kind == "seam" or payload.get("signal_type") == "redsign":
        return "premium"
    _, cells = packager._footprint(payload)
    live, echo = value_pyramid._red_by_provenance(view)
    red = {**echo, **live}
    if any(red.get(cell, 0) >= value_pyramid._MASS_MIN for cell in cells):
        return "premium"
    blue = value_pyramid._all_blue(view)
    if (option.kind == "blue_grab" or payload.get("signal_type") == "blue_sign"
            or any(blue.get(cell, 0) > 0 for cell in cells)):
        return "blue"
    return "explore" if option.kind == "frontier" else "low_red"


def apply(registry: dict, view: Mapping[str, Any]) -> None:
    from . import packager
    from ._v7.move_sanitizer import sanitize_moves
    from types import SimpleNamespace

    if not active(view):
        return
    priorities = {"premium": 0, "blue": 1, "support": 2, "explore": 3}
    viable = {}
    for identifier, option in registry.items():
        group = category(option, view)
        if group == "low_red":
            continue
        if group in ("premium", "blue", "explore"):
            if packager._probe_demand(option) > packager._probe_stock(view):
                continue
            if packager._harvester_demand(option) > len(packager._Packer(view).harvesters):
                continue
            moves, _ = packager.pack_recipe([option], view, complete=False)
            moves, _ = sanitize_moves(moves, view, blue_is_loot=True, deploy_idle=False)
            if not moves or (group != "premium" and not any(move.get("a") == "drop" for move in moves)):
                continue
            if option.kind != "seam" and group == "premium" and not any(move.get("a") == "drop" for move in moves):
                continue
            if group == "premium" and option.kind != "seam" and option.payload.get("signal_type") != "redsign":
                actual = {"cells": [move.get("at", move.get("to")) for move in moves if move.get("a") in ("drop", "step")]}
                if category(SimpleNamespace(kind="chain", payload=actual), view) != "premium":
                    continue
        viable[identifier] = (option, group)
    registry.clear()
    has_resource = any(group in ("premium", "blue") for _, group in viable.values())
    for identifier in sorted(viable, key=lambda key: priorities[viable[key][1]]):
        option, group = viable[identifier]
        if group == "explore" and has_resource:
            continue
        option.payload["early_priority"] = group
        registry[identifier] = option


def directive(registry: Mapping[str, Any], view: Mapping[str, Any]) -> str:
    if not active(view):
        return ""
    premium = [key for key, opt in registry.items() if opt.payload.get("early_priority") == "premium"]
    blue = [key for key, opt in registry.items() if opt.payload.get("early_priority") == "blue"]
    target = (
        "Premium red first: " + ", ".join(premium)
        if premium else "No executable premium-red option: prioritise blue/bluesign " + (", ".join(blue) or "exploration")
    )
    if "TOASTIE_JAM" in registry:
        target = "Opening-chaff comparison takes precedence; premium red is potential value, not an instruction to launch at H1"
    return (
        "EARLY ECONOMY (days 1-4): " + target + ". "
        "Use spare capacity for blue to fund chaff; keep seeking blue on non-premium nights "
        "even when armed. Do not pursue vein/trace-only red. This overrides generic "
        "red-over-blue advice for low-value red only. Preserve support and recovery; "
        "if no resource route is viable, explore legally or wait."
    )


def eligible_chain(hint: Mapping[str, Any], view: Mapping[str, Any]) -> bool:
    from types import SimpleNamespace

    return category(SimpleNamespace(kind="chain", payload=hint), view) in ("premium", "blue")
