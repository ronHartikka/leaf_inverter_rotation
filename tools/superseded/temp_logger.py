#!/usr/bin/env python3
"""
temp_logger.py  —  log ESP32 RTD temperatures with wall-clock timestamps.

Reads the ESP32's serial stream (the MAX31865 / PT1000 output), stamps every
line with an ISO wall-clock time, echoes to the screen, and appends to a file.
Wall-clock time is what lets us later merge this with the Arduino current log,
which is on a different machine with its own clock.

Usage:
    python3 temp_logger.py                         # defaults: /dev/ttyUSB0 @115200 -> temps.log
    python3 temp_logger.py /dev/ttyUSB0 115200 temps.log
    python3 temp_logger.py --port /dev/ttyACM0 --baud 115200 --out fridge_temps.log

Stop with Ctrl-C. Safe to run for hours.

Notes:
  * The ESP32 prints a multi-line block per reading (RTD value / Ratio /
    Resistance / Temperature1 / Temperature2, and sometimes a Fault line).
    This logger records EVERY line verbatim with a timestamp, so faults are
    preserved in-stream and can be filtered in post-processing.
  * It also writes a parallel CSV (same name + .csv) with just
    timestamp, temp1_c, temp2_c  for the lines it can parse, which is the
    convenient form for merging/plotting. The raw .log keeps everything.
"""

import sys
import re
import argparse
from datetime import datetime

try:
    import serial
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial --break-system-packages")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port_pos", nargs="?", default=None, help="serial port (positional)")
    ap.add_argument("baud_pos", nargs="?", type=int, default=None, help="baud (positional)")
    ap.add_argument("out_pos",  nargs="?", default=None, help="output file (positional)")
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=None)
    ap.add_argument("--out",  default=None)
    args = ap.parse_args()

    port = args.port or args.port_pos or "/dev/ttyUSB0"
    baud = args.baud or args.baud_pos or 115200
    out  = args.out  or args.out_pos  or "temps.log"
    csv_out = out.rsplit(".", 1)[0] + ".csv"

    print(f"# port={port} baud={baud}")
    print(f"# raw log  -> {out}")
    print(f"# csv temps-> {csv_out}")
    print("# Ctrl-C to stop.\n")

    # Regexes for the two temperature lines the ESP32 prints.
    # e.g. "Temperature1 = 25.99"  /  "Temperature2 = 53.77"
    t1_re = re.compile(r"Temperature1\s*=\s*(-?[\d.]+)")
    t2_re = re.compile(r"Temperature2\s*=\s*(-?[\d.]+)")
    fault_re = re.compile(r"[Ff]ault", )

    ser = serial.Serial(port, baud, timeout=1)

    rawf = open(out, "a", buffering=1)          # line-buffered
    csvf = open(csv_out, "a", buffering=1)
    # write CSV header if file is new/empty
    if csvf.tell() == 0:
        csvf.write("wallclock_iso,unix_s,temp1_c,temp2_c,fault\n")

    # We accumulate temp1/temp2 across the multi-line block and emit a CSV
    # row when we've seen a fresh pair (temp2 usually comes right after temp1).
    pending_t1 = None
    pending_fault = 0

    try:
        buf = b""
        while True:
            chunk = ser.read(256)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("latin-1", errors="replace").rstrip("\r")
                now = datetime.now()
                iso = now.isoformat(timespec="milliseconds")
                unix = now.timestamp()

                # raw log: every line, timestamped
                rawf.write(f"{iso}\t{text}\n")

                # track faults so a nearby CSV row can be flagged
                if fault_re.search(text):
                    pending_fault = 1

                m1 = t1_re.search(text)
                if m1:
                    pending_t1 = float(m1.group(1))

                m2 = t2_re.search(text)
                if m2 and pending_t1 is not None:
                    t2 = float(m2.group(1))
                    csvf.write(f"{iso},{unix:.3f},{pending_t1:.3f},{t2:.3f},{pending_fault}\n")
                    # echo a compact live view
                    flag = "  FAULT" if pending_fault else ""
                    print(f"{iso}  T1={pending_t1:6.2f}C  T2={t2:6.2f}C{flag}")
                    pending_t1 = None
                    pending_fault = 0

    except KeyboardInterrupt:
        print("\n# stopped.")
    finally:
        rawf.close()
        csvf.close()
        ser.close()


if __name__ == "__main__":
    main()
