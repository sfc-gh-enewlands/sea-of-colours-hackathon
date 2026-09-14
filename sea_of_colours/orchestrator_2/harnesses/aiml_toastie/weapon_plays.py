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
        play_id="ITS_MY_GRILL_NOW",
        weapon="chaff",
        when="always",
        hour="super_early",
        combines_with="blind_grab",
        title="ITS_MY_GRILL_NOW: cancel the rival's opening drop",
        why=(
            "a rival who discovered pure red last turn is likely to drop at H1; "
            "our opening chaff cancels that landing, creating a later grab opportunity"
        ),
        rationale=(
            "OFFENCE: select H1 chaff when this gate-qualified option is offered. "
            "A cancelled opening drop leaves subsequent harvester steps unable "
            "to work. COMPARE: racing a rival's anticipated H1 landing risks "
            "losing the pure or colliding; deny the opening before following an "
            "offered seam/hot-drop route after the chaff window. Carry-over "
            "self-jam also delays us. Neither enemy orders nor an uncontested "
            "pure are guaranteed. Both named plays draw from the same chaff stock."
        ),
    ),
    WeaponPlay(
        play_id="TOASTIE_JAM",
        weapon="chaff",
        when="always",
        hour="early",
        combines_with="smash_grab",
        title=f"TOASTIE_JAM: chaff at hour {COUNTER_HOUR}, anticipating an opening jam",
        why=(
            "a surviving single-orbit purchase of at least a chaff's blue cost "
            "and our previous-turn discovery make an enemy H1 jam highly likely; counter when "
            "their opening window lifts to deny their anticipated grab"
        ),
        rationale=(
            "COUNTER, not opener. Select this move when offered: the gate combines "
            "our previous-turn discovery with an unspent-chaff hypothesis from "
            "at least a chaff's cost purchased in ONE orbit. Treat an enemy H1 "
            "flare to cancel our initial drop as HIGHLY LIKELY. Separate smaller purchases never qualify. "
            "An EMP plus SNAP bought together can look identical: neither "
            "chaff ownership nor an H1 launch is confirmed. "
            f"If they flare at H1, answer at H{COUNTER_HOUR}, not inside their jam. "
            "COMPARE: an H1 grab is not a secure premium harvest in this scenario: "
            "a cancelled drop invalidates its subsequent steps and pickup. "
            "Counter their planned later entry instead. Chaff consumes its launch "
            "slot and self-jams during carry-over: the time cost is SYMMETRIC, "
            "not free tempo. Schedule our harvest after the counter window."
        ),
    ),
)
