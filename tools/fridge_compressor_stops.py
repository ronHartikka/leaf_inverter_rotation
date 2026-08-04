#!/usr/bin/env python3
"""Find where the FRIDGE'S OWN controller stopped a running compressor (relay
closed, current fresh, not a defrost). For each, report the 1-min-average FFC
temp at the stop (the fridge's compressor-off temperature, on our RTD) and how
long the compressor stayed off before running again. Pure python (no numpy) so
it runs on the Ubuntu box.

  Usage:  python3 tools/fridge_compressor_stops.py <run_*.csv>

States (from the current signal):
  Compressor running     = relay_cmd==1 AND current_stale==0 AND 0.35<=current<1.7 A
  Compressor not running = ...current<0.35 A
  Defroster running      = current>=1.7 A (a stop that leads to this is excluded)

Event = running -> not-running that then STAYS not-running >=60 s (so it's a real
stop, not an inverter ramp dip) with NO defroster within the next 180 s. We only
catch it when the relay is closed and data is fresh, so our own relay-open periods
(current frozen / stale) are naturally excluded.

9-column runs (no relay_cmd/current_stale columns) are the no-relay-control
captures: relay is treated as always closed and data as always fresh.

Output: per-event table (date, time, FFC 1-min avg + instant, off-duration min),
then summary stats for the FFC compressor-off temp and an off-duration histogram.
Used 2026-08-04 to characterize the fridge's own compressor-off temp (~35 F) and
off-duration (median ~23 min, no 7-min floor); see docs/lab_notebook.md.
"""
import csv, sys
from datetime import datetime

COMP_LO, COMP_HI = 0.35, 1.7
OFF_HOLD, DEFROST_LOOK, AVG_WIN = 60.0, 180.0, 60.0

ts, cur, t2, relay, stale = [], [], [], [], []
with open(sys.argv[1]) as f:
    for row in csv.DictReader(f):
        try:
            u = float(row["unix_s"])
        except (ValueError, KeyError):
            continue
        def gf(k):
            try:
                return float(row[k])
            except (ValueError, KeyError):
                return float("nan")
        ts.append(u); cur.append(gf("current_a")); t2.append(gf("t2_fridge_f"))
        # 9-col runs (no coast controller) have no relay_cmd/current_stale columns:
        # relay was always closed, and there's no stale flag -> default closed/fresh.
        relay.append((row.get("relay_cmd") or "1").strip())
        stale.append((row.get("current_stale") or "0").strip())

n = len(ts)
def is_run(i):
    c = cur[i]
    return relay[i] == "1" and stale[i] == "0" and c == c and COMP_LO <= c < COMP_HI
def is_off(i):
    c = cur[i]
    return relay[i] == "1" and stale[i] == "0" and c == c and c < COMP_LO

events, i = [], 1
while i < n:
    if is_run(i - 1) and is_off(i):
        t0 = ts[i]
        j, came_back, defrost = i, False, False
        while j < n and ts[j] - t0 <= DEFROST_LOOK:
            c = cur[j]
            if c == c and stale[j] == "0":
                if ts[j] - t0 <= OFF_HOLD and c >= COMP_LO:
                    came_back = True
                if c >= COMP_HI:
                    defrost = True
            j += 1
        if not came_back and not defrost:
            k, s, cnt = i, 0.0, 0
            while k >= 0 and t0 - ts[k] <= AVG_WIN:
                if t2[k] == t2[k]:
                    s += t2[k]; cnt += 1
                k -= 1
            avg = s / cnt if cnt else float("nan")
            inst = t2[i] if t2[i] == t2[i] else float("nan")
            r = i
            while r < n and not is_run(r):  # find next compressor-run = end of off period
                r += 1
            off_min = (ts[r] - t0) / 60.0 if r < n else float("nan")
            events.append((datetime.fromtimestamp(t0), avg, inst, off_min))
            i = r
            continue
    i += 1

print("Date        Time      FFC_1min_avg  (inst)  off_min")
for dt, avg, inst, off in events:
    print("%s  %s   %6.2f      %5.1f   %6.1f" %
          (dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"), avg, inst, off))
print("# events = %d" % len(events))
import statistics
a = sorted(x for (_, x, _, _) in events if x == x)
if a:
    print("# FFC_1min_avg: n=%d mean=%.2f median=%.2f std=%.2f min=%.2f max=%.2f"
          % (len(a), statistics.mean(a), statistics.median(a), statistics.pstdev(a), a[0], a[-1]))
    core = [x for x in a if x <= 37.0]  # tight band, drop warm door/defrost-recovery excursions
    if core:
        print("# core (<=37F): n=%d mean=%.2f median=%.2f std=%.2f min=%.2f max=%.2f"
              % (len(core), statistics.mean(core), statistics.median(core),
                 statistics.pstdev(core), min(core), max(core)))
d = sorted(o for (_, _, _, o) in events if o == o)
if d:
    print("# off_min: n=%d mean=%.1f median=%.1f min=%.1f max=%.1f"
          % (len(d), statistics.mean(d), statistics.median(d), d[0], d[-1]))
    buckets = [("<5", 0, 5), ("5-7", 5, 7), ("7-10", 7, 10), ("10-15", 10, 15),
               ("15-20", 15, 20), ("20-30", 20, 30), (">=30", 30, 1e9)]
    print("# off-duration histogram (min):")
    for lbl, lo, hi in buckets:
        c = sum(1 for x in d if lo <= x < hi)
        print("#   %-6s %2d  %s" % (lbl, c, "#" * c))
    print("# restarted in < 7 min: %d of %d" % (sum(1 for x in d if x < 7), len(d)))
