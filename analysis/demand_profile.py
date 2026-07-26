#!/usr/bin/env python3
"""
demand_profile.py -- average compressor demand (duty) vs TIME OF DAY.

Bins a dual_logger capture by time-of-day and plots the diurnal demand curve:
  - raw (all data) vs DEFROST-EXCLUDED (defrost + ~2 h recovery removed, since
    defrost is run-hours-based and lands at different clock times each day).
  - a low-pass (circular moving-average) smooth over both.
  - each calendar day drawn faintly, so a one-off event (e.g. a grocery restock,
    any time breakfast..dinner) shows as an outlier day, not hidden in the mean.

Usage: python3 demand_profile.py ../data/run_20260721_135703.csv
"""
import csv, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "../data/run_20260721_135703.csv"

ACTIVE      = 0.30      # compressor "on" threshold (A)
DEFROST     = 1.60      # defrost-heater band (A); above compressor max (~1.5 A recovery)
DEFROST_MIN = 300.0     # min seconds of >=DEFROST to count as a defrost event
RECOVERY_S  = 2*3600.0  # exclude this long AFTER defrost end (the recovery run)
BINW        = 0.5       # bin width (h) -- 30 min, finer than the 1 h ceiling
SMOOTH_BINS = 3         # +/- bins for the low-pass (3 -> +/-1.5 h window)

# ---- load (positional csv, slice iso for LOCAL time-of-day) ----
t, a, tod, day = [], [], [], []
with open(path) as f:
    r = csv.reader(f); next(r)
    for row in r:
        c = row[2]
        if not c:
            continue
        try:
            tt, aa = float(row[0]), float(c)
        except ValueError:
            continue
        iso = row[1]                       # 2026-07-21T13:59:18.253 (local)
        t.append(tt); a.append(aa)
        tod.append(int(iso[11:13]) + int(iso[14:16])/60.0 + int(iso[17:19])/3600.0)
        day.append(iso[5:10])
t = np.array(t); a = np.array(a); tod = np.array(tod); day = np.array(day)
active = a >= ACTIVE

# ---- mark defrost + recovery windows ----
excl = np.zeros(len(t), bool)
hi = a >= DEFROST
i, n, events = 0, len(a), []
while i < n:
    if hi[i]:
        j = i
        while j < n and hi[j]:
            j += 1
        if t[j-1] - t[i] >= DEFROST_MIN:
            events.append((t[i], t[j-1]))
        i = j
    else:
        i += 1
for s, e in events:
    excl |= (t >= s) & (t <= e + RECOVERY_S)

# ---- duty by 30-min bin over a chosen sample set ----
nb = int(round(24/BINW))
centers = (np.arange(nb) + 0.5) * BINW
idx = np.minimum((tod / BINW).astype(int), nb-1)

def duty(mask):
    out = np.full(nb, np.nan)
    for b in range(nb):
        sel = (idx == b) & mask
        tot = sel.sum()
        if tot > 0:
            out[b] = 100.0 * (active & sel).sum() / tot
    return out

def smooth(y, k):
    yy = np.where(np.isnan(y), np.nanmean(y), y)      # fill gaps for the filter
    ext = np.concatenate([yy[-k:], yy, yy[:k]])       # circular (wrap midnight)
    ker = np.ones(2*k+1)/(2*k+1)
    return np.convolve(ext, ker, "same")[k:-k]

raw = duty(np.ones(len(t), bool))
nod = duty(~excl)
raw_s, nod_s = smooth(raw, SMOOTH_BINS), smooth(nod, SMOOTH_BINS)

# ---- plot ----
fig, ax = plt.subplots(figsize=(11, 6.2))
for m in (7.0, 12.5, 17.5):                            # meal markers
    ax.axvspan(m-0.75, m+0.75, color="#f2c94c", alpha=0.15, zorder=0)

for d in sorted(set(day)):                             # faint per-day (defrost-excl)
    ax.plot(centers, duty((day == d) & ~excl), color="#9aa0a6",
            lw=0.8, alpha=0.5, zorder=1)
ax.plot([], [], color="#9aa0a6", lw=0.8, alpha=0.6, label="individual days (excl. defrost)")

ax.plot(centers, nod, "o", ms=3, color="#1f77b4", alpha=0.35, zorder=2)
ax.plot(centers, nod_s, color="#1f77b4", lw=2.6, zorder=4, label="defrost excluded (smoothed)")
ax.plot(centers, raw_s, color="#d62728", lw=1.8, ls="--", zorder=3,
        label="all data incl. defrost (smoothed)")

ax.set_xlim(0, 24); ax.set_ylim(0, 100)
ax.set_xticks(range(0, 25, 2))
ax.set_xlabel("Time of day (h, local)")
ax.set_ylabel("Compressor duty (%)")
ax.set_title("Kitchen fridge — average demand vs time of day\n"
             f"{path.split('/')[-1]}  ({len(set(day))} days, 30-min bins, ±1.5 h low-pass)")
ax.grid(True, ls="--", alpha=0.4)
for x, lbl in ((7.0, "breakfast"), (12.5, "lunch"), (17.5, "dinner")):
    ax.text(x, 4, lbl, ha="center", va="bottom", fontsize=8, color="#8a6d00")
ax.legend(loc="upper left", framealpha=0.9)
fig.tight_layout()
out = path.rsplit("/", 1)[0].replace("/data", "/analysis") + "/demand_profile.png"
out = "demand_profile.png" if "/" not in out else out
fig.savefig("demand_profile.png", dpi=130)
print(f"wrote demand_profile.png  ({len(events)} defrost events excluded)")
print("peak (excl-defrost):  %.0f%% at %04.1fh" % (np.nanmax(nod), centers[np.nanargmax(nod)]))
print("trough (excl-defrost): %.0f%% at %04.1fh" % (np.nanmin(nod), centers[np.nanargmin(nod)]))
