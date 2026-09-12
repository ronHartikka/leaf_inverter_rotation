# Outage procedures

Runbook for running the house loads off the LEAF + Renogy inverter during a grid
outage. Written to be followed in order, in the dark, when tired.

Absorbs the earlier `docs/LEAF_battery_Renogy_connection/Battery connection.md`
(§2 below is that file's content). That file is now redundant — delete it once this
one has been used through a full outage and proved complete.

Vocabulary used throughout (Ron's, from the temp rig):
**FFC** = kitchen-fridge fresh-food compartment · **FC** = kitchen-fridge freezer
compartment · **CF** = chest freezer.

---

## 1. First 30 minutes

- [ ] **Write down the time power went out.** Everything downstream is timed from it.
- [ ] **Keep the fridge and freezer shut.** Their contents are the reason for all of this.
- [ ] **Check LEAF state of charge.** Below ~50%, drive to a DC fast charger *now*,
      while it is still convenient. Charging is far easier before the setup is live.
      *(2026-09-03: went out at 28%, charged to 90%, home at 87%.)*
- [ ] Decide the first load. If the fridge has already been warming for hours it goes
      first; otherwise start with whichever is warmest.

---

## 2. Connecting the inverter to the LEAF battery

*(from the original `Battery connection.md`, unchanged except where noted)*

**Before touching anything:**

- Position the inverter near the center of the LEAF.
- Inverter must be **off** — not on, not remote.
- Car must be **off**, drawing as little power as possible, while connecting.

**Terminals:** 12 mm for **+**, 13 mm for **−**. A socket is best. Be careful not to
let the clamp spin on the battery post — it wants to.

- [ ] Connect **negative (black)** first — fewer places to make an accidental connection.
- [ ] Then connect **positive (red)** from inverter to battery.
- [ ] Then turn on the car.

**With the car on, check these are OFF:**

- [ ] Audio
- [ ] Heated seats
- [ ] HVAC
- [ ] Heated steering wheel
- [ ] Center display
- [ ] Headlights (switch OFF, not AUTO)

> Daytime running lights stay on and cannot practically be switched off. Measured
> 2026-09-04: they are ~10–30 W against a ~530 W total system draw — **not worth
> chasing.** Do not pull fuses on the vehicle that is currently the only power source.

**Bringing it up:**

- [ ] Make sure **no load** is plugged into the inverter.
- [ ] Turn on the inverter — it beeps once and an LED comes on.
- [ ] Plug in a test load (a light) and confirm.

**Hood:** close as far as possible without resting it on the inverter. A piece of 2x
blocking the latch is about the right thickness. **This is not storm-proof** — if
weather is still active, account for it.

---

## 3. Appliance settings for outage operation

- [ ] **FFC dial → 5.** This is the *outage setting*. Normal household setting is 3;
      5 tends to freeze things at the back of the fresh-food compartment, which is an
      acceptable trade during an outage but not otherwise.
- [ ] **FC dial → 1.** Normal is 3. This is the **documented rotation setting** and it
      was decided on measurement, not preference — see below.
- [ ] **Put a note somewhere you will see it** that FFC goes back to 3 and FC back to 3
      on restore. This is the single easiest thing to forget.

**Why FFC 5:** at FFC 5 the measured fresh-food band is **cut-out 35.3 °F / cut-in
40.1 °F**, i.e. it holds below the 40 °F line. Rotation means each box spends hours
unpowered and drifting up, so starting from a colder setpoint buys margin.

**Why FC 1 — and why the numbering is counterintuitive.** The FC dial is a **damper,
not a thermostat**: 1 sends maximum air to the FFC, 5 sends maximum air to the freezer
compartment. The compressor regulates on **FFC temperature only**, so this dial decides
where the cold goes, not how much of it there is.

FC 1 therefore does two things at once during an outage:

- **Aims cold at the compartment that needs it.** The FFC is the one that struggles
  during rotation and the one holding perishables. The fridge's freezer matters less
  when the CF is carrying the frozen load.
- **Cuts duty by about 12 points.** Measured, both at FFC 5:
  **FC 3 ≈ 51% duty · FC 1 ≈ 39%** (`docs/lab_notebook.md`, 2026-08-08). That comes
  straight off the LEAF.

> Setting the dial does nothing while the fridge is unpowered — it only redirects air
> when the compressor runs. Set it whenever; it takes effect on the next powered block.

> If there is food in the fridge's freezer you want kept hard, move it to the CF while
> the CF is running. FC 1 deliberately lets that compartment run warmer.

---

## 4. Rotation

**One load at a time.** The LEAF DC-DC ceiling is ~1.0–1.2 kW and only one compressor
may take a start surge at a time.

- The **CF is the only load with a true locked-rotor inrush** (PTC-start induction
  compressor). Start it with nothing else drawing.
- **Never re-energize a compressor that has just been cut.** Minimum ~180 s off; a
  sub-second blip to a running PTC-start compressor stalls it, heats it, and trips the
  overload. In practice a rotation swap is hours, so this only bites if you fumble a
  plug.
- Overnight is the longest unattended block. Give it to the load with the most to
  lose — normally the **CF**, since frozen food has less tolerance than fresh.
- Swapping pauses the fridge's defrost clock (see §6), which is a mild bonus.

### 4.1 When to swap — measured drift rates

Both measured during the 2026-09-03/04 outage, unpowered, doors mostly shut:

| Box | Drift while unpowered |
|---|---|
| Kitchen fridge (FFC) | **0.21 °F/h** (43 → 45 °F over 9.5 h overnight) |
| Chest freezer (CF) | **2.3 °F/h** (18 → 22 °F over 1.8 h) |

**The CF loses ground about 11× faster than the fridge.** That asymmetry is the whole
basis of the swap decision: a long unpowered block costs the fridge very little and
costs the CF a lot. When in doubt, the CF gets the power.

Note the CF's measured 2.3 °F/h is far *better* than the ~0.18 °F/min (≈11 °F/h) bench
figure in `docs/rotation_budget.md` — that bench number was a lightly-loaded unit in a
warm room. A full freezer in a cool house holds much better. Do not plan from the bench
figure.

### 4.2 Insulating the chest freezer

Added by Ron 2026-09-04, mid-outage. Cheap, reversible, and worth doing early rather
than once the CF is already climbing.

**The setup:**

- A **blanket over the lid**, hanging down **only a little past the lid seal** all the
  way around.
- A **folding foam mattress on top**, ~14" thick, slightly smaller than the lid.

**Why it helps here specifically.** The lid is a chest freezer's weakest surface and
the seal line is a thermal bridge. This unit is also **low on refrigerant charge** and
already runs ~70% duty (see `loads/chest_freezer.json`) — so cutting its heat load does
not merely save energy, it helps a struggling compressor actually keep up.

**Leave the cabinet sides and the back clear.** The blanket must not curtain the whole
cabinet to the floor.

**This unit is a confirmed hot-wall condenser** (verified by touch 2026-09-04 — warm
areas on the **front, left and right panels, high up**, near the lid flange; no separate
back coil). The cabinet's outer skin *is* the heat-rejection surface. Full detail in
`loads/chest_freezer.json` → `identity.heat_rejection`.

- The UL listing (Frigidaire MFC15M3BW0, built 01-94, R12) reads **"free-standing
  installation only"** — this is why.
- The compressor recess at the back also needs air.

Blocking heat rejection here is the one way this backfires: higher head pressure on a
compressor already fighting a low charge, longer runs, and a possible overload trip —
on a 32-year-old R12 system that is not economically repairable.

> ⚠ **The margin is thin.** The warm band begins **just below** where the blanket edge
> sits. You are clear as set up, but a careless re-drape after opening the lid can cover
> it without being obvious. Treat "a little past the seal" as a hard limit, not a loose
> tolerance — consider marking the line on the cabinet.

> **Data caveat:** the 2.3 °F/h CF drift in §4.1 and the ~70% duty in
> `chest_freezer.json` were both measured **uninsulated**. Any figure taken after
> 2026-09-04 is a different configuration. A fresh drift measurement over a CF-off
> stretch would quantify what the insulation bought — useful well beyond this outage,
> since it feeds the rotation budget directly.

### 4.3 The freezer-pack shuttle

Two 7 lb freezer packs (14 lb total) used as a portable cold reserve, moved between
boxes by hand. Introduced by Ron on 2026-09-04.

**The idea:** the packs are a thermal battery. They can only be *recharged* in the CF —
the FFC cannot get below freezing — but they can be *spent* in either box, holding
temperature during that box's unpowered block.

**Rules, in order of how easy they are to get backwards:**

1. **Leave the packs in whichever box is about to go unpowered.** That is when their
   stored cold is worth something. Moving them into a box that is *about to get power*
   wastes them.
2. **Return them to the CF only when the CF is already back near 0 °F and still
   powered.** Handing melted packs to a freezer that is itself 20 °F above target makes
   its recovery much worse — you are asking it to do two jobs at once.
3. **Do not shuttle them more often than needed.** A full melt-and-refreeze cycle costs
   roughly **2,200 BTU ≈ 0.65 kWh thermal ≈ 0.5 kWh electrical** — on the order of
   8 hours of normal CF running. Partial melt costs proportionally less, but the point
   stands: every round trip is paid for out of the LEAF.
4. **Keep them clear of food that must not freeze.** At FFC 5 the compartment already
   tends to freeze items at the back; 14 lb of sub-freezing mass makes that sharper
   locally. Milk, produce and eggs should not be touching the packs.

Worked example — the 2026-09-03/04 outage:

| Time | Action | State |
|---|---|---|
| 15:42 | Power out | — |
| 18:15 | Fridge on inverter | FFC 47 °F |
| 20:30 | — | FFC 43 °F, SOC 85% |
| ~22:00 | Swapped to CF overnight | — |
| 07:30 | Swapped back to fridge; 2×7 lb packs moved CF → FFC | FFC 45 °F |
| ~11:30 | **FFC dial 3 → 5** (outage setting) | — |
| 11:32 | — | SOC 71% |
| 11:37 | — | FFC 42.6, FC 7.6, CF 20 °F |
| 12:54 | Decision: swap back to CF | FFC 41.2, FC 0.4, CF 22 °F |
| ~13:00 | Swapped to CF; packs left in FFC | SOC 70% |

Reading the middle of that table: after the dial went to 5, **FC recovered fast**
(7.6 → 0.4 °F in 77 min, back inside its −4.3…+5.8 °F band) while **FFC moved slowly**
(42.6 → 41.2 °F). The freezer compartment recovers first and then acts as the fridge's
cold reservoir — so "FC back in band" is a reasonable signal that the fridge has banked
enough to give up the inverter.

---

## 5. Monitoring

- [ ] **SOC + clock time, morning and night.** Two readings ~12 h apart give total
      system draw with the SOC rounding error washed out. This is the number that
      tells you when to go charge.
- [ ] Temps: FFC, FC, CF.

**Measured 2026-09-04:** 85% → 71% over 15.0 h on a 62.5 kWh (2019) pack ≈
**530 W total**, of which the appliances are ~75 W and **the car idling is ~450 W**.
The car, not the load, is the bill.

Rule of thumb from that: **~1% SOC per hour.** Reserve 20% to reach a charger, so from
a full-ish pack expect roughly **2.5–3 days** per charge, less if the boxes are warm
and running hard.

---

## 6. Known appliance behavior (measured, don't re-derive)

- **Kitchen fridge, on every power-on:** defrost heater ~4 s, then a **~7 minute
  anti-short-cycle hold**, then compressor starts. Characterized over n=44 restarts,
  44/44 identical. So nothing appears to happen for 7 minutes — this is normal.
- **Defrost after a true power restore comes early: 4 compressor-run-hours**, versus
  7–50 run-hours normally. It costs ~29 min at ~1.9 A / 198 W, during which the box is
  heating itself. Once started it is the **minimum uninterrupted window** — do not cut
  power mid-defrost.
- Defrost triggers on **compressor run-hours, not wall-clock**, so an interrupted
  fridge defrosts less often per calendar day.
- **CF warms slowly** (good thermal mass) but it is the load most at risk over a long
  unpowered block.

---

## 7. On restore — do not skip

- [ ] **FFC dial back to 3.** The outage setting will over-freeze the fresh food if
      left in place.
- [ ] **FC dial back to 3.** Left at 1, the fridge's freezer compartment runs warmer
      than normal indefinitely — quiet, and easy to not notice for weeks.
- [ ] Turn off and disconnect the inverter (reverse of §2: inverter off, then
      positive off, then negative).
- [ ] Turn the car off.
- [ ] If the furnace was rewired (§8), put it back.
- [ ] Record in `docs/lab_notebook.md`: outage span, loads run, SOC readings,
      temperatures, anything that went wrong.

---

## 8. Furnace — NOT YET EXERCISED, read before attempting

The furnace has **never been run off the inverter.** All of its electrical values are
estimated. Do not treat this section as proven procedure.

From the original notes, the temporary-cord conversion:

- **Black wire:** remove from the normally-load side of the switch mounted to the
  furnace; wire-nut the temporary cord's black to it.
- **White wire:** remove from the wire nut inside the box mounted *inside* the
  furnace; wire-nut the temporary cord's white to it.
- It is hardwired, not cord-and-plug. **Never backfeed a receptacle.**

### 8.1 Grounding — facts and open questions

Recorded 2026-09-04. **Facts only; no mechanism is asserted here.** Do not act on this
section during an outage — the furnace is not currently an inverter load.

**Inverter identification**

- Model **RNG-INVT-1000-12V-P2**.
- Manual: Renogy INVT-P2 (covers 12 V 700 / 1000 / 2000 / 3000 W). Local copy:
  `docs/reference/Renogy_INVT-P2_inverter_manual.pdf` (git-ignored).

**Quoted from that manual, verbatim**

- AC terminals: *"Left: Neutral (N) · Middle: Ground (G) · Right: Live (L)"* —
  **"Note that Neutral and Ground are bonded inside."**
- **"GFCI LED (Yellow) — Indicates that the ground fault circuit has been interrupted.
  In such case, restart the inverter."**
- Grounding: *"If available, the chassis ground lug should be connected to a ground
  point such as a vehicle chassis or boat grounding system. In fixed locations, connect
  the ground lug to earth ground. The connections to ground must be tight and against
  bare metal. Grounding is highly recommended for both when using the inverter in a
  mobile application, such as an RV, or in a building."* Recommended wire: **14 AWG**
  for the 1000 W model.
- *"While the inverter is equipped with a GFCI, it is recommended to install an external
  GFCI where you can manually test the circuit."*
- AC outlets: **up to 8.7 A for 1000 W models.**

**Facts about the installation as it stands (Ron, 2026-09-04)**

- The chassis ground lug is connected to **neither** the car chassis **nor** earth.
- The original note — *"No loads should be connected to ground. The furnace is, so make
  sure the green wire from the inverter doesn't get to it"* — was written after early
  shutdowns that occurred when the inverter ground reached the furnace ground.
- Ron's recollection of those shutdowns: **yellow LED**, i.e. the GFCI indication above.
  Recalled, not logged at the time — treat as probable, not certain.

**RESOLVED 2026-09-12 — the furnace has already been run on this inverter**

Ron has run the furnace from the inverter, repeatedly, following the connection in §8
above: house black and white lifted at the furnace, inverter black/white wire-nutted to
the furnace black/white, **no green wire between inverter and furnace**. It lights,
proves flame, completes the cycle, and heats the house.

- **Flame proving does NOT need an external neutral-to-ground bond.** The
  flame-rectification loop closes INSIDE the furnace: control board → flame rod →
  flame → burner/chassis → back to the board's own ground reference. The board
  supplies both ends of the loop. (Confirmed by the rectification circuit diagram Ron
  supplied, and by the fact that it heats the house this way.)
- **The `loads/furnace.json` warning does not apply here** and has been corrected. It
  assumed a floating-output inverter; this one documents an internal N-G bond, so the
  premise never held for this unit — and the loop above is local regardless.
- **Removing the green wire did not un-ground the furnace.** Only black and white are
  lifted, so the chassis stays tied to the house equipment ground, the ductwork and the
  gas piping. What it removes is the earth reference of the *inverter's output*.
- **Why connecting green shuts the inverter down (MECHANISM INFERRED, not measured).**
  Neutral and ground are bonded inside the inverter and the GFCI compares current out on
  L against current back on N. A green wire to the earthed furnace chassis completes the
  only earth return path there is, so ordinary line-to-chassis leakage inside the furnace
  — ECM drive EMI-filter capacitors (two ECMs here), hot-surface igniter to its grounded
  mount — returns by a route other than the white wire and reads as a ground fault. A few
  milliamps is enough. With green off, that leakage has nowhere to go, so none flows.
  Nothing is wrong with the furnace; the GFCI was doing its job in both configurations.
- **Grounding the lug to earth as the manual instructs should be expected to trip the
  same way** — a ground rod earths the inverter's neutral exactly as the furnace chassis
  does. Same loop, same current. (Also inferred; untested.)
- **Confidence.** That it runs without green and shuts down with green = repeated
  practice, high confidence. That the indication was the **yellow GFCI LED** = Ron's
  recollection, not logged at the time — probable, not certain.

**Standing safety caveat (the reason §8.1 still says get an electrician's opinion).**
With the inverter's output floating, a single line-to-chassis fault inside the furnace is
silent: nothing trips, and the GFCI cannot see it, because that fault current returns
through the very conductors it measures. The system keeps running, now earth-referenced
through the fault, with the white wire sitting at 120 V to earth and no indication. This
is not an argument against how the furnace was run during an outage; it is the case to
put to an electrician before the arrangement becomes permanent.

**Still open**

- [ ] If a shutdown ever recurs, record **which LED** (yellow = GFCI, red = fault) and
      the exact circumstances. That distinguishes a ground fault from overload/thermal.
- [ ] Optional, would confirm the mechanism: reconnect green and note **when** it trips
      — at 115 V power-up with no heat call, during inducer pre-purge, at igniter
      warm-up, or at blower ramp. Igniter → HSI leakage; blower/inducer → ECM filter;
      immediate at power-up → board/transformer or a genuine fault.

**Before changing any grounding:** this combines a bonded-neutral source, a GFCI, and a
gas appliance whose chassis is earthed through its own ductwork and piping. Worth an
electrician's review rather than experiment, and not something to improvise in order to
make a furnace light.

Load-shedding policy once it *is* in service: **do not shed the furnace.** Shed the
fridge and CF instead and let a heat call finish. Restoring furnace power re-triggers
the ECM DC-bus inrush, an aborted cycle wastes a 17 s igniter warm-up, and repeated
aborts drive the control toward a 3-try lockout.

---

## 9. Gaps in this runbook

Fill these in as they are learned:

- Disconnect sequence in §7 is inferred as the reverse of connection — confirm it
  matches what you actually do.
- The grounding conflict is RESOLVED (§8.1): run the furnace on line and neutral only,
  no green wire. A full furnace procedure for §8 is still unwritten, and the furnace's
  electrical draw is still unmeasured.
- Extension cord routing / gauge not recorded.
- No guidance yet on when to stop rotating and go charge, beyond the 20% reserve.
