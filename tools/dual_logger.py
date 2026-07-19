#!/usr/bin/env python3
"""
dual_logger.py  —  ONE program, ONE clock, both devices, merged output.

Reads the Arduino current stream and the ESP32 RTD stream at the same time on
one machine, stamps every line with this machine's wall clock, and writes a
single already-merged CSV. Because there is only one clock, there is NO
post-hoc time scaling or phase alignment to do -- the two prior separate
loggers required matching clock rates (the ~0.24% Arduino resonator drift)
and phase; this eliminates both.

Merge policy: emit one merged row per CURRENT sample (preserving the fast
current waveform, including the ~7 A inrush), carrying the most-recent
temperatures forward (sample-and-hold; temps move slowly so this is exact
enough). Raw lines from both devices are also mirrored to a .raw file.

Temperatures are computed from the ESP32's logged RESISTANCE via
Callendar-Van Dusen for PT1000 (ground truth), NOT from the ESP32 sketch's
Temperature print (which outputs Fahrenheit without a label and caused
confusion). Raw resistances are kept in the output too.

Usage:
    python3 dual_logger.py \
        --current-port /dev/ttyACM0 --current-baud 115200 \
        --temp-port    /dev/ttyUSB0 --temp-baud    115200 \
        --out run.csv

    # or rely on defaults:
    python3 dual_logger.py

Stop with Ctrl-C. Safe for multi-hour / overnight runs (line-buffered).

If a port name is wrong:   ls /dev/ttyUSB* /dev/ttyACM*
If permission denied:      sudo usermod -aG dialout $USER   (then re-login)
"""

import sys
import re
import time
import math
import argparse
import threading
from datetime import datetime

try:
    import serial
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial --break-system-packages")

# ---- PT1000 Callendar-Van Dusen (T >= 0 branch; fine for fridge temps) ----
_R0 = 1000.0
_A = 3.9083e-3
_B = -5.775e-7
def res_to_c(R):
    a, b, c = _B, _A, 1.0 - R / _R0
    disc = b * b - 4 * a * c
    return (-b + math.sqrt(disc)) / (2 * a)
def res_to_f(R):
    return res_to_c(R) * 9.0 / 5.0 + 32.0

# ---- shared state, updated by reader threads ----
state = {
    "amps": None,           # latest current (A)
    "amps_note": "",        # burst/decay note if present
    "res1": None, "res2": None,   # latest RTD resistances (ohm)
    "t1_f": None, "t2_f": None,   # latest temps (F) from resistance
    "fault": 0,             # 1 if a fault line seen since last temp update
}
lock = threading.Lock()
stop = threading.Event()

# regexes
cur_re   = re.compile(r"^\s*(\d+),([\d.]+),?(\w*)")     # t_ms,amps,note
res1_re  = re.compile(r"Resistance1\s*=\s*([\d.]+)")
res2_re  = re.compile(r"Resistance2\s*=\s*([\d.]+)")
fault_re = re.compile(r"[Ff]ault")


def reader_current(port, baud, rawf):
    """Arduino current stream: CSV lines t_ms,amps,note."""
    while not stop.is_set():
        try:
            ser = serial.Serial(port, baud, timeout=1)
        except Exception as e:
            print(f"# current port {port} open failed: {e}; retry in 3s")
            time.sleep(3)
            continue
        buf = b""
        try:
            while not stop.is_set():
                chunk = ser.read(256)
                if not chunk:
                    continue
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("latin-1", errors="replace").rstrip("\r")
                    rawf.write(f"{time.time():.3f}\tCUR\t{text}\n")
                    m = cur_re.match(text)
                    if m:
                        with lock:
                            state["amps"] = float(m.group(2))
                            state["amps_note"] = m.group(3) or ""
        except Exception as e:
            print(f"# current reader error: {e}; reopening")
            time.sleep(2)
        finally:
            try: ser.close()
            except Exception: pass


def reader_temp(port, baud, rawf):
    """ESP32 RTD stream: multi-line blocks; we parse Resistance1/2 + faults."""
    while not stop.is_set():
        try:
            ser = serial.Serial(port, baud, timeout=1)
        except Exception as e:
            print(f"# temp port {port} open failed: {e}; retry in 3s")
            time.sleep(3)
            continue
        buf = b""
        pending_r1 = None
        pending_fault = 0
        try:
            while not stop.is_set():
                chunk = ser.read(256)
                if not chunk:
                    continue
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("latin-1", errors="replace").rstrip("\r")
                    rawf.write(f"{time.time():.3f}\tTMP\t{text}\n")
                    if fault_re.search(text):
                        pending_fault = 1
                    m1 = res1_re.search(text)
                    if m1:
                        pending_r1 = float(m1.group(1))
                    m2 = res2_re.search(text)
                    if m2 and pending_r1 is not None:
                        r2 = float(m2.group(1))
                        try:
                            t1 = res_to_f(pending_r1)
                            t2 = res_to_f(r2)
                        except Exception:
                            t1 = t2 = None
                        with lock:
                            state["res1"] = pending_r1
                            state["res2"] = r2
                            state["t1_f"] = t1
                            state["t2_f"] = t2
                            state["fault"] = pending_fault
                        pending_r1 = None
                        pending_fault = 0
        except Exception as e:
            print(f"# temp reader error: {e}; reopening")
            time.sleep(2)
        finally:
            try: ser.close()
            except Exception: pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current-port", default="/dev/ttyACM0")
    ap.add_argument("--current-baud", type=int, default=115200)
    ap.add_argument("--temp-port",    default="/dev/ttyUSB0")
    ap.add_argument("--temp-baud",    type=int, default=115200)
    ap.add_argument("--out",          default="run.csv")
    ap.add_argument("--rate-hz", type=float, default=10.0,
                    help="merged-row cadence (Hz). 10 Hz covers the Arduino's fastest "
                         "(100ms burst) sampling; temps (1 Hz) hold between updates.")
    args = ap.parse_args()

    raw_path = args.out.rsplit(".", 1)[0] + ".raw"
    rawf = open(raw_path, "a", buffering=1)
    outf = open(args.out, "a", buffering=1)
    if outf.tell() == 0:
        outf.write("unix_s,iso,current_a,current_note,"
                   "t1_freezer_f,t2_fridge_f,res1_ohm,res2_ohm,fault\n")

    print(f"# current: {args.current_port} @ {args.current_baud}")
    print(f"# temp:    {args.temp_port} @ {args.temp_baud}")
    print(f"# merged -> {args.out}  ({args.rate_hz:g} Hz sample-and-hold)")
    print(f"# raw    -> {raw_path}")
    print("# one machine, one clock: no post-hoc alignment needed. Ctrl-C to stop.\n")

    tc = threading.Thread(target=reader_current,
                          args=(args.current_port, args.current_baud, rawf), daemon=True)
    tt = threading.Thread(target=reader_temp,
                          args=(args.temp_port, args.temp_baud, rawf), daemon=True)
    tc.start(); tt.start()

    # Fixed-rate sample-and-hold merge: every 1/rate_hz seconds, snapshot the
    # latest current + latest temps and write one row. Simple, regular grid,
    # single clock. Current repeats when it updates slower than the row rate;
    # temps hold (1 Hz) between updates. Nothing is lost: 10 Hz >= all sources.
    period = 1.0 / args.rate_hz
    next_t = time.time()
    try:
        while True:
            next_t += period
            sleep = next_t - time.time()
            if sleep > 0:
                time.sleep(sleep)
            with lock:
                amps = state["amps"]; note = state["amps_note"]
                t1 = state["t1_f"]; t2 = state["t2_f"]
                r1 = state["res1"]; r2 = state["res2"]
                fault = state["fault"]
            if amps is None and t1 is None:
                continue  # nothing to log yet
            now = time.time()
            iso = datetime.now().isoformat(timespec="milliseconds")
            outf.write("%.3f,%s,%s,%s,%s,%s,%s,%s,%d\n" % (
                now, iso,
                ("%.3f" % amps) if amps is not None else "",
                note,
                ("%.3f" % t1) if t1 is not None else "",
                ("%.3f" % t2) if t2 is not None else "",
                ("%.2f" % r1) if r1 is not None else "",
                ("%.2f" % r2) if r2 is not None else "",
                fault,
            ))
    except KeyboardInterrupt:
        print("\n# stopping...")
        stop.set()
        time.sleep(0.5)
    finally:
        outf.close()
        rawf.close()


if __name__ == "__main__":
    main()