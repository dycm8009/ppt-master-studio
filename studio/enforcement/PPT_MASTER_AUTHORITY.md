# PPT Master Studio v3.2.0 — Authority

This Studio authority restricts and extends upstream PPT Master 5.0.0 without replacing its route-specific procedures.

## GitHub-first source authority
- `dycm8009/ppt-master-studio` is the single Studio Harness source authority.
- `main` is the upstream mirror; `studio-main` is stable; `studio-dev` is development.
- New projects resolve `studio-main` once and pin the exact commit SHA in `project_state.json`.
- In-progress projects must not silently move to a newer commit. Only an explicit Harness migration may change the pin.
- Uploaded Harness ZIPs are distribution/recovery artifacts only and may not compete with the GitHub pin.

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
11. A host filesystem reset triggers verified Portable Recovery; never reconstruct lost project evidence from chat memory.

## Authority order
1. Current explicit user request
2. This Authority
3. Studio Workflow
4. Static UI / Recovery Rules when active
5. Selected upstream route/profile
6. Template/Style/Layout authority
7. Page-level executor guidance
8. Heuristics/defaults
