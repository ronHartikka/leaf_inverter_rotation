# Superseded loggers — kept for provenance, not for use

These are the **two separately-clocked loggers** that `tools/dual_logger.py` replaced.
Do not run them for new captures.

- `collect_current.py` (2026-07-17) — Arduino current stream on `/dev/ttyACM0`, tee to a
  log file.
- `temp_logger.py` (2026-07-16) — ESP32 MAX31865 / PT1000 stream on `/dev/ttyUSB0`,
  wall-clock stamped, plus a parallel CSV.

They are here because they are the provenance of the July 2026 datasets, and because
until 2026-09-20 they existed only on the Ubuntu box, in no repo and no backup.

Why they were replaced is lesson #8. `temp_logger.py`'s own docstring states the problem
it could not solve: it stamps wall-clock time so the log can "later merge this with the
Arduino current log, **which is on a different machine with its own clock**." Merging two
separately-clocked streams needs both rate-scaling (the Arduino resonator runs ~0.24%
slow) and phase alignment. `dual_logger.py` removes the problem instead of correcting
for it — one logger, one machine, one clock.

Copied verbatim off the Ubuntu box; deliberately unmodified, headers and all.
