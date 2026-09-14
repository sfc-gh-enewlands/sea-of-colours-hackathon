"""TOASTIE_JAM declarations; counter_chaff owns purchase evidence and H4 timing.

The forge's `early` placeholder is retimed by the agency gate. Both the
compiled payload and model-facing instructions are updated at that boundary.
`always` builds a candidate only: the agency gate requires attributed live
discovery, our own chaff, and surviving rival purchase evidence before offering it.
"""

from __future__ import annotations

from .counter_chaff import COUNTER_HOUR
from .weapon_forge import EconomyPolicy, WeaponPlay

ECONOMY = EconomyPolicy()

PLAYS = (
    WeaponPlay(
        play_id="TOASTIE_JAM",
        weapon="chaff",
        when="always",
        hour="early",
        combines_with="smash_grab",
        title=f"TOASTIE_JAM: chaff at hour {COUNTER_HOUR}, anticipating an opening jam",
        why=(
            "a surviving single-orbit chaff-priced purchase suggests a rival "
            "could jam our opening drop on the pure we found; counter when "
            "their opening window lifts to deny their anticipated grab"
        ),
        rationale=(
            "COUNTER, not opener. The menu detail identifies a single-orbit "
            "purchase and an unspent-chaff hypothesis that still fits public "
            "launches and arsenal totals. Split purchases never qualify. "
            "An EMP plus SNAP bought together can look identical: neither "
            "chaff ownership nor an H1 launch is confirmed. "
            f"If they flare at H1, answer at H{COUNTER_HOUR}, not inside their jam. "
            "COMPARE: taking the pure or harvesting elsewhere may beat this "
            "counter. Chaff consumes its launch slot and self-jams during the "
            "carry-over window: the lost time is SYMMETRIC, not free tempo. "
            "If our own harvest during that window is worth more than denying "
            "their anticipated grab, do not fire. Holding the charge is valid."
        ),
    ),
)
