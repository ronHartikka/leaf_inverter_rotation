# Interruption test — can rotation steal the fridge's off-periods for free?

Status: PLANNED (run after the next observed defrost + recovery). Uses the kitchen
fridge already on the rig — no new hardware. This is the cheap, high-value experiment
that tests the *central rotation hypothesis* on the real appliance before committing to
the replacement-freezer characterization.

## The question
Rotation works by cutting a load's power to give the inverter to another load. For the
fridge, the tempting free lunch is its **natural OFF periods** (~40% of the time, ~21 min
each): if we cut power during an off period and restore it before the box would have
needed the compressor, the fridge shouldn't even "notice." Does it? And how does the
answer depend on how long the power is off (Δt)?

## Two clocks — Δt is compared against each
The fridge's response is governed by two independent things, and the whole result is
"which threshold did Δt cross."

1. **Thermostat (thermal).** Start from a natural cut-out (box coldest, ~-6 F freezer,
   compressor already resting). While unpowered the box warms. The pivot is the **cut-in
   temperature** (~+4 F freezer):
   - Δt SHORT (box stays below cut-in): on restore the compressor **stays off** until it
     naturally reaches cut-in — identical to no interruption. **Thermally FREE.**
   - Δt ≈ off-period (box reaches cut-in): compressor starts ~when it would have anyway.
   - Δt LONG (box overshoots past cut-in): compressor starts after restore's start delay
     and runs **longer** to recover the overshoot. Cost grows with the overshoot.
   The kink is at the **natural off-period length** (~21 min). Below it, stealing the
   window is ~free; above it, it costs recovery run-time. **That kink is the single most
   important number for rotation feasibility.**

2. **Control-board counters (defrost scheduling).** Defrost is compressor-RUN-HOURS based
   (manual: 7-50 h; and **4 h after a power restore**). Risk: does every rotation
   interruption look like a "power restore" that re-arms the 4-hour defrost or resets the
   run-hour count? **Known data point:** a **3-min** unplug (2026-07-21) did NOT reset the
   counter (an *overdue* defrost fired from the retained count, not a fresh 4-h one). So
   brief interruptions preserve it. **Unknown:** the reset threshold — how long off before
   the board forgets. If short, frequent rotation could wreck defrost scheduling (defrost
   far too often, or frost building because it keeps resetting).

## Preconditions (get to a clean, safe starting state)
1. Run until the **next defrost** fires (validates the ~7-50 run-hour cadence — 3rd point).
2. Wait out the **recovery** (~2 h continuous run back to cut-out; see kitchen_fridge.json
   defrost.recovery_note).
3. Wait for a **natural cut-out** (compressor off, freezer ~-6 F). Starting from cut-out is
   deliberate: the compressor is already resting, so removing power has **no hot-restart
   hazard**, and it isolates the "interrupt during an off period" case.

## Procedure — a Δt sweep (one afternoon)
Power is removed by **unplugging the fridge from the gear socket** and restored by
replugging (the gear relay stays closed; the sketch keeps running; the ESP32/temps are on
separate power and keep logging through the interruption — the whole event is captured).

For each Δt in **~5, ~15, ~30, ~60, ~120 min** (extend if useful):
1. Wait for a fresh **cut-out** (freezer ~-6 F, compressor off). Note the wall-clock time.
2. **Unplug** the fridge from the gear socket. Note the time.
3. Wait **Δt**.
4. **Replug.** Note the time.
5. Watch the strip chart on restore and record what the fridge does (below).
6. **Let it return to normal cycling before the next trial** so trials don't contaminate
   each other. (Each trial + recovery ≈ up to an hour for the big Δt.)

Do the SHORT Δt first (cheapest, safest), working up. Stop early if a trial shows the box
crossing well past cut-in and you don't want the recovery cost.

## What to record (per trial)
- Cut-out time, unplug time, replug time (so Δt and "box temp at restore" are exact — the
  CSV pins them; the current column drops to ~0 while unplugged).
- On restore: does the compressor **stay off** (current ~0 until a later natural cut-in) or
  **start** (after how many seconds of start delay)? Peak/steady current if it runs.
- Freezer + fresh-food temp at unplug, at replug, and the peak.
- Whether the **fault/defrost pattern** shifts in the hours after (counter-reset watch).

## Predicted outcomes (so you know what you're seeing)
Freezer warmup while off is **NOT linear**: fast at first (air probe, ~0.3 F/min measured
short-term) then much slower as it couples to the frozen thermal mass (~3-4 F/hr over the
7-h outage coast). So cut-in (~+4 F, ~10 F above cut-out) is reached ~20-25 min in; beyond
that the rise tapers. Rough expectations (the experiment refines the warmup curve):
- **Δt ~5 min:** box ~+1-2 F, below cut-in → compressor **stays off** on restore. Interruption ~invisible. **Free.**
- **Δt ~15 min:** box near cut-in → borderline; likely stays off or starts right at restore.
- **Δt ~30 min:** box past cut-in (~+7-9 F) → compressor **starts** on restore, modest extra run.
- **Δt ~60 min:** box ~+12-18 F → longer recovery run.
- **Δt ~120 min:** box ~+20-25 F → significant recovery pull (approaching the post-defrost recovery regime).

## What each result means for rotation
- If short-Δt trials are **free** (compressor stays off, no counter disruption): the fridge's
  ~40% idle time is **stealable** — the rotation budget is far friendlier than additive
  free-running duties suggest. This is the hoped-for result.
- The Δt where cost starts (the kink) = **the max off-window rotation can take from the
  fridge "for free"** — a direct scheduler parameter.
- If any interruption **re-triggers defrost** (4-h-after-restore behavior) or resets the
  run-hour count: rotation must avoid power-cycling the fridge more often than that, or
  accept extra defrost load — a real constraint to design around.

## Open sub-question the sweep only partly answers
The **defrost counter reset threshold** needs watching defrost *timing* over the hours
AFTER long-Δt interruptions (does a defrost come at 4 run-hours post-restore, or does the
prior count resume?). The 3-min data point says short interruptions preserve the count; the
sweep's long-Δt trials + follow-on watching bracket the threshold.

## Relation to the replacement freezer
This fridge experiment tests "are off-periods stealable" on the appliance we have. The
**replacement freezer under interruption remains the eventual gating unknown** for the
budget (its duty is what the 3-load sum turns on). Replacement freezer: not yet ordered
(~2026-07-23), going **Energy Star for better insulation** — which should mean lower duty
and slower warmup (favorable, but re-measure; do NOT inherit the old unit's numbers).
