#!/usr/bin/env bash
# Live-stream the Ubuntu logger's NEWEST capture CSV to the Mac chart.
# Auto-picks the most-recently-modified file matching REMOTE_GLOB on Ubuntu, so you
# never have to edit this file when dual_logger.py writes a new (timestamped) run.
# Replays existing rows, then follows new appends. One clock stays on Ubuntu.
#
# Usage:
#   ./tools/watch_run.sh                 # newest run*.csv, 4-hour window
#   ./tools/watch_run.sh 8               # newest run*.csv, 8-hour window
#   ./tools/watch_run.sh 8 'dryrun*.csv' # follow the dry-run file instead
#   ./tools/watch_run.sh 8 '*.csv'       # newest capture of any name
set -euo pipefail

HOST="ubuntu"                                   # ssh alias (~/.ssh/config, mDNS -> no hardcoded IP)
REMOTE_DIR="Documents/RetirementWork/Engineer/inverter"
HOURS="${1:-4}"                                 # chart window in hours
REMOTE_GLOB="${2:-run*.csv}"                     # which captures to consider (newest wins).
                                                # default run*.csv = timestamped real captures,
                                                # excludes dryrun*.csv and the old shakedown.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Resolve the newest matching capture on the Ubuntu side (by mtime). REMOTE_DIR is
# quoted (has spaces); the glob stays unquoted so the REMOTE shell expands it.
REMOTE_CSV="$(ssh "$HOST" "ls -1t \"$REMOTE_DIR\"/$REMOTE_GLOB 2>/dev/null | head -1")"
if [ -z "$REMOTE_CSV" ]; then
  echo "watch_run: no files matching '$REMOTE_DIR/$REMOTE_GLOB' on $HOST" >&2
  echo "watch_run: (is the logger running? try a broader glob, e.g. '*.csv')" >&2
  exit 1
fi
echo "watch_run: following  $REMOTE_CSV   (newest match for '$REMOTE_GLOB', ${HOURS}h window)" >&2

ssh "$HOST" "cat \"$REMOTE_CSV\"; tail -f -n 0 \"$REMOTE_CSV\"" \
  | "$HERE/venv/bin/python" -u "$HERE/tools/live_chart.py" --hours "$HOURS"
