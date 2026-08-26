# PPT Master Studio Overlay

PPT Master Studio is a thin host/policy overlay on top of the upstream PPT Master skill.
The fork's `main` branch remains the upstream mirror. Studio-owned behavior lives under
`studio/` and should not be copied into upstream files unless an upstream compatibility
fix is truly required.

## Branch model

- `main` — upstream mirror; do not place Studio policy here.
- `studio-main` — stable Studio channel used by new PPT projects.
- `studio-dev` — development channel for Studio changes and regression testing.

A PPT project resolves the current `studio-main` HEAD once, records the exact commit SHA
in `project_state.json`, and stays on that commit until the user explicitly requests a
Harness migration. "Latest" is a project-start behavior, not a mid-project behavior.

## Overlay responsibilities

- human confirmation on serverless ChatGPT hosts through static HTML surfaces
- portable recovery across runtime resets
- long-deck art direction and similarity constraints
- image semantic/template compatibility policy
- motion budget and restrained motion defaults
- mandatory render/deck/postflight QA policy
- regression tests that keep those additions from drifting

The upstream Strategist, Executor, template system, SVG/PPTX converter, animation
registry, image acquisition, and route authorities remain upstream-owned.

## Runtime entry

Read `studio/PROJECT_BOOTSTRAP.md`. It is the canonical ChatGPT Project bootstrap
contract. Do not use a previously uploaded Harness ZIP as a competing authority.
