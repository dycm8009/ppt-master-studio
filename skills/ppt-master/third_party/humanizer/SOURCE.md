# Humanizer source record

| Field | Value |
|---|---|
| Upstream repository | `blader/humanizer` |
| Evaluated commit | `e2e92e7b4b8229253ed5c8e81dc65463fdeddda5` |
| Source file | `SKILL.md` |
| Source blob | `c9c22422f822f07767ad1b6e79eedccbfe4e9f63` |
| Upstream version | `2.11.2` |
| License | MIT |
| Local adapter | `../../references/copy-naturalness.md` |

## Retained concepts

- preserve every source claim and do not invent facts;
- match a supplied writer sample before applying default style guidance;
- diagnose clusters of artificial-writing patterns rather than treating one signal as proof;
- rewrite the sentence or paragraph around its main point instead of replacing watched words mechanically;
- run a second factual/claim check after rewriting;
- use embedded output behavior when another workflow owns the artifact.

## Excluded concepts

- the pasted-text draft/critique/final response format;
- generic file-editing behavior outside PPT Master;
- a global em/en-dash ban;
- English lexical watch lists as universal rules;
- any rewrite that changes source, confirmation, template, page, or notes-coverage authority.

## Local differences

The PPT Master adapter:

- covers visible slide copy and agent-authored speaker notes only;
- adds separate Chinese diagnostic examples;
- protects presentation topology, formulas, code, citations, final narration, and template fidelity;
- creates no new route, gate, field, receipt, sidecar, or post-processing pass;
- discards a rewrite when protected content or supported claims change.

See `LICENSE` in this directory for the upstream license text.
