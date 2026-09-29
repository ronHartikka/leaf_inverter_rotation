#!/usr/bin/env python3
"""
serial_capture.py -- dumb, durable serial-to-file logger.

Writes whatever a board sends, unchanged, one line per line. No parsing, no merging:
it is deliberately NOT dual_logger.py, which expects the Arduino's `t_ms,amps,note`
and the RTD node's resistance blocks. Used for firmware/esp32_ads1115_cycle_stats,
whose output is its own CSV.

WHY IT EXISTS: captures on a laptop die silently when the laptop sleeps -- lessons.md
#11, which cost a night of freezer cycles. The Ubuntu box does not sleep, so running
captures there removes that failure mode entirely, and frees the Mac.

Usage:
    python3 serial_capture.py --out fridge_jackery.txt
    python3 serial_capture.py --port /dev/ttyUSB0 --baud 115200 --out run.txt

Leave it running under tmux or nohup so a closed ssh session does not kill it:
    tmux new -s cap 'python3 serial_capture.py --out run.txt'      # ctrl-b d to detach
    nohup python3 serial_capture.py --out run.txt &

Stop with Ctrl-C (or `tmux kill-session -t cap`).

CORRELATION WITH OTHER CAPTURES: the board emits a millisecond uptime, not wall clock,
so this writes a `# unix <epoch> iso <time>` comment every 60 s. Comment lines start
with '#', so any parser that selects on field count ignores them -- the data format is
unchanged. Interpolating between two markers converts t_ms to wall clock to well under
a second, which is what merging against the rig's unix_s needs.
"""
import argparse, os, sys, time
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial")

# CP2102 / CH340 / FTDI -- the USB-UART bridges on the ESP32 boards here.
KNOWN_VIDS = {0x10c4, 0x1a86, 0x0403, 0x2341}

def autodetect():
    cands = [p for p in list_ports.comports() if p.vid in KNOWN_VIDS]
    if not cands:
        sys.exit("# no known USB-serial adapter found. Use --port, or --list to see what is attached.")
    if len(cands) > 1:
        sys.exit("# AMBIGUOUS -- more than one USB-serial adapter attached:\n  "
                 + "\n  ".join(f"{p.device}  {p.vid:04x}:{p.pid:04x}  {p.description}" for p in cands)
                 + "\n# pass --port explicitly.")
    return cands[0].device

def main():
    ap = argparse.ArgumentParser(description="Log a serial stream to a file, unchanged.")
    ap.add_argument("--port", default=None, help="serial device (default: auto-detect)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default=None, help="output file (default: timestamped)")
    ap.add_argument("--mark-s", type=float, default=60.0, help="wall-clock marker interval (default 60 s)")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            vid = f"{p.vid:04x}" if p.vid else "----"
            print(f"{p.device}  {vid}:{p.pid:04x}  {p.description}" if p.pid else f"{p.device}  {p.description}")
        return

    port = args.port or autodetect()
    if args.out is None:
        args.out = datetime.now().strftime("capture_%Y%m%d_%H%M%S.txt")
        print(f"# no --out given; using {args.out}")

    # Never clobber a capture. Same guard, same reasoning, as dual_logger.py: long runs
    # are expensive and unrepeatable.
    if os.path.exists(args.out):
        sys.exit(f"# refusing to write: {args.out} already exists.\n"
                 f"# pick a new --out name (this logger never overwrites or appends).")
    try:
        out = open(args.out, "x", buffering=1)   # exclusive-create; line-buffered
    except FileExistsError:
        sys.exit(f"# refusing to write: {args.out} already exists.")

    print(f"# {port} @ {args.baud} -> {args.out}")
    n = 0
    last_mark = 0.0
    ser = None
    try:
        while True:
            try:
                if ser is None:
                    ser = serial.Serial(port, args.baud, timeout=1)
                    out.write(f"# open {port} @ {args.baud} unix {time.time():.3f} "
                              f"iso {datetime.now().isoformat(timespec='seconds')}\n")
                line = ser.readline()
                if not line:
                    continue
                out.write(line.decode("latin-1", errors="replace").rstrip("\r\n") + "\n")
                n += 1
                now = time.time()
                if now - last_mark >= args.mark_s:
                    out.write(f"# unix {now:.3f} iso {datetime.now().isoformat(timespec='seconds')}\n")
                    last_mark = now
            except (serial.SerialException, OSError) as e:
                # A board reset or a re-enumerated port must not end a long capture.
                print(f"# serial error: {e}; reopening in 2 s")
                out.write(f"# DISCONNECT unix {time.time():.3f} {e}\n")
                try:
                    if ser: ser.close()
                except Exception:
                    pass
                ser = None
                time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n# stopped after {n} lines -> {args.out}")
    finally:
        out.close()
        if ser:
            try: ser.close()
            except Exception: pass

if __name__ == "__main__":
    main()
