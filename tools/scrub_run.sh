#!/usr/bin/env bash
# Scrub/inspect a recorded logger CSV from the Ubuntu box on the Mac chart.
# Lists run_auto*.csv on Ubuntu, lets you pick one, streams it into
# tools/scrub_chart.py (an offline pan/zoom viewer). Companion to watch_run.sh.
#
# Usage:
#   ./tools/scrub_run.sh                 # menu of run_auto*.csv, 1 Hz (stride 10)
#   ./tools/scrub_run.sh 1               # full resolution (stride 1; slower load)
#   ./tools/scrub_run.sh 10 '*.csv'      # widen the file list to any capture
#
# One clock stays on Ubuntu; only the chosen file's rows cross the wire. Rows are
# thinned on the Ubuntu side with awk (keep header + every STRIDE-th row) so even
# the multi-day 200 MB+ captures load quickly. Pass stride 1 for every sample.
set -euo pipefail

HOST="ubuntu"                                   # ssh alias (same as watch_run.sh)
REMOTE_DIR="Documents/RetirementWork/Engineer/inverter"
STRIDE="${1:-10}"                                # keep every STRIDE-th data row (10 = ~1 Hz)
REMOTE_GLOB="${2:-run_auto*.csv}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Numbered menu of matching captures, newest first.
# (portable read into array -- macOS ships bash 3.2, which has no `mapfile`.)
FILES=()
while IFS= read -r line; do
  FILES+=("$line")
done < <(ssh "$HOST" "ls -1t \"$REMOTE_DIR\"/$REMOTE_GLOB 2>/dev/null")
if [ "${#FILES[@]}" -eq 0 ]; then
  echo "scrub_run: no files matching '$REMOTE_DIR/$REMOTE_GLOB' on $HOST" >&2
  exit 1
fi

echo "Captures on $HOST (newest first):" >&2
for i in "${!FILES[@]}"; do
  printf "  %2d) %s\n" "$((i+1))" "$(basename "${FILES[$i]}")" >&2
done
printf "Pick a file [1]: " >&2
read -r PICK </dev/tty || PICK=1
PICK="${PICK:-1}"
if ! [[ "$PICK" =~ ^[0-9]+$ ]] || [ "$PICK" -lt 1 ] || [ "$PICK" -gt "${#FILES[@]}" ]; then
  echo "scrub_run: invalid choice '$PICK'" >&2
  exit 1
fi
REMOTE_CSV="${FILES[$((PICK-1))]}"
NAME="$(basename "$REMOTE_CSV")"
echo "scrub_run: loading $NAME  (stride $STRIDE)" >&2

# Thin on the Ubuntu side: keep the header (NR==1) and every STRIDE-th data row.
ssh "$HOST" "awk -v s=$STRIDE 'NR==1{print;next} (NR-2)%s==0' \"$REMOTE_CSV\"" \
  | "$HERE/venv/bin/python" -u "$HERE/tools/scrub_chart.py" --title "$NAME"
