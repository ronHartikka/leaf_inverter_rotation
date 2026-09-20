#!/usr/bin/env python3
"""
Serial logger for the Arduino Uno WiFi Rev2 current capture (chest-freezer run).
Linux/Ubuntu version. Reads bytes from the Arduino serial port, echoes to the
terminal, and tees to a log file. Same behavior as the macOS one-liner used for
the dorm-fridge run, with a Linux port and a few unattended-run niceties.

Usage:
    python3 collect_current.py [PORT] [LOGFILE]

    PORT     default /dev/ttyACM0   (the Uno WiFi Rev2 enumerates here on Linux)
    LOGFILE  default chestfreezer_current_YYYYmmdd_HHMMSS.log

Find the port:   ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
Permissions:     sudo usermod -a -G dialout $USER   (then log out/in)

Note: the ESP32 temp logger uses /dev/ttyUSB0 and this one uses /dev/ttyACM0,
so both can run at once in separate terminals without a port collision.
"""
import serial, sys, time

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
LOG  = sys.argv[2] if len(sys.argv) > 2 else time.strftime("chestfreezer_current_%Y%m%d_%H%M%S.log")
BAUD = 115200

print(f"[collect_current] port={PORT} baud={BAUD} log={LOG}", file=sys.stderr)
print("[collect_current] Ctrl-C to stop.", file=sys.stderr)

s = serial.Serial(PORT, BAUD, timeout=1)
f = open(LOG, "wb")
try:
    while True:
        d = s.read(s.in_waiting or 1)
        if d:
            sys.stdout.buffer.write(d); sys.stdout.flush()
            f.write(d); f.flush()
except KeyboardInterrupt:
    print("\n[collect_current] stopping.", file=sys.stderr)
finally:
    f.close(); s.close()
