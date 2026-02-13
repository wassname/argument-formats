# Verified Argument Maps - repeatable commands

# default file stem
default_stem := "example"

# Parse argdown to JSON (outputs json next to the .argdown file)
json stem=default_stem:
    npx @argdown/cli json {{stem}}.argdown "$(dirname {{stem}})"

# Verify + render enriched HTML (single step, like quarto render)
render stem=default_stem: (json stem)
    uv run --with sympy --with networkx python argmap.py {{stem}}.json {{stem}}_verified.html

# Render argument map to SVG/PDF (argdown CLI)
map stem=default_stem:
    npx @argdown/cli map {{stem}}.argdown "$(dirname {{stem}})"

# Full pipeline
all stem=default_stem: (render stem) (map stem)
