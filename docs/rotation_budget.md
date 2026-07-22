# Rotation budget — the make-or-break question

The whole project turns on one inequality: with 3 loads sharing one inverter
one-at-a-time, the **sum of their duty cycles must stay well under 100%**. If it
doesn't, no rotation schedule can keep all three adequately powered.

## Measured so far

| Load           | Running current | Duty cycle | Warmup (OFF)  | Status |
|----------------|-----------------|------------|---------------|--------|
| Dorm fridge    | ~0.68 A         | ~50%       | ~1.1 °F/min   | done (test piece, worst case) |
| Chest freezer  | ~0.72 A         | ~70%       | ~0.18 °F/min  | done — **flagged for replacement** (running over factory spec) |
| Kitchen fridge | ~0.75 A (meas.) | ~60% night (meas.) | TBD (×2 compartments) | night baseline done; daytime capture till 10pm 2026-07-22 |
| Furnace        | TBD             | TBD        | TBD           | later |

**Kitchen fridge — night baseline measured [2026-07-21/22 fresh capture].**
~15 h continuous capture with the 3.5 A firmware; clean cycling, no false trips.
- Running current: variable-speed inverter — **~0.75 A steady** near setpoint,
  **~1.5 A during pulldown/recovery** (warm box, e.g. post-defrost).
- **Duty ~59-60%** over 11 h of overnight steady cycling (12 clean cycles: ON mean
  ~32 min, OFF mean ~21 min). Consistent with the 2026-07-19/20 shakedown's ~64%
  eyeball -> the fridge settles around ~60%.
- Freezer band ~-6 to ~+4-5 °F; food-safe throughout. (Per-compartment warmup rate
  + exact band: finalize after the daytime capture, on the full file.)
- Defrost characterized: ~29 min, ~1.8 A / 198 W, sensor-based adaptive. See
  loads/kitchen_fridge.json "defrost".
- STILL NIGHT-ONLY / "pre-stabilized": undisturbed, few door openings, night
  ambient. DAYTIME capture (running till 10pm 2026-07-22) will add the
  higher-duty, doors-open, warmer-ambient regime that reflects real use. Finalize
  day-vs-night duty + per-compartment thermal after that. ~60% is the night floor;
  daytime will likely be higher.

A ~60% fridge is freezer-territory duty and, on its own, hostile to a naive
3-load budget. But see "The real question" below — additive free-running duties
are NOT how this system will actually be scheduled.

## Where this stands
Dorm fridge (~50%) + chest freezer (~70%) already sum past 100% — but the dorm
fridge is a test piece and the freezer is being replaced, so neither is a final
deployment number. The real budget is: **kitchen fridge + replacement freezer +
furnace.** The fridge duty is the next input. A replacement freezer should land far
below 70% (the current unit's high duty is a low-charge/frost fault, not inherent to
chest freezers — its warmup rate proves the thermal mass is excellent).

Michigan outages are cold-weather events, so real-world duty runs below warm-bench
numbers — a tailwind, but don't rely on it to rescue a marginal budget.

## The real question — freezer duty UNDER INTERRUPTION is the gating unknown [2026-07-22]

The tempting arithmetic: fridge ~60% duty -> ~24 min/hr of free inverter time
(measured OFF windows 18-32 min, mean 21). Could the freezer live in that gap?
- Current (faulty) freezer ~70% duty needs ~42 min/hr -> takes ALL the offered gap
  and still falls behind. Doesn't fit.
- A healthy replacement (expected ~20-35%) needs ~12-21 min/hr -> the gap covers it
  with margin. Fits.
So the answer swings ENTIRELY on the replacement freezer's duty — a number we do
not have.

Do we have enough to answer confidently? NO. Three reasons, in priority order:
1. REPLACEMENT FREEZER NOT CHARACTERIZED. The current unit's ~70% is explicitly a
   low-charge/frost FAULT, not the deployment number. This is THE dominant unknown;
   the whole budget pivots on it.
2. FREE-RUNNING DUTY != DUTY UNDER INTERRUPTION. Duty measured under continuous
   power does not directly predict behavior when a box is force-cut for hours
   (recovery is deeper/longer, nonlinearly). Free-running 60%/70% are inputs to a
   guess, not the answer. Only measuring duty IN the interruption regime settles it.
3. REGIME MISMATCH. Intended use is HOURS-on / HOURS-off (not minute-scale
   gap-filling), and in the real system BOTH boxes get interrupted — the fridge will
   not free-run while the freezer sips its gaps. The clean "fridge runs / freezer
   fills gaps" picture does not hold in deployment.

=> NEXT REAL OBJECTIVE: characterize the REPLACEMENT freezer UNDER INTENTIONAL
   INTERRUPTION (simulate the hours-scale rotation blocks the system will actually
   run: power freezer alone, then freezer+fridge). Measuring duty in the deployed
   regime — not more free-running fridge data — is the single measurement that most
   moves the budget toward a confident yes/no. The fridge side is essentially done
   (~60% night baseline; daytime baseline in progress).

PRACTICAL NOTE (carry forward, do not chase the mechanism): the fridge tends to
DEFROST right when power is restored. So each multi-hour ON block in deployment may
open with a ~30 min 198 W defrost + recovery — budget for it; no need to understand
the trigger logic further.

## Rule of thumb
- 3 × 50% = 150% → impossible.
- 3 × 15–20% = 45–60% → feasible with margin.

Note ambient temperature with every duty-cycle observation; duty is strongly
ambient-dependent.
