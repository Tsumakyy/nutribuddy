"""Cálculo determinístico de substituições equivalentes.

Toda a matemática nutricional do Buddy fica aqui, fora do modelo de linguagem:
o modelo local é pequeno demais para escolher porções com segurança. Uma troca
só é oferecida quando calorias e o macronutriente principal do grupo ficam
próximos aos do alimento original.
"""
import re
import unicodedata
from functools import lru_cache

from .nutrition_catalog import (
    HEALTHY_SUBSTITUTES_BY_GROUP,
    TACO_EXPANDED_FOODS,
    _table,
    find_nutribr_food,
    infer_food_group,
)

GRAMS_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramas?)\s*$", re.IGNORECASE)
MACROS = ("kcal", "protein_g", "carbs_g", "fat_g")

# Macronutriente que define a função do alimento no prato.
PRIMARY_MACRO = {
    "protein": "protein_g",
    "dairy_cheese": "protein_g",
    "carb": "carbs_g",
    "legume": "kcal",
    "fruit": "carbs_g",
    "fat": "fat_g",
    "dairy_drink": "kcal",
    "vegetable": "kcal",
}
MAX_KCAL_DIFF = 0.15
MAX_PRIMARY_DIFF = 0.15
MAX_GRAMS = {
    "protein": 300, "dairy_cheese": 200, "carb": 400, "legume": 350,
    "fruit": 400, "fat": 150, "dairy_drink": 400, "vegetable": 400,
}
# Alimentos medidos em unidades: (gramas por unidade, singular, plural)
UNIT_SIZES = {
    "Ovo cozido": (50, "unidade", "unidades"),
    "Ovo mexido": (50, "ovo", "ovos"),
    "Clara de ovo cozida": (30, "clara", "claras"),
    "Pão de forma integral": (25, "fatia", "fatias"),
    "Pão francês": (50, "unidade", "unidades"),
    "Castanha-do-pará": (4, "unidade", "unidades"),
}
FAMILIES = ("frango", "ovo", "arroz", "feijao", "banana", "leite", "iogurte", "batata", "pao", "macarrao", "queijo")
# Carboidratos têm "estilo": ninguém troca o pão do café por arroz.
CARB_STYLES = {
    "breakfast": {"pao", "tapioca", "aveia", "cuscuz"},
    "main": {"arroz", "macarrao", "batata", "mandioca", "quinoa", "cuscuz"},
}
TRAINING_ONLY = {"Whey protein concentrado"}
TRAINING_MEALS = {"pre_treino", "pos_treino", "pre_atividade", "pos_atividade"}

DESCRIPTORS = {
    "grelhado", "grelhada", "cozido", "cozida", "cozidos", "integral", "natural",
    "fresco", "fresca", "desnatado", "semidesnatado", "light", "escorrido", "agua",
    "de", "do", "da", "dos", "das", "com", "sem", "em", "flocos", "hidratada", "goma",
    "firme", "moido", "concentrado", "protein", "peito", "oliva", "folhas", "crespa",
    "prata", "nanica", "papaia", "pera", "italia", "parboilizado", "pasta",
}
# "pera" é descritor de "Laranja pera", mas também é a fruta Pera.
FOOD_KEYWORD_ALIASES = {
    "peixe": ("tilapia", "salmao", "atum"),
    "carne": ("patinho", "alcatra"),
    "bife": ("alcatra", "patinho"),
    "boi": ("patinho", "alcatra"),
    "aipim": ("mandioca",),
    "macaxeira": ("mandioca",),
    "ovos": ("ovo",),
    "pao": ("pao",),
    "paes": ("pao",),
    "file": ("tilapia", "frango"),
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _singular(token: str) -> str:
    if token.endswith("oes") and len(token) > 4:
        return token[:-3] + "ao"
    if token.endswith("aes") and len(token) > 4:
        return token[:-3] + "ao"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def tokens(text: str) -> list[str]:
    return [_singular(tok) for tok in re.findall(r"[a-z0-9]+", normalize(text))]


def food_tokens(name: str) -> set[str]:
    raw = [tok for tok in re.findall(r"[a-z]+", normalize(name))]
    significant = {_singular(tok) for tok in raw if tok not in DESCRIPTORS and len(tok) >= 3}
    if normalize(name) == "pera":
        significant.add("pera")
    return significant or {_singular(tok) for tok in raw if len(tok) >= 3}


def match_score(food_name: str, text_tokens: list[str]) -> int:
    """Quantos termos significativos do alimento aparecem no texto."""
    expanded = set(text_tokens)
    for tok in text_tokens:
        expanded.update(FOOD_KEYWORD_ALIASES.get(tok, ()))
    return len(food_tokens(food_name) & expanded)


@lru_cache(maxsize=1)
def catalog() -> tuple[dict, ...]:
    foods: dict[str, dict] = {}
    for entry in TACO_EXPANDED_FOODS:
        foods[normalize(entry["name"])] = {
            "name": entry["name"],
            "category": entry["category"],
            "group": entry["group"],
            **{key: float(entry[key]) for key in MACROS},
        }
    for name in _table().listar_alimentos():
        food = find_nutribr_food(name)
        group = infer_food_group(name)
        if food and group and normalize(food["name"]) not in foods:
            foods[normalize(food["name"])] = {
                "name": food["name"],
                "category": food["category"],
                "group": group,
                **{key: float(food[key]) for key in MACROS},
            }
    return tuple(foods.values())


def resolve_food(name: str, extra_foods: dict | None = None) -> dict | None:
    """Encontra os valores por 100 g de um alimento do plano."""
    norm = normalize(name)
    if extra_foods and norm in extra_foods:
        entry = dict(extra_foods[norm])
        entry.setdefault("group", infer_food_group(name))
        entry.setdefault("category", "")
        return entry if entry["group"] else None
    for food in catalog():
        if normalize(food["name"]) == norm:
            return food
    # Nome livre digitado pelo nutricionista ("Frango", "Tilápia") → melhor correspondência
    # dentro do mesmo grupo nutricional.
    group = infer_food_group(name)
    name_tokens = list(food_tokens(name))
    best, best_score = None, 0
    for food in catalog():
        if group and food["group"] != group:
            continue
        score = match_score(food["name"], name_tokens)
        if score > best_score:
            best, best_score = food, score
    return best


def parse_grams(qty: str) -> float | None:
    match = GRAMS_RE.fullmatch(qty or "")
    return float(match.group(1).replace(",", ".")) if match else None


def totals(food: dict, grams: float) -> dict:
    return {key: round(food[key] * grams / 100.0, 1) for key in MACROS}


def _round_portion(food_name: str, grams: float) -> float:
    if food_name in UNIT_SIZES:
        size = UNIT_SIZES[food_name][0]
        return max(1, round(grams / size)) * size
    if grams < 30:
        return max(1, round(grams))
    return max(5, round(grams / 5) * 5)


def portion_label(food_name: str, grams: float) -> str:
    grams_text = f"{int(grams)}g"
    if food_name in UNIT_SIZES:
        size, singular, plural = UNIT_SIZES[food_name]
        units = int(round(grams / size))
        return f"{units} {singular if units == 1 else plural} (~{grams_text})"
    return grams_text


def qty_like(original_qty: str, grams: float) -> str:
    """Grava a quantidade no mesmo estilo usado pelo nutricionista ("120 g" ou "120g")."""
    separator = " " if re.search(r"\d\s+g", original_qty or "") else ""
    return f"{int(grams)}{separator}g"


OLIVE_OIL = {"name": "Azeite de oliva", "group": "fat", "kcal": 884.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0}
MAX_OIL_GRAMS = 15
NO_COMPLEMENT_GROUPS = {"fat", "vegetable"}


def _diffs(new: dict, ref: dict, primary: str) -> tuple[float, float]:
    kcal_diff = abs(new["kcal"] - ref["kcal"]) / max(ref["kcal"], 1.0)
    primary_diff = (
        abs(new[primary] - ref[primary]) / max(ref[primary], 1.0) if primary != "kcal" else kcal_diff
    )
    return kcal_diff, primary_diff


def evaluate(original: dict, original_grams: float, candidate: dict, allow_complement: bool = True) -> dict:
    """Calcula a porção equivalente de `candidate` e o quanto ela se afasta do original.

    Quando o substituto é mais magro (ex.: frango no lugar de ovo), a porção que iguala o
    macronutriente principal fica com menos calorias. Nesse caso, como numa lista de
    equivalentes, completa-se com um pouco de azeite para repor a gordura boa.
    """
    group = original["group"]
    primary = PRIMARY_MACRO.get(group, "kcal")
    ref = totals(original, original_grams)
    base = {
        "food": candidate["name"],
        "group": candidate["group"],
        "category": candidate.get("category", ""),
        "primary": primary,
        "original_totals": ref,
        "extra": None,
    }
    gram_options = {}
    for key in {"kcal", primary}:
        if ref[key] > 0 and candidate[key] > 0:
            gram_options[key] = _round_portion(candidate["name"], ref[key] / candidate[key] * 100.0)
    if not gram_options:
        return {**base, "ok": False, "reason": "sem_dados", "error": 9.0}

    portions = set(gram_options.values())
    if candidate["name"] in UNIT_SIZES:
        size = UNIT_SIZES[candidate["name"]][0]
        for grams in list(portions):
            portions.update({max(size, grams - size), grams + size})

    attempts = []
    for grams in sorted(portions):
        new = totals(candidate, grams)
        kcal_diff, primary_diff = _diffs(new, ref, primary)
        attempts.append({**base, "grams": grams, "totals": new,
                         "kcal_diff": round(kcal_diff, 3), "primary_diff": round(primary_diff, 3),
                         "error": kcal_diff + primary_diff})

    primary_grams = gram_options.get(primary, next(iter(gram_options.values())))
    primary_totals = totals(candidate, primary_grams)
    gap = ref["kcal"] - primary_totals["kcal"]
    if (
        allow_complement
        and group not in NO_COMPLEMENT_GROUPS
        and gap > 0.15 * ref["kcal"]
        and ref["fat_g"] > primary_totals["fat_g"]
    ):
        oil = max(5, round(gap / OLIVE_OIL["kcal"] * 100 / 5) * 5)
        if oil <= MAX_OIL_GRAMS:
            oil_totals = totals(OLIVE_OIL, oil)
            combined = {key: round(primary_totals[key] + oil_totals[key], 1) for key in MACROS}
            kcal_diff, primary_diff = _diffs(combined, ref, primary)
            fat_close = abs(combined["fat_g"] - ref["fat_g"]) <= max(3.0, 0.5 * ref["fat_g"])
            if fat_close:
                attempts.append({**base, "grams": primary_grams, "totals": combined,
                                 "extra": {"food": OLIVE_OIL["name"], "grams": oil},
                                 "kcal_diff": round(kcal_diff, 3), "primary_diff": round(primary_diff, 3),
                                 # Troca simples é preferível a troca com complemento.
                                 "error": kcal_diff + primary_diff + 0.08})

    for attempt in attempts:
        too_big = attempt["grams"] > MAX_GRAMS.get(group, 400)
        attempt["ok"] = (
            attempt["kcal_diff"] <= MAX_KCAL_DIFF
            and attempt["primary_diff"] <= MAX_PRIMARY_DIFF
            and not too_big
        )
        if not attempt["ok"]:
            attempt["reason"] = "porcao_grande" if too_big else "nao_equivalente"
    attempts.sort(key=lambda a: (not a["ok"], a["error"]))
    best = attempts[0]
    # Para explicar ao paciente por que a troca não fecha.
    best["primary_match"] = {"grams": primary_grams, "totals": primary_totals}
    return best


def _carb_styles(food_name: str) -> set[str]:
    tok = food_tokens(food_name)
    return {style for style, words in CARB_STYLES.items() if tok & words}


def candidate_pool(group: str, meal_key: str) -> list[dict]:
    preferred = [normalize(name) for name in HEALTHY_SUBSTITUTES_BY_GROUP.get(group, [])]
    pool = []
    for food in catalog():
        if food["name"] in TRAINING_ONLY and meal_key not in TRAINING_MEALS:
            continue
        if food["group"] == group or normalize(food["name"]) in preferred:
            pool.append(food)
    return pool


def find_equivalents(
    original: dict,
    original_grams: float,
    meal_key: str,
    exclude_names: set[str] | None = None,
    disliked_tokens: set[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Melhores substitutos saudáveis do mesmo grupo, ordenados pela proximidade nutricional."""
    exclude = {normalize(name) for name in (exclude_names or set())}
    exclude.add(normalize(original["name"]))
    disliked = disliked_tokens or set()
    original_tokens = food_tokens(original["name"])
    preferred = [normalize(n) for n in HEALTHY_SUBSTITUTES_BY_GROUP.get(original["group"], [])]

    results = []
    for food in candidate_pool(original["group"], meal_key):
        norm = normalize(food["name"])
        tok = food_tokens(food["name"])
        if norm in exclude or tok & disliked:
            continue
        # Evita "trocar" arroz integral por arroz: precisa ser outro alimento de verdade.
        if tok and tok <= original_tokens:
            continue
        original_styles = _carb_styles(original["name"])
        if original_styles and not (_carb_styles(food["name"]) & original_styles):
            continue
        result = evaluate(original, original_grams, food, allow_complement="azeite" not in disliked)
        if not result["ok"]:
            continue
        penalty = 0.0 if food.get("category") == original.get("category") else 0.05
        penalty += 0.01 * (preferred.index(norm) if norm in preferred else len(preferred))
        result["rank"] = result["error"] + penalty
        results.append(result)

    results.sort(key=lambda item: item["rank"])
    # Diversifica: no máximo um item por "família" (ex.: dois tipos de frango).
    chosen, families = [], set()
    for item in results:
        item_tokens = food_tokens(item["food"])
        family = next((fam for fam in FAMILIES if fam in item_tokens), item["food"])
        if family in families:
            continue
        families.add(family)
        chosen.append(item)
        if len(chosen) >= limit:
            break
    return chosen
