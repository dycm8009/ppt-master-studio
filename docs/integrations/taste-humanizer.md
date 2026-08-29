# Taste Skill and Humanizer integration plan

## Status

| Phase | State | Delivery boundary |
|---|---|---|
| 0. Decision, provenance, and roadmap | Implemented in the first integration change | Repository documentation and pinned third-party records |
| 1. Copy naturalness adapter | Implemented in the first integration change | Conditional PPT Master reference, no new route or gate |
| 2. Taste pilot workspace | Planned | Explicit unregistered Style workspace |
| 3. A/B evaluation | Planned | Repeatable corpus, blind rubric, and recorded evidence |
| 4. Production promotion | Blocked on Phase 3 | Only measured cross-scenario rules may move into a global reference |

The implementation baseline is `studio-main` commit `50779430c8be0fb6800b7a9c79c10756eae6ab78`.

---

## 1. Decision

Integrate selected capabilities as pinned PPT Master adapters. Do not install either upstream `SKILL.md` as a global runtime skill.

| Source | Evaluated pin | Decision |
|---|---|---|
| `blader/humanizer` | `e2e92e7b4b8229253ed5c8e81dc65463fdeddda5` | Adapt first as locale-aware, expression-only guidance for agent-authored slide copy and speaker notes |
| `Leonxlnx/taste-skill` | `ccbc15639c97057cbfcf32ecebc38ef716e4bb37` | Pilot later as an explicit unregistered Style; promote only measured, PPT-relevant rules |

Existing PPT Master route selection, Stage 1/Stage 2 confirmation, template ownership, image policy, motion policy, recovery, QA, and export remain authoritative.

---

## 2. Authority boundary

| Concern | Owner after integration |
|---|---|
| Top-level route and profile | Existing `routing.md` and selected runtime authority |
| Communication contract and production confirmation | Existing Stage 1 and Stage 2 |
| Source facts, approved claims, page roster, and prepared resources | Existing Strategist/Quick ownership |
| Geometry, composition, native construction, and SVG realization | Existing Executor/Quick ownership |
| Notes coverage and final-SVG grounding | Existing notes authority |
| Natural wording of agent-authored prose | Conditional `copy-naturalness.md`, subordinate to every owner above |
| Visual-taste experiment | Phase 2 explicit Style workspace, never a new workflow authority |
| Quality and export | Existing static checker, optional Visual Review, and exporter |

The adapters create no fifth route, confirmation field, receipt, lock key, persistent reasoning artifact, or post-processing rewrite pass.

---

## 3. Phase 1: copy naturalness

### 3.1 Trigger

`SKILL.md` conditionally loads `references/copy-naturalness.md` immediately before an owning context authors new visible slide prose or agent-authored speaker notes.

This placement covers Default, Quick, fresh/resumed Executor contexts, and notes-producing native routes without duplicating instructions across each workflow. It does not affect Stage 1 or Stage 2 recommendations.

### 3.2 Protected boundary

The adapter cannot change:

- confirmed values, source facts, claims, relationships, qualifiers, or uncertainty;
- names, product/API identifiers, numbers, dates, units, currencies, URLs, citations, Fact IDs, quotations, formulas, code, commands, or paths;
- user-final/literal wording, legal copy, or final narration;
- page count/order, template assignment, mirror/strict text topology, animation state, or production settings.

If a protected item or supported claim changes, the rewrite is discarded.

### 3.3 Language behavior

English and Chinese use separate diagnostic examples. The adapter treats pattern lists as illustrative evidence, not lexical bans. A writer sample or stable source voice takes precedence; technical and reference material remains neutral.

### 3.4 Output behavior

The adapter runs in embedded mode. It returns only the owning artifact's final prose and writes no draft, critique, score, or sidecar.

---

## 4. Phase 2: Taste pilot

Create an explicit workspace outside the registered Style index. A user or evaluation run must supply its exact root.

### 4.1 Retained concepts

- brief inference from audience, context, references, brand assets, and quiet constraints;
- presentation-specific variance, motion, and density reasoning;
- anti-default review for generic AI visual habits;
- redesign audit before visual change;
- cross-page composition-family and rhythm review;
- preflight checks expressed as defaults or references unless an objective PPT failure exists.

### 4.2 Excluded concepts

- React, Next.js, Tailwind, Motion, GSAP, navigation, CTA, forms, mobile viewport, and web-performance rules;
- AIDA as a mandatory deck structure;
- mandatory randomization or static-is-failure behavior;
- global em/en-dash, equal-card, icon-authoring, or SVG-construction bans;
- any rule that competes with Brand, Style, Layout, Deck, confirmed user values, or PPT Master construction authority.

### 4.3 Registration gate

Do not add the pilot to `styles_index.json` until Phase 3 shows that it is a distinct reusable presentation method rather than a general aesthetic checklist.

---

## 5. Phase 3: A/B evaluation

Use the same source corpus, page-count boundary, model/runtime pin, and confirmation values across variants.

| Variant | Naturalness adapter | Taste pilot |
|---|---:|---:|
| Baseline | No | No |
| Naturalness | Yes | No |
| Taste | No | Yes |
| Combined | Yes | Yes |

The corpus must include creative pitch, product launch, investor pitch, technical deep dive, academic research, operating review, incident postmortem, data-heavy material, Chinese, bilingual, Brand, and structured-template scenarios.

### 5.1 Measures

| Dimension | Evidence |
|---|---|
| Factual fidelity | Protected-token and claim comparison against approved sources |
| Communication quality | Blind reviewer score for clarity, specificity, hierarchy, and audience fit |
| Visual quality | Preference score plus existing Hard/Soft Visual Review findings |
| Template safety | Page topology, identity, placeholder, and strict/mirror preservation |
| Context cost | Loaded prompt bytes/tokens and avoidable repetition |
| Stability | Cross-run variance and failure/rework count |

### 5.2 Promotion threshold

Promotion requires a consistent preference gain in target scenarios, no factual or topology regressions, no increase in Visual Review Hard findings, and acceptable context cost. Scenario-specific benefit does not justify a global rule.

---

## 6. Phase 4: production promotion

Move only validated cross-scenario rules into a compact presentation-taste reference. Keep scenario-specific behavior in Style workspaces. Keep the upstream sources pinned and update them only through a reviewed diff.

The production reference must remain subordinate to:

1. explicit user and source requirements;
2. confirmed communication and production state;
3. Brand/Style/Layout/Deck ownership;
4. Strategist/Quick content and resource planning;
5. Executor construction and existing QA.

---

## 7. Provenance and updates

Third-party records live under `skills/ppt-master/third_party/`. Each source record contains its repository, evaluated commit, source blob, license, retained concepts, excluded concepts, and local behavior differences.

Runtime execution never fetches upstream `main`. An update starts with a pinned-source diff, then repeats the relevant Phase 3 evaluation before changing local behavior.
