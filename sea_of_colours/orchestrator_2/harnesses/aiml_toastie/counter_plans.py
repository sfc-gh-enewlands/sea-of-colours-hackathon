"""Threat-conditioned previews of existing counter and harvest option IDs."""

from copy import deepcopy

from sea_of_colours.game.policy import MAX_MOVES

from . import counter_chaff, option_economics, packager, seam_control
from ._v7 import move_sanitizer


def preview(counter, harvest, view, *, day, day_cap, hazard_cells=()):
    options = deepcopy([counter, harvest])
    need = packager._harvester_demand(harvest)
    if need < 1 or need > len(packager._orbit_harvester_ids(view)):
        return None
    probes = sum(packager._probe_demand(option) for option in options)
    if probes > packager._probe_stock(view):
        return None
    kept, report = packager.reconcile_selected(options, view)
    if len(kept) != 2 or any(row["status"] == "dropped" for row in report):
        return None
    moves, _ = packager.pack_recipe(
        kept, view, forbidden_cells=set(hazard_cells),
        live_red_cells=set(seam_control._live_red(view)), complete=False,
    )
    if not moves or len(moves) > MAX_MOVES:
        return None
    sanitized, _ = move_sanitizer.sanitize_moves(
        deepcopy(moves), view, is_final_night=day >= day_cap,
        blue_is_loot=True, extra_bad_cells=set(hazard_cells),
        deploy_idle=False, release_vacated_cells=True,
    )
    if sanitized != moves:
        return None
    start = counter.payload["at_hour"]
    _, end = counter_chaff.chaff_window(start)
    launches = [index + 1 for index, move in enumerate(moves) if move["a"] == "chaff_flare"]
    if launches != [start] or any(move["a"] != "wait" for move in moves[start:end]):
        return None
    drops = [(index + 1, move) for index, move in enumerate(moves) if move["a"] == "drop"]
    pickups = [(index + 1, move) for index, move in enumerate(moves) if move["a"] == "pickup"]
    if len(drops) != need or len(pickups) != need:
        return None
    live = set(move_sanitizer._live_vision_cells(view))
    world = view.get("world") or {}
    width, height = int(world.get("width") or 40), int(world.get("height") or 28)
    positions = {}
    visited = set()
    for hour, move in enumerate(moves, 1):
        action = move["a"]
        if action == "probe":
            live.update(move_sanitizer._euclid_disk(*move["at"], width, height))
        elif action == "drop":
            cell = tuple(move["at"])
            if hour <= end or cell not in live or cell in positions.values() or cell in visited:
                return None
            positions[move["unit"]] = cell
            visited.add(cell)
        elif action == "step":
            cell = tuple(move["to"])
            current = positions.get(move["unit"])
            if current is None or abs(cell[0] - current[0]) + abs(cell[1] - current[1]) != 1:
                return None
            if not (0 <= cell[0] < width and 0 <= cell[1] < height):
                return None
            if cell in positions.values() or cell in hazard_cells or cell in visited:
                return None
            positions[move["unit"]] = cell
            visited.add(cell)
        elif action == "pickup":
            if positions.pop(move["unit"], None) is None:
                return None
    if positions:
        return None
    desired = set(option_economics.walk_cells(harvest.payload))
    actual = {tuple(move.get("at", move.get("to"))) for move in moves if move["a"] in ("drop", "step")}
    if not desired.issubset(actual):
        return None
    value = option_economics.yield_breakdown(list(actual), view)
    return {
        "plan": [counter.option_id, harvest.option_id], "moves": moves,
        "drop_hours": [hour for hour, _ in drops], "pickup_hours": [hour for hour, _ in pickups],
        "probes": probes, "harvesters": need, "potential_red": value.get("red_pts", 0),
    }


def comparison(registry, view, *, day, day_cap, hazard_cells=()):
    counter = registry.get(counter_chaff.PLAY_ID)
    if counter is None:
        return ""
    start = counter.payload["at_hour"]
    _, end = counter_chaff.chaff_window(start)
    lines = [
        "OPENING-CHAFF COMPARISON - precedes premium-red ranking",
        "Our previous-turn discovery and rival purchase evidence make H1 chaff highly likely under our policy, not confirmed orders.",
        f"Exposed opening grab: potential yield only without interference; against H1-H{start - 1} chaff its drop fails and the dependent outing banks 0.",
        f"Delayed grab without counter: avoids the opening window but allows rival entry at H{start}-H{end}.",
        f"TOASTIE_JAM + later harvest: denies rival H{start}-H{end} follow-up; our harvest starts after H{end}. Neither denial score nor later ownership is guaranteed.",
        "Enemy vision does not protect against global chaff. A later mass wave does not save the cancelled jackpot outing.",
        "Prefer TOASTIE_JAM over ITS_MY_GRILL_NOW under this predicted enemy-H1 scenario; shared stock still applies.",
        "chaff_react does not schedule protection. Select the actual option IDs below; these are alternative pairs, not extra composite moves.",
    ]
    candidates = []
    for option in registry.values():
        if option.kind not in ("grab", "chain", "seam", "hotdrop"):
            continue
        candidate = preview(counter, option, view, day=day, day_cap=day_cap, hazard_cells=hazard_cells)
        if candidate:
            candidates.append(candidate)
    candidates.sort(key=lambda row: (-row["potential_red"], len(row["moves"])))
    for row in candidates[:2]:
        lines.append(
            f"VALIDATED PAIR {row['plan']}: chaff H{start}; drops {row['drop_hours']}; "
            f"pickups {row['pickup_hours']}; 1 chaff, {row['harvesters']} harvester(s), "
            f"{row['probes']} probe(s). Potential red ~{round(row['potential_red'])} IF actions resolve and target value remains."
        )
    if not candidates:
        lines.append("No counter-plus-harvest pair passed validation. Do not invent a safe timeline; evaluate the remaining options.")
    lines.append("Validation covers this exact pair against the current view, not enemy behaviour. Extra selections/avoid constraints require revalidation; autofill can append later orders.")
    return "\n".join(lines)
