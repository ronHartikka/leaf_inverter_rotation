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
  The tempting conclusion was a Battery Save deadband — charge to 85%, stop, let the load
  draw down, resume lower. **Wrong.** The charger was in a bad socket of a power strip.
  Moving the plug one socket over brought input to **207 W** and SOC began climbing
  (81 → 83%), 0.4 h to full. **"Holds at 85% on pass-through" stands as recorded in §9.**
  Note the input did not appear *immediately* on re-plugging — there is a lag of some
  seconds before the unit registers and reports charge.
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
