# dual_logger socket ingest — design scope

Status: **scope only, not built** (2026-09-12).

Why: with idea #3 there is no rotation, so nothing needs to command the Arduino — it
only has to send. That removes the DTR-reset control path that was the reason the USB
cable could not go away. Both the Arduino and the RTD nodes can become one-way senders
and `dual_logger.py` becomes a listener. Ubuntu then no longer has to sit with the rig.

---

## 1. What does NOT change

This is the point of the design. `dual_logger.py` already separates transport from
parsing:

- `_serial_lines()` is a generator that yields decoded text lines and mirrors each one
  to the `.raw` sidecar, tagged `CUR` / `TMP`, stamped with this machine's wall clock
  on arrival.
- `reader_current()` / `reader_temp()` consume that generator and update `state`.
- The merge loop reads only `state`. It never knows where a line came from.

So the change is one new generator with the same contract. Untouched:

- every regex (`cur_re`, `res1_re`, `res2_re`, `fault_re`)
- the sample-and-hold merge, the CSV columns, the derived status bits
- `CUR_STALE_S` / `COMP_ON_A` and their meaning
- the never-overwrite guards on the output files

**Nodes send exactly the line format they send over serial today** — `t_ms,amps,note`
from the Arduino, the `Resistance1 = …` blocks from the RTD node. No new wire format.
That keeps the `.raw` files comparable across the transport change, so
`tools/cur_corruption_scan.py` measures before-and-after on the same footing.

## 2. Direction and framing

Nodes **dial out** to the logger; the logger **listens**. This is what the existing
`esp32_rtd_wifi_node.ino` already does (TCP push to HOST:PORT), and it means the logger
never needs to know a node's address, so DHCP can move them freely.

Newline-delimited text, one line per record, as now.

## 3. Open decision — one port or one per role

**Option A: one listening port, nodes identify themselves.** Each node sends a hello
line on connect giving its role (`current` / `temp`) and a node id. One port to open,
one to configure, and it extends to a third node without new config. Costs a small
protocol and a hello-line parser.

**Option B: one port per role** (e.g. 9000 temp, 9001 current). No protocol at all —
the port *is* the role. More listeners and more configuration, and each new node needs
a new port assigned.

A is better if more nodes are coming; B is less code today.

## 4. Connection handling

- **One live connection per role.** A new connection for a role replaces the existing
  one — that is a node that rebooted, not a second node.
- **Idle timeout.** A node that loses power without closing its socket leaves the
  logger holding a half-open connection that looks alive forever. If no line arrives
  for the timeout, close it and wait for a fresh connect. (A node-side heartbeat gives
  the timeout something to see during genuinely quiet periods.)
- **Reconnect markers.** Write a marker line into `.raw` on every connect and
  disconnect, so gaps are visible in the capture rather than inferred.
- **Dropouts are already handled.** A WiFi dropout looks exactly like a sensor dropout:
  the merge holds the last value and `current_stale` goes to 1 after `CUR_STALE_S`.
  That mechanism was built for the serial case and covers this one unchanged.

## 5. One clock — keep it

`.raw` lines are stamped on arrival with the logger's wall clock, exactly as now.

**A reconnecting node must DROP whatever it could not send, never replay it.** Replayed
samples would arrive with arrival-stamps that are wrong by the length of the outage,
which is precisely the two-clock merge problem lesson #8 was written about. Buffering
across a dropout is not worth reintroducing it.

## 6. Coast control must refuse to run over a socket

`coast_controller` holds a load off by DTR-resetting the Arduino through
`state["arduino_ser"]`. A socket has no DTR. The socket transport leaves
`arduino_ser` as `None`, so a cut would simply never happen.

The failure direction is safe (power stays on) but silent, which is worse than useless
during a run. **Refuse at startup**: `--coast-control` together with a socket current
source is a fatal argument error, not a warning.

Coast control was temporary scaffolding for the fridge experiments and #3 does not use
it, so this is a guard, not a limitation.

## 7. Configuration

`--current-port` / `--temp-port` accept `socket` (or `tcp:<port>`) alongside `auto` and
a device path. One flag per role, as now, and **mixed mode works**: Arduino on USB with
temps over WiFi, or the reverse.

Mixed mode is not a curiosity — it is how the EMI question gets tested. Run the current
channel on USB with the temp node wireless, then flip it, and compare corrupt-line rates
from `tools/cur_corruption_scan.py`.

## 8. Startup behavior changes

Today `main()` resolves BOTH serial ports up front and exits if either device is
missing. That is why a current-only run is impossible without editing the logger.

With a socket source: **bind the listening socket up front** (fail fast if the port is
already taken) but do **not** require a node to have connected. Nodes may join late,
leave, and rejoin. The merge already skips rows until at least one source has data.

## 9. Node-side requirements

- **Never block in `connect()`.** Measured on the RTD node 2026-09-10: with no listener,
  a blocking connect starved the sample loop to 41 samples in 122 s where 1 Hz should
  give ~122. Bound the attempt and keep sampling regardless.
- Drop unsent samples on reconnect (§5).
- Same line format as serial (§1).
- Arduino Uno WiFi Rev2 carries its own radio, so the current node needs no extra
  hardware. **Unverified:** which library revision is installed and whether its connect
  can be bounded — confirm before committing to it.

## 10. Open question this does not settle

If RF near the rig is what corrupts the USB serial link, then putting a transmitter on
the Arduino board itself — inches from the ACS712 analog lines — may trade a comms
problem for a measurement problem. Test before committing: log current over USB with
the board's radio idle, then transmitting, and compare.

## 11. Out of scope, adjacent

The second current column (channel 2) and the deferred `t1_freezer_f` → `t1_f` rename
are a HEADER change and must land atomically across every consumer, per the repo
convention. Separable from this work; do them in one pass, not two.

## 12. Testing

- Extend `--self-test` with a loopback case: feed canned lines over a socket and assert
  the same CSV rows the serial path produces from the same input.
- A fake-node script to exercise reconnect, idle timeout, and role replacement.
- A short side-by-side run — same appliance, both transports — before trusting a long
  capture to the new path.
