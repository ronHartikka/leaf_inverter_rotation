#!/usr/bin/env python3
"""
airgradient_poll.py  --  poll the AirGradient monitor's LOCAL API, log fridge ambient.

Replaces manual batch downloads from the AirGradient cloud. The monitor serves its
current measurements over plain HTTP on the LAN, no token and no internet, so this
keeps working during an outage (the monitor is on inverter-backed power along with
the modem).

    GET http://<host>/measures/current
      -> {"atmp":21.06,"rhum":66.1,"rco2":1345.33,...}

Verified 2026-09-20 against the monitor on the house LAN:
    model I-9PSL (AirGradient ONE), firmware 3.7.0, serial 3cdc75bc2990

ONE CLOCK.  Run this on the SAME machine as dual_logger.py (the Ubuntu box). Both
stamp on arrival with that machine's wall clock, so the ambient log joins the merged
capture on unix_s with NO rate scaling and NO phase alignment -- which is the whole
point of lesson #8. Running it on a second machine reintroduces exactly the two-clock
merge problem that lesson was written about. Don't.

Ambient moves slowly, so joining is a sample-and-hold on unix_s, the same policy
dual_logger.py already uses to carry temperatures forward onto current samples.

Usage:
    python3 airgradient_poll.py --once                 # one reading, print, exit
    python3 airgradient_poll.py --out ambient.csv      # log until Ctrl-C
    python3 airgradient_poll.py                        # timestamped default name

Stop with Ctrl-C. Safe for multi-day runs (line-buffered).

Stdlib only -- deliberately no `requests`, so there is nothing to install on the
Ubuntu box before a capture.
"""

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

# The serial number is part of the mDNS name, so this default is specific to OUR
# monitor. If the name does not resolve, mDNS is the usual culprit, not the device:
#   macOS   dns-sd -B _airgradient._tcp local.
#   Ubuntu  avahi-browse -rt _airgradient._tcp     (needs avahi-daemon + libnss-mdns)
# An IP address works too and sidesteps mDNS entirely -- but the monitor is on DHCP,
# so a pinned name is the more durable choice for a long capture.
DEFAULT_HOST = "airgradient_3cdc75bc2990.local"

# atmp is CELSIUS.  /config reports temperatureUnit:"f" on this monitor, but that
# setting drives the on-device DISPLAY only -- the API answers in Celsius either way
# (measured 2026-09-20, fw 3.7.0: display in F, API returned atmp 21.06). Both units
# are written below so nothing downstream has to remember this.
#
# atmp_comp_c is the monitor's own compensated temperature. On this unit it currently
# equals atmp (no temperature correction configured -- /config `corrections` carries
# only pm02). It is logged as its own column so that if a correction is ever enabled,
# the divergence is visible in the data instead of silently changing what atmp means.
CSV_HEADER = ("unix_s,iso,ok,atmp_c,atmp_f,atmp_comp_c,rhum_pct,rco2_ppm,"
              "wifi_dbm,boot_count,note\n")


def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0


class Endpoint:
    """The monitor's address, resolved ONCE and cached.

    Resolving the .local name costs a flat ~5 s per lookup while the monitor itself
    answers in ~30 ms -- measured 2026-09-20 on macOS:

        by hostname   dns=5.006  connect=5.022  total=5.043
        by IP         dns=0.006  connect=0.014  total=0.033

    So a naive poll spends 99% of its time in name resolution, and at a short
    --interval the cadence is set by the lookup rather than by the interval. The
    resolver appears to try unicast DNS and time out before falling back to mDNS.

    Caching the address fixes that but would strand the poller if DHCP moved the
    monitor mid-capture, so the address is dropped on any failed poll and looked up
    again on the next one. That is the same re-resolve-on-reconnect policy
    dual_logger.py's _serial_lines() uses to survive a USB re-enumeration.

    Passing --host as an IP skips the lookup entirely.
    """

    def __init__(self, host):
        self.host = host
        self.addr = None

    def resolve(self, timeout):
        """Cached address, resolving if needed. Raises OSError if it cannot."""
        if self.addr is None:
            prev = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                info = socket.getaddrinfo(self.host, 80, socket.AF_INET,
                                          socket.SOCK_STREAM)
            finally:
                socket.setdefaulttimeout(prev)
            self.addr = info[0][4][0]
        return self.addr

    def invalidate(self):
        self.addr = None


def fetch_current(endpoint, timeout):
    """One bounded GET. Returns (decoded JSON dict, address used), or raises."""
    addr = endpoint.resolve(timeout)
    req = urllib.request.Request(f"http://{addr}/measures/current",
                                 headers={"Accept": "application/json",
                                          "Host": endpoint.host})
    # Bounded, always. A hung socket here must never stall the poll loop -- the
    # RTD node's blocking-connect starvation (41 samples in 122 s where 1 Hz should
    # give ~122, measured 2026-09-10) is the same failure in the other direction.
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")), addr


def _num(d, key):
    """Field as a float, or None if absent/unparseable. Missing fields log as empty
    rather than as 0 -- a zero here is a real reading (pm01 legitimately reads 0)."""
    v = d.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v, places=2):
    return "" if v is None else f"{v:.{places}f}"


def _note(text):
    """Notes share a comma-delimited line, so strip commas rather than quote."""
    return str(text).replace(",", ";").replace("\n", " ").strip()


def poll_once(endpoint, timeout):
    """Returns (ok, data_dict_or_None, note, raw_text, addr_or_None).

    Any failure drops the cached address, so the next poll re-resolves -- a monitor
    that moved on DHCP recovers by itself instead of failing forever on a stale IP.
    """
    try:
        data, addr = fetch_current(endpoint, timeout)
        return True, data, "", json.dumps(data, separators=(",", ":")), addr
    except urllib.error.HTTPError as e:
        note = f"http {e.code}"
    except urllib.error.URLError as e:
        note = f"unreachable: {e.reason}"
    except (TimeoutError, OSError) as e:
        note = f"io: {e}"
    except ValueError as e:          # json.JSONDecodeError subclasses ValueError
        note = f"bad json: {e}"
    endpoint.invalidate()
    return False, None, note, note, None


def write_row(outf, now, ok, data, note):
    iso = datetime.fromtimestamp(now).isoformat(timespec="milliseconds")
    if ok and data is not None:
        atmp_c = _num(data, "atmp")
        outf.write(
            f"{now:.3f},{iso},1,"
            f"{_fmt(atmp_c)},{_fmt(c_to_f(atmp_c) if atmp_c is not None else None)},"
            f"{_fmt(_num(data, 'atmpCompensated'))},"
            f"{_fmt(_num(data, 'rhum'), 1)},{_fmt(_num(data, 'rco2'), 1)},"
            f"{_fmt(_num(data, 'wifi'), 0)},{_fmt(_num(data, 'bootCount'), 0)},"
            f"{_note(note)}\n")
    else:
        # A failed poll is RECORDED, not skipped. A gap that is only an absence of
        # rows is indistinguishable from the logger having been stopped.
        outf.write(f"{now:.3f},{iso},0,,,,,,,,{_note(note)}\n")


def main():
    ap = argparse.ArgumentParser(
        description="Poll the AirGradient local API and log ambient temperature.")
    ap.add_argument("--host", default=DEFAULT_HOST,
                    help=f"monitor hostname or IP (default {DEFAULT_HOST})")
    ap.add_argument("--interval", type=float, default=30.0,
                    help="seconds between polls (default 30; ambient is slow)")
    ap.add_argument("--timeout", type=float, default=8.0,
                    help="per-request timeout in seconds (default 8)")
    ap.add_argument("--out", default=None,
                    help="output CSV (default: timestamped ambient_YYYYmmdd_HHMMSS.csv)")
    ap.add_argument("--once", action="store_true",
                    help="print one reading and exit; writes no files")
    args = ap.parse_args()

    endpoint = Endpoint(args.host)

    if args.once:
        ok, data, note, raw, addr = poll_once(endpoint, args.timeout)
        if not ok:
            sys.exit(f"# {args.host}: {note}")
        atmp_c = _num(data, "atmp")
        print(f"# {args.host} ({addr})  model={data.get('model')} "
              f"fw={data.get('firmware')} serial={data.get('serialno')}")
        print(f"# atmp  {_fmt(atmp_c)} C  /  "
              f"{_fmt(c_to_f(atmp_c) if atmp_c is not None else None)} F")
        print(f"# rhum  {_fmt(_num(data, 'rhum'), 1)} %   "
              f"rco2 {_fmt(_num(data, 'rco2'), 1)} ppm   "
              f"wifi {_fmt(_num(data, 'wifi'), 0)} dBm")
        return

    if args.interval <= 0:
        sys.exit("# --interval must be positive")

    if args.out is None:
        args.out = datetime.now().strftime("ambient_%Y%m%d_%H%M%S.csv")
        print(f"# no --out given; using timestamped {args.out}")

    raw_path = args.out.rsplit(".", 1)[0] + ".raw"
    # Never clobber an existing capture -- same guard, and same reasoning, as
    # dual_logger.py: long captures are expensive and unrepeatable.
    for p in (args.out, raw_path):
        if os.path.exists(p):
            sys.exit(f"# refusing to write: {p} already exists.\n"
                     f"# pick a new --out name (this logger never overwrites or "
                     f"appends to an existing capture).")
    try:
        # Exclusive-create so a race between the check above and the open still
        # fails rather than clobbers.
        rawf = open(raw_path, "x", buffering=1)
        outf = open(args.out, "x", buffering=1)
    except FileExistsError as e:
        sys.exit(f"# refusing to write: {e.filename} already exists.")

    outf.write(CSV_HEADER)
    print(f"# ambient: http://{args.host}/measures/current every {args.interval:g}s")
    print(f"# logging -> {args.out}   raw -> {raw_path}")

    n_ok = n_fail = 0
    was_ok = None
    last_addr = None
    next_t = time.time()
    try:
        while True:
            now = time.time()
            ok, data, note, raw, addr = poll_once(endpoint, args.timeout)

            # Address markers, per docs/dual_logger_socket_ingest.md sec 4: a DHCP
            # move should be visible in the capture, not inferred from a gap.
            if addr is not None and addr != last_addr:
                stamp = datetime.fromtimestamp(now).isoformat(timespec="seconds")
                msg = (f"resolved {args.host} -> {addr}" if last_addr is None
                       else f"{args.host} MOVED {last_addr} -> {addr}")
                rawf.write(f"{now:.3f}\tAG-MARK\t{msg}\n")
                print(f"# {stamp} {msg}")
                last_addr = addr

            # Full JSON to the sidecar, tagged AG, in dual_logger's .raw line shape:
            # <unix_s>\t<TAG>\t<text>. The CSV carries only the ambient-relevant
            # fields, so mirroring the whole payload is what makes every other field
            # (PM, TVOC, NOx) recoverable later without re-running the capture --
            # the same reason dual_logger keeps raw resistances alongside temps.
            rawf.write(f"{now:.3f}\tAG\t{raw}\n")

            write_row(outf, now, ok, data, note)

            # Announce edges only; a multi-hour dropout must not fill the console.
            if ok != was_ok:
                print(f"# {datetime.fromtimestamp(now).isoformat(timespec='seconds')} "
                      + ("reading OK" if ok else f"poll failed: {note}"))
                was_ok = ok
            n_ok, n_fail = (n_ok + 1, n_fail) if ok else (n_ok, n_fail + 1)

            # Fixed-cadence schedule so slow requests do not let the interval drift.
            next_t += args.interval
            behind = time.time() - next_t
            if behind > 0:
                # Fell behind (long timeouts, or the machine slept). Resync to now
                # and DROP the missed slots -- never fire a burst to catch up. A
                # backfilled sample would carry an arrival stamp that is wrong by
                # the length of the outage, which is the two-clock problem again
                # (docs/dual_logger_socket_ingest.md sec 5, lesson #8).
                next_t = time.time() + args.interval
            time.sleep(max(0.0, next_t - time.time()))
    except KeyboardInterrupt:
        print(f"\n# stopped. {n_ok} readings, {n_fail} failed polls -> {args.out}")
    finally:
        outf.close()
        rawf.close()


if __name__ == "__main__":
    main()
