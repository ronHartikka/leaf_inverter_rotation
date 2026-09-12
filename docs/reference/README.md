# Reference documents

Manufacturer manuals and datasheets are **not committed** here — they're copyrighted
and large. This file records what we reference and where to find it; the actual PDFs
live locally in this folder (git-ignored).

## Kitchen fridge — LG **LTCS20020S** (top-freezer)

LG service manual. Sections we rely on:

- **8-1-2 / 8-1-7 Defrost cycle** — defrost triggers at **7–50 accumulated
  compressor-run-hours**, shortened by door-open time; **4 run-hours** after a
  power-on / power restore. Defrost ends when the defrost sensor reaches **10 °C
  (50 °F)** (or 1–2 h = fault). Matches the ~7.8–8.5 run-hour intervals measured in
  our captures (see docs/lab_notebook.md).
- **8-1-12 Test mode** — TEST 1 (compressor runs continuously), **TEST 2 = forced
  defrost** (defrost heater ON, compressor OFF; ends at sensor 10 °C or 2 h),
  Reset (default settings; *"compressor will start in 7-minute delay"*).
- The 7-minute post-power-on compressor start delay in the manual confirms the
  delay we reverse-engineered from the current traces.

Source: <https://research.encompass.com/ZEN/sm/LTCS20020S.pdf> (Encompass). Local
copy: `docs/reference/LTCS20020S.pdf` (git-ignored).

## Inverter — Renogy **RNG-INVT-1000-12V-P2**

User manual (Renogy INVT-P2, version A2; covers 12 V 700 / 1000 / 2000 / 3000 W).
Facts we rely on, quoted verbatim:

- AC terminal block: *"Left: Neutral (N) · Middle: Ground (G) · Right: Live (L). Note
  that **Neutral and Ground are bonded inside**."* — matters because
  `loads/furnace.json` warns about *floating*-output inverters and flame
  rectification; that premise does not hold for this unit.
- *"**GFCI LED (Yellow)** — Indicates that the ground fault circuit has been
  interrupted. In such case, restart the inverter."* Red = Fault (overheat, overload,
  under/overvoltage). The LED color identifies the shutdown cause.
- Grounding: *"the chassis ground lug should be connected to a ground point such as a
  vehicle chassis or boat grounding system. In fixed locations, connect the ground lug
  to earth ground… Grounding is highly recommended."* 14 AWG for the 1000 W model.
- AC outlets: **up to 8.7 A for 1000 W models.**

Source: <https://www.renogy.com/pages/1000w-12v-pure-sine-wave-inverter-rng-invt-1000-12v-p2-html>
(PDF mirror: `lithiumion-batteries.com/uploads/files/17009/INVT-P2-Manual…pdf`).
Local copy: `docs/reference/Renogy_INVT-P2_inverter_manual.pdf` (git-ignored).
See `docs/outage_procedures.md` §8.1 for the open grounding questions.

## Thermostat — Carrier **Infinity System Control SYSTXCCITC01-B**

**Identity, resolved 2026-09-03.** Three numbers are attached to this unit and only
one is the model:

| Number | Where | What it is |
|---|---|---|
| `SYSTXCCITC01-B` | Carrier app | **the model** |
| `A240356` | label on back of thermostat | Carrier illustration/artwork number, 2024 series |
| `A170203` | Owner's Manual cover, **black** unit | ditto, 2017 series |
| `A180218C` | Owner's Manual cover, **white** unit | ditto, 2018 series |

`A`-numbers are figure/artwork numbers, formatted `A` + 2-digit year + sequence, and
they appear all through these books (`A150175`, `A160107`, `A170241C`, `A13122A` …).
They are **not** model or form numbers.

The cover-caption confusion is worth recording, because the guess is a natural one:
the cover shows two controllers side by side, black captioned `A170203` and white
captioned `A180218C`, which reads as if the caption names the unit. It doesn't — those
are captions on two product photos. They *do* correspond to two different physical
finishes covered by the same book, so the black image does depict this unit's type;
it just isn't a part number. `A240356` on the rear label dates that label's artwork to
2024, consistent with a late production run of the `-B` carrying firmware v2.00.

Carrier's real form number lives in the footer: **Catalog No. SYSTXCCITC-05SI**,
Edition Date 03/19, replacing `-04SI` / `-03SI` / `-02SI`.

Cover lists four models — SYSTXCCITC01-B / SYSTXCCWIC01-B / SYSTXCCICF01-B /
SYSTXCCWIF01-B — but they appear **only** on the cover; the body never distinguishes
them, so this document does not say what separates the variants (or which is the white
one). The model identification here rests on the Carrier app, not on the artwork.

⚠ A still-later edition exists (`SYSTXCCITC-08SI`, seen at cematraining.com, 403 on
fetch). Given the 2024-dated rear label it may match this unit more closely. Checked:
§6.3.3.3 and §6.4.2 are **byte-identical between the 09/17 (`-02SI`) and 03/19
(`-05SI`) editions**, and the `-C` manual lists the same six staging values — so the
quotes below look stable across revisions. Still, if a screen ever disagrees with
them, suspect the edition first.

This is the installer/service document — the Owner's Manual does **not** cover the
service menu (§6: *"This information is not covered in the Owner's Manual."*).
Sections we rely on:

- **§6. Service Menu** — entry: *"touch menu, then touch and hold the SERVICE icon,
  for at least ten seconds, until the icon turns green."* Not documented in the
  Owner's Manual, which is why a short press only shows service info / reminders /
  software update / model numbers / utility event.
- **§6.3.3.3 Furnace Staging** — `Stages: System, Low, Low-Med, Med, Med-High, or
  High`, default `System`. LOW/MED/HIGH are single-stage locks; LOW-MED and MED-HIGH
  enable *two* stages each. Note: *"Two-stage furnace has LOW and HIGH selections
  only"* — the 58MVC is three-stage, so MED should be available.
- **§6.4.2 Check out → Furnace** — exercises the furnace on demand with selectable
  Low Heat / High Heat run times (0–120 min, default 5). Runs the full ignition
  sequence and displays live operating status. This is the forcing mechanism for
  warm-weather measurement — see `loads/furnace_electrical_load.md` §8.
- **§6.3.3.1 Furnace Airflow** — Comfort/Efficiency, default **Comfort**. Relevant
  because the cooling/heat-pump checkout items are documented as forcing
  **Efficiency** airflow; whether §6.4.2 does the same is an open question that
  decides whether Checkout-mode blower watts transfer to real heat calls.

Source: <https://esmithair.com/wp-content/uploads/2020/02/Thermostats_SYSTXCCITC01-B.pdf>
(the `-05SI` edition; the older `-02SI` is at
<https://resource.carrierenterprise.com/is/content/Watscocom/carrier_systccitc01-b_article_931768170498288_en_ii>).
Local copy: `docs/reference/SYSTXCCITC-05SI_installation_instructions.pdf` (git-ignored).
Owner's Manual local copy: `OMSYSTXCCITC-VC-03.pdf` (git-ignored),
<https://www.shareddocs.com/hvac/docs/1009/Public/00/OMSYSTXCCITC-VC-03.pdf>

**Extraction note:** WebFetch returns unreadable binary for these Carrier PDFs, and
its summaries across mirrors contradicted each other (one confidently reported a
staging list that does not exist in this document). Extract locally instead —
`pdftotext -layout file.pdf file.txt` — then grep. That is how §6.3.3.3 and §6.4.2
below were read.

## INFINITY ICS MODEL 58MVC DELUXE 4---WAY MULTIPOISE VARIABLE---SPEED MULTI---STAGE CONDENSING GAS FURNACE Series 100, Input Rates: 60,000 thru 120,000 Btuh
### 

### Product Data

<https://americancoolingandheating.com/wp-content/uploads/carrier-product-data-specifications/58MVC-5PD.pdf>

