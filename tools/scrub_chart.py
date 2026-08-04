#!/usr/bin/env python3
"""scrub_chart.py — static, scrubbable viewer for a logger CSV.

Companion to live_chart.py: instead of following a live capture, this loads one
already-recorded run and lets you pan/zoom the time axis to look around. Same
colors/axes as live_chart.py.

  Usage:  python3 tools/scrub_chart.py <run.csv>          # read a local file
          cat run.csv | python3 tools/scrub_chart.py      # or read stdin
          ./tools/scrub_run.sh                            # or fetch from Ubuntu

Reads a CSV path if given, else stdin. tools/scrub_run.sh is the wrapper that
picks a file on the Ubuntu box and streams it in (decimated with awk for speed).
A small sample to try it on is committed at data/sample_run_auto.csv.

Controls (matplotlib widgets, standard look):
  Start slider  — scrollbar; drag to pan the window across the whole file.
  Span -1h/+1h  — widen/narrow the visible window (horizontal time span).
  |< / < / > / >|  — jump backward/forward by a full span or half a span.
Window start defaults to the file start; span defaults to 10 h.

Columns are looked up by NAME from the header, so 9-col and 12-col runs both work.
On 12-col runs the background is shaded where current_stale=1 (sensor dropout,
pink) and where relay_cmd=0 (our controller coasting = power cut, gray), so the
artifacts vs real fridge behavior we chased down are visible at a glance.
"""
import sys
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from matplotlib.ticker import FuncFormatter, MaxNLocator

DEFAULT_SPAN_H = 10.0
MIN_SPAN_S = 600          # don't let the window shrink below 10 min
TEMP_MIN_F, TEMP_MAX_F = -20, 70
CUR_MIN_MA, CUR_MAX_MA = 0, 2000


def load_input(fh):
    """Parse CSV lines from `fh` (an open file or sys.stdin) by column NAME.
    Returns dict of numpy arrays."""
    header = None
    idx = {}
    t, cur, t1, t2 = [], [], [], []
    relay, stale, comp = [], [], []
    for line in fh:
        parts = line.rstrip("\n").split(",")
        if header is None:
            header = parts
            idx = {name: i for i, name in enumerate(header)}
            if "unix_s" not in idx:
                # no header (shouldn't happen via the wrapper) -> assume canonical order
                idx = {"unix_s": 0, "current_a": 2, "t1_freezer_f": 4, "t2_fridge_f": 5}
                # fall through and treat this first line as data
            else:
                continue

        def g(name):
            i = idx.get(name)
            if i is None or i >= len(parts):
                return np.nan
            s = parts[i].strip()
            if s == "":
                return np.nan
            try:
                return float(s)
            except ValueError:
                return np.nan

        ts = g("unix_s")
        if ts != ts:  # NaN timestamp -> skip junk/blank rows
            continue
        t.append(ts)
        cur.append(g("current_a"))
        t1.append(g("t1_freezer_f"))
        t2.append(g("t2_fridge_f"))
        relay.append(g("relay_cmd"))
        stale.append(g("current_stale"))
        comp.append(g("compressor_on"))

    return dict(
        t=np.array(t), cur=np.array(cur), t1=np.array(t1), t2=np.array(t2),
        relay=np.array(relay), stale=np.array(stale), comp=np.array(comp),
        has12=("relay_cmd" in idx),
    )


def true_spans(t, mask):
    """Yield (start_epoch, end_epoch) for each contiguous run of mask==True."""
    if mask.size == 0:
        return
    m = mask.astype(bool)
    edges = np.diff(m.astype(np.int8))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)
    if m[0]:
        starts = [0] + starts
    if m[-1]:
        ends = ends + [len(m)]
    for s, e in zip(starts, ends):
        yield t[s], t[min(e, len(t) - 1)]


def main():
    import os
    args = sys.argv[1:]
    title = None
    if "--title" in args:
        i = args.index("--title")
        title = args[i + 1]
        del args[i:i + 2]
    # remaining non-flag arg = optional input CSV path; if absent, read stdin
    # (so `scrub_chart.py run.csv` and `cat run.csv | scrub_chart.py` both work).
    path = next((a for a in args if not a.startswith("-")), None)
    if path:
        fh = open(path)
        if title is None:
            title = os.path.basename(path)
    else:
        fh = sys.stdin
    if title is None:
        title = "run"

    sys.stderr.write("scrub_chart: loading...\n")
    sys.stderr.flush()
    d = load_input(fh)
    if d["t"].size == 0:
        sys.stderr.write("scrub_chart: no data rows parsed\n")
        sys.exit(1)
    t = d["t"]
    t0, t1 = float(t[0]), float(t[-1])
    total = max(t1 - t0, 60.0)
    sys.stderr.write(f"scrub_chart: {t.size} points, "
                     f"{datetime.fromtimestamp(t0)} .. {datetime.fromtimestamp(t1)} "
                     f"({total/3600:.1f} h)\n")

    fig, ax_l = plt.subplots(figsize=(12, 7))
    ax_r = ax_l.twinx()
    plt.subplots_adjust(bottom=0.30, top=0.93)

    (ln_cur,) = ax_r.plot(t, d["cur"] * 1000.0, color="#1f77b4", lw=1.2, label="current (mA)")
    (ln_t1,) = ax_l.plot(t, d["t1"], color="#ff7f0e", lw=1.4, label="t1_freezer_f")
    (ln_t2,) = ax_l.plot(t, d["t2"], color="#2ca02c", lw=1.4, label="t2_fridge_f")

    # Shade sensor dropouts and coasts so real fridge behavior stands out (12-col only).
    if d["has12"]:
        for a, b in true_spans(t, d["stale"] == 1):
            ax_l.axvspan(a, b, color="#d62728", alpha=0.12, lw=0)
        for a, b in true_spans(t, d["relay"] == 0):
            ax_l.axvspan(a, b, color="#7f7f7f", alpha=0.15, lw=0)

    ax_l.set_ylim(TEMP_MIN_F, TEMP_MAX_F)
    ax_r.set_ylim(CUR_MIN_MA, CUR_MAX_MA)
    ax_l.set_ylabel("Temperature (°F)", color="#ff7f0e")
    ax_r.set_ylabel("Current (mA)", color="#1f77b4")
    ax_l.grid(True, linestyle="--", alpha=0.5)
    ax_l.legend(handles=[ln_cur, ln_t1, ln_t2], loc="upper left")
    shade_note = "  (pink=stale sensor, gray=coast)" if d["has12"] else ""
    ax_l.set_title(f"{title}{shade_note}")

    def fmt_x(x, _pos):
        try:
            return datetime.fromtimestamp(x).strftime("%m-%d\n%H:%M")
        except (ValueError, OSError):
            return ""
    ax_l.xaxis.set_major_formatter(FuncFormatter(fmt_x))
    ax_l.xaxis.set_major_locator(MaxNLocator(8))

    state = {"start": t0, "span": min(DEFAULT_SPAN_H * 3600, total), "guard": False}

    def clamp(v, lo, hi):
        return max(lo, min(v, hi))

    def apply():
        s, sp = state["start"], state["span"]
        ax_l.set_xlim(s, s + sp)
        win.set_text(f"span {sp/3600:.1f} h   |   "
                     f"{datetime.fromtimestamp(s):%m-%d %H:%M} → "
                     f"{datetime.fromtimestamp(s+sp):%m-%d %H:%M}")
        fig.canvas.draw_idle()

    def set_start(v, from_slider=False):
        v = clamp(v, t0, max(t0, t1 - MIN_SPAN_S))
        state["start"] = v
        if not from_slider:
            state["guard"] = True
            s_start.set_val(v)
            state["guard"] = False
        apply()

    def set_span(new_span):
        state["span"] = clamp(new_span, MIN_SPAN_S, total)
        set_start(state["start"])  # re-clamp start against the new span

    # --- widgets ---
    ax_slider = fig.add_axes([0.08, 0.20, 0.86, 0.03])
    s_start = Slider(ax_slider, "Start", t0, max(t0 + 1, t1), valinit=t0)
    s_start.valtext.set_visible(False)
    s_start.on_changed(lambda v: (None if state["guard"] else set_start(v, from_slider=True)))

    win = fig.text(0.08, 0.025, "", fontsize=10, family="monospace")

    btns = []  # keep references alive

    def mkbtn(left, label, cb, w=0.09):
        axb = fig.add_axes([left, 0.09, w, 0.055])
        b = Button(axb, label)
        b.on_clicked(cb)
        btns.append(b)
        return b

    mkbtn(0.08, "Span -1h", lambda e: set_span(state["span"] - 3600))
    mkbtn(0.18, "Span +1h", lambda e: set_span(state["span"] + 3600))
    mkbtn(0.42, "|< span", lambda e: set_start(state["start"] - state["span"]))
    mkbtn(0.52, "< ½", lambda e: set_start(state["start"] - state["span"] / 2), w=0.07)
    mkbtn(0.60, "½ >", lambda e: set_start(state["start"] + state["span"] / 2), w=0.07)
    mkbtn(0.68, "span >|", lambda e: set_start(state["start"] + state["span"]))

    apply()
    plt.show()


if __name__ == "__main__":
    main()
