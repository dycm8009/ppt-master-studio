# PPT Master Studio v3.2.1 — Authority

This Studio authority restricts and extends upstream PPT Master 5.0.0 without replacing its route-specific procedures. Project-state/recovery schema remains on the compatible 3.2.0 contract; v3.2.1 changes host bootstrap behavior only.

## GitHub-first source authority
- `dycm8009/ppt-master-studio` is the single Studio Harness source authority.
- `main` is the upstream mirror; `studio-main` is stable; `studio-dev` is development.
- New projects resolve `studio-main` once and pin the exact commit SHA in `project_state.json`.
- In-progress projects must not silently move to a newer commit. Only an explicit Harness migration may change the pin.
- Hand-uploaded Harness ZIPs are not source authority. GitHub Runtime Release ZIPs are commit-bound executable distribution artifacts.
- NEW and RESUME are distinct host modes. NEW projects never require a project Recovery Bundle. Recovery authority applies only to continuation/recovery of an existing project.
- On ChatGPT/serverless hosts, stable SHA resolution must try the connected GitHub connector first and a public GitHub Web/API fallback second before declaring the source inaccessible.

## Non-negotiable rules
1. Do not bypass PPT Master with ad-hoc slide generation.
2. Decks with 18+ slides require deck-level rhythm/composition direction before authoring.
3. Image decisions follow Image Opportunity → Semantic Necessity → Template Compatibility → Image Role Fitness → Treatment & Placement; images are never a diversity quota.
4. General + Dark Tech is solid-surface and SVG-native by default; raster backgrounds, ambient AI backgrounds, full-bleed dense HUD/concept art are forbidden by default.
5. Long decks may not receive deck-wide automatic object animation. Motion requires a budget and page-level communication justification.
6. Final delivery requires SVG QA, render review, deck diversity/similarity review, image audit when applicable, motion audit when applicable, and PPTX postflight.
7. Missing required workflow artifacts stop execution; never silently downgrade.
8. Beautify/Convert preserves source content, facts, and sequence unless the user explicitly authorizes rewriting.
9. Every project must carry a GitHub Harness binding (`repo`, `ref`, exact `commit`); runtime commit mismatch is blocking.
10. On serverless hosts, preserve user-owned confirmation through the Static UI Adapter; never let the agent accept its own Stage 1/2 recommendation because Flask cannot run.
11. A host filesystem reset on a RESUME project triggers verified Portable Recovery; never reconstruct lost project evidence from chat memory.
12. Ordinary handoff/source ZIPs are inputs, not recovery evidence, unless they contain a valid `PPT_MASTER_RECOVERY_MANIFEST.json` with a supported `ppt-master-portable-recovery/*` schema.

## Authority order
1. Current explicit user request
2. This Authority
3. Studio Workflow
4. Static UI / Recovery Rules when active
5. Selected upstream route/profile
6. Template/Style/Layout authority
7. Page-level executor guidance
8. Heuristics/defaults
