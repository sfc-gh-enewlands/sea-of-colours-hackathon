> ### This directory is yours — AIML_TOASTIE
>
> The baseline tour below was written about V12. The fork-specific changes
> are documented first. Two things
> to read past:
>
> - **"Don't edit this directory"** applies to `harnesses/tabula_v12/`,
>   the pristine baseline you are scored against. It does not apply here.
>   Edit anything in this directory you like — that is the exercise.
> - **The fork instructions** are how you got here. You do not need them
>   again unless you want a second agent.
>
> Rewrite this README as the description below stops being true. What you
> changed and why is what the league reads.

## TOASTIE_JAM: Purchase Evidence (Forge Phases 1-2)

### ITS_MY_GRILL_NOW: Opening Offence

When a live beacon records a rival discovery on the previous turn and we hold
chaff, offer ITS_MY_GRILL_NOW at H1. No enemy weapon-purchase evidence is needed.
At the current duration, it denies H1-H3, including the anticipated opening drop.
Select a separate offered seam/hot-drop route for H4 onward; a required probe
can put the actual landing at H5. The rival also resumes at H4, so uncontested
ground is an opportunity rather than a guarantee. Fuzzy beacons do not reveal
the exact pure coordinates.

Blue funds one shared chaff rack for this offence and TOASTIE_JAM's defence.
Orbit remains deterministic: buy when affordable and below the existing one-charge
cap. If both plays are offered, the model chooses; stock reconciliation retains
the first selected chaff play when only one charge exists and reports the excess.
The compiler also rejects duplicate/over-budget chaff selections. No harvest
geometry or harvester ownership is duplicated inside either weapon play.

### Early Economy (Days 1-4)

Executable redsign/pure/mass routes have priority. Otherwise prioritise blue
and bluesign to fund chaff, including with a single harvester and after the
first chaff is held. Vein/trace-only harvesting options are removed after the
registry's idle-fleet backstop; compiler completion cannot restore them.
Incidental low-value cells on a premium/blue route remain valid.

Lower-purity blue can be offered early where harvesting does not require
crushing a friendly probe. Existing vision, stock and sanitizer checks remain.
If neither premium red nor blue is executable, explore legally or wait.
Day 5 onward retains the previous thresholds and strategy. Buying remains
buy-ASAP with the existing one-chaff cap; seeking blue does not raise that cap.

This is an offline-tested policy, not evidence of improved season scores.

This fork offers an H4 counter-chaff only when we hold chaff, a live beacon
credits our discovery/co-discovery on the previous turn, and a rival has a surviving hypothesis of an unspent chaff bought
in one qualifying orbit. It remains a selectable option, not a forced shot.

The declaration uses `when="always"` to build a candidate, not to offer it
unconditionally. The harness gate requires a public-view beacon with `mine: true`
and valid `id`, `day`, and `hour`. Seeing a pure alone is not discovery credit.
The discovery block tells the model when we discovered/co-discovered it and
that rivals received an anonymous fuzzy beacon. It does not claim unique priority.

Successful own probe events at the same discovery day/hour corroborate the
timing but are optional: harvesters and existing probes can also discover seams.
No probe-to-seam causality is inferred from coincident timestamps. Attribution
is recorded while the beacon is live; counter eligibility requires its discovery
day to be the immediately previous game day.

Public observations expose arsenal value, not individual purchase transactions.
For consecutive planning days, inferred purchases equal current arsenal minus
previous arsenal plus the priced value of last night's observed weapon launches.
A purchase of at least the season's chaff price qualifies; 100 blue on one turn
and 200 on another do not qualify merely because the rack now totals 300.
An EMP and SNAP bought together remain indistinguishable from one chaff.

`counter_chaff.py` carries possible racks and qualifying purchase days through
the existing per-session/player memory in `harness.py`. Public consumption
retires hypotheses; missing history, unresolvable gaps, missing launch counts
or changed prices discard the evidence. First observations establish a baseline,
not a purchase. Existing frozen turns without this memory cannot qualify.

The agency hook withholds unsupported plays and aligns the payload, detail and
execution instructions to `1 + CHAFF_DURATION_HOURS` (currently H4). The installed
forge is unchanged. Chaff self-jams, so the rationale prices both sides' lost time.

Run the fork's tests explicitly; the shared pytest suite does not collect them:

```bash
python -m pytest sea_of_colours/orchestrator_2/harnesses/aiml_toastie -q
```

Generic wiring checks bypass this historical gate. They do not prove purchase
inference or actual model selection. Live commissioning remains Forge Phase 4.

### Observed Counter Failure and Phase 5 Correction

Fulgur_Marrow, day 3, p2: TOASTIE_JAM was offered with qualifying purchase and
discovery evidence. The model chose WALKIN_GRAB, SS1 and PR2, predicting an
early pickup before a supposed H6-H9 jam window. The replay shows p1 chaff at
H1, our drop cancelled, later steps failing because the unit never landed,
and p1 harvesting the pure at H5. There was no model fallback.

The fork now replaces inherited chaff safe-hour guidance in the actual prompt.
It explicitly recommends selecting the COUNTER when enemy H1 chaff is highly
likely under the gates above; this is a strategic prediction, not certain
enemy ownership or orders. `chaff_react` reports belief and does not rewrite
the route. H4 chaff denies H4-H6, derived from `game/weapons.py`; its yield text
no longer invents an H1 denial or a numerical score without an enemy plan.
The launcher still self-jams during carry-over, as demonstrated by the replay.

The original checker, frozen baseline and installed forge remain untouched.
Offline regressions do not prove the model will select the revised counter;
a controlled live replay remains necessary to measure that.

# V12 — the agent you fork

V12 is the LLM agent this distribution ships, and the baseline your
hackathon entry has to beat. It is strong at what it does and has two
deliberate holes. Closing either one is a good day's work; closing both
should win you the room.

**Don't edit this directory.** Fork it:

```bash
python scripts/soc.py new --team redwatch --name reaper \
    --participants "Ada Lovelace, Grace Hopper"
```

That copies these files to `harnesses/redwatch_reaper/`, repoints the
imports, renames the agent identity so your turns show up under your own
name in the audit trail, and writes the `agent.json` that registers it.
Nothing shared is edited. Restart the server and `REDWATCH_REAPER` is in
the New Game dropdown. Keeping V12 pristine
is what lets you answer "is my change actually better?" — you need
something to play against.

---

## The two gaps (this is the exercise)

### Gap 1 — it buys weapons and never fires them

V12 builds EMPs and chaff in orbit, then plays the whole night as if it
were unarmed. The stockpile just grows.

The buying half **is** yours to change (v1.40). It used to delegate to the
shared heuristic, which meant no fork could edit its own economy; the
policy now lives in the fork, with the thresholds hoisted into one
dataclass at the top of the file:

```44:75:sea_of_colours/orchestrator_2/harnesses/aiml_toastie/orbit_policy.py
@dataclass(frozen=True)
class OrbitDials:
    probe_target_stock: int = 4
    blue_always_build: int = 300
    blue_emp_roll: int = 250
    emp_stockpile_cap: int = 2
    # ... prices below are fallbacks; the engine's win
```

Retuning those is the cheapest experiment in the kit — `blue_always_build`
alone decides whether the seat is ever armed before night three. But note
the trap: **buying more weapons without closing the firing half makes the
agent worse**, because BLUE spent on an unused rack is BLUE not spent on
harvesters. The two halves of gap 1 have to move together.

The not-firing is structural. Check where you stand at any point with:

```bash
python scripts/soc.py weapons --agent <yours>
```

It walks four rungs and names the next action. They are ordered because
each is invisible until the one before it works — building doctrine
first changes nothing you can observe.

**Rung 1 — the agent does not know it owns a rack.** The only module in
the whole harness that reads `weapon_stock` is `orbit_policy.py`, the
buying code. `world_view.py` does not carry it and `prompt.py` never
says it. What the prompt *does* render is the opponents' estimated
arsenal, and only when a rival is thought to be armed. So the agent is
told what might be shot at it, and never what is in its own rack. Start
here: it is about twenty lines, and the change is immediately visible on
the card.

**Rungs 2–4** are the four places below that must all agree before a
salvo launches:

1. **The move schema doesn't allow it.** The LLM is physically unable to
   emit a weapon move, because the JSON schema constrains the verb to
   four values:

```43:43:sea_of_colours/orchestrator_2/harnesses/aiml_toastie/_v7/chat_schema.py
        "a": {"type": "string", "enum": ["drop", "step", "pickup", "probe"]},
```

2. **The option menu has no weapon plays.** `agency.build_registry()`
   registers seams, hot drops, probes, chains, supersedes and grabs.
   Nothing offensive. The model picks from this menu, so an absent
   option is an unthinkable move.
3. **The doctrine is defensive-only.** `doctrine.py` tells the agent how
   to *survive* an EMP (`DOCTRINE_BEWARE_EMP`) and how to shorten chains
   when chaffed, never how to use its own.
4. **The packager can't compile one.** Even a hand-written weapon
   selection wouldn't survive `packager.py` → `move_sanitizer.py`.

The engine supports all of it — `RED_HARVEST` (weapons on) fires both,
in `sea_of_colours/agent/heuristic_agent.py` around lines 2250–2410.
That's the reference for what legal weapon moves look like.

**Rough shape of the work:** widen the schema, add weapon options to the
menu, teach the doctrine when firing beats harvesting, extend the
packager and sanitizer to pass the new verbs through. Do them in that
order and you can test after each step.

### Gap 2 — it treats BLUE as an afterthought

BLUE funds the weapons economy, so gap 2 is partly *why* gap 1 stays
unexploited. V12 will grab blue, but only through a narrow gate, and
five separate mechanisms push in the same direction:

| Lever | Where | Current setting |
| --- | --- | --- |
| Purity floor before blue is even offered | `value_pyramid.py` | `_BLUE_GRAB_MIN = 192` |
| Blue must not cost a harvester a strong red chain | `value_pyramid.py` | `_STRONG_CHAIN_RED_MIN = 150` |
| Blue only "requested" when the vault is short **and** ≥2 harvesters live | `prompt.py` | `blue_is_requested()` |
| Blue chain hints suppressed unless requested | `harness.py` | `want_blue` gate |
| Doctrine explicitly ranks blue below red | `doctrine.py` | "RED always outranks blue for a scarce harvester" |

Loosening one lever alone usually does nothing, because another still
gates it. That is the interesting part of the problem.

---

## How a turn actually works

Read this before changing anything; most "my edit did nothing" reports
are edits to a stage that gets overridden two stages later.

```
run()                                    harness.py:284
  ├─ orbit? → orbit.py (heuristic, no LLM)
  └─ night:
      1. read memory, last night, journal
      2. PRECOMPUTE THE MENU  ← deterministic Python, no LLM
         chain hints · probe hints · hot drops · seam patterns
         · supersedes · frontier · grabs   →  agency.build_registry()
      3. THINK   → prose reasoning about the board        (LLM call)
      4. PLAN    → picks option ids, e.g. ["SMASH_GRAB", "PR2"]  (LLM call)
      5. resolve ids → concrete waves → packager compiles moves
      6. sanitize (fix illegal drops, collisions, self-crush)
      7. submit_policy()
      8. write the card + memory
```

The single most important thing to understand: **the LLM does not invent
moves. It picks ids off a menu that Python built.** If a play isn't in
the menu, no amount of prompt editing will produce it. That is why
"teach V12 to use weapons" is a code change, not a prompt change.

### What a "card" is

`card.py` is not part of the prompt — it is the **debug artifact**. One
human-readable page per turn: the prompt the model saw, the reasoning it
wrote back, and what that compiled to. Turn it on:

```bash
SOC_CARD_DUMP_DIR=/tmp/cards python run_web.py
# then read /tmp/cards/d03_p2.txt after night 3
```

This is the fastest debugging loop you have. When your agent does
something baffling, the card usually shows either a menu that didn't
contain the play you expected, or a plan that named an id the packager
then dropped.

---

## Where to make changes

| I want to… | Edit | Notes |
| --- | --- | --- |
| Add a named multi-wave play | `seam_control.py` | Add a `SeamPattern`; it's picked up automatically |
| Change what counts as worth grabbing | `value_pyramid.py` | The constants at the top |
| Add a new kind of play | `agency.py` `build_registry()` | Plus a builder module for the geometry |
| Change strategy advice | `doctrine.py` | Prose the model reads |
| Change *when* advice appears | `prompt.py` `_assemble_doctrine()` | State-gated |
| Change the output contract | `chat_schema.py` | Then packager + sanitizer must agree |
| Change move compilation | `packager.py` | Ids → concrete moves |
| Change move repair | `_v7/move_sanitizer.py` | Last line before submit |
| Change orbit buying | `orbit.py` | Currently delegates to the heuristic |

### `_v7/` — the substrate

Vendored from the retired `tabula_v7` harness when V12 was made
self-contained. Geometry, validators, hint compilers, the sanitizer.
Prefer changing `aiml_toastie/` proper; touch `_v7/` only for shared
infrastructure, and expect wider blast radius when you do.

---

## Dials you can turn without writing code

| Env var | Default | Effect |
| --- | --- | --- |
| `AIML_TOASTIE_SINGLE` | `0` | `1` skips the THINK/PLAN split — one LLM call, faster, dumber |
| `AIML_TOASTIE_AUTOFILL` | `0` | `1` lets the packager top up a short plan |
| `SOC_CARD_DUMP_DIR` | unset | Write a debug card per turn |

(In your fork these are renamed to your agent — `REDWATCH_REAPER_SINGLE`
and so on — so two teams on one machine don't fight over them.)

Tuning constants worth knowing: `_BLUE_GRAB_MIN` and
`_STRONG_CHAIN_RED_MIN` in `value_pyramid.py`, `_PROBE_FLOOR` in
`orbit.py`, `_MAX_PLAN_IDS` in `_v7/directive.py`.

---

## Testing your fork

```bash
# Scenario suite — fixed boards with assertions:
python -m sea_of_colours.orchestrator_2.evals.cli \
    --config redwatch_reaper --runtime cortex --backend memory

# Head-to-head against the baseline:
python scripts/run_matchup_v12.py --modes lite

# Fast sanity check, no credentials:
pytest sea_of_colours/orchestrator_2/tests -q
```

Your label works as an eval `--config` with no extra setup — the
`agent.json` in your own directory is the only registration there is.

## Known rough edges

Worth knowing before you spend an hour blaming your own change.

- **The finisher fallback is dead.** When the mover returns unparseable
  JSON, `harness.py` tries a "finisher" repair call
  (`CortexAgentInvoker(agent_name=FINISHER_AGENT_NAME)`) before giving
  up. That invoker talks to the Cortex **Agents API** and asks for an
  agent *object* — `SOC_RED_REAPER_TABULA_V7_FINISHER` — which was
  deleted along with the rest of the agent specs when V12 moved to
  Cortex inference over REST. So the repair call fails and the turn
  drops straight to `_heuristic_fallback_decision`. Effect is a worse
  recovery, not a crash. Repairing it (port the call to
  `CortexChatInvoker`) is a legitimate, self-contained hackathon win.
- **Orbit doesn't think.** `orbit.py` delegates to the shared heuristic,
  so the LLM has no say in what gets bought. If your strategy depends on
  buying different things, that is where to start.
- **`_v7` docstrings still say v7.** They describe the vendored
  substrate accurately; only the name is historical.

## Also worth reading

- `manual/agent.html` — one real V12 turn taken apart, percept to moves.
  Start here if the pipeline above felt abstract.
- `ENGINE_INTERFACE.md` (this directory) — the engine boundary a harness
  must respect.
- `../../README.md` — the plug-in contract, if you'd rather write an
  agent from scratch than fork this one.
- `RULEBOOK.md` — canonical rules. If the doctrine text and the RULEBOOK
  disagree, the RULEBOOK is right and the doctrine is a bug.
