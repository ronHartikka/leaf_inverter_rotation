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

## TWO different off-window numbers (they serve different regimes)
- **"FREE" window (~20 min):** Δt short enough that the box stays below cut-in, so the
  compressor just stays off on restore — zero cost, the fridge never notices. Good for
  FINE-GRAINED rotation (steal the natural idle gap). This is what Part A below measures.
- **"SAFE" window (hours):** how long power can be cut before a compartment crosses the
  40 F food-safety line, ACCEPTING a recovery run afterward. This is the binding number
  for HOURS-SCALE rotation (Ron's intended use: hours on / hours off). The free window
  (~20 min) is far too short for that; the safe window is what matters, and it is what the
  colder-setpoint and ice-block strategies EXTEND. Part B below measures it across configs.

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

## PART A — the Δt sweep (the FREE window)
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

## PART B — Outage-config coast experiments (the SAFE-window strategies)
Everything above (Part A) measures the ~20 min FREE window. Part B measures the SAFE
window — time to reach the 40 F food-safety line while unpowered — and how two cheap
strategies extend it. This is the number that governs HOURS-SCALE rotation, so it is
arguably the more important half for the deployed system.

Common measured output for every config: **COAST-TO-SAFETY per compartment** = from a
natural cut-out, cut power and let it warm; record the time for each compartment to reach
its Tmax (below), and the curve. Plus the recovery run needed to return to setpoint after.
(Same rig, same unplug-from-gear method; temps keep logging while unpowered.)

### Tmax (abort thresholds on OUR air RTDs) [decided 2026-07-23]
- **Tmax_fresh = 42 F**, **Tmax_freezer = 19 F.**
- Rationale: these are the fridge's OWN air excursions at defrost, which the manufacturer
  treats as food-safe (fresh air routinely hits ~40-42 F, freezer air ~16-19 F, every
  defrost, x4 observed). So they are manufacturer-demonstrated-safe air limits on our
  probes. Freezer 19 F also keeps food well FROZEN (below thaw), protecting quality;
  fresh 42 F gives real coast room above the ~37 F setpoint (the food lags/damps the air,
  so ~42 F air != food over 40 F).
- CAVEAT (timescale): the air-leads-food margin SHRINKS on hours-scale coasts (food
  catches up to air), so 42 F is generous for short excursions but tighter over hours.
  Validate with the food-simulant probe below before leaning on it for multi-hour offs.
- These are the abort thresholds for both the coast tests AND the deployment control law
  (P2+ "abort on either compartment's Tmax, restore power, hold until recovered").

Add a **food-simulant probe** for these runs: an RTD in a water bottle (or in an ice
block) beside the air probe, to measure FOOD temp vs AIR temp directly at the coast
timescale. This is what pins how far the air RTD can lead the food -> sets Tmax on data,
not guesswork. Do NOT map our air RTDs to the fridge's internal defrost/coil sensor: ours
read compartment AIR; the fridge's defrost sensor is on the evaporator COIL (heated to
50 F during defrost) -- a different coupling in defrost vs coast. Air is the right signal
for FOOD safety anyway (food lives in the air, not on the coil).

Four configs (do baseline first; add one variable at a time so effects are separable):

| Config        | Setpoint  | Ice blocks        | What it isolates                                  |
|---------------|-----------|-------------------|---------------------------------------------------|
| Baseline      | 3/5 lights| none              | current coast + steady duty (reference)           |
| Colder        | 4/5 lights| none              | Idea 1: coast GAIN vs the DUTY-cost penalty       |
| Mass          | 3/5 lights| +blocks/compartment| Idea 2: coast gain at ~no steady-duty cost        |
| Outage config | 4/5 lights| +blocks/compartment| the real deployment combo (both levers together)  |

Idea-1 note (colder setpoint): expect LONGER coast but HIGHER steady duty (bigger ΔT to
ambient -> more heat leak). It is a TRADE (buy coast with duty), not a free win. Record
both the new steady duty AND the coast gain so the trade can be judged. Food-safety is not
the concern (colder is safe); the duty penalty is. Current baseline: 3/5 lights gives RTD
averages ~0 F freezer / ~37 F fresh-food (good).

Idea-2 note (ice blocks): each block is labeled "= 7 lb ice" (~1000 BTU latent at 32 F +
~100 BTU sensible), pre-frozen and living in the CHEST FREEZER at ~0 F. In outages Ron
already moves a couple into EACH fridge compartment (leaving one in the chest freezer).
This adds coast runway with ~NO steady-duty cost (once frozen they are passive buffer;
they arrive pre-charged). Rough magnitude: fridge heat leak ~few hundred BTU/hr, so one
block ~ a couple hours of coast; two per compartment ~ many hours -> potentially the thing
that makes HOURS-off safe for the fridge. Compartment nuance: blocks buffer hardest at
their 32 F melt point -> ideal for fresh-food (~37 F); for the freezer (~0 F) they first
buffer cold (sensible) then, once at 32 F, hold the freezer up near 32 F -- warmer than
normal but still food-safe (<40 F). So expect the freezer to ride warmer during a long
coast WITH blocks, but stay safe far longer. Staging: blocks are already at ~0 F in the
chest freezer -> ready; just relocate before the Mass/Outage runs.

Part-B caveat: coast-to-40F runs take HOURS each (esp. with blocks) and warm the box
substantially -> each run needs a full recovery before the next. Budget a day+ for the
full four-config set; you need not run all four in one sitting.

## Relation to the replacement freezer
This fridge experiment tests "are off-periods stealable" on the appliance we have. The
**replacement freezer under interruption remains the eventual gating unknown** for the
budget (its duty is what the 3-load sum turns on). Replacement freezer: not yet ordered
(~2026-07-23), going **Energy Star for better insulation** — which should mean lower duty
and slower warmup (favorable, but re-measure; do NOT inherit the old unit's numbers).
