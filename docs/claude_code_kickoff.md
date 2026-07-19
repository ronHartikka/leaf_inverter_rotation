# First Claude Code session — kickoff prompt

Paste the block below as your first message in Claude Code, opened at the repo
root (`leaf_inverter_rotation/`). It points Claude Code at the durable context
already in the repo instead of re-explaining everything.

---

This is an Arduino/ESP32 hardware project: an automatic load-rotation controller
that shares one Leaf-inverter power source among household appliances during
outages, one load at a time. I'm continuing work that was scaffolded in a prior
chat and committed to this repo.

Before doing anything, read these for full context:
- `README.md` — what the project is, repo layout, workflow
- `docs/lessons.md` — 10 hard-won hardware lessons; treat as guardrails
- `docs/hardware.md` — authoritative pin map / power / rig facts
- `docs/rotation_budget.md` — the make-or-break duty-cycle question + status
- `docs/todo.md` — the prioritized backlog; THIS is the work queue

Work the backlog in `docs/todo.md` priority order. Start with P0 (the PT1000
sub-zero conversion fix in `tools/dual_logger.py`) — it's a real correctness bug
with a recorded architecture decision; do NOT relitigate the decision, implement
it. Verify with the self-test and cross-check described there BEFORE changing
anything that's currently trusted, and note that a live capture may be running on
a separate Ubuntu box (the repo copy of `dual_logger.py` is the reference; the
Ubuntu process runs its own copy and won't pick up edits until restarted).

Then P2 is the real objective: characterize the kitchen fridge (dual-compartment).

Working style: deep, careful debugging partner; establish authoritative facts
before moving on; prefer measured data over assumed values; mark confidence
honestly; document hardware quirks in code comments. The 0-indexed array vs
1-indexed physical channel label is a recurring snare — state both when it matters.
Make header/column changes (P1) as atomic commits across all consumers, never
piecemeal.

Confirm you've read the docs and give me your plan for P0 before editing.

---

## Note on scope
Priorities 0-3 and "Later" in `docs/todo.md` are the whole roadmap. P0 (temp
conversion) must not be lost — it was discovered late and is easy to forget.
The physical fridge capture (P2) needs you at the rig; ask this chat (or Claude
Code) for the at-the-rig checklist when you're ready to carry the setup upstairs.
