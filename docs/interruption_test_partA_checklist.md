# Part A — Δt sweep: at-the-rig checklist

Companion to `interruption_test.md` (Part A). Print/keep at the rig. Part A tests the
central rotation hypothesis: can we steal the fridge's natural OFF periods for free? Start
from a natural cut-out, pull power for a set Δt, restore, and watch whether the compressor
**stays off** (free — box never crossed cut-in) or **starts** (paid recovery run-time).
The number you're hunting is **the kink** — the Δt where free turns into costs recovery
(predicted near the ~21 min natural off-period; cut-in ~+4 F reached ~20–25 min in).

## Before you start (state check)
- [ ] Confirm a **defrost fired overnight** and fully **recovered** (compressor back to
      ~0.8 A cycling, freezer back to cut-out). Don't start mid-recovery — warm box
      contaminates the trial.
- [ ] Sketch still logging: current trace live on Ch4/"Spare" (array idx 3); both RTDs
      reading (`t1_freezer_f` = freezer, `t2_fridge_f` = fresh-food).
- [ ] Clock/phone for wall-times + a notepad. Times pin Δt and box-temp-at-restore (CSV
      timestamps them; current column drops to ~0 while unplugged).
- [ ] Have the afternoon: each trial + full recovery runs up to ~an hour for the big Δt.

## Per trial — repeat for Δt ≈ 5, 15, 30, 60, 120 min (SHORT FIRST)
- [ ] Wait for a **fresh natural cut-out**: compressor off, current ~0, freezer near
      coldest (~-4 to -6 F). **Note cut-out wall-time.**
- [ ] **Unplug the fridge from the GEAR SOCKET** (not the relay — gear relay stays closed,
      sketch keeps running). **Note unplug time.** Record freezer + fresh-food temp.
- [ ] Wait **Δt**.
- [ ] **Replug. Note replug time.** Record freezer + fresh-food temp.
- [ ] Watch the strip chart on restore and record:
  - Compressor **stays off** (current ~0 until a later natural cut-in) **or starts**?
    If it starts, **how many seconds of start delay** first.
  - Peak / steady current if it runs.
  - **Peak** freezer + fresh-food temp reached.
- [ ] **Let it return to normal cycling before the next trial** (no cross-contamination).
- [ ] **Stop early** if a trial pushes the box well past cut-in and you don't want the
      recovery cost.

## After the sweep (counter-reset watch)
- [ ] Keep logging the hours after the long-Δt trials — watch whether a **defrost comes
      ~4 run-hours post-restore** (counter reset) or the prior run-hour count resumes. The
      open sub-question the sweep only partly answers. (3-min unplug on 7/21 did NOT reset.)

## Predicted outcomes (so you know what you're seeing)
- **Δt ~5 min:** box ~+1–2 F, below cut-in → **stays off**. Interruption ~invisible. Free.
- **Δt ~15 min:** box near cut-in → borderline; likely stays off or starts right at restore.
- **Δt ~30 min:** box past cut-in (~+7–9 F) → **starts**, modest extra run.
- **Δt ~60 min:** box ~+12–18 F → longer recovery run.
- **Δt ~120 min:** box ~+20–25 F → significant recovery pull (approaching post-defrost regime).

## Safety notes (baked into the method)
- Starting from **cut-out** is deliberate: compressor already resting → **no hot-restart
  hazard**. Removing power during an off period isolates the "interrupt during idle" case.
- Cut-out target ~-6 F per `interruption_test.md`, but cleanest measured cut-out was
  **-3.6 F** — don't wait forever for -6 F if it's cycling out around -4 F.
