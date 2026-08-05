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

Source: search **"LG LTCS20020S service manual"** (LG support / service-manual
archives). Local copy: `docs/reference/LTCS20020S.pdf` (git-ignored). _Add the exact
URL here once confirmed._
