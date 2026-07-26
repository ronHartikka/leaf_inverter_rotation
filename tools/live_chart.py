import sys
import select
from datetime import datetime, timedelta
from collections import deque
import argparse
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.ticker import FormatStrFormatter

# FIXED (non-autoscaling) y-axis ranges, picked so both axes have the SAME number of
# intervals -> the horizontal gridlines connect a round tick on each scale.
#   Left  (temperature): -10..70 F,  step 4   -> 20 intervals (21 ticks)
#   Right (current):     0..2000 mA, step 100 -> 20 intervals (21 ticks)
# Current is stored in AMPS in the CSV; we plot it x1000 as mA for round labels.
TEMP_MIN_F, TEMP_MAX_F, TEMP_STEP_F = -10, 70, 4
CUR_MIN_MA, CUR_MAX_MA, CUR_STEP_MA = 0, 2000, 100

# 1. Parse command-line configuration arguments
parser = argparse.ArgumentParser(description="Live streaming time-series chart from stdin.")
parser.add_argument(
    "--hours", 
    type=float, 
    default=2.0, 
    help="Number of hours of data history to display in the rolling window view."
)
args = parser.parse_args()

WINDOW_DURATION = timedelta(hours=args.hours)

# Data queues to hold the dynamic dataset inside the window boundaries
times = deque()
item3 = deque()
item5 = deque()
item6 = deque()

# 2. Build the visual plot framework with static, crash-proof labels
fig, ax_left = plt.subplots(figsize=(10, 6))
ax_right = ax_left.twinx()  # Share x-axis for the alternate scale
plt.subplots_adjust(bottom=0.15)

# Statically bind labels immediately so the legend can NEVER fail or disappear
line3, = ax_right.plot([], [], label="current (mA)", color="#1f77b4", linewidth=1.5)
line5, = ax_left.plot([], [], label="t1_freezer_f", color="#ff7f0e", linewidth=1.5)
line6, = ax_left.plot([], [], label="t2_fridge_f", color="#2ca02c", linewidth=1.5)

# Formatting foundational structures
ax_left.set_xlabel("Time (ISO 8601 Timestamp)")
ax_right.set_ylabel("Current (mA)", color="#1f77b4")
ax_left.set_ylabel("Temperature (°F)", color="#ff7f0e")
ax_left.set_title(f"Live Inverter Telemetry Metrics (Rolling {args.hours}-Hour View)")
ax_left.grid(True, linestyle="--", alpha=0.6)

# Fixed limits + round, equal-count ticks on both axes (endpoints made inclusive with
# a small epsilon). Both get 21 ticks / 20 intervals, so every gridline meets a round
# value on each scale. Set once here; update() no longer rescales Y.
ax_left.set_ylim(TEMP_MIN_F, TEMP_MAX_F)
ax_left.set_yticks(np.arange(TEMP_MIN_F, TEMP_MAX_F + 0.001, TEMP_STEP_F))
ax_right.set_ylim(CUR_MIN_MA, CUR_MAX_MA)
ax_right.set_yticks(np.arange(CUR_MIN_MA, CUR_MAX_MA + 0.001, CUR_STEP_MA))
ax_left.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
ax_right.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))

# Initialize legend once safely at boot time
ax_left.legend(handles=[line3, line5, line6], loc="upper left")

def parse_line(line):
    """Processes a raw incoming text row to safely extract timestamp and numbers."""
    try:
        parts = line.strip().split(',')
        if len(parts) < 3:
            return None
        
        # Skip header explicitly by checking string text
        if "unix_s" in parts or "iso" in parts or "current_a" in parts:
            return None 

        # Parse timestamp from column 2 (Index 1)
        t_val = datetime.strptime(parts[1].strip(), "%Y-%m-%dT%H:%M:%S.%f")
        
        # Extract metrics safely based on absolute indexes confirmed by test
        v3 = float(parts[2].strip()) if parts[2].strip() else None
        v5 = float(parts[4].strip()) if (len(parts) > 4 and parts[4].strip()) else None
        v6 = float(parts[5].strip()) if (len(parts) > 5 and parts[5].strip()) else None
        
        if t_val is None or v3 is None:
            return None
            
        return t_val, v3, v5, v6
    except Exception:
        return None

def update(frame):
    """Execution step firing at 2Hz to clear stale elements and draw lines."""
    # Consume any text strings buffered in standard input cache
    while select.select([sys.stdin], [], [], 0)[0]:
        input_line = sys.stdin.readline()
        if not input_line:
            break
        
        parsed = parse_line(input_line)
        if parsed:
            t, v3, v5, v6 = parsed
            times.append(t)
            item3.append(v3)
            item5.append(v5)  
            item6.append(v6)

    # FIXED: Only clean out trailing old data if we actually have times loaded
    if len(times) > 0:
        cutoff_time = times[-1] - WINDOW_DURATION
        while times and times[0] < cutoff_time:
            times.popleft()
            item3.popleft()
            item5.popleft()
            item6.popleft()

    # Re-draw lines dynamically
    if len(times) > 0:
        line3.set_data(list(times), [v * 1000.0 for v in item3])  # A -> mA

        # Mask out any None values for temperatures so matplotlib skips them cleanly
        valid_times_5 = [t for t, v in zip(times, item5) if v is not None]
        valid_vals_5 = [v for v in item5 if v is not None]
        line5.set_data(valid_times_5, valid_vals_5)

        valid_times_6 = [t for t, v in zip(times, item6) if v is not None]
        valid_vals_6 = [v for v in item6 if v is not None]
        line6.set_data(valid_times_6, valid_vals_6)

        # X scrolls with the data window; both Y-axes are FIXED (set once at boot), so
        # there is no per-frame rescaling -- the round ticks and gridline alignment hold.
        ax_left.set_xlim(times[0], times[-1])

        fig.autofmt_xdate()

    return line3, line5, line6

# Initialize the automated execution rendering loop ticking every 500ms (2Hz)
ani = animation.FuncAnimation(fig, update, interval=500, blit=False, cache_frame_data=False)
plt.show()

