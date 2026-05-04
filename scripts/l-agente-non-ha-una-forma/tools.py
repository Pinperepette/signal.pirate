"""Layer 4 — Tool / Azioni (dominio cucina).

Tre tool, ognuno con uno scopo netto:
  get_recipe         legge una ricetta dal Knowledge Graph (Array Redis)
  convert_servings   parsa gli ingredienti e li scala per N persone
  shopping_list      aggrega gli ingredienti di piu' ricette

Nessun tool e' "intelligente": sono deterministi e fanno una cosa
sola. L'agente li compone. Questo e' il punto del Layer 4: roba che
agisce, non roba che parla.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ToolResult:
    ok: bool
    payload: str
    source: str = ""


# --------------------------------------------------------------------- #
# get_recipe
# --------------------------------------------------------------------- #


def get_recipe(kg, name: str) -> ToolResult:
    """Lookup di una ricetta dal KG (esposto come tool)."""
    raw = kg.get(name)
    if not raw:
        return ToolResult(ok=False, payload=f"Ricetta '{name}' non trovata.", source="kg:get")
    return ToolResult(ok=True, payload=raw, source=f"kg:{name}")


# --------------------------------------------------------------------- #
# convert_servings
# --------------------------------------------------------------------- #


# parsing degli ingredienti tipo "- 200g spaghetti", "- 4 tuorli",
# "- 1.5L acqua", "- pepe nero". Le voci senza numero passano intatte.
_INGREDIENT_RE = re.compile(
    r"^\s*-\s*"                                     # bullet
    r"(?P<qty>\d+(?:[.,]\d+)?)\s*"                  # numero (4, 1.5, 1,5)
    r"(?P<unit>g|kg|ml|l|cl|cucchiai|cucchiaini)?"  # unita'
    r"\s+(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)


def _parse_servings(recipe_text: str) -> int | None:
    m = re.search(r"^servings:\s*(\d+)", recipe_text, re.MULTILINE)
    return int(m.group(1)) if m else None


def _scale_quantity(qty: float, factor: float) -> str:
    scaled = qty * factor
    if scaled == int(scaled):
        return str(int(scaled))
    return f"{scaled:.2f}".rstrip("0").rstrip(".")


def convert_servings(kg, recipe_name: str, target: int) -> ToolResult:
    """Scala una ricetta per N persone. Tool deterministico, niente LLM."""
    res = get_recipe(kg, recipe_name)
    if not res.ok:
        return res
    recipe_text = res.payload

    base = _parse_servings(recipe_text)
    if base is None:
        return ToolResult(
            ok=False,
            payload=f"Ricetta '{recipe_name}': servings di partenza non trovati.",
            source="convert_servings",
        )

    factor = target / base
    out_lines = [
        f"# {recipe_name} — convertita per {target} persone (da {base})",
        f"# NOTA: tutti i numeri sotto sono GIA' SCALATI per {target}",
        f"# persone con fattore {factor:g}. Non rieseguire la conversione.",
    ]

    in_ingredients = False
    for line in recipe_text.splitlines():
        # sovrascrivi la riga servings: per evitare che il LLM pensi
        # che la ricetta sia ancora quella originale e riscala
        if re.match(r"^\s*servings:", line, re.IGNORECASE):
            out_lines.append(f"servings: {target}  # originali: {base}")
            continue
        if line.strip().lower().startswith("## ingredienti"):
            in_ingredients = True
            out_lines.append(line)
            continue
        if in_ingredients and line.startswith("##"):
            in_ingredients = False
        if in_ingredients:
            m = _INGREDIENT_RE.match(line)
            if m:
                qty = float(m.group("qty").replace(",", "."))
                unit = m.group("unit") or ""
                rest = m.group("rest")
                scaled = _scale_quantity(qty, factor)
                out_lines.append(f"- {scaled}{unit} {rest}")
                continue
        # tutto il resto passa intatto
        out_lines.append(line)

    return ToolResult(
        ok=True,
        payload="\n".join(out_lines),
        source=f"convert_servings:{recipe_name}:{target}",
    )


# --------------------------------------------------------------------- #
# shopping_list
# --------------------------------------------------------------------- #


def shopping_list(kg, recipe_names: list[str], servings: int = 4) -> ToolResult:
    """Aggrega gli ingredienti di piu' ricette in una lista unica.

    Tool composito: chiama convert_servings internamente per uniformare
    le porzioni. Mostra come si possono concatenare tool deterministici.
    """
    aggregated: dict[str, tuple[float, str]] = {}
    missing: list[str] = []
    for name in recipe_names:
        res = convert_servings(kg, name, servings)
        if not res.ok:
            missing.append(name)
            continue
        for line in res.payload.splitlines():
            m = _INGREDIENT_RE.match(line)
            if not m:
                continue
            qty = float(m.group("qty").replace(",", "."))
            unit = (m.group("unit") or "").lower()
            ing = m.group("rest").strip().lower()
            key = f"{ing}|{unit}"
            prev_qty, prev_unit = aggregated.get(key, (0.0, unit))
            aggregated[key] = (prev_qty + qty, prev_unit)

    out = [f"# Lista della spesa ({servings} persone)"]
    for key in sorted(aggregated.keys()):
        ing, unit = key.split("|", 1)
        qty, _ = aggregated[key]
        scaled = _scale_quantity(qty, 1.0)
        out.append(f"- {scaled}{unit} {ing}")
    if missing:
        out.append("")
        out.append(f"# Ricette non trovate: {', '.join(missing)}")
    return ToolResult(ok=True, payload="\n".join(out), source="shopping_list")
