# Jackery Explorer 300 Plus — as a power source in this system

Recorded 2026-09-14 from a working conversation. **Nothing here is measured on the
unit.** Specifications are from vendor/retail pages, not from the manual; every number
about the loads is from this repo's own measurements or its estimates, marked as such.

> **MODEL CONFIRMED 2026-09-29: Explorer 300 Plus.** Not the v2, so there is **no UPS
> bypass** — the output is always inverter-generated.
>
> That cuts both ways, and not as this doc originally assumed. **In favour of the buffer
> idea:** with no bypass there is no transfer at all when input power is removed, so the
> fridge sees nothing — not even the v2's ~20 ms. The seamlessness the scheme depends on
> comes for free. **Against:** conversion losses are paid CONTINUOUSLY, because the
> fridge's power goes through the inverter even while the wall is feeding it. Round-trip
> on a time-shifted watt-hour is likely 80–85%, so the fridge's ~26 W average becomes
> ~31 W as seen by the rig. Not fatal to the ~9 h of deferral the buffer buys, but a real
> tax that §3 did not account for.

## 1. Specifications (vendor sources, unverified against the manual)

- **288 Wh** capacity, LiFePO4
- **300 W continuous** AC, **600 W surge**, pure sine wave
- **Pass-through charging supported** — AC output can run while the wall charger is
  connected. One secondary source cautions that sustained high output *while* charging
  runs hot (its example: 200 W out plus the charger). Our use is milder; confirm
  against the manual.
- No UPS bypass on the Plus (that is the 300 v2).

Sources: jackery.com product page; outboundpower.com listing; Jackery's own
"can you charge and use at the same time" article.

## 2. Verdict per load

### Kitchen fridge — YES
Fits comfortably. Measured: running ~0.75 A (~86 VA), pulldown ~1.5 A, defrost heater
1.9 A (~218 VA), worst case the ~2 s defrost-entry overlap at 2.4–2.6 A (~276–300 VA),
which is inside the 600 W surge. No locked-rotor inrush — BLDC inverter compressor,
1.5 A peak measured.

**Energy: ~3–5 h** if it were the only source. Averaging 50–80 W (mean current 0.689 A
over the 3-day July capture, discounted for power factor), 288 Wh does not last long.
So the Jackery is not a fridge power *source* for an outage — see §3 for what it is
actually good for.

### Chest freezer — NO, on present evidence
Steady draw is fine (~0.72 A, similar to the fridge). **The start is the problem.** It
is the one load here with a true locked-rotor inrush (PTC-start induction compressor)
and **that surge has never been measured** — lessons.md #10 is explicit that the
~3.5 A figure is method-limited, since 10 Hz / 100 ms RMS cannot resolve a sub-100 ms
transient, and the true peak is likely higher. The 600 W surge ceiling is only ~5.2 A
at 115 V. That is an unmeasured number against a close ceiling.

A trip would not be harmless: lessons.md #2 — a PTC compressor re-energized while hot
stalls, draws locked-rotor, heats, trips its overload. A failed start could cascade
into repeated stall attempts rather than a clean shutdown.

**This is the single strongest argument for the queued scope measurement of the chest
freezer's starting surge.** It answers this question, inverter sizing, and the
pre-power-overlap idea at once.

### Furnace — NO, and the reason is the igniter, not the blower
Per-stage estimates from `loads/furnace.json` (all `confidence: low`, cube-law
derived, **none measured**): low 79 W / 0.8 A, medium 126 W / 1.2 A, **high 426 W /
4.0 A**. High fire exceeds the 300 W continuous rating outright. Power factor is
recorded as `null` / `confidence: none`; an ECM drive without active PFC can run
PF 0.5–0.6, which would nearly double apparent power.

**Locking to low fire does not solve it.** The igniter fires *"once per heat call, all
stages"*. Estimated at 2.4 A / 260 W for **17 seconds**, resistive, with the inducer
running alongside: low fire totals roughly **310 W sustained for 17 s**, already past
the continuous rating on estimates alone — and the file warns the silicon-nitride
element's cold resistance is low, so expect a higher spike in the first second.
17 seconds is not a surge that a 600 W peak rating covers.

Also: the furnace is **hardwired**, not cord-and-plug (see `outage_procedures.md` §8).

**Energy, corrected.** An earlier figure of "3½ hours" in conversation was *burn* time,
not wall-clock — a furnace cycles. **ASSUMING** 25–35% duty at low fire in a cold house
(an assumption; furnace duty is still TBD in `rotation_budget.md`), average draw
including the 12 W standby lands near 30–40 W, so 288 Wh would carry roughly **7–10 h
of wall clock**. Materially better than the burn-time figure suggests.

**Testable, safely:** warm weather, grid up, furnace on the Jackery, `Check out →
Furnace` with low-heat time set and high-heat set to 0. That forces the full ignition
sequence on demand, displays live status, and leaves no stored setting behind. If it
rides through ignition, the running stage follows immediately.

## 3. The actual best use: a buffer, not a source

Ron's idea. **Rig socket → Jackery → fridge.** The rig's relay then controls only
whether the Jackery is *charging*; the fridge sees an unbroken supply.

What that buys:

- **No ~7-minute anti-short-cycle** after a swap — the fridge never loses power.
- **No 4-second defrost-heater pulse** on every power-on.
- Cooling **decoupled from the rotation schedule**: charge while the inverter is free,
  let the fridge run on battery while the freezer needs the inverter. It time-shifts
  the fridge's energy rather than reducing it — which is what rotation actually needs.
- Double-conversion loss is real but small (order 10 W), negligible beside the LEAF's
  ~450 W idle.

### Costs and unknowns

- **The charging draw is a new unknown and may exceed the fridge's own draw.** If the
  Jackery pulls 200–300 W while charging, that changes the rotation arithmetic against
  the 1 kW inverter — trading a small intermittent load for a larger schedulable one.
  **Is the charge rate settable?** Some Jackery models expose that in the app. A limited
  charge rate would make it far better behaved here. UNKNOWN.
- **It blinds the rig's current sensor to the fridge.** Behind a battery, the rig's
  channel measures the Jackery charging, not the compressor — no cycling signal, no
  duty cycle, `compressor_on` meaningless on that channel. Two ways out: §4 or §5.
- **Ordering:** this is a DEPLOYMENT configuration, not a characterization one. Do the
  free-running both-loads capture first, add the buffer after — unless §5 lands first.

## 4. Reading data from the Jackery itself

The Plus series supports Bluetooth and Wi-Fi through the Jackery app. Community
integrations exist, including one that talks **directly over BLE with no cloud, no
Jackery account and no internet**, built by analysing traffic between the official app
and the device; others go through Jackery's cloud API and republish over MQTT.
(`theak/jackery-homeassistant`; `Wlad2288/Ultra_Jack`; Home Assistant community thread.)

These report battery status, **power output**, input and temperature. Output power *is*
the fridge's draw, so this would dissolve the blinding problem in §3.

Caveats:

- **Unofficial, reverse-engineered, model-specific.** The repos name the Explorer 2000
  Plus. Whether the 300 Plus speaks the same BLE protocol is unestablished.
- **Seconds-scale polling.** Fine for duty cycle and energy — ~86 VA running against
  ~12 W idle is unmistakable. Useless for transients; that stays scope-and-shunt work
  per lessons.md #10.
- It would be **another one-way sender**, which fits the listener architecture in
  `docs/dual_logger_socket_ingest.md` — same clock, same merge.
- Convenient: the Ubuntu box already has a Bluetooth dongle attached
  (`0a12:0001 Cambridge Silicon Radio`, seen in `lsusb` 2026-09-12). **Unconfirmed**
  whether that part is BLE-capable or Bluetooth-only.

## 5. Better: our own sensing point between Jackery and fridge

Ron's preference, and the stronger option — our own sensor, our clock, our line format,
10 Hz, no dependence on a protocol someone reverse-engineered for a different model.

- The fridge is **upstairs, out of USB reach**, so this has to be its own node
  reporting over WiFi. That is precisely what the socket-ingest design turns
  `dual_logger` into: a listener with several one-way senders.
- **A relay is probably worth including** — for the overcurrent trip (already scaled to
  3.5 A for this fridge) and for deliberate coasting experiments while the Jackery
  stays charged. It should NOT be used for routine rotation: cutting the fridge from
  the Jackery re-imposes the very ~7-minute penalty the buffer exists to avoid.
- **Hardware gotcha, decide before buying or soldering.** The ACS712 is a 5 V
  ratiometric part with a 2.5 V zero. That is above an ESP32's 3.3 V ADC range, so an
  ESP32 node needs a divider — and a divider breaks the ratiometric relationship the
  sensing depends on. `firmware/shared/current_sense.h` also sanity-checks the auto-zero
  against a ~2.3–2.7 V window that assumes the 5 V arrangement (lessons.md #4). **A 5 V
  Arduino upstairs sidesteps all of it and reuses the shared code unchanged.**
- The no-relay version is the minimum that lets the buffer and the measurement coexist.
  The relay can be added later without changing the sensing.

## 6. Open questions

- [ ] Which unit is it — 300 Plus or 300 v2? (Ron checking the manual.)
- [ ] Does the manual confirm pass-through charging, and does it caution about it?
- [ ] What is the AC charging draw, and is the charge rate settable?
- [ ] Does the 300 Plus expose the same BLE protocol the community integrations use?
- [ ] Is the Ubuntu box's CSR dongle BLE-capable?
- [ ] Chest freezer starting surge — the measurement that decides §2.
- [ ] **The mock-up (§7): what to record. NOT YET DECIDED — to be settled with Ron.**

## 7. Queued: mock it up

**Plug the Jackery into a wall outlet, plug the fridge into the Jackery, and record.**
Grid power, no rig, no inverter — the simplest possible version of §3, to see how the
combination behaves before it is wired into anything.

**What to record is deliberately left open** — Ron: *"record … what? We'll talk about
it soon."* Candidates raised so far, for that conversation, none chosen:

- AC charging draw while the fridge runs, and whether it is steady or bursty
- Whether the Jackery holds the fridge through a defrost (its ~218 VA / ~29 min)
- Battery state of charge over a full fridge cycle — does it net-gain while plugged in?
- Whether pass-through runs hot over hours
- Whether the fridge's ~7-min startup delay and 4-s heater pulse really do disappear
- Fridge duty cycle as seen from this configuration, for comparison with the
  free-running capture

---

## 9. MEASURED — the buffer mock-up, 2026-09-29

The experiment §7 left open. Run on grid power with no inverter and no rotation: the
fridge on Jackery battery alone, current measured by `firmware/esp32_ads1115_cycle_stats`
at 60 windows/s (`fridge_on_jackery.txt`, logged on the Ubuntu box). A defrost fired
during the run, so this became the worst case the buffer would ever face rather than the
steady-state test intended.

### The fridge runs normally behind it

Crest factor **2.73–2.76** on the Jackery against **2.68** on wall power, measured minutes
apart with the same sensor and the same fridge. Current comparable. **A 300 W portable
inverter handles this load's waveform without visible distress** — that was a real
question, since the fridge draws ~2.7× its RMS in peak current.

### Discharge, measured at two load levels

| phase | delivered | pack draw | rate | efficiency |
|---|---|---|---|---|
| defrost heater | 187 VA | ~243 W | **1.41 %/min** | **77%** |
| recovery run | ~73 W | ~84 W | **0.48 %/min** | **~85%** |

Efficiency is better at the lower load, as expected. These are the first measured
round-trip figures for this unit; §3 had assumed 80–85% without evidence.

### A defrost costs 43% of a full pack

100% → 57% over a 30.4 min heater period: **124 Wh from the pack to deliver ~95 Wh.**

Worse in Battery Save, which is the mode to actually run: charging stops at 85% and output
**cuts at 15%**, so usable capacity is 70% ≈ **202 Wh**. A defrost eats **61% of that**.

**The 15% cutoff is a hazard, not just a limit** — it drops the fridge with no warning,
and restoring power afterwards is another power-cycle on a box that is already warm.
Abort to wall power well before it.

### Charging — the number the whole argument needed

**207 W input while simultaneously delivering 70 W**, giving **~137 W net into the pack**
and ~0.8 %/min. Pass-through works; the fridge never noticed the changeover.

**This is what converts the fridge from a rotation problem into a scheduling one:**

- Before: **~47% duty, thermostat-driven, UNINTERRUPTIBLE** — cutting it costs a ~7 min
  anti-short-cycle.
- After: **~18% duty** (≈37 W average demand ÷ 207 W charge rate), **fully schedulable and
  interruptible at any instant** — no minimum run, no lockout, no penalty for stopping
  mid-charge.

Charging is the only load in this system that can be started and stopped arbitrarily.
Everything else carries a compressor's constraints.

**And the defrost stops being a crisis.** Replacing its 124 Wh takes ~55 min of charging
at 207 W — under **4% additional daily duty** if defrosts run roughly daily, taken at a
moment of your choosing rather than the fridge's.

### Thermal — and the unit has its own fan

206 W in plus 70 W out ≈ **276 W against a 300 W rating, doing both at once**, which is
exactly the condition §1 records a caution about. **The case stayed cool.**

**It has an INTERNAL FAN.** Airflow is **IN the left (larger) vent, OUT the right
(smaller — the AC input is on that side).** Detected with tissue paper, because the unit
sits on a running fridge and neither sound nor vibration can be trusted there.

**So any external fan must ASSIST that flow, never oppose it** — blow into the left
intake, or extract from the right exhaust. Blowing into the right exhaust fights the
internal fan and could be worse than nothing.

**CAVEAT on the "stayed cool" reading:** an external fan was running during it, in a
position that happened to assist. So that observation is NOT a fair test of the unit
unaided. It was unplugged afterwards for a clean run — see the result below when
recorded. If the unit stays comfortable through simultaneous charge-and-discharge on its
own fan, the vendor caution is settled for this application and no external cooling is
needed.

If cooling is ever wanted, giving the **intake** clear cool air does more than forcing
extra flow through — sitting on top of a fridge it draws whatever rises off the cabinet.

### Deferral, revised

**~6 hours** of fridge-off-the-inverter, from 202 Wh usable against ~35 W average pack
draw during ordinary cycling. This SUPERSEDES the ~9 h figure asserted earlier in
conversation, which ignored both inverter losses and the Battery Save window.

**Still preliminary:** the steady-state discharge rate is NOT measured. This run could not
reach it — the recovery run would have outlasted the battery. It needs its own run: full
pack, no defrost, two SOC readings 30 min apart during ordinary cycling.

### Unresolved from this run

- **RESOLVED — output frequency is 60 Hz.** A basic DMM read 80–90 Hz varying on the
  output while reading 59.x Hz correctly at the wall. **The Jackery's own screen settles
  it: `120V 60Hz` with the charger unplugged and `124V 60Hz` with the charger in. The
  manual labels that field "Output Voltage and Frequency", so BOTH are the output** —
  i.e. the inverter's output rises ~4 V while charging, presumably off a higher DC bus.
  Use 124 V for VA arithmetic during charging and 120 V on battery alone. The DMM's voltage was right — 120.7 V against the unit's 120 —
  and only its frequency counter was confused, as suspected. Per-cycle framing of this
  run's data is therefore valid, and the chest freezer's induction motor would see a
  correct 60 Hz if ever put on the Jackery.
- **Power factor is NOT ~0.55.** Combining this instrument's current against the Jackery's
  own wattmeter at the confirmed 120 V output: 0.932 A/100 W, 0.938 A/85 W, 0.753 A/70 W
  → **PF 0.76–0.89, about 0.78**, and apparently varying with compressor load. The ~0.55
  on record in `loads/kitchen_fridge.json` looks too low. Neither is a direct measurement;
  settle it with a meter that reports PF, spot-reading each operating state.

### Follow-on idea worth pursuing — DC charging

The unit accepts **12 V or 10–27 V, 5 A max** on its DC input. At 12 V that is **60 W**,
which comfortably exceeds the fridge's ~30 W average demand, and it **bypasses the
inverter entirely** — so the fridge would leave the one-at-a-time rotation altogether
rather than merely being rescheduled within it. 60 W is negligible against the Leaf's
~1.0–1.2 kW DC-DC ceiling.

The obstacle is physical: 12 V delivered from the Leaf (outdoors, ~25 ft from a basement
window) up to the fridge, at 5 A, needs heavy cable and fusing at the source. The same
port takes 10–27 V, so solar is the other obvious source — and higher voltage means less
current for the same power, which makes the cable problem easier.

## 10. Reading SOC off the screen with a camera — 2026-09-30

> **MOVED 2026-10-04.** The camera/OCR work now has its own project:
> `../jackery_display_reader` (sibling directory, own git repo). Its `CLAUDE.md`
> carries the facts it depends on, chiefly the §11 finding that "input" is charge into
> the battery. **This section stays as the record of how the approach was arrived at**;
> active work, open questions and hardware choices live over there.
>
> The interface back is a one-way sender into the `dual_logger` listener — same clock,
> same line format, per `docs/dual_logger_socket_ingest.md`.

Context: §4's BLE route is dead in practice — the unit shuts Bluetooth off once it has
Wi-Fi, and its Wi-Fi goes to Jackery's cloud, which is gone in an outage. A camera on the
front panel is fully local and model-independent, so it survives what the app route
cannot.

### The display timeout is settable — and that decides feasibility

The Jackery app offers three **Screen** options: **2 hr, 2 m, Off.** The prior art below
was built around a 2-minute timeout and needed a robot finger to defeat it; a 2-hour
setting removes most of that problem.

Two things to establish before relying on it:

- [ ] **What "Off" means** — screen never lights, or timeout disabled so it stays lit?
      Settle by observation, not by reading the label.
- [ ] **Does the setting persist a Jackery power cycle, with no app and no internet?**
      This is the one that matters. The setting is made through the cloud-dependent app,
      so if it lives only in the app's session rather than the unit's non-volatile
      memory, it evaporates in exactly the situation we need it. Set it, fully power the
      unit down, bring it back up, and look.
- [ ] Standing cost of a lit display. Probably under a watt, but against a 288 Wh pack a
      continuously-lit screen is worth a number rather than a shrug. Measurable by
      difference with the instrument, at a settled output.

If the 2 hr setting holds across a power cycle, a wake actuator becomes an occasional
convenience rather than a requirement. Ron has hobby servos; a bracket the Jackery sits
in, rather than anything glued to the case, is the preferred form if one is built.

### Prior art: `philippbussche/jacktessery` (read 2026-09-30)

Same problem, different model — Explorer **1000 Pro**. ESP32-CAM photographs the panel
and POSTs the JPEG to a Flask API that does the reading. Worth knowing in detail because
it is a working instance, not a proposal.

**No OpenCV and no machine learning.** The entire image pipeline is Pillow, about 25
lines: greyscale → threshold at 230 → crop to a fixed region of interest → dilate (3×3
max filter) → invert → add a 10 px white border then a 5 px black border → Tesseract.

**Tesseract does work on seven-segment digits — with the right model.** The config uses
`lang = ssd_alphanum_plus`, a Tesseract model trained on seven-segment displays, with
`--psm 8` (treat the region as a single word). Plain Tesseract is poor at segment digits;
that tessdata plus a tight region of interest is a legitimate route and is less work than
writing segment-decode logic by hand. *(An earlier claim in this project's conversation
that Tesseract is the wrong tool here was too broad — it is wrong only without the
seven-segment model.)*

**The validation layer is the real engineering content**, and any version we build needs
its equivalent — `metrics.py` there carries, per value:

- `max_value` — SOC cannot exceed 100
- `max_rate` plus a 900 s grace period — reject an implausible jump *unless* enough time
  has elapsed to justify it. Our rate limit is already derivable from measured data:
  roughly 2 %/hour at 52 W output (§9).
- `min_confidence` — Tesseract's own per-word confidence, floored at 60
- on a failed read, revert to the last good value rather than publish garbage

That this scaffolding was necessary says the OCR misreads regularly. Plan for it.

**A tell in its configuration.** Only `charging_status` (SOC) is `enabled = true`;
`input_watts` and `output_watts` are configured but switched off, and `input_watts` has
its confidence floor dropped to 20. Read that as: the large SOC digits are gettable, the
smaller wattage fields were not reliable enough to ship. Acceptable for us — SOC is the
number the charging decision needs, and we measure watts ourselves.

**Its timeout workaround, for the record:** a Fingerbot glued to the USB-output button on
four daily schedules, yielding two readings per day. Our 2 hr setting should beat that
outright.

### What this does not solve

Region-of-interest coordinates are per-model and per-mounting; the 1000 Pro's numbers
transfer nothing but the method. Rigid mounting is load-bearing — if the camera shifts,
every region of interest breaks — and a shroud is needed against glare on the panel.

### 2026-09-30: the app is currently a dead control path

Sequence, recorded because it bears on whether §10's camera route can be configured at
all:

- Display read **SOC 81%** with **input 0 W** while the charger appeared to be plugged in.
  Moving the plug one socket over in the same power strip brought input to **207 W** and
  SOC began climbing (81 → 83%), 0.4 h to full. The input did not appear *immediately* on
  re-plugging — there is a lag of some seconds before the unit registers charge.

  **The cause is UNRESOLVED, and the test above cannot settle it.** Two hypotheses fit
  every observation equally:

  - **(a) dead socket** — the charger was never drawing, and the pack fell 85 → 81%
    under the fridge load.
  - **(b) Battery Save deadband with a resume point near 80%** — the charger was fine,
    0 W input at 81% was correct behaviour, and *the act of re-plugging reset the charging
    logic*, which is why input appeared.

  Re-plugging changes the state, so it produces the same result under both. This was
  briefly written up here as (a) confirmed; that was wrong, and the confound is recorded
  as lessons.md #12.

  **The discriminating test does not involve the Jackery at all: plug a known load — a
  lamp, the 80 W crock pot, a meter — into the ORIGINAL socket and see whether it works.**
  If that socket is live, (a) is dead and the deadband is real.

  Weak supporting arithmetic for (b), not conclusive: at ~74 W the pack falls roughly
  25–29%/h (measured: 85 → 46% in 80 min), so 85 → 80% is only ~10 min of compressor
  running. A tight 80–85% deadband would therefore cycle every ~20–30 min and would spend
  most of its time *below* 85% — yet every earlier look at the screen found 85%. That
  argues for (a), or for a socket that was intermittent rather than dead.

- **The Jackery app will not connect.** Every attempt and every app restart ends in a
  "connecting Bluetooth" timeout; no valid data, controls inert. Ruled out: unit asleep
  (screen lit, and it answers ping on the LAN at `192.168.1.65`, MAC `f0:a7:31:94:e2:d`,
  0% loss); phone state (phone restarted); a "Bluetooth advertises only while awake"
  theory (tried with the display lit — still no connection).
- So the app appears to want **Bluetooth for control**, using Wi-Fi only to reach
  Jackery's cloud — and this unit turns Bluetooth off once Wi-Fi is up. That is a
  deadlock, and it means **the Screen timeout setting is presently unreachable.**

**Consequence for the camera route.** §10 rests on setting Screen to 2 hr. If the setting
can only be made through an app that cannot connect, the wake actuator (servo or similar)
goes back to being a requirement rather than a convenience. Two things to try, in order:

- [ ] **Does the manual expose the Screen timeout from the unit's own buttons?** This
      would remove the app dependency entirely and is the outcome to hope for.
- [ ] **Take the unit's Wi-Fi away and see whether Bluetooth returns** — a MAC filter
      entry for `f0:a7:31:94:e2:0d` on the gateway. Ron looked at this earlier for the
      BLE reverse-engineering route; the reason now is different but the action is the
      same. Reversible.

---

## 11. MEASURED — the display's "input" field is charge into the BATTERY, not wall draw

**2026-09-30.** Settled by two simultaneous readings, with a clamp meter on the Jackery's
AC input cord and the fridge compressor running:

| source | reading |
|---|---|
| clamp meter, Jackery AC input | **0.66 A** (~79 VA at 120 V) |
| Jackery display, input | **0 W** |
| Jackery display, output | **51 W** |
| Jackery display, SOC | **85%** (Battery Save ceiling) |

Current flows in the cord while the display reads input 0 W. The field cannot be wall
draw. (The clamp reads CURRENT, so 79 VA is an upper bound on watts — which only
strengthens the conclusion.)

**0.66 A is nowhere near a charging current.** Delivering 51 W *and* charging would be
~1.6 A (at 137 W into the pack) or ~2.3 A (at 207 W). Measured is 2.4–3.5× below either.
It is almost exactly pass-through alone: 51 W out at §9's measured ~82% conversion plus
~5 W unit overhead is ~67 W, against ≤79 VA measured.

### What this confirms

- **Ron's two-mode model.** At/above the ceiling the wall carries the load and the
  battery idles ("LO"); below a resume point the charger runs hard and restores the
  ceiling in minutes ("HI"). 5 points at 207 W into a 288 Wh pack is **4.2 min** — his
  "a few minutes".
- **Why every glance finds 85% / 0 W.** A ~4 min recharge every ~12 h is a **0.6% duty
  cycle**; the unit sits at the ceiling with the charger idle ~99% of the time. §10
  argued *against* the deadband hypothesis on exactly this observation, reasoning a tight
  deadband would spend most of its time below 85%. That reasoning assumed the 25–29 %/h
  fridge-on-battery drain; under pass-through the net draw is ~1.2 W and the argument
  inverts. **The deadband hypothesis is now the supported one.**
- **The dead-socket hypothesis is no longer needed.** 0 W input at 81% with the charger
  plugged in is ordinary LO-mode behaviour. The socket in use is live and the charger
  draws. (This does not *prove* the original socket was live — that stays untested — but
  nothing requires it any more.)
- **The overnight number stops being impossible.** 5% over 12 h with a cycling fridge is
  ~1.2 W net, a small shortfall in the pass-through balance. A cycling fridge off the
  *pack* would be ~35 W → 420 Wh over 12 h, more than the whole 288 Wh pack.

### The display cannot distinguish "unplugged" from "full"

Both read input 0 W. **The confound recorded as lessons.md #12 was structural, not just
procedural** — no amount of careful screen-watching could have settled the dead-socket
question, because the instrument does not expose the variable. A clamp on the input cord
does, and touches nothing.

### Corrections to §9 — its charging and thermal arithmetic was built on the wrong label

- **"207 W input … giving ~137 W net into the pack" is wrong.** There is nothing to
  subtract: 207 W was going into the pack. Wall draw at that moment was therefore
  ~207 + 70/0.85 + overhead ≈ **290 W (~2.3–2.4 A)**, NOT 207 W. **Unverified** — clamp
  the cord during a charge pulse to check it.
- **Charge rate: 1.20 %/min (71.9 %/h), not ~0.8 %/min.** And §9's 0.8 %/min was
  *derived* from the 137 W figure, not measured against a clock — circular, so it never
  arbitrated anything. **There is still no clock-measured charge rate.** The corrected
  1.20 %/min is likewise derived.
- **The 207 W figure now looks like the unit's charge-rate CEILING**, a constant, rather
  than a wall draw that would vary with output. That shape fits the display holding a
  steady 207 better than the old reading did.
- **§9's thermal line "206 W in plus 70 W out ≈ 276 W against a 300 W rating"
  double-counts.** Under the corrected reading the wall drew ~290 W while the unit moved
  207 W into the pack and inverted 70 W out. Higher, not lower. And its "case stayed
  cool" observation was already caveated as confounded by an external fan.
- **§9's DISCHARGE table survives unchanged.** Those rows come from SOC %/min against
  measured output VA and never used the input field: 1.41 %/min × 288 Wh × 60 = 243 W
  pack draw ✓.

### Do not derive rates from the unit's own time-to-empty estimate

Readings 55 min apart, fridge idle:

| time | SOC | input | output | time-to-empty |
|---|---|---|---|---|
| 09:49 | 85% | 0 W | 1 W | 38 h |
| 10:44 | 85% | 0 W | 1 W | 38 h |

**The 38 h did not decrement in 55 minutes.** It is not a live integration of actual
drain, and a 5–6 W idle draw inferred from it (288 Wh × 0.85 ÷ 38 h) was wrong — SOC held
85% across the interval, bounding idle drain under ~3 W. Separately, the unit's "0.4 h to
full" from 81% predicts ~24 min where 1.20 %/min predicts ~3.3 min. **Treat every derived
figure on this display as unreliable; only SOC, input, output and voltage/frequency are
readings.**

### Next, in order

- [ ] Clamp the AC input during a HI-mode recharge pulse. Predicted ~2.3–2.4 A against
      the 0.66 A measured in LO mode — an unmistakable difference, and it verifies both
      the 207 W-into-pack reading and the charge rate.
- [ ] Time a recharge against a clock for the first real charge-rate measurement.
      Deliberately discharging well below the deadband gives a longer, easier interval
      than the ~4 min ceiling pulse.
- [ ] Log the input cord with `firmware/esp32_ads1115_cycle_stats` for the unattended
      overnight watch. A ~4 min pulse at ~0.6% duty will not be caught by looking.

### REVISION to the time-to-empty claim above — it is a valid instantaneous estimate

The subsection above concluded "treat every derived figure on this display as unreliable."
**That was too broad.** A third reading settles what the field actually is:

| time | SOC | input | output | wall clamp | time-to-empty |
|---|---|---|---|---|---|
| 09:49 | 85% | 0 W | 1 W | — | 38 h |
| 10:44 | 85% | 0 W | 1 W | — | 38 h |
| 13:02 | **84%** | 0 W | 1 W | 52 mA | **37 h** |

288 Wh × 0.85 ÷ 38 h = **6.44 W**; 288 Wh × 0.84 ÷ 37 h = **6.54 W**. Self-consistent at
~6.5 W — and that is essentially the measured wall draw of 6.2 VA. So the field is
**remaining Wh ÷ present total draw**, i.e. "how long the pack would last if the wall
disappeared right now." It did not decrement between 09:49 and 10:44 because SOC had not
ticked; 1% resolution, not a broken counter.

**This field is therefore genuinely useful in an outage** and is worth reading alongside
SOC: at 51 W output the total draw is ~70 W, so it would report ~3.5 h rather than 37 h.
It reprices itself against the actual load. (Its "0.4 h to full" while charging remains
unexplained and disagrees with the charge rate by ~7×; the *discharge* estimate is the
one shown here to be coherent.)

### State of charge falling while plugged in, measured

SOC 85% → 84% somewhere between 10:44 and 13:02. One point is 2.88 Wh, so the net pack
drain is **0.9–1.25 W** (the bracket is the unknown tick instant inside the window).

**That agrees with the ~1.2 W derived independently from the overnight 5% / 12 h fall** —
two unrelated observations landing on the same number. Ron's "about 12 hr ± 3" for 85% →
80% was right: 14.4 Wh at 0.9–1.25 W is **11.5–16 h**.

**Open, and cheap to settle: is it constant or load-driven?** The wall covers the
1 W output and the housekeeping with 0 W into the battery, so a *constant* ~1 W bleed
would mean the unit draws some of its own housekeeping from the pack by design — which is
exactly the mechanism Ron proposed ("designed somehow so that SoC always slowly falls in
LO mode"). Discriminator: a constant bleed ticks SOC every ~2.3–3.2 h regardless of
whether the compressor runs.

**Prediction from 84% at 13:02:** 83% by roughly 15:30–16:15, and the 80% resume point at
**22:15–01:50 tonight.**

#### Time-to-empty confirmed by prediction, 13:06 — compressor running

| time | SOC | input | output | wall clamp | time-to-empty |
|---|---|---|---|---|---|
| 13:02 | 84% | 0 W | 1 W | 52 mA | 37 h |
| **13:06** | 84% | 0 W | **52 W** | **755 mA** | **3.3 h** |

The model above predicted ~3.5 h at ~51 W output before this reading was taken; it came in
at **3.3 h**. 288 Wh × 0.84 ÷ 3.3 h = **73 W implied total pack-side draw** for 52 W
delivered. The field reprices against real load exactly as described, across a 50× range
of output. **Two load points, one coherent formula — the discharge estimate is a real
reading, not decoration.**

**Consequence for the camera route:** this field is a direct "hours of fridge left" number
that already accounts for conversion losses, which arguably makes it *more* actionable in
an outage than SOC. Worth including as an OCR target alongside SOC — with jacktessery's
caveat that it shipped with only the large SOC digits enabled, the smaller fields having
proved unreliable.

**Pass-through roughly balances during a compressor run.** 755 mA is ~91 VA; at a plausible
charger PF that is close to the ~81 W wall-side needed to cover a 73 W pack-side draw, with
input reading 0 W. So the ~1 W net draw is probably NOT accumulated during compressor runs —
which favours the constant-bleed mechanism over a load-driven one.

**Unexplained, flagged rather than theorised:** 660 mA at 51 W output (earlier) vs 755 mA at
52 W output (here) — 14% apart for the same delivered power. Could be BLDC compressor speed,
charger PF varying with load, or meter range. Watch it; do not build on either figure.

**Range pairing corrected — and the discrepancy is NOT resolved.** An earlier note here
claimed the 660 mA reading was taken on the 400 mA range and so was out of spec. Wrong:
the 400 mA range reading was the **~52 mA idle** one (13% of full scale, a good reading),
and ~600 mA would flash over-range on that scale. **Both 660 mA and 755 mA were on the
4000 mA range**, so they are directly comparable and the 14% gap at nearly the same output
stands as an open observation. The pairing was inferred instead of asked; Ron corrected it.

Candidates, none tested:

- **The wall/battery split may not be tightly regulated.** The display has **no field for
  battery DISCHARGE** — "input" reports charge into the pack only. So a run where the wall
  supplied ~91 VA, and one where it supplied ~79 VA with the pack quietly covering the
  difference, look identical on screen. This would also account for the ~1 W average net draw
  as the residue of a loose split.
- **The compressor is variable-speed** (BLDC inverter). Two snapshots of a modulating load
  taken at different moments need not agree, and the output field's 1 W resolution can hide
  a real difference underneath 51 vs 52 W.
- Charger PF shifting with load — weakest, since delivered power was nearly identical.

Nothing built on the sub-amp readings changes: the pass-through-not-charging conclusion
rested on an order-of-magnitude gap (sub-amp against 1.7-2.4 A), not on precision.

**What this costs the camera route:** battery discharge rate is not on the display at any
load. **SOC trend over time is the only way to see it** — a direct argument for logging SOC
continuously rather than glancing at it.

**Range discipline for the overnight watch: leave the meter on 4000 mA.** It is the only
range that holds the predicted 1.7-2.4 A pulse without over-ranging. The cost is that the
52 mA idle floor sits at ~1% of full scale and reads poorly -- an acceptable trade, since
the question is whether the pulse fires. Take idle readings on the 400 mA range
deliberately, as separate spot measurements.

#### State of charge series, 2026-09-30 (fridge on the Jackery throughout, charger connected)

| time | SOC | display input | output | wall clamp |
|---|---|---|---|---|
| 09:49 | 85% | 0 W | 1 W | — |
| 10:44 | 85% | 0 W | 1 W | — |
| 13:02 | 84% | 0 W | 1 W | 52 mA (400 mA range) |
| 13:06 | 84% | 0 W | 52 W | 755 mA |
| 17:10 | **83%** | 0 W | 55 W | 750 mA |

**Net power out of the pack, revised: ~0.78 W.** 2 points (5.76 Wh) over the 7.35 h from 09:49 to 17:10; the
±1-point quantization puts it in ~0.5-1.2 W. Each added point has come in at the low end of
the previous estimate, so the earlier 0.9-1.25 W bracket should be read as an upper region.

**80% crossing projected 01:45-05:30 tomorrow** (3 points, 8.64 Wh, at 0.7-1.0 W). Firmly
overnight — which is what makes a max-hold clamp reading, or the ESP32 log, the only
practical way to catch it.

**Constant bleed vs load-driven is STILL not discriminated.** Both fit: the fridge's duty is
roughly constant, so a load-proportional drain looks constant too. 1% SOC resolution cannot
separate them on this timescale. It would need a long compressor-off stretch, which a running
fridge does not provide.

**Wall draw while the compressor runs, three readings:** 660 mA @ 51 W, 755 mA @ 52 W,
750 mA @ 55 W. The last two agree; **660 mA now looks like the outlier of three**, not
evidence of a second operating level. All three give output/input-VA of 57-65%.

#### The time-to-empty field implies the unit's own efficiency model

Three readings at widely separated loads, converting each to an implied total pack-side
draw as (SOC x 288 Wh) / hours-to-empty:

| SOC | output | time-to-empty | implied pack draw |
|---|---|---|---|
| 84% | 1 W | 37 h | 6.5 W |
| 84% | 52 W | 3.3 h | 73.3 W |
| 82% | 75 W | 2.3 h | 102.7 W |

Linear across a **75x range of output**, slope ~1.29-1.31, intercept ~5.2 W:

**implied pack draw = 1.30 x output + 5.2 W**

That is **~77% inverter efficiency plus ~5.2 W standing overhead** — and the 5.2 W
independently reproduces the ~5 W overhead inferred from the measured 6.2 VA wall draw at
1 W output. Two unrelated routes to the same constant.

**Caveats.** This is the unit's INTERNAL model, not an independent measurement: it rests on
the 288 Wh nameplate and on SOC being linear in energy. The hours field is also quantised
(2.3 / 3.3 / 37), which is most of the slope scatter.

**It conflicts with one figure in section 9.** That section's recovery run measured ~73 W
delivered for ~84 W pack draw (0.48 %/min) = **~87%**, where this model predicts ~100 W for
73 W out = **77%**. Section 9's defrost row, 77%, agrees with the model instead. Unresolved;
candidates are the unit being deliberately conservative, an optimistic 288 Wh nameplate, or
the single recovery-run figure being wrong.

**Operationally useful either way:** if the display is the conservative one, the hours it
shows UNDERSTATE remaining time, which errs in the safe direction during an outage.

#### State of charge series, continued

| time | SOC | output | wall clamp |
|---|---|---|---|
| 17:10 | 83% | 55 W | 750 mA |
| 20:10 | **82%** | **75 W** | **970 mA** |

**Net power out of the pack now ~0.84 W** (3 points / 8.64 Wh over the 10.35 h from 09:49 to 20:10), tightening
on the earlier 0.78 W rather than moving. **80% crossing projected ~03:00.**

Pass-through still balances: 970 mA ~= 116 VA covers the model's 103 W pack-side draw plus
charger loss, with input at 0 W.

**Watch, do not yet conclude:** output has risen 51 -> 52 -> 55 -> 75 W across the day. Could
be normal compressor variation or a warming box. Well below the ~187 VA defrost heater, so
not a defrost.

#### The fall is ACCELERATING, and it tracks the load

| interval | SOC | elapsed per 1% | implied net out of pack | output at the reading |
|---|---|---|---|---|
| 13:02 -> 17:10 | 84 -> 83% | 4.13 h | **0.70 W** | 55 W |
| 17:10 -> 20:10 | 83 -> 82% | 3.00 h | **0.96 W** | 75 W |
| 20:10 -> 22:45 | 82 -> **81%** | 2.58 h | **1.12 W** | 68 W |

Day average 09:49 -> 22:45: 4 points / 11.52 Wh over 12.93 h = **0.89 W**.

**Three consecutive intervals, each faster than the last, over a period when the fridge was
working harder (dinner prep, door openings, RTD placement).** That is the direction a
load-driven bleed predicts and a constant bleed does not. Stronger than the two-interval hint
noted earlier -- but three intervals monotonic by chance alone is still ~1 in 6, so this is
evidence, not proof.

**COMPETING EXPLANATION, not excluded: SOC may not be linear in energy.** Near the top of a
LiFePO4 curve the voltage-to-SOC relationship is steep, so an accelerating fall in
percentage points can be a reporting artifact rather than rising energy draw. Everything in
this section that converts percent to watt-hours assumes 2.88 Wh per point throughout.
Distinguishing them needs a measurement over a lower, flatter part of the range.

**80% crossing revised to ~01:20-03:00** (1 point at 0.9-1.12 W, slower if the quiet house
lowers the load as predicted).

#### The morning reading, and what a NEGATIVE does not prove

From 81% at 22:45, a ~07:00 reading:

- **~83-84%** -> fired around 02:00, recharged, re-latched. Only one pulse is expected, since
  85% -> 80% takes 11-16 h.
- **~78%** -> no pulse overnight.

**But a negative is ambiguous and must not be read as "it never resumes."** The 80% resume
point is an ASSUMPTION, taken from the one re-plug observation. If the real threshold is 75%
or 70%, tonight simply will not reach it, and the result looks identical to no auto-resume at
all. Before concluding the unit cannot recover on its own, the fall has to be followed down
through 78 -> 75 -> 70%.

## 12. RESOLVED — the unit resumes charging on its own, 2026-10-01

| time | SOC |
|---|---|
| 20:09 | 82% |
| 22:44 | 81% |
| **04:46** | **85%** |

**Nothing was touched.** No re-plug, no app, no power cycle. The pack fell to a resume point
overnight, the charger ran, and the ceiling was restored.

### What this closes

- **The unit self-manages at the Battery Save ceiling.** It stops charging at 85% and resumes
  without intervention. No babysitting in an outage.
- **The dead-socket hypothesis is finished** — not merely unnecessary, as section 11 had it,
  but excluded: that socket delivered a full recharge unattended while nobody was near it.
- **lessons.md #12 stands undamaged.** Its point was that re-plugging cannot discriminate,
  and that remains exactly right. What has changed is only the particular open sub-question
  it named. The discriminating test it proposed -- a known load in the ORIGINAL socket -- was
  never needed in the end, because a zero-touch observation answered it instead. That is the
  lesson's own advice carried out: the test that settles a thing is usually the one that
  changes nothing.

### What is NOT established

- **The resume threshold.** Only bounded as **<= 81%**. It could be 80% or lower; the pack
  passed through whatever it is between 22:44 and 04:46.
  **UPDATE 2026-10-07: resumes AT 80%** (one observation). Caught by the display reader's
  camera, one frame a minute, no load: 81% / 0 W at 14:14, **80% / 200 W at 14:15**, then
  ~1%/min at 206-207 W to 85% / 0 W at 14:20. Ron predicted "at or below 80%". Details:
  `../jackery_display_reader/docs/display_indicators.md`.
- **The time of the pulse**, loosely. Since SOC still read 85% at 04:46, less than one point
  (2.88 Wh) had fallen back, so the recharge completed within 2.6 h (at the 1.11 W evening
  rate) to 5.8 h (at 0.5 W) beforehand -- i.e. somewhere after about 23:00, and after 02:08
  if the evening rate had persisted. **Second half of the night.**
- **Whether it fired once or more.** One pulse is expected, since 85% -> 80% takes hours.
- **The charging current.** The predicted 1.7-2.4 A, which would confirm 207 W into the pack,
  still wants a clamp or a log on the input cord.

### Supporting evidence for load-driven over constant

At the evening rate of 1.11 W and an 80% threshold, the crossing would have been ~01:19 and
04:46 should read **84%**, having fallen ~1.3 points since. It reads **85%**. That requires the
fall to have SLOWED overnight -- which is when the house went quiet and the fridge's duty
dropped. Consistent with the three accelerating evening intervals. Still not proof: a resume
threshold below 80% combined with a faster fall also fits.

### Design consequence for the rotation controller

Section 3 notes that putting the fridge behind the Jackery blinds the rig's current sensor to
the compressor. This adds a sharper version: **offering the Jackery a rotation slot can produce
ZERO draw**, because the unit refuses charge at its ceiling. The channel will read ~0 A while
everything is healthy. Any logic that treats "relay closed, no current" as a fault, a failed
start, or an absent load will misfire on this channel. The Jackery is the one load in the system
that can decline a slot.

## 13. The Jackery will normally be DEEP, not near full — and SOC is the control variable

**2026-10-01, Ron's correction.** An earlier version of this arithmetic asked how long the
fridge runs on 5% of the pack (the 80-85% Battery Save window). **That premise does not occur
in operation.** The inverter will have been serving the chest freezer and/or the furnace, so
the Jackery's turn arrives with the pack well down -- never 5%.

### Inverter time budget, with the furnace included

| load | occupancy | basis |
|---|---|---|
| chest freezer | **61%** | MEASURED, gap-free 13.2 h deployment capture (52.3 on / 33.8 off) |
| furnace, low fire | **25-35%** | ASSUMED in section 2; furnace duty is still TBD in rotation_budget.md |
| fridge via Jackery | **17%** | derived: 207 W into pack balancing a 43 W continuous pack draw |
| **total** | **103-113%** | **over budget** |

**The Jackery's share is what gets squeezed**, because it is the only interruptible one.

### How fast it loses ground, and the cutoff

Over an hour with charging fraction t: net pack = 207t - 43(1-t) = 250t - 43 Wh/h.
Break-even is t = **17.2%**.

| charging share it actually gets | net pack | time to the 15% output cutoff (202 Wh usable) |
|---|---|---|
| 14% (furnace at 25%) | -8 Wh/h | **~25 h** |
| 4% (furnace at 35%) | -33 Wh/h | **~6 h** |

**Section 9 already flags the 15% cutoff as a hazard, not just a limit:** it drops the fridge
with no warning, and restoring power is another power-cycle on a box that is already warm.

### The offsetting factor, unquantified and the biggest lever here

`chest_freezer.json` records that its 61-70% duty is a warm-ambient figure and that "real
cold-ambient Michigan outages would lower duty somewhat" -- **without a number.** Cold ambient
is exactly when the furnace runs, so the two demands partly cancel. If the CF fell to ~50% the
total would be 92-102%, i.e. borderline rather than over. **Quantifying the CF's cold-ambient
duty is worth more to this budget than any other single measurement.**

### Why this is the quantitative case for reading SOC in an outage

The scheme does not fail abruptly; it loses ground at 8-33 Wh/h and then drops the fridge at
the 15% cutoff, somewhere between ~6 h and ~25 h in. **Nothing else on the rig can see that
coming.** The rig's own current sensor is blind to the fridge behind the battery (section 3),
and wall-side current cannot distinguish "holding steady" from "slowly losing." **SOC is the
state variable that says which side of break-even the rotation is on**, and the decision it
drives is concrete: give the Jackery a bigger share at the furnace's or the freezer's expense,
or move the fridge to direct inverter power before the cutoff. That is the operational
justification for the camera route in section 10 -- not convenience.

### Open question, NOT settled here

This budget assumes the loads cannot overlap. The project's stated reason for one-at-a-time is
that simultaneous compressor STARTS exceed the DC-DC ceiling -- the CF's start is ~1400 VA
(17.8 A peak). But STEADY running is small: CF ~84 W, furnace low fire ~79 W, Jackery charging
~290 W, totalling ~450 W against a ~1.0-1.2 kW ceiling. **If steady runs may overlap and only
starts must be serialised, the over-100% problem largely dissolves.** Raised as a question for
Ron, not a conclusion -- it is a change to the control philosophy, and the igniter (~310 W for
17 s, once per heat call) plus a CF start would still exceed the ceiling.
