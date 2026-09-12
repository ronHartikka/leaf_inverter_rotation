#!/usr/bin/env python3
"""cur_corruption_scan.py -- count corrupt CUR serial lines and bucket them by the
current level in effect at the time.

WHY THIS EXISTS
Occasional CUR lines arrive garbled over the Arduino's USB link (docs/todo.md,
"CURRENT-CHANNEL SERIAL CORRUPTION"). The Arduino's computed value is fine; the
corruption happens in transit. The standing hypothesis is that it clusters as the
current levels off near setpoint -- i.e. when the fridge's BLDC inverter compressor is
running SLOW -- which would point at low-speed PWM noise coupling into the USB lead.

This tests that. On an inverter compressor the running current IS a proxy for speed, so
bucketing the corrupt-line rate by amps asks the question directly: is corruption a
function of compressor speed, or is it flat across all speeds?

It also produces the measuring stick docs/todo.md asks for -- a corrupt-line RATE that
can be compared before vs after ONE change (lower baud, or a ferrite / re-route), so the
two candidate causes can be told apart instead of guessed at.

The .raw sidecar is what makes this possible: dual_logger.py's hardened parser DROPS
corrupt lines from the merged CSV, but mirrors every byte from both devices to .raw,
each line stamped with the logger machine's wall clock on arrival.

  Usage:  python3 cur_corruption_scan.py FILE.raw [FILE.raw ...]
"""
import re
import sys
import os
from collections import defaultdict

# The same strict, end-anchored pattern dual_logger.py uses to accept a data line:
# "t_ms,amps,note" with the decimal point REQUIRED. Anything data-shaped that fails
# this is what the old prefix-matching parser used to swallow as a false 0.000 A.
CUR_DATA_RE = re.compile(r"^\s*(\d+),(\d+\.\d+),(\w*)\s*$")

# A line is "data-shaped" if it opens like a data line: digits then a comma. Banners,
# countdowns and "# ..." comments are legitimate non-data output, NOT corruption, and
# must not be counted as such.
DATA_SHAPED_RE = re.compile(r"^\s*\d+,")

# Bytes outside printable ASCII in a data-shaped line mean the line was physically
# mangled rather than merely mis-formatted.
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}

# If the last clean reading is older than this, we don't know what the compressor was
# doing when the corrupt line arrived, so the line is bucketed as unknown rather than
# attributed to a stale current level.
MAX_ATTRIBUTION_AGE_S = 5.0

BUCKET_W = 0.05          # amps per bucket
IDLE_A   = 0.20          # below this the compressor is off (fridge idles ~0.12 A)


def bucket_label(a):
    if a < IDLE_A:
        return "idle (<0.20)"
    lo = int(a / BUCKET_W) * BUCKET_W
    return "%.2f-%.2f" % (lo, lo + BUCKET_W)


def scan(path):
    clean = defaultdict(int)     # bucket -> clean data lines seen
    corrupt = defaultdict(int)   # bucket -> corrupt data lines seen
    n_cur = n_clean = n_corrupt = n_info = n_info_garbled = 0
    last_amps = None
    last_t = 0.0
    corrupt_times = []

    with open(path, "rb") as f:
        for raw in f:
            parts = raw.rstrip(b"\r\n").split(b"\t", 2)
            if len(parts) < 3 or parts[1] != b"CUR":
                continue
            n_cur += 1
            try:
                t = float(parts[0])
            except ValueError:
                continue
            body = parts[2]
            text = body.decode("latin-1")
            garbled = any(b not in PRINTABLE for b in body)

            if DATA_SHAPED_RE.match(text) or (garbled and b"," in body):
                m = CUR_DATA_RE.match(text)
                if m and not garbled:
                    n_clean += 1
                    amps = float(m.group(2))
                    clean[bucket_label(amps)] += 1
                    last_amps, last_t = amps, t
                else:
                    n_corrupt += 1
                    corrupt_times.append(t)
                    if last_amps is not None and (t - last_t) <= MAX_ATTRIBUTION_AGE_S:
                        corrupt[bucket_label(last_amps)] += 1
                    else:
                        corrupt["unknown"] += 1
            else:
                n_info += 1
                if garbled:
                    n_info_garbled += 1

    return dict(clean=clean, corrupt=corrupt, n_cur=n_cur, n_clean=n_clean,
                n_corrupt=n_corrupt, n_info=n_info, n_info_garbled=n_info_garbled,
                corrupt_times=corrupt_times)


def report(name, r):
    print("=" * 78)
    print(name)
    print("-" * 78)
    tot = r["n_clean"] + r["n_corrupt"]
    rate = (1000.0 * r["n_corrupt"] / tot) if tot else 0.0
    print("  CUR lines %d | data clean %d | data CORRUPT %d | info/banner %d (%d garbled)"
          % (r["n_cur"], r["n_clean"], r["n_corrupt"], r["n_info"], r["n_info_garbled"]))
    print("  overall corrupt rate: %.3f per 1000 data lines" % rate)
    if not r["n_corrupt"]:
        print("  no corrupt data lines -- nothing to correlate.")
        return
    ts = sorted(r["corrupt_times"])
    span_h = (ts[-1] - ts[0]) / 3600.0 if len(ts) > 1 else 0.0
    print("  corrupt lines span %.1f h, %.1f per hour" %
          (span_h, len(ts) / span_h if span_h else 0.0))
    print()
    print("  %-14s %12s %9s %14s" % ("current band", "clean lines", "corrupt", "per 1000"))
    keys = sorted(set(r["clean"]) | set(r["corrupt"]),
                  key=lambda k: (k in ("unknown",), k))
    for k in keys:
        c, x = r["clean"].get(k, 0), r["corrupt"].get(k, 0)
        if not c and not x:
            continue
        per = (1000.0 * x / c) if c else float("nan")
        flag = "  <<<" if c and per > 3 * rate and x >= 3 else ""
        print("  %-14s %12d %9d %14s%s"
              % (k, c, x, ("%.3f" % per) if c else "n/a", flag))
    print()


def main(paths):
    grand = dict(clean=defaultdict(int), corrupt=defaultdict(int), n_cur=0, n_clean=0,
                 n_corrupt=0, n_info=0, n_info_garbled=0, corrupt_times=[])
    for p in paths:
        r = scan(p)
        report(os.path.basename(p), r)
        for k in ("clean", "corrupt"):
            for b, v in r[k].items():
                grand[k][b] += v
        for k in ("n_cur", "n_clean", "n_corrupt", "n_info", "n_info_garbled"):
            grand[k] += r[k]
        grand["corrupt_times"] += r["corrupt_times"]
    if len(paths) > 1:
        report("ALL FILES COMBINED", grand)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
