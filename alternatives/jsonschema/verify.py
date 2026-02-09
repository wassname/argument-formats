"""
Argument graph verifier.

Reads a YAML argument file, validates against JSON schema,
then runs additional checks that schemas can't express:
- Referential integrity (inference refs -> premise ids)
- Math expression evaluation (SymPy)
- Source URL liveness (requests)
- Graph structure analysis (NetworkX)

Usage: python verify.py antipasto.yaml
"""
import json
import sys
from pathlib import Path

import jsonschema
import networkx as nx
import sympy
import yaml


def load_schema():
    schema_path = Path(__file__).parent / "argument_schema.json"
    return json.loads(schema_path.read_text())


def load_arguments(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text())


def check_schema(data: dict, schema: dict) -> list[str]:
    """JSON Schema validation: structural checks including obs-must-have-source."""
    errors = []
    v = jsonschema.Draft202012Validator(schema)
    for e in v.iter_errors(data):
        errors.append(f"SCHEMA: {e.json_path}: {e.message}")
    return errors


def check_refs(data: dict) -> list[str]:
    """Check that inference premise refs actually exist in the argument."""
    errors = []
    for arg in data["arguments"]:
        premise_ids = {p["id"] for p in arg["premises"]}
        for inf in arg["inferences"]:
            for ref in inf["from"]:
                if ref not in premise_ids:
                    errors.append(
                        f"REF: {arg['name']}: inference references '{ref}' "
                        f"but premises are {premise_ids}"
                    )
    return errors


def check_math(data: dict) -> list[str]:
    """Evaluate math expressions in premises using SymPy."""
    errors = []
    for arg in data["arguments"]:
        for p in arg["premises"]:
            expr_str = p.get("math")
            if not expr_str:
                continue
            try:
                result = sympy.sympify(expr_str)
                if result == True:  # noqa: E712
                    pass  # ok
                elif result == False:  # noqa: E712
                    errors.append(
                        f"MATH FAIL: {arg['name']}/{p['id']}: "
                        f"'{expr_str}' evaluates to False"
                    )
                else:
                    # expression didn't reduce to bool, evaluate numerically
                    val = float(result.evalf())
                    errors.append(
                        f"MATH EVAL: {arg['name']}/{p['id']}: "
                        f"'{expr_str}' = {val:.4f} (not a boolean comparison)"
                    )
            except Exception as e:
                errors.append(
                    f"MATH ERROR: {arg['name']}/{p['id']}: "
                    f"'{expr_str}' raised {e}"
                )
    return errors


def check_graph(data: dict) -> list[str]:
    """Build argument graph with NetworkX and check structure."""
    G = nx.DiGraph()
    errors = []

    # Add claim nodes
    for cid, claim in data.get("claims", {}).items():
        G.add_node(cid, type="claim", text=claim["text"])

    # Add argument conclusion nodes and relation edges
    conclusion_to_arg = {}
    for arg in data["arguments"]:
        cid = arg["conclusion"]["id"]
        G.add_node(cid, type="conclusion", text=arg["conclusion"]["text"])
        conclusion_to_arg[cid] = arg["name"]

        for rel in arg.get("relations", []):
            target = rel["target"]
            G.add_edge(cid, target, relation=rel["type"])

    # Check for orphaned conclusions (no outgoing relations)
    for arg in data["arguments"]:
        cid = arg["conclusion"]["id"]
        if G.out_degree(cid) == 0:
            errors.append(
                f"GRAPH: {arg['name']}: conclusion '{cid}' has no relations "
                f"(supports/attacks nothing)"
            )

    # Check for dangling relation targets
    for u, v, d in G.edges(data=True):
        if v not in G.nodes:
            errors.append(
                f"GRAPH: relation {d['relation']} targets '{v}' which doesn't exist"
            )

    # Check for cycles
    cycles = list(nx.simple_cycles(G))
    for cycle in cycles:
        errors.append(f"GRAPH CYCLE: {' -> '.join(cycle)}")

    # Report unsupported claims (no incoming support edges)
    for cid in data.get("claims", {}):
        supporters = [
            u for u, v, d in G.in_edges(cid, data=True)
            if d["relation"] == "supports"
        ]
        if not supporters:
            errors.append(f"GRAPH: claim '{cid}' has no supporting arguments")

    return errors


def check_sources(data: dict, verify_urls: bool = False) -> list[str]:
    """Check that observations have sources. Optionally verify URLs."""
    errors = []
    for arg in data["arguments"]:
        for p in arg["premises"]:
            if p["tag"] == "observation" and "source" not in p:
                errors.append(
                    f"SOURCE: {arg['name']}/{p['id']}: "
                    f"observation without source"
                )
            if verify_urls and "source" in p:
                import requests
                url = p["source"]["url"]
                if url.startswith("http"):
                    try:
                        r = requests.head(url, timeout=5)
                        if r.status_code >= 400:
                            errors.append(
                                f"SOURCE URL: {arg['name']}/{p['id']}: "
                                f"{url} returned {r.status_code}"
                            )
                    except Exception as e:
                        errors.append(
                            f"SOURCE URL: {arg['name']}/{p['id']}: "
                            f"{url} error: {e}"
                        )
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "antipasto.yaml"
    verify_urls = "--check-urls" in sys.argv

    schema = load_schema()
    data = load_arguments(path)

    all_errors = []
    all_errors += check_schema(data, schema)
    all_errors += check_refs(data)
    all_errors += check_math(data)
    all_errors += check_graph(data)
    all_errors += check_sources(data, verify_urls=verify_urls)

    if all_errors:
        print(f"\n{len(all_errors)} issues found:\n")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("All checks passed.")

        # Print summary
        n_args = len(data["arguments"])
        n_obs = sum(
            1 for a in data["arguments"]
            for p in a["premises"] if p["tag"] == "observation"
        )
        n_asm = sum(
            1 for a in data["arguments"]
            for p in a["premises"] if p["tag"] == "assumption"
        )
        n_math = sum(
            1 for a in data["arguments"]
            for p in a["premises"] if p.get("math")
        )
        print(f"\n  {n_args} arguments, {n_obs} observations, "
              f"{n_asm} assumptions, {n_math} math checks verified")


if __name__ == "__main__":
    main()
