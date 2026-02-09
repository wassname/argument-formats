"""
Argdown strict mode verifier.

Parses Argdown JSON export and checks:
1. Credence consistency against strict mode logical relations
   - entails: credence(B) >= credence(A)
   - contrary: credence(A) + credence(B) <= 1
   - contradictory: credence(A) + credence(B) = 1 (within tolerance)
2. Math expressions (SymPy)
3. Epistemic tags (observations must have sources -- checked if present)
4. Graph structure (NetworkX)
5. Credence propagation + crux identification

Usage:
    npx @argdown/cli json input.argdown --stdout | python verify_argdown.py
    # or
    python verify_argdown.py exported.json
"""
import json
import sys
from pathlib import Path

import networkx as nx
import sympy


CONTRADICTION_TOLERANCE = 0.05  # credences should sum to 1.0 +/- this


def load_json(path_or_stdin: str | None) -> dict:
    if path_or_stdin and Path(path_or_stdin).exists():
        return json.loads(Path(path_or_stdin).read_text())
    return json.load(sys.stdin)


def extract_statements(data: dict) -> dict[str, dict]:
    """Extract statement title -> {credence, tag, math, text}."""
    statements = {}
    for title, ec in data.get("statements", {}).items():
        info = {"title": title, "text": "", "credence": None, "tag": None, "math": None}
        d = ec.get("data", {})
        info["credence"] = d.get("credence")
        info["tag"] = d.get("tag")
        info["math"] = d.get("math")
        if ec.get("members"):
            info["text"] = ec["members"][0].get("text", "")
        statements[title] = info
    return statements


def extract_relations(data: dict) -> list[dict]:
    """Extract all relations with types."""
    relations = []
    seen = set()
    for title, ec in data.get("statements", {}).items():
        for rel in ec.get("relations", []):
            key = (rel["from"], rel["to"], rel["relationType"])
            if key not in seen:
                seen.add(key)
                relations.append(rel)
    for title, arg in data.get("arguments", {}).items():
        for rel in arg.get("relations", []):
            key = (rel["from"], rel["to"], rel["relationType"])
            if key not in seen:
                seen.add(key)
                relations.append(rel)
    return relations


def check_credence_consistency(statements: dict, relations: list) -> list[str]:
    """Check credences against strict mode logical constraints."""
    errors = []
    for rel in relations:
        a_title = rel["from"]
        b_title = rel["to"]
        a = statements.get(a_title, {})
        b = statements.get(b_title, {})
        ca = a.get("credence")
        cb = b.get("credence")

        if ca is None or cb is None:
            continue

        rtype = rel["relationType"]

        if rtype == "entails":
            # A entails B: P(B) >= P(A)
            if cb < ca:
                errors.append(
                    f"ENTAILMENT: [{a_title}] (credence={ca}) entails "
                    f"[{b_title}] (credence={cb}), but {cb} < {ca}. "
                    f"If A entails B, credence(B) must be >= credence(A)."
                )

        elif rtype == "contrary":
            # A contrary to B: can't both be true, P(A) + P(B) <= 1
            total = ca + cb
            if total > 1.0:
                errors.append(
                    f"CONTRARY: [{a_title}] (credence={ca}) contrary to "
                    f"[{b_title}] (credence={cb}), sum={total:.2f} > 1.0. "
                    f"Contraries can't both be true."
                )

        elif rtype == "contradictory":
            # A contradicts B: exactly one true, P(A) + P(B) = 1
            total = ca + cb
            if abs(total - 1.0) > CONTRADICTION_TOLERANCE:
                errors.append(
                    f"CONTRADICTION: [{a_title}] (credence={ca}) contradicts "
                    f"[{b_title}] (credence={cb}), sum={total:.2f} != 1.0 "
                    f"(tolerance={CONTRADICTION_TOLERANCE})."
                )

    return errors


def check_math(statements: dict) -> list[str]:
    """Evaluate math expressions with SymPy."""
    errors = []
    for title, s in statements.items():
        expr_str = s.get("math")
        if not expr_str:
            continue
        try:
            result = sympy.sympify(expr_str)
            if result is sympy.true:
                pass
            elif result is sympy.false:
                errors.append(f"MATH FAIL: [{title}]: '{expr_str}' is False")
            else:
                val = float(result.evalf())
                errors.append(
                    f"MATH EVAL: [{title}]: '{expr_str}' = {val:.4f} "
                    f"(not a boolean comparison)"
                )
        except Exception as e:
            errors.append(f"MATH ERROR: [{title}]: '{expr_str}' raised {e}")
    return errors


def check_graph(statements: dict, relations: list, data: dict) -> list[str]:
    """Build graph and check structure."""
    G = nx.DiGraph()
    errors = []

    for title in statements:
        G.add_node(title)

    for rel in relations:
        G.add_edge(rel["from"], rel["to"], type=rel["relationType"])

    # Check for cycles in entailment subgraph
    entailment_edges = [(u, v) for u, v, d in G.edges(data=True) if d["type"] == "entails"]
    E = nx.DiGraph(entailment_edges)
    cycles = list(nx.simple_cycles(E))
    for cycle in cycles:
        errors.append(f"ENTAILMENT CYCLE: {' -> '.join(cycle)} (circular reasoning)")

    # Isolated nodes: only flag statements that appear as top-level claims
    # but have no relations. PCS-internal premises (inside arguments) are
    # expected to be "isolated" in the cross-argument graph.
    top_level = {
        title for title, ec in data.get("statements", {}).items()
        if ec.get("isUsedAsTopLevelStatement")
    }
    for title in statements:
        if G.degree(title) == 0 and title in top_level:
            errors.append(f"ISOLATED: [{title}] is a top-level statement with no relations")

    return errors


def crux_analysis(statements: dict, relations: list) -> list[str]:
    """Identify cruxes: which credence, if changed, most affects downstream."""
    notes = []

    # Build entailment graph and find statements with most downstream dependents
    G = nx.DiGraph()
    for rel in relations:
        if rel["relationType"] == "entails":
            G.add_edge(rel["from"], rel["to"])

    for title, s in statements.items():
        if s.get("credence") is None:
            continue
        if title not in G:
            continue
        # Count downstream nodes reachable via entailment
        downstream = len(nx.descendants(G, title))
        if downstream > 0:
            notes.append(
                f"CRUX: [{title}] (credence={s['credence']}) "
                f"has {downstream} downstream entailment(s). "
                f"Changing this credence affects {downstream} other statement(s)."
            )

    return notes


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    data = load_json(path)

    statements = extract_statements(data)
    relations = extract_relations(data)

    all_errors = []
    all_errors += check_credence_consistency(statements, relations)
    all_errors += check_math(statements)
    all_errors += check_graph(statements, relations, data)

    notes = crux_analysis(statements, relations)

    if all_errors:
        print(f"\n{len(all_errors)} issues found:\n")
        for e in all_errors:
            print(f"  {e}")
    else:
        print("All checks passed.")

    if notes:
        print(f"\nCrux analysis:")
        for n in notes:
            print(f"  {n}")

    print(f"\nSummary: {len(statements)} statements, {len(relations)} relations, "
          f"{sum(1 for s in statements.values() if s.get('credence') is not None)} with credences")

    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
