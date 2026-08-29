# Taste and Humanizer Phase 3 rubric

Use this rubric after the four blind-labeled variants for one scenario have completed normal PPT Master validation and export.

---

## 1. Prerequisites

| Requirement | Failure behavior |
|---|---|
| Identical source-bundle digest across four variants | Discard the scenario |
| Identical confirmation-snapshot digest across four variants | Discard the scenario |
| Correct runtime and workspace pins | Discard the affected run |
| Successful attribution guard | Stop the affected run |
| Required route validation and SVG quality checks | Record failure; no preference result can make it promotable |
| At least two independent reviewers | Keep the scenario incomplete |
| Hidden label-to-variant mapping during scoring | Repeat the blind review |

Visual Review is explicitly requested by this evaluation protocol. It remains the existing optional stage and receives no new rubric rules from this package.

---

## 2. Factual and literal audit

Audit final visible copy and notes against the approved source and confirmation snapshot before subjective review.

| Finding | Count as a regression |
|---|---|
| Changed name, identifier, number, date, unit, currency, URL, citation, Fact ID, quotation, formula, code, command, path, or literal text | Yes |
| Added unsupported claim, example, attribution, causal explanation, or recommendation | Yes |
| Lost claim, condition, exception, qualifier, comparison basis, dependency, or implication | Yes |
| Scenario presented as fact, recommendation presented as decision, or uncertainty removed | Yes |
| Harmless reordering or wording change with identical meaning and protected content | No |

One factual, literal, or protected-content regression blocks promotion of the responsible adapter or rule even when reviewers prefer the result.

---

## 3. Template and identity audit

Run this audit for Brand, Layout, Deck, mirror, strict, and structured scenarios.

| Finding | Count as a regression |
|---|---|
| Brand/Deck identity overridden by the pilot Style | Yes |
| Master/Layout identity or placeholder topology changed outside the active contract | Yes |
| Literal or strict text topology changed without permission | Yes |
| Template candidate, reuse scope, or adherence changed between variants because of the experiment | Yes |
| An adaptive change already permitted by the frozen confirmed plan | No |

A topology or identity regression blocks promotion.

---

## 4. Machine quality audit

Record existing checker and Visual Review results without inventing new quality rules.

| Measure | Interpretation |
|---|---|
| Attribution guard | Required pass |
| Project validation | Required when the route owns it |
| SVG quality | Required pass for SVG-authoring routes |
| Visual Review Hard findings | Must not increase against the matching baseline |
| Visual Review Soft findings | Review context; one soft count alone does not decide promotion |
| Rework count | Lower is better when output quality and scope remain equal |
| Input/output tokens | Context-cost evidence, not a quality score |

A preferred deck with a new Hard finding is not promotable.

---

## 5. Blind human review

Reviewers receive only blind-labeled final artifacts and the frozen audience/outcome brief. Do not reveal the variant, prompt text, branch, or expected hypothesis.

Score each dimension from 1 to 5:

| Dimension | Reviewer question |
|---|---|
| Clarity | Can the main point and page sequence be understood without reconstructing the author's intent? |
| Specificity | Does the wording and design feel tied to this subject rather than a generic AI template? |
| Hierarchy | Is attention directed to the intended claim, evidence, or decision on each page? |
| Audience fit | Does the register, density, evidence, and visual posture fit the frozen audience and context? |
| Visual quality | Does the deck feel coherent, deliberate, legible, and professionally resolved? |

After scoring, rank the four artifacts from 1 to 4 for the scenario. A comment must identify the concrete page or wording behavior behind any strong preference.

Do not reward visual novelty that weakens evidence, editability, identity, legibility, or the communication objective.

---

## 6. Interpretation

Evaluate the adapters separately before evaluating the Combined variant.

| Comparison | Question |
|---|---|
| Naturalness vs Baseline | Does expression improve without protected-content, claim, or tone regressions? |
| Taste vs Baseline | Does brief-led specificity and roster rhythm improve without template, evidence, or Hard-review regressions? |
| Combined vs Naturalness | Does Taste add visual value after wording quality is already improved? |
| Combined vs Taste | Does naturalness add copy value without weakening the visual argument? |

A win limited to creative scenarios supports a scenario-specific Style. It does not support a global presentation-taste rule.

---

## 7. Phase 4 gate

Set promotion to `eligible` only when all required scenarios and reviewer records are complete and all conditions below hold:

- zero protected-content, unsupported-claim, lost-claim, literal, topology, and identity regressions;
- no increase in Visual Review Hard findings for the candidate behavior;
- consistent reviewer benefit in the scenarios where the behavior is proposed to apply;
- no material loss in technical, academic, operating, regulated, bilingual, or structured-template controls;
- context and rework cost are recorded and proportionate to the measured benefit;
- each proposed rule has a named evidence trail and an explicit scope.

Otherwise set the decision to `blocked` for incomplete evidence or `rejected` for completed evidence that fails the gate. Never register Taste Lab or add a global Taste reference automatically.
