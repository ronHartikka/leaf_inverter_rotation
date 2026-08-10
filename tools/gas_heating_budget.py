#!/usr/bin/env python3
"""Reconstruct the furnace heating-budget numbers from the DTE daily-gas exports.

Makes the numbers in loads/furnace.json thermal/duty_cycle sections RE-RUNNABLE
from committed source data, and extends the original single-season (2022-23)
analysis across EVERY heating season present in data/gas/.

It loads ALL data/gas/gas_usage_report_*.csv files, merges them by date (dedup;
the overlapping 2022-23 files are verified to agree), then for each Oct 1 -> May 31
heating season reports:
  - heating gas CCF            (baseload-subtracted)
  - low-fire clock hours       (heating BTU / low-fire input rate)
  - full-fire-equivalent hours
  - seasonal runtime fraction  (low-fire hours / season hours)
  - peak single day and peak 4-day-average low-fire duty
  - the bracketing summer baseload (drift check)
Partial seasons (data starting mid-winter) are flagged and excluded from the
season-fraction summary.

The 2022-23 season doubles as a self-test: its recomputed values are checked
against the numbers stored in furnace.json (STORED below).

WHAT IT DOES NOT DO HERE:
  - UA (house conductance) and balance point. Those need an outdoor-temperature
    series, which is not in the repo. `regress_ua` is implemented but stays
    dormant unless you supply monthly mean outdoor temps in
    data/gas/monthly_outdoor_normals.csv (month,mean_temp_f). Substituting DAILY
    airport-station temps there is the known highest-value open item for
    tightening UA/balance point (furnace.json provenance.open_items).

Usage:
  python3 tools/gas_heating_budget.py            # all seasons, table
  python3 tools/gas_heating_budget.py --monthly  # also per-month fractions
  python3 tools/gas_heating_budget.py --baseload 0.50
"""

import argparse
import csv
import datetime as dt
import glob
import os
from collections import defaultdict

# --- Method constants (reproduce furnace.json on the 2022-23 season) ---
HHV_BTU_PER_CCF = 103_000           # natural-gas higher heating value (~1.037 therm/CCF)
WINTER_BASELOAD_CCF_PER_DAY = 0.50  # non-furnace gas (water heater, range) in winter
LOW_FIRE_INPUT_BTUH = 32_000        # stage input rates, from furnace.json
FULL_FIRE_INPUT_BTUH = 80_000       # "high" = full fire
SEASON_START_MONTH, SEASON_START_DAY = 10, 1   # Oct 1
SEASON_END_MONTH, SEASON_END_DAY = 5, 31       # May 31 (following year)

# Stored 2022-23 values in loads/furnace.json, for a printed self-test.
STORED_2022_23 = {
    "season_heating_gas_ccf": 470,
    "season_full_fire_equivalent_hours": 605,
    "season_clock_hours_at_low_fire": 1513,
    "season_runtime_fraction": 0.26,
    "peak_low_fire_duty_fraction": 0.62,
}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAS_GLOB = os.path.join(REPO, "data", "gas", "gas_usage_report_*.csv")
NORMALS_CSV = os.path.join(REPO, "data", "gas", "monthly_outdoor_normals.csv")


def load_all():
    """Merge every DTE export in data/gas into {date: (ccf, is_estimated)}.

    First file to supply a date wins; conflicting duplicates are reported (there
    should be none). Returns (merged_dict, conflict_list, file_spans)."""
    merged, conflicts, spans = {}, [], {}
    for p in sorted(glob.glob(GAS_GLOB)):
        first = last = None
        n = os.path.basename(p)
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                d = dt.datetime.strptime(r["Day"], "%m/%d/%Y").date()
                ccf = float(r["Daily Total"])
                est = r["Estimated Read"].strip() == "Yes"
                first = d if first is None or d < first else first
                last = d if last is None or d > last else last
                if d in merged:
                    if abs(merged[d][0] - ccf) > 1e-9:
                        conflicts.append((d, merged[d][0], ccf, n))
                else:
                    merged[d] = (ccf, est)
        spans[n] = (first, last)
    return merged, conflicts, spans


def low_fire_hours(ccf):
    return ccf * HHV_BTU_PER_CCF / LOW_FIRE_INPUT_BTUH


def full_fire_hours(ccf):
    return ccf * HHV_BTU_PER_CCF / FULL_FIRE_INPUT_BTUH


def days_in_month(year, month):
    nxt = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return (nxt - dt.date(year, month, 1)).days


def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def season_stats(merged, start_year, baseload):
    """Compute one Oct1(start_year) -> May31(start_year+1) heating season."""
    s = dt.date(start_year, SEASON_START_MONTH, SEASON_START_DAY)
    e = dt.date(start_year + 1, SEASON_END_MONTH, SEASON_END_DAY)
    have = [(d, merged[d]) for d in daterange(s, e) if d in merged]
    if not have:
        return None
    covered = len(have)
    total_days = (e - s).days + 1
    first_have = have[0][0]
    partial = covered < total_days or first_have > s
    est_frac = sum(1 for _, (_, est) in have if est) / covered

    h_ccf = sum(max(0.0, ccf - baseload) for _, (ccf, _) in have)
    lf = low_fire_hours(h_ccf)
    ff = full_fire_hours(h_ccf)
    frac = lf / (covered * 24)   # fraction over COVERED days (fair for partials)

    # peaks: single day and best 4-consecutive-day average, low-fire duty
    def duty(ccf_day):
        return low_fire_hours(max(0.0, ccf_day - baseload)) / 24.0
    day_ccf = {d: ccf for d, (ccf, _) in have}
    peak_day = max(have, key=lambda x: x[1][0])
    peak_day_duty = duty(peak_day[1][0])
    # 4-day window
    best4 = (None, -1)
    ds = [d for d, _ in have]
    for i in range(len(ds) - 3):
        window = [ds[i] + dt.timedelta(k) for k in range(4)]
        if all(w in day_ccf for w in window):
            avg = sum(day_ccf[w] for w in window) / 4
            if avg > best4[1]:
                best4 = (window[0], avg)

    # bracketing summer baseload (Jun1-Aug31 of the season's END year)
    yr = start_year + 1
    summer = [ccf for d, (ccf, _) in merged.items()
              if dt.date(yr, 6, 1) <= d <= dt.date(yr, 8, 31)]
    summer_bl = sum(summer) / len(summer) if summer else None

    return {
        "label": f"{start_year}-{str(start_year + 1)[2:]}",
        "start": s, "end": e, "covered": covered, "total_days": total_days,
        "partial": partial, "est_frac": est_frac,
        "heating_ccf": h_ccf, "low_fire_hours": lf, "full_fire_hours": ff,
        "runtime_fraction": frac,
        "peak_day": peak_day[0], "peak_day_ccf": peak_day[1][0],
        "peak_day_duty": peak_day_duty,
        "peak4_start": best4[0], "peak4_avg_ccf": best4[1],
        "peak4_duty": duty(best4[1]) if best4[0] else None,
        "summer_baseload": summer_bl,
    }


def selftest(s2223):
    print("SELF-TEST vs furnace.json (2022-23):")
    checks = [
        ("heating gas CCF", s2223["heating_ccf"], STORED_2022_23["season_heating_gas_ccf"], "{:.0f}", 0.02),
        ("full-fire-equiv hrs", s2223["full_fire_hours"], STORED_2022_23["season_full_fire_equivalent_hours"], "{:.0f}", 0.02),
        ("low-fire clock hrs", s2223["low_fire_hours"], STORED_2022_23["season_clock_hours_at_low_fire"], "{:.0f}", 0.02),
        ("runtime fraction", s2223["runtime_fraction"], STORED_2022_23["season_runtime_fraction"], "{:.3f}", 0.02),
        ("peak 4-day duty", s2223["peak4_duty"], STORED_2022_23["peak_low_fire_duty_fraction"], "{:.2f}", 0.05),
    ]
    ok = True
    for label, got, want, fmt, tol in checks:
        rel = abs(got - want) / want if want else 0
        mark = "OK " if rel <= tol else "!! "
        if rel > tol:
            ok = False
        print(f"  {mark}{label:22s} recomputed {fmt.format(got):>8s}   stored {fmt.format(want):>8s}")
    print(f"  => {'PASS' if ok else 'MISMATCH'}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseload", type=float, default=WINTER_BASELOAD_CCF_PER_DAY,
                    help="winter non-furnace baseload CCF/day to subtract")
    ap.add_argument("--monthly", action="store_true",
                    help="also print per-month low-fire runtime fractions")
    args = ap.parse_args()

    merged, conflicts, spans = load_all()
    days = sorted(merged)
    print(f"Loaded {len(spans)} files, {len(days)} unique days "
          f"{days[0]} .. {days[-1]}")
    calspan = (days[-1] - days[0]).days + 1
    gaps = calspan - len(days)
    print(f"  calendar span {calspan} days, gaps {gaps}, "
          f"overlap conflicts {len(conflicts)}")
    for c in conflicts[:5]:
        print("   conflict:", c)
    print(f"  method: baseload {args.baseload} CCF/day, HHV {HHV_BTU_PER_CCF} BTU/CCF, "
          f"low fire {LOW_FIRE_INPUT_BTUH} BTU/h\n")

    # every plausible season start year in range
    seasons = []
    for sy in range(days[0].year - 1, days[-1].year + 1):
        st = season_stats(merged, sy, args.baseload)
        if st:
            seasons.append(st)

    # self-test on 2022-23 if present and full
    for st in seasons:
        if st["label"] == "2022-23" and not st["partial"]:
            selftest(st)
            break

    # table
    hdr = (f"{'season':8s} {'days':>7s} {'heatCCF':>8s} {'LFhrs':>6s} "
           f"{'duty':>6s} {'peakday':>16s} {'pk4dy':>6s} {'sumBL':>6s}  note")
    print(hdr)
    print("-" * len(hdr))
    full = []
    for st in seasons:
        note = "PARTIAL" if st["partial"] else ""
        if st["est_frac"] >= 0.5:
            note = (note + " " if note else "") + f"est{st['est_frac']*100:.0f}%"
        daycol = f"{st['covered']}" + ("" if not st["partial"] else f"/{st['total_days']}")
        pk = f"{st['peak_day_ccf']:.2f}@{st['peak_day'].strftime('%m-%d')}"
        pk4 = f"{st['peak4_duty']:.2f}" if st["peak4_duty"] is not None else "  -"
        sbl = f"{st['summer_baseload']:.3f}" if st["summer_baseload"] is not None else "  -"
        print(f"{st['label']:8s} {daycol:>7s} {st['heating_ccf']:8.0f} "
              f"{st['low_fire_hours']:6.0f} {st['runtime_fraction']:6.2f} "
              f"{pk:>16s} {pk4:>6s} {sbl:>6s}  {note}")
        if not st["partial"]:
            full.append(st)

    if full:
        fr = [s["runtime_fraction"] for s in full]
        cc = [s["heating_ccf"] for s in full]
        print("-" * len(hdr))
        print(f"{'FULL x'+str(len(full)):8s} {'':>7s} "
              f"{sum(cc)/len(cc):8.0f} {'':>6s} {sum(fr)/len(fr):6.2f}   "
              f"mean duty; range {min(fr):.2f}-{max(fr):.2f}, "
              f"heatCCF {min(cc):.0f}-{max(cc):.0f}")

    if args.monthly:
        print("\nPER-MONTH low-fire runtime fraction")
        by = defaultdict(float)
        for d, (ccf, _) in merged.items():
            if d.month in (10, 11, 12, 1, 2, 3, 4, 5):
                by[(d.year, d.month)] += max(0.0, ccf - args.baseload)
        for (y, m) in sorted(by):
            mf = low_fire_hours(by[(y, m)]) / (days_in_month(y, m) * 24)
            print(f"  {y}-{m:02d}  {mf*100:5.1f}%")

    print("\nUA / BALANCE POINT")
    if os.path.exists(NORMALS_CSV):
        print(f"  (found {os.path.relpath(NORMALS_CSV, REPO)} — regression hook is "
              f"present in prior versions; wire per-season temps to enable)")
    else:
        print(f"  SKIPPED: no outdoor-temperature series. Add "
              f"{os.path.relpath(NORMALS_CSV, REPO)} (month,mean_temp_f) to enable. "
              f"Daily airport-station temps would sharpen UA/balance point.")


if __name__ == "__main__":
    main()
