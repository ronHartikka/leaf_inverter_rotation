import sys
import select
from datetime import datetime, timedelta
from collections import deque
import argparse
import matplotlib.pyplot as plt
import matplotlib.animation as animation

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
line3, = ax_right.plot([], [], label="current_a", color="#1f77b4", linewidth=1.5)
line5, = ax_left.plot([], [], label="t1_freezer_f", color="#ff7f0e", linewidth=1.5)
line6, = ax_left.plot([], [], label="t2_fridge_f", color="#2ca02c", linewidth=1.5)

# Formatting foundational structures
ax_left.set_xlabel("Time (ISO 8601 Timestamp)")
ax_right.set_ylabel("Current (A)", color="#1f77b4")
ax_left.set_ylabel("Temperature (°F)", color="#ff7f0e")
ax_left.set_title(f"Live Inverter Telemetry Metrics (Rolling {args.hours}-Hour View)")
ax_left.grid(True, linestyle="--", alpha=0.6)

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
        line3.set_data(list(times), list(item3))
        
        # Mask out any None values for temperatures so matplotlib skips them cleanly
        valid_times_5 = [t for t, v in zip(times, item5) if v is not None]
        valid_vals_5 = [v for v in item5 if v is not None]
        line5.set_data(valid_times_5, valid_vals_5)
        
        valid_times_6 = [t for t, v in zip(times, item6) if v is not None]
        valid_vals_6 = [v for v in item6 if v is not None]
        line6.set_data(valid_times_6, valid_vals_6)
        
        # Adjust frame limits dynamically based on current data window
        ax_left.set_xlim(times[0], times[-1])
        
        # Dynamically scale left Y-axis (Temperatures)
        if valid_vals_5 or valid_vals_6:
            left_vals = valid_vals_5 + valid_vals_6
            min_l, max_l = min(left_vals), max(left_vals)
            pad_l = (max_l - min_l) * 0.1 if max_l != min_l else 1.0
            ax_left.set_ylim(min_l - pad_l, max_l + pad_l)
        else:
            ax_left.set_ylim(-0.5, 0.5)
            
        # Dynamically scale right Y-axis (Current)
        right_vals = [v for v in item3 if v is not None]
        if right_vals:
            min_r, max_r = min(right_vals), max(right_vals)
            pad_r = (max_r - min_r) * 0.1 if max_r != min_r else 1.0
            ax_right.set_ylim(min_r - pad_r, max_r + pad_r)
            
        fig.autofmt_xdate()

    return line3, line5, line6

# Initialize the automated execution rendering loop ticking every 500ms (2Hz)
ani = animation.FuncAnimation(fig, update, interval=500, blit=False, cache_frame_data=False)
plt.show()

