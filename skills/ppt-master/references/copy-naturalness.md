# Copy Naturalness Specification

PPT-specific guidance for revising agent-authored slide prose and speaker notes so they sound deliberate and natural without changing the communication contract, facts, or execution topology.

**Trigger**: the active route is about to author new visible slide prose, adapt non-literal planned wording, or draft agent-authored speaker notes. Load once in each owning context before the first affected text is written.

---

## 1. Scope and ownership

| Surface | Apply | Boundary |
|---|---|---|
| Slide title, subtitle, core message, labels, captions, and concise body copy | Yes, when agent-authored or semantically adaptable | Keep the page job, hierarchy, claim set, and planned emphasis unchanged |
| Speaker notes | Yes, after the owning notes authority has established complete content coverage | Improve spoken rhythm without dropping any visible claim, evidence, relationship, qualifier, or bridge |
| User-provided final/literal script or wording | No | Preserve verbatim |
| Quotation, legal/compliance copy, code, command, formula, URI, file path, citation, or source label | No | Preserve verbatim |
| Mirror or strict-preservation text topology | No unless the owning fidelity authority explicitly permits prose changes | Preserve node count, order, and literal text where required |
| Stage 1/Stage 2 confirmation recommendations and receipts | No | This reference creates no recommendation field, confirmation item, receipt, or gate |
| Template specifications and repository documentation | No | Their owning authoring rules remain authoritative |

**Hard rule — expression only**: Change wording and sentence structure only. Never change a confirmed value, source fact, named entity, relationship, comparison basis, uncertainty, permission, prohibition, page roster, template assignment, or production outcome.

**Hard rule — owning authority wins**: Source materials, user instructions, confirmed state, Design Spec, lock, template fidelity, and the owning notes/page workflow remain authoritative. When a natural rewrite cannot preserve them confidently, keep the original wording.

---

## 2. Protected content

Before rewriting, inventory every protected item in the affected text. After rewriting, compare the result against that inventory.

| Protected class | Required preservation |
|---|---|
| Names and identifiers | Exact spelling of people, organizations, products, APIs, standards, files, keys, and version identifiers |
| Quantities | Exact numbers, signs, dates, times, units, currencies, percentages, ranges, rankings, and mathematical relationships |
| Evidence | Exact source attribution, citation marker, URL, Fact ID, quotation, sample boundary, and uncertainty qualifier |
| Literal material | Exact user-final wording, legal text, slogans marked literal, code, commands, formulas, paths, and hyperlink targets |
| Semantics | Every independent claim, condition, exception, comparison, dependency, causal link, and required implication |
| Topology | Any word/node/order constraint owned by mirror, strict template reuse, animation state, or final narration segmentation |

**Hard rule — zero protected delta**: If one protected token changes, disappears, is duplicated, or gains a new unsupported companion claim, discard the rewrite and retain the original text.

**Hard rule — no factual enrichment**: Naturalness is not research. Do not add a name, number, date, quote, citation, example, ranking, causal explanation, or recommendation that the approved source boundary does not support.

---

## 3. Rewrite procedure

1. Identify the surface, audience, reading mode, and whether a real writer sample or established source voice exists.
2. Mark protected content and the complete claim/relationship inventory.
3. Rewrite the whole sentence or short block around its actual point. Do not patch one watched word at a time or preserve an artificial structure merely because it already exists.
4. Verify protected content, claim coverage, tone, and fit. Keep the original when any check is uncertain.

**Default — voice matching (may override when the artifact requires a neutral register)**: Follow a supplied writer sample or stable source voice first. Otherwise use plain, domain-appropriate language. Keep technical, legal, scientific, financial, and incident-reporting material neutral rather than adding personality.

**Default — sentence rhythm (may override for a deliberate rhetorical pattern)**: Vary sentence length and openings enough to avoid a uniform mid-length cadence. Preserve deliberate repetition when it performs emphasis or sequence.

---

## 4. Language-aware diagnostics

The rows below are common triggers rather than a closed word blacklist. One occurrence does not prove a problem; revise when several signals combine or the wording obscures the point.

### 4.1 English

| Signal | Rewrite direction |
|---|---|
| Inflated importance, legacy, or trend claims | State the specific fact and its supported consequence |
| Sales language or decorative praise | Replace adjectives with concrete properties, evidence, or nothing |
| Vague experts, reports, observers, or critics | Name the supplied source or remove the unsupported attribution |
| Shallow `-ing` clauses that pretend to analyze | State the supported relationship directly |
| Avoidance of `is`, `are`, or `has` | Prefer the simple verb when it is clearer |
| Repeated `not X but Y`, forced groups of three, false ranges, or synonym cycling | Use the structure the meaning actually needs |
| Passive voice or missing subject | Name the actor when that clarifies responsibility |
| Repeated sentence openings, filler, stacked qualifiers, or announced transitions | Merge, vary, or start with the substantive point |
| Generic challenge/outlook ending, forced punchline, or vague optimism | End on the last concrete fact, decision, or next action |
| Chatbot residue, praise, or offers to continue | Remove it from standalone presentation copy |

### 4.2 Chinese

| Signal | Rewrite direction |
|---|---|
| Generic openings such as broad era/background statements without a sourced role | Start with the concrete situation, decision, or evidence |
| Repeated abstract verbs such as empower, enable, lead, build, or create without a clear object and outcome | Name who does what, to what, and with what observable result |
| Formulaic `not only... but also...`, mechanical three-part lists, or repeated `first/second/finally` | Use only the distinctions and sequence the argument needs |
| Stacked four-character phrases, intensifiers, or parallel slogans that add no information | Keep the strongest specific statement |
| Fixed `opportunities, challenges, and outlook` or generic positive closing | End with the actual unresolved issue, decision, owner, or next step |
| Repeated `through... achieve...` constructions | Put the actor and action first |
| Vague scale words such as multi-dimensional, comprehensive, deep, systemic, or high-quality without evidence | Replace them with the supported dimension or remove them |
| Uniform sentence length and repeated topic restatement | Combine redundant clauses and vary rhythm without losing formal precision |

**Hard rule — locale is not translation**: Diagnose patterns native to the active language. Do not mechanically translate an English watch list or force English punctuation preferences onto another language.

---

## 5. Surface profiles

### 5.1 Visible slide copy

**Default — compact direct copy (may override when reading mode is text-heavy)**: Prefer one governing assertion per title/core-message relationship. Keep labels parallel only when the items are true peers. Reduce repetition before reducing font size, but do not delete a required claim to make a page sparse.

**Hard rule — hierarchy preservation**: A rewrite may not move a qualifier, exception, source, or condition out of the text role that makes it understandable. It may not turn a neutral finding into a promise, a scenario into a fact, or a recommendation into a decision.

### 5.2 Speaker notes

**Mandatory**: Complete the owning notes authority's final-SVG coverage inventory before applying this reference. Naturalize the fully covered narration, not an incomplete draft.

**Default — spoken prose (may override for a formal scripted register)**: Use natural transitions, simple verbs, and varied sentence length. Avoid repetitive phrases such as “this slide shows” when the content can be stated directly. Keep every required claim, decisive value, comparison basis, uncertainty, implication, and forward bridge.

**Hard rule — coverage before fluency**: A smoother sentence never justifies dropping an information-bearing SVG group or a required speech-only role. Final/literal scripts remain verbatim.

---

## 6. Validation

Before committing the affected prose, answer every check from the actual before/after text:

| Check | Pass condition |
|---|---|
| Protected atoms | Exact values and required topology are unchanged |
| Claims | No fact, relationship, condition, exception, qualifier, or implication was added or removed |
| Source boundary | No unsupported detail or attribution was introduced |
| Voice | The result matches the writer/source register or the required neutral domain register |
| Surface fit | Slide copy remains scannable; notes remain complete and speakable |
| Workflow | No route, gate, confirmation field, page assignment, template contract, or production setting changed |

A failed or uncertain check restores the original wording. Return only the owning artifact's final prose; do not emit a draft, critique, AI-pattern report, or separate naturalness artifact.

---

## 7. Attribution

This specification adapts selected concepts from the MIT-licensed `blader/humanizer` project. Pin and local-difference records are in [`third_party/humanizer/SOURCE.md`](../third_party/humanizer/SOURCE.md).
