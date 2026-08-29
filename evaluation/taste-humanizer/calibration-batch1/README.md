# Taste and Humanizer calibration batch 1

This directory freezes three closed-corpus scenarios for the first executable Phase 3 calibration batch.

It is evaluation input, not PPT Master runtime policy. Merging it does not register Taste Lab, change a route, or promote any rule.

## Scenarios

| Scenario | Role in calibration | Slides |
|---|---|---:|
| `creative-pitch` | High expected Taste benefit and claim-restraint test | 6 |
| `technical-deep-dive` | Precision, mechanism, density, and neutral-tone control | 7 |
| `chinese-explainer` | Chinese naturalness and technical-claim preservation | 7 |

Each scenario contains:

- `source.md`: one closed source bundle;
- `confirmation.json`: common Stage 1 and Stage 2 values plus the explicit workspace manipulation;
- SHA-256 values recorded in `manifest.json`.

## Confirmation delegation

Repository-owner approval of the calibration PR delegates replay of the frozen confirmation values for these evaluation runs only. It does not delegate or alter confirmation in ordinary user projects.

The only variant manipulation is:

- `baseline`: baseline runtime, free design;
- `naturalness`: Humanizer runtime, free design;
- `taste`: baseline runtime plus the explicit unregistered Taste Lab workspace;
- `combined`: Humanizer runtime plus the same explicit workspace.

All other source, canvas, page count, palette, typography, image availability, production settings, notes policy, and Visual Review activation remain fixed.

## Execution boundary

The complete batch contains 12 generated decks: 3 scenarios × 4 variants.

Generated projects, PPTX files, blind-label maps, reviewer identities, and review evidence remain outside this input directory. Only hashes and final structured results should be committed after the runs complete.
