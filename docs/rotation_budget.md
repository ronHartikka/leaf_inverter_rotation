# Rotation budget — the make-or-break question

The whole project turns on one inequality: with 3 loads sharing one inverter
one-at-a-time, the **sum of their duty cycles must stay well under 100%**. If it
doesn't, no rotation schedule can keep all three adequately powered.

## Measured so far

| Load           | Running current | Duty cycle | Warmup (OFF)  | Status |
|----------------|-----------------|------------|---------------|--------|
| Dorm fridge    | ~0.68 A         | ~50%       | ~1.1 °F/min   | done (test piece, worst case) |
| Chest freezer  | ~0.72 A         | ~70%       | ~0.18 °F/min  | done — **flagged for replacement** (running over factory spec) |
| Kitchen fridge | ~0.7 A (expect) | **TBD**    | TBD (×2 compartments) | **NEXT** |
| Furnace        | TBD             | TBD        | TBD           | later |

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
