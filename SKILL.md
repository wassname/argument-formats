---
name: verified-argument-maps
version: 1.0.0
description: |
  Write structured argument maps in Argdown strict mode (.argdown files) with
  labeled premises, credences, and source verification. Use when analyzing
  claims, building argument structures, or evaluating evidence chains.
  Produces verifiable HTML via `just render`.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Task
---

# Verified Argument Maps

Write structured argument maps where every claim links to a source with a quote, premises get credences, inference steps are one-liners, and conclusions are computed. The output is an `.argdown` file that `just render` turns into verified HTML with credence coloring.

## Your Task

When asked to analyze a claim, build an argument map, or evaluate evidence:

1. **State the claim** as a falsifiable thesis with no hardcoded credence
2. **Search for evidence** -- find papers/sources, extract ONE direct quote per claim
3. **Write the .argdown file** using the patterns below
4. **Verify** by running `just render` (parses to JSON, checks credences, renders HTML)

---

## Four Principles

1. **Every claim has a source you can click.** `#observation` premises link to a paper/URL and include a blockquote of verbatim source text. A reader verifies in 10 seconds: click link, ctrl-F for quote.
2. **Separate observation from inference from conclusion.** Premises are sourced facts (`#observation`) or flagged assumptions (`#assumption`). The inference between `--` lines is one sentence. Each step is checkable in your head.
3. **Commit to numbers, not vibes.** Premises get `{credence: X}` (trust in the source, 0-1). Conclusions get `{inference: X}` (how strong the reasoning step is, 0-1). The verifier computes `conclusion_credence = product(premise_credences) * inference`. Nothing derivable is hardcoded.
4. **The argument computes a bottom line.** Entailments and contraries propagate through the graph. The top-level claim gets no hardcoded credence -- it's computed from everything below via log-odds aggregation.

---

## Argdown Strict Mode Syntax

### Frontmatter (required)

```argdown
===
title: Question Being Investigated
author: Agent Name
model:
    mode: strict
===
```

### Statements

```argdown
[ShortName]: Descriptive text about the claim. #tag
  > "exact quote from source"
  [Author Year](https://url-to-paper)
  {credence: 0.85, reason: "why this credence"}
```

- `[Title]` creates a named statement. Same title = same logical entity everywhere.
- `#observation` = sourced fact (must have URL + quote). `#assumption` = unsourced belief.
- `> "quote"` is the evidence. The premise text is just a pointer to it.

### Arguments (Premise-Conclusion Structures)

```argdown
<Argument Name>

(1) [Premise A]: Sourced claim. #observation
    > "quote"
    [Source](url)
    {credence: 0.90}
(2) [Premise B]: Assumed claim. #assumption
    {credence: 0.70}
----
(3) [Conclusion]: What follows from premises.
    {inference: 0.80}
  +> [Main Claim]
```

- Premises numbered `(1)`, `(2)`, etc.
- `----` (4+ hyphens) = collapsed inference bar
- `--` / rule text / `--` = expanded inference with rule name
- Last statement after the bar is the conclusion
- `{inference: X}` on conclusions, NOT `{credence: X}` (credence is computed)
- **ALL conclusions MUST be named** with `[Name]:` prefix. Never leave a conclusion as a bare sentence -- unnamed conclusions show as `[Untitled N]` in the verifier.

### Relations

| Syntax | Context | Name | Constraint | Use when |
|--------|---------|------|------------|----------|
| `+> [S]` | inside PCS, after conclusion | Entails/Support | P(B) >= P(A) | PCS conclusion supports statement S |
| `-> [S]` | inside PCS, after conclusion | Contrary/Attack | P(A) + P(B) <= 1 | PCS conclusion attacks statement S |
| `_> <A>` | inside PCS, after conclusion | Undercut | attacks inference, not premise | "Even if true, doesn't follow" |
| `+ <A>` | top-level, under statement | Support | argument A supports this statement | Linking argument to thesis |
| `- <A>` | top-level, under statement | Attack | argument A attacks this statement | Linking argument to thesis |
| `- [S]` | top-level, statement-to-statement | Contrary | P(A) + P(B) <= 1 | Mutual exclusion (use mutual `- [other]`) |

**Note on contradictions:** The `><` syntax is in the Argdown spec but does NOT parse in the CLI. To express "exactly one is true" (P(A) + P(B) = 1), use mutual contraries with a comment:

```argdown
// Contradiction: P(A) + P(B) = 1
[A]: ... {credence: 0.60}
  - [B]
[B]: ... {credence: 0.40}
  - [A]
```

### Top-Level Structure (every map uses this)

```argdown
[Thesis]: The thing you're arguing about.
  + <Pro Argument 1>
  + <Pro Argument 2>
  - <Con Argument 1>
  - <Con Argument 2>
```

Then each `<Argument>` expands into a PCS with sourced premises and inference bars.

---

## Structural Patterns

### Pattern 1: Sourced Premise (the atomic unit)

Every factual claim. The blockquote IS the evidence.

```argdown
[ShortName]: Author Year found X in study of Y. #observation
  > "exact quote from the source"
  [Author Year](https://url-to-paper)
  {credence: 0.90, reason: "well-cited, peer reviewed"}
```

For unsourced claims: `[Name]: Your assumption. #assumption {credence: 0.65}`

### Pattern 2: Evidence Chain (the workhorse)

Premises -> inference bar -> conclusion -> relation to claim.

```argdown
<Argument Name>

(1) [Premise A]: ... #observation
    > "quote"
    [Source](url)
    {credence: 0.90}
(2) [Premise B]: ... #assumption
    {credence: 0.70}
----
(3) [Conclusion]: What follows.
    {inference: 0.80}
  +> [Main Claim]
```

### Pattern 3: Undercut

Attacks the inference step, not the premises. `_> <Target>` says "even if your premises are true, your conclusion doesn't follow."

```argdown
<Model Collapse>
(1) [Collapse]: Shumailov 2024 showed recursive self-training degrades quality. #observation
    > "Model collapse is a degenerative process"
    [Shumailov et al. 2024, Nature](https://www.nature.com/articles/s41586-024-07566-y)
    {credence: 0.85}
----
(2) Naive synthetic scaling degrades quality.
    {inference: 0.80}
  _> <Synthetic Data Fix>
```

### Pattern 4: Contradiction (value tensions, scenario splits)

Two claims that cannot both be fully true. Use mutual contraries (see Relations note above).

```argdown
// Contradiction: P(Risk Real) + P(Opportunity Cost) = 1
[Risk Real]: AI catastrophe probability >= 5%. #observation
  {credence: 0.70}
  - [Opportunity Cost]

[Opportunity Cost]: Pausing delays millions of QALYs per year. #assumption
  {credence: 0.30}
  - [Risk Real]
```

### Pattern 5: Multi-Step Inference

Intermediate conclusions feed the next step. Name every conclusion.

```argdown
<Recursive Takeoff>
(1) [No Ceiling]: No fundamental barrier at human level. #observation
    {credence: 0.85}
(2) [Self Improve]: Capable AI could improve its own training. #assumption
    {credence: 0.50}
----
(3) [Rapid Gain]: Recursive self-improvement could produce rapid capability gain.
    {inference: 0.40}
(4) [Narrow Window]: Intervention window may be very short. #assumption
    {credence: 0.35}
----
(5) [Pause Buys Time]: A pause gives safety margin before recursive takeoff.
    {inference: 0.30}
```

### Pattern 6: Sub-Question Decomposition

Break complex questions into independent sub-questions, each with own evidence. A crux that `- [Main Q]` means: **if this crux resolves true, Main Q becomes less likely**. Use `+ [Main Q]` for cruxes that support the main question if true.

```argdown
[Main Q]: Scaling laws hold to 10^29 FLOP.

[Data Wall]: Data runs out before 10^29 FLOP. #crux
  - [Main Q]

[Energy Wall]: Energy costs become prohibitive. #crux
  - [Main Q]
```

Then each `#crux` gets its own PCS arguments with evidence.

### Pattern 7: Synthesis / Bottom Line

Pull conclusions from multiple arguments into a verdict. The verdict uses `+> [Main Claim]` if the evidence supports it, or `-> [Main Claim]` if the evidence goes against it. Set `{inference: X}` to reflect how strongly the evidence points that direction.

```argdown
<Bottom Line>
(1) [Evidence A Conclusion]
(2) [Evidence B Conclusion]
(3) [Counter Conclusion]
--
Weighing pro and con arguments {uses: [1, 2, 3]}
--
(4) [Verdict]: Net assessment after weighing all evidence.
    {inference: 0.55}
  +> [Main Claim]
```

### Pattern 8: Conditional Decomposition

Express conditional probabilities using mutual contraries + branched arguments.

```argdown
// Contradiction: exactly one scenario
[Condition True]: The conditioning variable is true. #assumption
  {credence: 0.70}
  - [Condition False]
[Condition False]: The conditioning variable is false. #assumption
  {credence: 0.30}
  - [Condition True]

<Event If Condition True>
(1) [Condition True]
(2) [Evidence For Event]: Evidence under this scenario. #observation {credence: 0.80}
----
(3) [Event Likely If True]: Under this condition, event probability is high.
    {inference: 0.75}
  +> [Event]
```

### Pattern 9: Correlated Arguments

Tag arguments sharing evidence base with `#cluster-X` to avoid double-counting.

```argdown
<Economic Cost> #cluster-cost
(1) [GDP Hit]: Sanctions could cost 7% of GDP. #observation {credence: 0.70}
----
(2) Economic costs deter. {inference: 0.65}
  + [Safe Outcome]

<Reputational Cost> #cluster-cost
(1) [Brand Risk]: Brand damage from unsafe deployment. #assumption {credence: 0.60}
----
(2) Reputation costs deter. {inference: 0.55}
  + [Safe Outcome]
```

### Pattern 10: Base Rate Prior

Mark the base rate explicitly. Other arguments are updates from it.

```argdown
[Base Rate]: Historical base rate is 3-5% per year. #prior #observation
  {credence: 0.80, role: "prior", base_rate: 0.04}
  + [Event]

<Upward Update>
(1) [New Signal]: Elevated risk indicator. #observation {credence: 0.75}
----
(2) Update upward from base rate.
    {inference: 0.60, role: "update", direction: "up", magnitude: 1.5}
  + [Event]
```

---

## Metadata Convention

Argdown passes arbitrary YAML `{key: value}` through to JSON. Only these keys are consumed by the verifier:

| Key | On what | Meaning |
|-----|---------|---------|
| `credence` | premises | Trust in this source/claim (0-1) |
| `inference` | conclusions | Strength of reasoning step (0-1). Credence is computed, not hardcoded. |
| `reason` | any | Why this credence/inference value (shown as tooltip) |

Optional metadata for rendering:

| Key | On what | Meaning |
|-----|---------|---------|
| `role` | statements | `"prior"` for base rate anchors, `"update"` for evidence shifts |
| `base_rate` | prior statements | The numeric base rate (e.g., 0.04) |
| `direction` | update conclusions | `"up"` or `"down"` from prior |
| `magnitude` | update conclusions | Likelihood ratio (e.g., 1.5 = 50% more likely) |

## Tag Convention

| Tag | Meaning |
|-----|---------|
| `#observation` | Sourced factual claim (must have link + quote) |
| `#assumption` | Unsourced belief or modeling choice |
| `#mechanism` | Explanation of how/why something works |
| `#crux` | A sub-question that determines the main answer |
| `#prior` | Base rate or reference class |
| `#cluster-X` | Correlated arguments sharing evidence base |
| `#pro` / `#con` | Classification for coloring |

---

## Procedure

1. **State the claim** -- falsifiable, no hardcoded credence
2. **Find evidence** -- search for papers/sources, find ONE direct quote per claim
3. **Write the top-level structure** -- Pattern: Pro/Con Map (thesis + supporting/attacking arguments)
4. **Write premises** -- Pattern 1 (sourced with quote + URL) or variant (assumption with reason)
5. **Write the inference** -- between `--` lines, ONE sentence, optionally `{uses: [1, 2]}`
6. **Write conclusion** -- `{inference: X}` not `{credence: X}`
7. **Connect to top-level claim** -- `+>` (entails) or `->` (contrary) or `_>` (undercut)
8. **Add structural patterns** as needed:
   - Simple empirical: Patterns 1-2, 7
   - Technical prediction: add Pattern 6 (sub-questions)
   - Forecasting: add Patterns 8 (conditionals), 10 (base rate)
   - Policy/normative: add Patterns 4 (contradictions), 5 (multi-step)
   - Complex evidence: add Patterns 3 (undercuts), 9 (correlation)
9. **Add a synthesis** -- Pattern 7 (bottom line weighing all evidence)
10. **Verify**: `just render` (or `npx @argdown/cli json file.argdown . && uv run python argmap.py file.json file_verified.html`)

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Premise text summarizes the finding | Put finding in the blockquote, keep premise text as a brief pointer |
| Blockquote is a question or vague | Find a declarative finding from the source |
| `{credence: X}` on a conclusion | Use `{inference: X}` -- credence is computed as product(premise_credences) * inference |
| `{credence: X}` on top-level claim | Remove it -- computed via log-odds propagation |
| Multi-sentence inference | Split into sub-arguments (Pattern 5) |
| Using `(1) and (2):` in inference text | Use `{uses: [1, 2]}` YAML on the inference rule instead |
| No URL on `#observation` | Every observation must link to a source |
| URL in `{url: "..."}` metadata | Use markdown link `[Label](url)` in the statement body |
| Counting correlated arguments independently | Tag with `#cluster-X` (Pattern 9) |
| Base rate treated as just another argument | Mark with `#prior` and `{role: "prior"}` (Pattern 10) |
| Square brackets in blockquotes | Escape `[` as `\[` inside `> "quote"` -- argdown parser treats `[text]` as statement references |
| Too many premises per argument | 2-4 premises per PCS is typical; more than 5 means split into sub-arguments |
| No `#observation` or `#assumption` tag on premises | Every premise needs one -- the tag tells the reader whether to expect a source |
| Missing `reason` on credence/inference | Always explain why you chose that number |
| Blockquote is just a paper title or abstract heading | Find a specific declarative finding from the paper. If you can't, use `#assumption` instead of `#observation` and note that the exact quote was unavailable |
| Paraphrasing instead of quoting | Copy the exact source text. If you paraphrase, mark it: `> "paraphrase: ..."` and lower credence |
| Unnamed PCS conclusions | Every conclusion needs `[Name]:` prefix. Unnamed shows as `[Untitled N]` |

---

## Full Example

```argdown
===
title: Are Linear Probes Reliable for Evaluating Representations?
author: Deep Research Agent
model:
    mode: strict
===

// Top-level claim: credence is computed from the arguments below
[Reliable]: Linear probes are a reliable method for evaluating
  neural network representations.
  + <Linear Separability>
  - <Probe Overfitting>

# Evidence For

<Linear Separability>

(1) [Monotonic]: Alain & Bengio 2016 train linear classifier probes
    on intermediate layers of Inception v3 and ResNet-50. #observation
    [Alain & Bengio 2016](https://arxiv.org/abs/1610.01644)
    > "we observe experimentally that the linear separability of features increase monotonically along the depth of the model"
    {reason: "4000+ citations, replicated across architectures", credence: 0.92}
(2) [Linearity Assumption]: If a property is linearly separable in
    a representation, it is likely encoded explicitly rather than
    requiring nonlinear computation to extract. #assumption
    {reason: "plausible but nonlinear features exist too", credence: 0.65}
--
Monotonic separability suggests probes track genuine feature quality
{uses: [1, 2]}
--
(3) [Probes Valid]: Linear probes reveal genuine structure in
    neural network representations.
    {inference: 0.92, reason: "direct implication if both premises hold"}
  +> [Reliable]

# Evidence Against

<Probe Overfitting>

(1) [Control Tasks]: Hewitt & Liang 2019 propose control tasks
    to test probe selectivity on ELMo representations. #observation
    [Hewitt & Liang 2019](https://arxiv.org/abs/1909.03368)
    > "popular probes on ELMo representations are not selective"
    {reason: "well-designed experiment, widely cited", credence: 0.90}
(2) [Limitations Survey]: Belinkov 2022 reviews the probing
    classifiers methodology. #observation
    [Belinkov 2022](https://arxiv.org/abs/2102.12452)
    > "recent studies have demonstrated various methodological limitations of this approach"
    {reason: "comprehensive survey but some claims are speculative", credence: 0.88}
--
High accuracy alone is insufficient evidence of encoding
{uses: [1, 2]}
--
(3) [Probes Mislead]: High probe accuracy may not reliably indicate
    that a representation genuinely encodes a property.
    {inference: 0.51, reason: "shows problems exist but doesn't prove probes are useless"}
  -> [Reliable]
```

This produces: `[Reliable]` implied credence ~65% (+1.8 log-odds from pro, -0.4 from con).

---

## Rendering

Run `just render` in the project directory. This:
1. Parses `.argdown` to JSON via `npx @argdown/cli json`
2. Runs `python argmap.py` which checks credence consistency, computes conclusions, and renders HTML with credence coloring

The HTML output shows:
- Bottom-line credence with log-odds breakdown
- Each argument as a card with colored borders (green = supports, red = challenges)
- Premises with blockquotes, source links, and credence badges
- Inference steps with strength indicators
- Computed conclusion credences with explicit math (premise1 x premise2 x inference = result)
