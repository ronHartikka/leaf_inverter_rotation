#!/usr/bin/env python3
"""
characterize.py -- compute load-characterization numbers from a dual_logger CSV.

Reproduces the analysis run by hand for the chest freezer, as a repeatable script.
Point it at a merged dual_logger capture and it prints the numbers that go into
the per-load JSON: duty cycle, running current, end-of-run current, inrush
(method-limited), thermostat band, warmup + pulldown rates.

Usage:
    python3 characterize.py ../data/kitchen_fridge_run.csv
    python3 characterize.py ../data/kitchen_fridge_run.csv --temp-col t2_fridge_f

CSV columns expected (dual_logger.py output):
    unix_s,iso,current_a,current_note,t1_freezer_f,t2_fridge_f,res1_ohm,res2_ohm,fault

Current ON/OFF uses hysteresis (START_CONFIRM_A / STOP_A). Defaults suit the
~0.7A compressor class; override with --on / --off if a load differs.

NOTE (lesson #10): inrush from this data is method-limited, NOT a true surge peak.
The start transient is sub-100ms and falls between 10Hz samples.
"""
import csv, argparse, statistics


def load_rows(path, temp_col, tmin=None, tmax=None):
    rows = []
    dropped = 0
    with open(path) as f:
        r = csv.DictReader(f)
        if temp_col not in r.fieldnames:
            raise SystemExit(f"temp column {temp_col!r} not in CSV; found: {r.fieldnames}")
        for row in r:
            try:
                temp = float(row[temp_col])
                # Drop nonphysical temps (RTD open/short from a bump, or a door-open
                # warm spike) so a 3-second glitch can't pollute the envelope or a
                # segment's warmup/pulldown slope. Opt-in via --temp-min/--temp-max;
                # the `fault` flag misses bad-but-in-range resistances, so filter by value.
                if (tmin is not None and temp < tmin) or (tmax is not None and temp > tmax):
                    dropped += 1
                    continue
                rows.append((float(row['unix_s']), float(row['current_a']),
                             temp, int(row.get('fault', 0) or 0)))
            except (ValueError, KeyError):
                continue  # tolerate the occasional RTD fault line
    if not rows:
        raise SystemExit("no usable rows parsed")
    if dropped:
        print(f"# dropped {dropped} rows outside [{tmin}, {tmax}] F (nonphysical/artifact)")
    return rows


def segment(rows, on_a, off_a):
    """Split into ON runs and OFF gaps via current hysteresis. Returns (runs, offs)
    where each is a list of segments, each segment a list of (t, current, temp)."""
    state = False
    runs, offs, cur, coff = [], [], [], []
    for (t, a, temp, _fault) in rows:
        if not state and a >= on_a:
            state = True
            if coff:
                offs.append(coff); coff = []
            cur = [(t, a, temp)]
        elif state and a < off_a:
            state = False
            if len(cur) > 50:
                runs.append(cur)
            coff = [(t, a, temp)]
        elif state:
            cur.append((t, a, temp))
        else:
            coff.append((t, a, temp))
    return runs, offs


def slope_f_per_min(seg):
    if len(seg) < 2:
        return None
    dt = (seg[-1][0] - seg[0][0]) / 60.0
    if dt <= 0:
        return None
    return (seg[-1][2] - seg[0][2]) / dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--temp-col", default="t1_freezer_f",
                    help="temperature column to analyze (default t1_freezer_f)")
    ap.add_argument("--on", type=float, default=0.35, help="START_CONFIRM_A (default 0.35)")
    ap.add_argument("--off", type=float, default=0.20, help="STOP_A (default 0.20)")
    ap.add_argument("--temp-min", type=float, default=None,
                    help="drop rows below this temp (F) as nonphysical (e.g. a bump/RTD open)")
    ap.add_argument("--temp-max", type=float, default=None,
                    help="drop rows above this temp (F) as artifact (e.g. a door-open spike)")
    args = ap.parse_args()

    rows = load_rows(args.csv, args.temp_col, args.temp_min, args.temp_max)
    t0, tN = rows[0][0], rows[-1][0]
    dur = tN - t0

    runs, offs = segment(rows, args.on, args.off)

    on_time = sum(seg[-1][0] - seg[0][0] for seg in runs)
    duty = 100.0 * on_time / dur if dur else 0.0

    bodies = [statistics.mean(a for (t, a, _) in seg
                              if seg[0][0] + 5 < t < seg[-1][0] - 5) or 0
              for seg in runs if len(seg) > 20]
    tails = [statistics.mean(a for (t, a, _) in seg if t >= seg[-1][0] - 60)
             for seg in runs if any(t >= seg[-1][0] - 60 for (t, a, _) in seg)]
    peaks = [max(a for (t, a, _) in seg if t <= seg[0][0] + 3) for seg in runs]

    warms = [s for s in (slope_f_per_min(o) for o in offs if len(o) > 600) if s is not None]
    pulls = [s for s in (slope_f_per_min(r) for r in runs if len(r) > 600) if s is not None]

    cutouts = [min(t2 for (_, _, t2) in seg) for seg in runs]
    cutins = [max(t2 for (_, _, t2) in seg) for seg in offs if len(seg) > 100]

    temps = [t2 for (_, _, t2, _f) in rows]
    starts = [o[0][0] for o in offs]  # approx: each off ends at a start

    def fmt(x, p=3):
        return f"{x:.{p}f}" if x is not None else "n/a"

    print(f"file: {args.csv}   temp col: {args.temp_col}")
    print(f"duration: {dur/3600:.2f} h   samples: {len(rows)}")
    print(f"runs detected: {len(runs)}   (hysteresis on={args.on} off={args.off})")
    print("-" * 56)
    print(f"DUTY CYCLE:            {duty:.1f} %   ({on_time/3600:.2f} h ON)")
    if len(runs) > 1:
        periods = [runs[i+1][0][0] - runs[i][0][0] for i in range(len(runs)-1)]
        print(f"mean cycle period:    {statistics.mean(periods)/60:.1f} min")
        print(f"mean run duration:    {statistics.mean(seg[-1][0]-seg[0][0] for seg in runs)/60:.1f} min")
    if bodies:
        print(f"running current:      {fmt(statistics.mean([b for b in bodies if b]))} A (steady body)")
    if tails:
        print(f"end-of-run (60s):     {fmt(statistics.mean(tails))} A  range {fmt(min(tails))}-{fmt(max(tails))}")
    if peaks:
        print(f"inrush (METHOD-LIMITED): {fmt(statistics.mean(peaks),2)} A  -- NOT a true surge peak")
    print(f"temp envelope:        {min(temps):.2f} .. {max(temps):.2f} F")
    if cutouts and cutins:
        print(f"thermostat band:      cut-out {statistics.mean(cutouts):.2f}  cut-in {statistics.mean(cutins):.2f}  "
              f"band {statistics.mean(cutins)-statistics.mean(cutouts):.2f} F")
    if warms:
        print(f"WARMUP (OFF):         mean {fmt(statistics.mean(warms))}  max {fmt(max(warms))} F/min")
    if pulls:
        print(f"pulldown (ON):        mean {fmt(statistics.mean(pulls))}  min {fmt(min(pulls))} F/min")


if __name__ == "__main__":
    main()
