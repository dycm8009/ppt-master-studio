# PPT Master Studio — Portable Recovery Rules

Serverless runtimes may reset local filesystems. Fail Closed must distinguish a host reset from invalid project evidence without recreating lost files from memory.

- `project_state.json` is the normal resume entry while present.
- If missing, attempt verified recovery before final refusal.
- Recovery authority is only a `*.ppt-recovery.zip` produced by `studio/scripts/enforced_recovery.py snapshot` and verified by manifest + per-file SHA-256.
- Recovery manifests carry the exact GitHub Harness repo/ref/commit binding.
- Required serverless checkpoints: planning-ready before authoring; authoring-reviewed after accepted Deck Review changes and before QA; final QA/motion checkpoint before export.
- After restore, materialize the pinned Harness commit and run bootstrap + preflight against that SHA.
- Never recreate state, spec lock, accepted confirmation receipts, SVGs, image assets, or validation reports from chat memory.
- `deck_review.html` may be used only for partial SVG salvage; it is not a complete recovery authority.
