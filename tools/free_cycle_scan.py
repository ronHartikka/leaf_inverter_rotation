#!/usr/bin/env python3
"""free_cycle_scan.py — find the fridge's NATIVE compressor free-cycles.

A "native free-cycle" = the fridge's own thermostat opens the compressor while
mains power is still available (our relay CLOSED). We care because the coast
experiment assumes the fridge cycles as a stable function of its dial setting;
if native cut-out/cut-in temps (read on OUR RTD) wander >24 h after a setting
change, the FC=1-vs-FC=3 duty comparison is confounded (see docs/lab_notebook.md
08-03 ~4am observation).

DISCRIMINATOR (verified 2026-08-03 against the labeled 12-col run — the kitchen
fridge is an INVERTER compressor, no PTC/locked-rotor):

  state                         current signature
  ---------------------------   ------------------------------------------
  our coast (relay OPEN)        FROZEN: reading holds its last value exactly
                                (Δ==0 sample-to-sample), typically ~0.85 A
                                (a RUNNING value, NOT near zero) => level is
                                useless; a plateau held >= --frozen-s is coast.
  native off (relay closed)     low ~0.18 A AND jittery (nonzero |Δ|)
  running (relay closed)        ~0.7-1.0 A, jittery; inverter ramps its speed
  native cut-in                 soft step to ~0.7 A then gradual ramp up

So we DON'T threshold on level. We reduce the current trace to constant-value
runs; any run held >= --frozen-s is a coast (relay open) and is excluded. On the
remaining powered samples, compressor-on = current > --on-thresh, and a native
free-cycle is an off stretch >= --min-off (and < --max-off; longer => DEFROST?).

12-col runs (relay_cmd/compressor_on present) use those columns directly and
ignore the texture heuristic — that's the ground truth the heuristic was tuned to.

Temps on the FFC RTD = t2_fridge_f; freezer t1_freezer_f for context.
Cut-out temp = t2 at off start (cold end); cut-in temp = t2 at off end (warm end).
"""
import argparse, csv, sys, statistics
from datetime import datetime


def parse_iso(s):
    return datetime.fromisoformat(s)


def fnum(row, key):
    try:
        return float(row[key])
    except (ValueError, KeyError, TypeError):
        return float("nan")


def iter_rows(path, lo, hi):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        cols12 = "compressor_on" in r.fieldnames and "relay_cmd" in r.fieldnames
        yield ("__META__", cols12)
        for row in r:
            iso = row.get("iso", "")
            if not iso or "T" not in iso:
                continue
            try:
                ep = float(row["unix_s"])
            except (ValueError, KeyError):
                continue
            if lo or hi:
                t = parse_iso(iso)
                if lo and t < lo:
                    continue
                if hi and t > hi:
                    break
            yield (ep, iso, fnum(row, "current_a"), fnum(row, "t2_fridge_f"),
                   fnum(row, "t1_freezer_f"),
                   row.get("relay_cmd", "").strip(), row.get("compressor_on", "").strip(),
                   row.get("current_stale", "").strip())


def segments(path, lo, hi, frozen_s, on_thresh, force_texture=False):
    """Yield ('coast'|'on'|'off', ep_start, ep_end, t2_start, t2_end, t2_min, t1_start).
    12-col: segments from relay_cmd/compressor_on. 9-col: from current texture."""
    it = iter_rows(path, lo, hi)
    cols12 = next(it)[1] and not force_texture  # first yield is ("__META__", cols12)

    if cols12:
        cur_state = None
        s_ep = s_t2 = s_t1 = None
        t2min = float("inf")
        last = None
        for ep, iso, cur, t2, t1, relay, comp, stale in it:
            if relay != "1":
                st = "coast"
            elif stale == "1":
                st = "coast"  # current-sense dropout: reading frozen/unknown, not a real cutoff
            elif comp == "1":
                st = "on"
            else:
                st = "off"
            if st != cur_state:
                if cur_state is not None:
                    yield (cur_state, s_ep, last[0], s_t2, last[3], t2min, s_t1)
                cur_state, s_ep, s_t2, s_t1, t2min = st, ep, t2, t1, (t2 if t2 == t2 else float("inf"))
            else:
                if t2 == t2:
                    t2min = min(t2min, t2)
            last = (ep, iso, cur, t2, t1)
        if cur_state is not None and last is not None:
            yield (cur_state, s_ep, last[0], s_t2, last[3], t2min, s_t1)
        return

    # 9-col: constant-value run reduction -> coast/on/off
    run_ep0 = run_cur = run_t20 = run_t1 = None
    run_last = None
    run_t2min = float("inf")

    def classify_run(dur, cur):
        if dur >= frozen_s:
            return "coast"
        return "on" if cur > on_thresh else "off"

    # merge consecutive same-classified runs into segments
    seg_state = None
    seg_ep0 = seg_t20 = seg_t1 = None
    seg_t2min = float("inf")
    seg_last = None

    for ep, iso, cur, t2, t1, _, _, _ in it:
        if run_cur is None or cur != run_cur:
            # close previous run
            if run_cur is not None:
                dur = run_last[0] - run_ep0
                st = classify_run(dur, run_cur)
                # feed run as a segment unit
                if st != seg_state:
                    if seg_state is not None:
                        yield (seg_state, seg_ep0, seg_last[0], seg_t20, seg_last[3], seg_t2min, seg_t1)
                    seg_state, seg_ep0, seg_t20, seg_t1 = st, run_ep0, run_t20, run_t1
                    seg_t2min = run_t2min
                    seg_last = run_last
                else:
                    seg_t2min = min(seg_t2min, run_t2min)
                    seg_last = run_last
            run_ep0, run_cur, run_t20, run_t1 = ep, cur, t2, t1
            run_t2min = t2 if t2 == t2 else float("inf")
        else:
            if t2 == t2:
                run_t2min = min(run_t2min, t2)
        run_last = (ep, iso, cur, t2, t1)
    # flush tail
    if run_cur is not None:
        dur = run_last[0] - run_ep0
        st = classify_run(dur, run_cur)
        if st != seg_state:
            if seg_state is not None:
                yield (seg_state, seg_ep0, seg_last[0], seg_t20, seg_last[3], seg_t2min, seg_t1)
            seg_state, seg_ep0, seg_t20, seg_t1 = st, run_ep0, run_t20, run_t1
            seg_t2min, seg_last = run_t2min, run_last
        else:
            seg_t2min = min(seg_t2min, run_t2min)
            seg_last = run_last
    if seg_state is not None:
        yield (seg_state, seg_ep0, seg_last[0], seg_t20, seg_last[3], seg_t2min, seg_t1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--on-thresh", type=float, default=0.35, help="A, compressor-on (9-col)")
    ap.add_argument("--frozen-s", type=float, default=60.0, help="s, constant-current plateau => coast")
    ap.add_argument("--min-off", type=float, default=120.0, help="s, ignore offs shorter than this")
    ap.add_argument("--max-off", type=float, default=1800.0, help="s, longer offs flagged DEFROST?")
    ap.add_argument("--from", dest="ts_from")
    ap.add_argument("--to", dest="ts_to")
    ap.add_argument("--texture", action="store_true",
                    help="force the 9-col current-texture path even on 12-col runs (validation)")
    ap.add_argument("--change", help="ISO time of the last dial/setting change; per-event "
                    "hours-since-change are printed and split at 24 h")
    args = ap.parse_args()
    lo = parse_iso(args.ts_from) if args.ts_from else None
    hi = parse_iso(args.ts_to) if args.ts_to else None
    change_ep = parse_iso(args.change).timestamp() if args.change else None

    events, defrosts, coasts = [], [], 0
    prev_state = "?"  # state of the segment immediately before an off period
    for st, ep0, ep1, t2_0, t2_1, t2min, t1_0 in segments(
            args.csv_path, lo, hi, args.frozen_s, args.on_thresh, args.texture):
        if st == "coast":
            coasts += 1
        elif st == "off":
            dur = ep1 - ep0
            if dur >= args.min_off:
                iso0 = datetime.fromtimestamp(ep0).isoformat()
                hrs = (ep0 - change_ep) / 3600.0 if change_ep else None
                # was the compressor RUNNING just before (fridge cut off a running
                # compressor, like 3:53) or had we just COASTED (restart delay)?
                pre = "running" if prev_state == "on" else ("post-coast" if prev_state == "coast" else prev_state)
                rec = dict(iso0=iso0, dur=dur, t2_out=t2_0, t2_in=t2_1, t2min=t2min,
                           t1_out=t1_0, hrs=hrs, pre=pre)
                (defrosts if dur > args.max_off else events).append(rec)
        prev_state = st

    print(f"# {args.csv_path}")
    print(f"# native free-cycles={len(events)}  defrost?-flagged={len(defrosts)}  coasts(masked)={coasts}")
    hrhdr = f" {'hrs_chg':>7s}" if change_ep else ""
    print(f"# {'start':19s} {'dur_min':>7s} {'t2_out(cold)':>12s} {'t2_min':>7s} {'t2_in(warm)':>11s} {'t1_out':>7s}{hrhdr}")
    for e in events:
        hrc = f" {e['hrs']:7.1f}" if change_ep else ""
        print(f"  {e['iso0'][:19]} {e['dur']/60:7.1f} {e['t2_out']:12.1f} {e['t2min']:7.1f} {e['t2_in']:11.1f} {e['t1_out']:7.1f}{hrc}  {e['pre']}")
    if events:
        def stat(x):
            x = [v for v in x if v == v]
            if not x:
                return "n=0"
            return f"n={len(x)} mean={statistics.mean(x):.1f} med={statistics.median(x):.1f} min={min(x):.1f} max={max(x):.1f}"
        print(f"# CUT-OUT t2 (cold end): {stat([e['t2_out'] for e in events])}")
        print(f"# CUT-IN  t2 (warm end): {stat([e['t2_in'] for e in events])}")
        print(f"# OFF dur min:           {stat([e['dur']/60 for e in events])}")
        if change_ep:
            early = [e['t2_out'] for e in events if e['hrs'] is not None and e['hrs'] < 24]
            late = [e['t2_out'] for e in events if e['hrs'] is not None and e['hrs'] >= 24]
            print(f"# CUT-OUT t2  <24h after change: {stat(early)}")
            print(f"# CUT-OUT t2 >=24h after change: {stat(late)}")
    for e in defrosts:
        print(f"# DEFROST? {e['iso0'][:19]} {e['dur']/60:.1f}min  t1_out={e['t1_out']:.1f}")


if __name__ == "__main__":
    main()
