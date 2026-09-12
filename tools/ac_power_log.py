#!/usr/bin/env python3
"""ac_power_log.py -- witness whether a commanded relay-open ACTUALLY cuts power.

Plug the logging laptop's adapter into the RELAY-SWITCHED (fridge-side) power,
run this on the SAME box as dual_logger (same wall clock), then cross-reference
ac_online transitions here against relay_cmd in the run CSV:

  relay_cmd 1->0  AND  ac_online 1->0 together  = REAL power cut
  relay_cmd 1->0  but  ac_online stays 1        = PHANTOM cut (relay didn't cut power)

Logs one row on every AC/battery change (the events we care about), plus a
heartbeat every --heartbeat s so we can tell it's still alive. Pure stdlib;
reads /sys/class/power_supply/.  Timestamps are unix seconds (match the run CSV).

  Usage:  python3 ac_power_log.py [--out FILE] [--interval 1.0] [--heartbeat 60]
"""
import time
import sys
import glob
from datetime import datetime

AC_PRIMARY = "/sys/class/power_supply/AC/online"


def read_first(paths):
    for p in paths:
        try:
            with open(p) as f:
                return f.read().strip()
        except OSError:
            continue
    return "?"


def read_ac():
    return read_first([AC_PRIMARY] + glob.glob("/sys/class/power_supply/A*/online"))


def read_bat():
    return read_first(glob.glob("/sys/class/power_supply/BAT*/status"))


def arg(name, default):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a else default


def main():
    interval = float(arg("--interval", 1.0))
    heartbeat = float(arg("--heartbeat", 60.0))
    out = arg("--out", "ac_power_%s.log" % datetime.now().strftime("%Y%m%d_%H%M%S"))

    f = open(out, "a", buffering=1)  # line-buffered: no data lost if killed
    f.write("unix_s,iso,ac_online,bat_status,event\n")
    sys.stderr.write("# ac_power_log -> %s  (AC path %s = %s now)\n"
                     % (out, AC_PRIMARY, read_ac()))
    sys.stderr.flush()

    last_ac = last_bat = None
    last_write = 0.0
    while True:
        now = time.time()
        ac, bat = read_ac(), read_bat()
        iso = datetime.now().isoformat(timespec="milliseconds")
        changed = (ac != last_ac) or (bat != last_bat)
        event = ("start" if last_ac is None else "change") if changed \
            else ("heartbeat" if now - last_write >= heartbeat else None)
        if event:
            f.write("%.3f,%s,%s,%s,%s\n" % (now, iso, ac, bat, event))
            last_write = now
            if event != "heartbeat":
                sys.stderr.write("# %s  ac_online=%s  bat=%s  (%s)\n" % (iso, ac, bat, event))
                sys.stderr.flush()
        last_ac, last_bat = ac, bat
        time.sleep(interval)


if __name__ == "__main__":
    main()
