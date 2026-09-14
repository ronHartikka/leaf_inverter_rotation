# Jackery Explorer 300 Plus — as a power source in this system

Recorded 2026-09-14 from a working conversation. **Nothing here is measured on the
unit.** Specifications are from vendor/retail pages, not from the manual; every number
about the loads is from this repo's own measurements or its estimates, marked as such.

> **MODEL NOT YET CONFIRMED.** Ron is checking the manual to confirm which unit he has.
> This matters: the newer **Explorer 300 v2** has a UPS bypass mode (~20 ms transfer)
> that the **300 Plus** does not. If the unit turns out to be a v2, the buffer idea in
> §3 gets easier, not harder.

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
