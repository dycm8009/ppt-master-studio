---
description: Non-blocking read-only Storyboard projection from the current Design Spec.
---

# Storyboard Projection Stage

Project the current `design_spec.md §IX` into a compact human-readable Storyboard without creating a second planning authority or confirmation gate.

## 1. Entry

**When to run**: Default Generate after Design Spec Gate 1 and the current lock Gate 2 have passed, before Executor begins. Rebuild after any later Design Spec mutation before presenting the Storyboard again.

**Hard rule — read-only authority**: `design_spec.md` remains the only planning authority. `live_preview/storyboard.json` and `live_preview/storyboard.html` are derived views and never confirm, lock, override, or repair a planning value.

Run:

```bash
python3 "${SKILL_DIR}/scripts/storyboard_handoff.py" build <project_path>
```

The command writes:

- `<project_path>/live_preview/storyboard.json`
- `<project_path>/live_preview/storyboard.html`

The projection includes the exact slide roster plus page title, audience move, core message, evidence/source dependency, layout/visual focus, content, optional visualization/images/math/motion fields, adjacency, and deterministic risk hints.

---

## 2. Presentation

**Default — present when the host supports a useful artifact surface (may override when the user explicitly asks to skip previews)**: expose `launch_path` through the host's normal user-accessible file transport. Opening or ignoring the Storyboard never blocks the route.

**Hard rule — no implied confirmation**: a Storyboard view produces no user receipt. Do not treat a page visit, silence, or the existence of the derived files as approval of the Design Spec.

**Staleness**: the projection records `design_spec_sha256`. If `design_spec.md` changes, run:

```bash
python3 "${SKILL_DIR}/scripts/storyboard_handoff.py" status <project_path>
```

A `stale: true` result requires rebuild before any later presentation of the Storyboard. Staleness does not itself reopen a previously closed official planning gate; the owning Generate recovery rule decides whether the Design Spec mutation was valid.

---

## 3. Quality experiments

**Reference — not a constraint**: `skills/ppt-master/experiments/representative_calibration.py` and `skills/ppt-master/experiments/semantic_review.py` consume the Storyboard only for benchmark work. They are not runtime triggers, do not alter the current `P01 → uninterrupted remaining pages` generation rhythm, and do not create advisory or blocking production gates until separate evaluation justifies an official workflow change.

## 4. Projection integrity

The view is a static snapshot, not a live connection to the source. The owning
`status` and `load_current` checks reject missing or changed source/HTML,
modified JSON projection, and duplicate page identity. Rebuild before presenting
an out-of-date view. Code fences and indentation remain literal content rather
than page/field syntax. Risk labels are heuristics, not confirmed capabilities.

Both experimental consumers use `load_current` and include the source digest
in their output. Their results are not evidence of factual correctness, topology
correctness, native PowerPoint fidelity, or production-quality improvement.
