#!/usr/bin/env python3
"""
crosscheck_temps.py  --  three-way PT1000 temperature cross-check (P0 verify).

For a dual_logger .raw capture, pair each ESP32 TMP block's
    Resistance{1,2} = <ohm>       (the raw truth logged every cycle)
    Temperature{1,2} = <degF>     (the ESP32 sketch's OWN conversion, Adafruit lib)
and compare three independent witnesses of the same physical temperature:

  1. ESP32 degF        -- from the sketch's Temperature print (its display value)
  2. logger degF       -- dual_logger.res_to_f() recomputed from the resistance
                          (now the FIXED both-branch Callendar-Van Dusen)
  3. reference degF     -- an INDEPENDENT correct sub-zero CVD recomputed here
                          from scratch, so agreement means "right", not "same code"

Why three and not two: the ESP32's Adafruit temperature() and our conversion could
AGREE and both be WRONG on the cold side (older Adafruit versions use the same
positive-only quadratic). Only an independent reference distinguishes "agree and
right" from "agree and both wrong (same bug)". (See docs/todo.md, P0 UPDATE.)

Usage:
    python3 tools/crosscheck_temps.py data/kitchen_fridge_run.raw
"""

import sys
import re
import math
import os

# Import the logger's (fixed) conversion so we test the ACTUAL shipping code.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dual_logger import res_to_f as logger_res_to_f  # noqa: E402

# ---- Independent reference conversion (recomputed fresh, NOT imported) ----
# Same physics, deliberately a separate implementation so a bug in dual_logger
# cannot hide by being copied here. Newton on the exact both-branch forward CVD.
_R0, _A, _B, _C = 1000.0, 3.9083e-3, -5.775e-7, -4.183e-12
def ref_res_to_f(R):
    # seed with positive-branch closed form
    disc = _A*_A - 4*_B*(1.0 - R/_R0)
    t = (-_A + math.sqrt(disc)) / (2*_B)
    if R < _R0:
        for _ in range(50):
            f = _R0*(1 + _A*t + _B*t*t + _C*(t-100.0)*t**3) - R
            fp = _R0*(_A + 2*_B*t + _C*(4*t**3 - 300*t*t))
            step = f/fp
            t -= step
            if abs(step) < 1e-10:
                break
    return t*9.0/5.0 + 32.0

res_re = re.compile(r"Resistance([12])\s*=\s*([\d.]+)")
tmp_re = re.compile(r"Temperature([12])\s*=\s*(-?[\d.]+)")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: crosscheck_temps.py <capture.raw>")
    path = sys.argv[1]

    # Pair resistance with the temperature that follows it in the same block,
    # per channel. Keep the most recent resistance seen for each channel.
    pending_r = {}
    rows = []  # (channel, R, esp_f)
    with open(path, "r", errors="replace") as f:
        for line in f:
            if "\tTMP\t" not in line:
                continue
            mr = res_re.search(line)
            if mr:
                pending_r[mr.group(1)] = float(mr.group(2))
                continue
            mt = tmp_re.search(line)
            if mt:
                ch = mt.group(1)
                if ch in pending_r:
                    rows.append((ch, pending_r[ch], float(mt.group(2))))

    if not rows:
        sys.exit(f"# no Resistance/Temperature pairs parsed from {path}")

    # Aggregate stats, split warm (>=32F) vs cold (<32F, the sub-zero branch).
    def stats(label, subset):
        if not subset:
            print(f"# {label}: (none)")
            return
        d_el = [abs(logger_res_to_f(R) - esp) for _, R, esp in subset]   # logger vs esp
        d_rl = [abs(logger_res_to_f(R) - ref_res_to_f(R)) for _, R, _ in subset]  # logger vs ref
        d_er = [abs(esp - ref_res_to_f(R)) for _, R, esp in subset]      # esp vs ref
        print(f"# {label}  (n={len(subset)})")
        print(f"#     |logger - esp32|   max {max(d_el):.4f}F  mean {sum(d_el)/len(d_el):.4f}F")
        print(f"#     |logger - ref  |   max {max(d_rl):.4f}F  mean {sum(d_rl)/len(d_rl):.4f}F")
        print(f"#     |esp32  - ref  |   max {max(d_er):.4f}F  mean {sum(d_er)/len(d_er):.4f}F")

    print(f"# crosscheck {path}: {len(rows)} resistance/temperature pairs\n")
    coldest = min(rows, key=lambda r: r[1])      # smallest R = coldest
    warmest = max(rows, key=lambda r: r[1])
    print("# representative points (R ohm -> esp32 / logger / reference degF):")
    for tag, (ch, R, esp) in (("coldest", coldest), ("warmest", warmest)):
        print(f"#   {tag:7s} ch{ch}  R={R:8.2f}  esp={esp:8.3f}  "
              f"logger={logger_res_to_f(R):8.3f}  ref={ref_res_to_f(R):8.3f}")
    print()
    stats("cold side (<32F, sub-zero branch)",
          [r for r in rows if ref_res_to_f(r[1]) < 32.0])
    stats("warm side (>=32F, positive branch)",
          [r for r in rows if ref_res_to_f(r[1]) >= 32.0])


if __name__ == "__main__":
    main()
