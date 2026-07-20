# Rotation budget — the make-or-break question

The whole project turns on one inequality: with 3 loads sharing one inverter
one-at-a-time, the **sum of their duty cycles must stay well under 100%**. If it
doesn't, no rotation schedule can keep all three adequately powered.

## Measured so far

| Load           | Running current | Duty cycle | Warmup (OFF)  | Status |
|----------------|-----------------|------------|---------------|--------|
| Dorm fridge    | ~0.68 A         | ~50%       | ~1.1 °F/min   | done (test piece, worst case) |
| Chest freezer  | ~0.72 A         | ~70%       | ~0.18 °F/min  | done — **flagged for replacement** (running over factory spec) |
| Kitchen fridge | ~0.75 A (meas.) | ~64% (prov.)| TBD (×2 compartments) | in progress |
| Furnace        | TBD             | TBD        | TBD           | later |

**Kitchen fridge — provisional, low confidence [2026-07-19/20 run].** Running
current ~0.75 A is a clean measured baseline from the pre-event current trace
(slightly above the ~0.7 A compressor class). Duty ~64% is a ROUGH eyeball from
the observed cycling before the overcurrent event: ON ~30 min, OFF ~20/20/10 min
(90 on / 50 off ≈ 64%). Caveats:
- EXCLUDES an initial ~6 h continuous pulldown (warm start during probe
  placement) — that's a transient, not steady-state duty.
- Warm-bench ambient; real cold-weather-outage duty runs lower (note ambient when
  finalizing). Off-windows were SHRINKING (20→20→10), consistent with a frosting
  evaporator heading into the defrost/overcurrent event — so even this window may
  run hot vs a defrosted steady state.
- Only ~2.3 h of cycling captured before the current column went stale at the
  00:38:17 overcurrent latch (valid current requires unix_s ≤ 1784522297).
- SUPERSEDE with `analysis/characterize.py` on the pre-event current column, per
  compartment. ~64% is only a sanity anchor. If it holds, a ~64% fridge is
  freezer-territory and hostile to a 3-load budget (see rule of thumb below).

## Where this stands
Dorm fridge (~50%) + chest freezer (~70%) already sum past 100% — but the dorm
fridge is a test piece and the freezer is being replaced, so neither is a final
deployment number. The real budget is: **kitchen fridge + replacement freezer +
furnace.** The fridge duty is the next input. A replacement freezer should land far
below 70% (the current unit's high duty is a low-charge/frost fault, not inherent to
chest freezers — its warmup rate proves the thermal mass is excellent).

Michigan outages are cold-weather events, so real-world duty runs below warm-bench
numbers — a tailwind, but don't rely on it to rescue a marginal budget.

## Rule of thumb
- 3 × 50% = 150% → impossible.
- 3 × 15–20% = 45–60% → feasible with margin.

Note ambient temperature with every duty-cycle observation; duty is strongly
ambient-dependent.
