#!/usr/bin/env python3
"""
clean_window_duty.py -- per-night fridge duty over a DEFROST-FREE window.

Duty = 100 * relay_closed / window, taken from the coast log (each CUT..RESTORE is
relay-open / power-off). A defrost and the long continuous recovery run that follows
it inflate duty and contaminate a fixed overnight window, so instead of a fixed
00:00-06:30 we score each night like this:

  1. Find defrosts: the ~1.9 A resistive heater shows as current flat in 1.6-2.05 A
     for >=10 min. Bridge dips <300 s (the board pulses to ~1 A every ~10 min sampling
     the coil). Search from 20:00 the PRIOR evening, because a pre-midnight defrost's
     recovery bleeds past midnight into the window.
  2. Exclude defrost + recovery: recovery is "done" at the first coast CUT after the
     defrost (the box can shed load again), so exclude [defrost_start, that_cut].
  3. Take the LONGEST remaining defrost-free span within 00:00-07:00, trim to 5 h.
  4. Report duty over that clean span (plus the old fixed 00:00-06:30 for comparison).

Same mechanical rule every night -> adjustable window POSITION, fixed LENGTH, chosen
to remove defrost/recovery. Not "grab the best coasts" (that would bias duty low).

Usage:  python3 clean_window_duty.py <run_basename> <YYYY-MM-DD> [<YYYY-MM-DD> ...]
        reads <run_basename>.csv and <run_basename>.coast from the current directory.
"""
import csv, argparse
from datetime import datetime

DEFROST_LO, DEFROST_HI = 1.6, 2.05   # A: flat resistive-heater band
DIP_BRIDGE_S = 300                    # bridge coil-temp sampling dips
DEFROST_MIN_S = 600                   # >=10 min to count as a defrost
SEARCH_BACK_S = 4 * 3600             # look back to 20:00 prior evening
CLEAN_MAX_S = 5 * 3600              # trim clean span to 5 h

def ts(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").timestamp()
def hm(t): return datetime.fromtimestamp(t).strftime("%m-%d %H:%M")

def parse_coast(fn):
    out, cur = [], None
    for ln in open(fn):
        p = ln.rstrip().split("\t")
        if len(p) < 2:
            continue
        try: t = ts(p[0][:19])
        except ValueError: continue
        if p[1].startswith("CUT start"): cur = t
        elif p[1].startswith("RESTORE") and cur is not None: out.append((cur, t)); cur = None
    return out

def merge(ivs):
    ivs = sorted(ivs); m = []
    for a, b in ivs:
        if m and a <= m[-1][1]: m[-1][1] = max(m[-1][1], b)
        else: m.append([a, b])
    return m

def subtract(a0, b0, holes):
    res, cur = [], a0
    for ha, hb in holes:
        if hb <= a0 or ha >= b0: continue
        if ha > cur: res.append((cur, min(ha, b0)))
        cur = max(cur, hb)
    if cur < b0: res.append((cur, b0))
    return res

def find_defrosts(rows):
    defr, st, last = [], None, None
    for t, c in rows:
        band = c is not None and DEFROST_LO <= c <= DEFROST_HI
        if band:
            if st is None: st = t
            last = t
        elif st is not None and t - last > DIP_BRIDGE_S:
            if last - st >= DEFROST_MIN_S: defr.append((st, last))
            st = None
    if st is not None and last - st >= DEFROST_MIN_S: defr.append((st, last))
    return defr

def analyze(basename, date):
    W0 = ts(date + "T00:00:00"); W1 = ts(date + "T07:00:00"); SW0 = W0 - SEARCH_BACK_S
    rows = []
    with open(basename + ".csv") as f:
        r = csv.reader(f); next(r)
        for x in r:
            if len(x) < 6: continue
            try: t = float(x[0])
            except ValueError: continue
            if not (SW0 <= t <= W1): continue
            try: c = float(x[2])
            except ValueError: c = None
            rows.append((t, c))
    cuts = parse_coast(basename + ".coast")
    defr = find_defrosts(rows)
    cont = merge([(ds, min([c for c, rr in cuts if c > de], default=W1)) for ds, de in defr])

    def duty(a, b):
        o = sum(max(0, min(rr, b) - max(cc, a)) for cc, rr in cuts)
        return 100 * (1 - o / (b - a)), o / 60, sum(1 for cc, rr in cuts if min(rr, b) > max(cc, a))

    old = duty(W0, ts(date + "T06:30:00"))[0]
    clean = subtract(W0, W1, cont)
    best = max(clean, key=lambda iv: iv[1] - iv[0]) if clean else None
    dl = ", ".join("%s-%s" % (hm(a), hm(b)) for a, b in defr) or "none"
    if best:
        a, b = best
        if b - a > CLEAN_MAX_S: b = a + CLEAN_MAX_S
        d, o, n = duty(a, b); L = (b - a) / 3600
        cw = "CLEAN %s-%s (%.1fh): %.0f%%  (off %.0f min, %d coasts)%s" % (
            hm(a), hm(b), L, d, o, n, "" if L >= 3 else "  [<3h LOW-CONF]")
    else:
        cw = "no defrost-free span"
    print("%s  defrost: %-30s  OLD 00:00-06:30 %.0f%%  ->  %s" % (date, dl, old, cw))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="run basename; reads <run>.csv and <run>.coast")
    ap.add_argument("dates", nargs="+", help="one or more YYYY-MM-DD dawn dates")
    a = ap.parse_args()
    for d in a.dates:
        analyze(a.run, d)
