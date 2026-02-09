# Verified Argument Maps

Structured arguments with automated verification, using Argdown strict mode + Bayesian credences + a Python verifier.

## The Problem

LLMs produce fluent arguments that bury their reasoning. Humans can't efficiently audit a wall of text for hidden assumptions, unsourced claims, or logical inconsistencies. Even human-written arguments smuggle in unjustified leaps.

## The Solution

Write arguments in Argdown strict mode with three additions:

1. **Epistemic tags** on every premise: `#observation`, `#assumption`, or `#definition`
2. **Sources** on every observation: `[Source](url)` + `> "direct quote"`
3. **Credences** on every statement: `{credence: 0.85}`

Strict mode gives logical relations (entailment, contrary, contradiction) instead of vague "support/attack". A Python verifier then checks what humans shouldn't have to:

| Check | Automated | How |
|---|---|---|
| Entailment consistency | Yes | credence(B) >= credence(A) when A entails B |
| Contrary consistency | Yes | credence(A) + credence(B) <= 1 |
| Contradiction consistency | Yes | credence(A) + credence(B) = 1 |
| Math claims | Yes | SymPy evaluates expressions |
| Graph structure | Yes | NetworkX finds cycles, orphans |
| Crux identification | Yes | Sensitivity analysis: which credence most affects downstream |
| Source URLs live | Yes | HTTP HEAD requests |
| Inference validity | No | This is what the human checks -- but it's now a short one-liner, not a paragraph |

The human's job shrinks to: read each one-liner inference step, and decide if it follows from the premises. Everything else is automated.

## Principles

**Separate observation from inference from conclusion.** Premises are either sourced facts or flagged assumptions. The inference step between `----` lines is a short one-liner. Conclusions get `[Titles]` so they can be referenced elsewhere.

**Credences make reasoning quantitative.** Instead of "I think this is true", commit to a number. The verifier catches inconsistencies: you can't be 95% sure of A, claim A entails B, but only be 80% sure of B.

**Strict mode makes relations logical.** `+` means entailment (not vague "support"). `-` means contrary (not vague "attack"). `><` means contradiction. These have checkable probability constraints.

**Crux identification is automatic.** The verifier finds which premises, if updated, would most change downstream conclusions. This tells you where to focus investigation.

## Use Cases

### Scalable oversight

An LLM generates an argument in Argdown format. The verifier checks everything it can (math, sources, credence consistency, graph structure). A human reviewer then only needs to check the inference steps -- which are forced to be short one-liners. This is scalable because the automated checks handle the mechanical parts, and the structured format makes human review efficient.

### Alignment via debate

Two LLM agents argue opposing positions in Argdown. A judge reviews the debate. The verifier:
- Identifies the most contentious statements (highest credence disagreement between agents)
- Checks that both agents' credences are internally consistent
- Verifies sourced claims automatically
- Flags where agents share assumptions (cruxes) vs where they disagree on facts

The judge focuses on the cruxes and disputed inferences rather than re-reading everything. Agents are incentivized to produce well-structured arguments because the verifier catches sloppy ones.

### Research argument auditing

Map the argument for a research decision (architecture choice, hyperparameter, method). The Argdown format forces you to make premises explicit, source observations, and flag assumptions. The verifier catches when your credences are inconsistent with your stated logical relations. The argument map (SVG) gives a visual overview.

## Quick Start

```bash
npm install -g @argdown/cli
pip install sympy networkx   # or: uv run --with sympy --with networkx
```

```bash
# Render argument map
argdown map example.argdown .

# Verify credence consistency, math, graph structure
argdown json example.argdown .
python verify_argdown.py example.json
```

## Example

```argdown
===
title: Should We Deploy the New Scoring Model?
model:
    mode: strict
===

[Deploy]: We should deploy the new scoring model.
  + <Accuracy Improvement>
  - <Fairness Concern>

<Accuracy Improvement>

(1) [Benchmark]: AUC=0.94 vs baseline 0.87 (n=50k, 5-fold CV). #observation
    [results.csv](./experiment/results.csv)
    > "mean AUC 0.937 (95% CI: 0.931-0.943)"
    {credence: 0.95, math: "0.937 > 0.871"}
(2) [Relevance]: 0.07 AUC gain = ~12% fewer false negatives. #observation
    [threshold_analysis.py](./experiment/threshold_analysis.py)
    {credence: 0.85}
----
(1) shows significant improvement; (2) shows it matters
----
(3) [Model Better]: New model meaningfully outperforms baseline.
    {credence: 0.80}
  +> [Deploy]

<Fairness Concern>

(1) [Disparity]: 8% TPR gap between groups A and B (p=0.003). #observation
    [fairness_audit.csv](./experiment/fairness_audit.csv)
    {credence: 0.92}
(2) [Policy]: Company requires <5% TPR gap. #definition
    {credence: 0.99}
----
(1) exceeds (2): 8% > 5%
----
(3) [Fails Fairness]: Model fails fairness threshold.
    {credence: 0.91}
  -> [Deploy]

// Strict relations with credence constraints
[Benchmark]
  +> [Model Better]      // entailment: verifier checks 0.80 >= 0.95 -- FAILS
[Model Better]
  - [Fails Fairness]     // contrary: verifier checks 0.80+0.91 <= 1.0 -- FAILS
[Fails Fairness]
  >< [Fairness OK]: Meets threshold. {credence: 0.09}  // contradiction: 0.91+0.09=1.0 OK
```

### Verifier output

```
2 issues found:

  ENTAILMENT: [Benchmark] (0.95) entails [Model Better] (0.80), but 0.80 < 0.95.
  CONTRARY: [Model Better] (0.80) contrary to [Fails Fairness] (0.91), sum=1.71 > 1.0.

Crux analysis:
  CRUX: [Benchmark] (0.95) has 2 downstream entailment(s).
```

The verifier caught: you can't be 95% sure of the benchmark AND only 80% sure the model is better (if one entails the other). And you can't be 80% sure it's better AND 91% sure it fails fairness (if those are contraries). Fix your credences or weaken the relations.

### Rendered argument map

See `example.html` (open in browser) or `example.pdf`.

## Files

```
example.argdown      # main example
verify_argdown.py    # Python verifier (credences, math, graph, cruxes)
example.json         # parsed JSON (generated)
example.html         # rendered HTML (generated)
example.pdf          # rendered PDF (generated)
alternatives/        # comparison: Lean4 DSL, ACE, JSON Schema approaches
```

## References

- Argdown: https://argdown.org/syntax/
- Argdown strict mode: https://argdown.org/syntax/#relations-between-statements
- AI Safety via Debate: Irving et al. 2018 (https://arxiv.org/abs/1805.00899)
- Scalable oversight: Bowman et al. 2022 (https://arxiv.org/abs/2211.03540)
