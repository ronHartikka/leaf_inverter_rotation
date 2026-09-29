# Jackery buffer mock-up — procedure

The experiment `docs/todo.md` queued on 2026-09-14 and left open on "decide WHAT to
record". That is now settled, because the instrument exists.

**Grid power. No inverter, no rig rotation, no Leaf.** This is the simplest form of the
buffer idea, run to see how the pair behaves before anything is wired into the rotation.

```
wall ──▶ rig socket ──▶ Jackery 300 Plus ──▶ kitchen fridge ──▶ (instrument in place)
          ~1 Hz                                                   60 windows/s
          CHARGING current                                         FRIDGE current
```

Both sides get measured at once, which is what resolves the measurement conflict
`todo.md` flagged: behind a battery the rig's channel sees charging, not the compressor.
Now it sees charging **on purpose**, while the fast instrument watches the fridge.

**The rig's 1 Hz chain is the right tool for the charging side** — a slow steady load is
what it does well. Its weakness (lesson #10, #11) is fast transients, and there are none
on that side.

## What this answers

1. **The Jackery's AC charging rate and profile.** The number the whole
   duty-cycle-decoupling argument turns on, because after this change the rig switches
   CHARGING, not the fridge. Constant-power or tapering decides whether it fits in
   rotation gaps.
2. **Whether the fridge runs normally behind a 300 W portable inverter.** Its current has
   a crest factor of **2.68** (`loads/kitchen_fridge.json`), so it demands ~2.7× its RMS
   in peak current. That is a real test of a small inverter, and a changed waveform on the
   output side would show it immediately.
3. **Whether duty genuinely decouples** — the fridge cycling on its own thermostat while
   the charging draw follows a different, schedulable pattern. The premise of the whole
   idea, demonstrated rather than argued.
4. **Round-trip efficiency.** Charging energy in versus fridge energy out, over a window
   with equal start and end state of charge. Expect 80–85%; it is a continuous tax on this
   unit, because the 300 Plus has no UPS bypass and always runs through its inverter.

## Before you start

- [ ] **Jackery partly discharged is BETTER, not worse.** The first charge cycle runs at
      full rate, which is the number being measured. A full battery would taper
      immediately and hide it.
- [ ] Note the Jackery's starting state of charge from its display.
- [ ] Fridge interruption costs ~7 min of anti-short-cycle. Budget it; it is not a fault.

## Run it

1. **Start both captures FIRST**, before plugging anything in. The insertion transient
   and the initial charge are the most informative part of the run — do not miss them by
   starting the capture afterwards.
2. Plug the Jackery into the rig socket; plug the fridge into the Jackery.
3. Note the wall-clock time of the plug-in, to line the two captures up.
4. Let it run through **at least two full fridge cycles** — about 2 h at the measured
   ~25 min on / ~28 min off.
5. Note the Jackery's state of charge at the end.

## While it runs

- [ ] **Check the Jackery's case temperature.** `docs/jackery_300_plus.md` records a
      vendor caution that sustained output *while charging* runs hot. This mock-up is
      exactly that condition, continuously.
- [ ] Confirm the fridge is actually cooling — this is the food-safety-critical load.

## Afterwards

Check both captures for gaps BEFORE analysing (lessons.md #11), then compare:

- charging profile against fridge draw — do they decouple in time?
- fridge RMS and **crest factor** against the direct-mains figures: 0.78 A and 2.68
- energy in vs energy out over a state-of-charge-neutral window

## Note on where the capture runs

The fridge instrument's capture should move to the **Ubuntu box** (`tools/serial_capture.py`)
rather than the Mac. The Ubuntu box does not sleep, which removes lesson #11's failure
mode entirely, and frees the Mac. That means carrying the Ubuntu laptop to the fridge —
USB will not span basement to upstairs — which is the direction
`docs/dual_logger_socket_ingest.md` is headed anyway.

Until then the Mac works, with `caffeinate -is` running and AC connected.
