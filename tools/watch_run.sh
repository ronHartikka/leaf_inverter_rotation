#!/usr/bin/env bash
# Live-stream the Ubuntu logger's CSV to the Mac chart.
# Replays existing rows, then follows new appends. One clock stays on Ubuntu.
set -euo pipefail

HOST="ubuntu"   # ssh alias in ~/.ssh/config -> resolves via mDNS, no hardcoded IP
REMOTE_CSV="Documents/Retirement Work/Engineer/inverter/run.csv"
HOURS="${1:-4}"   # window in hours; default 4, override: ./tools/watch_run.sh 8

# repo root = parent of this script's dir, so paths work from anywhere
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ssh "$HOST" "cat \"$REMOTE_CSV\"; tail -f -n 0 \"$REMOTE_CSV\"" \
  | "$HERE/venv/bin/python" -u "$HERE/tools/live_chart.py" --hours "$HOURS"
