import unicodedata
from functools import lru_cache

from nutribr import TabelaNutricional

# Expanded Brazilian food reference table (values per 100 g, based on TACO/TBCA).
# Each entry includes a nutritional group so healthy, nutrient-similar substitutes can be suggested.
TACO_EXPANDED_FOODS: list[dict] = [
    # Cereais, pães e tubérculos (carboidratos)
    {"name": "Arroz integral", "category": "Cereais e derivados", "group": "carb", "kcal": 124.0, "protein_g": 2.6, "carbs_g": 25.8, "fat_g": 1.0},
    {"name": "Arroz branco cozido", "category": "Cereais e derivados", "group": "carb", "kcal": 128.0, "protein_g": 2.5, "carbs_g": 28.1, "fat_g": 0.2},
    {"name": "Arroz parboilizado cozido", "category": "Cereais e derivados", "group": "carb", "kcal": 123.0, "protein_g": 2.5, "carbs_g": 26.2, "fat_g": 0.3},
    {"name": "Aveia em flocos", "category": "Cereais e derivados", "group": "carb", "kcal": 394.0, "protein_g": 13.9, "carbs_g": 66.6, "fat_g": 8.5},
    {"name": "Cuscuz de milho cozido", "category": "Cereais e derivados", "group": "carb", "kcal": 113.0, "protein_g": 2.2, "carbs_g": 25.3, "fat_g": 0.4},
    {"name": "Tapioca (goma hidratada)", "category": "Cereais e derivados", "group": "carb", "kcal": 240.0, "protein_g": 0.2, "carbs_g": 59.6, "fat_g": 0.0},
    {"name": "Pão francês", "category": "Pães e massas", "group": "carb", "kcal": 300.0, "protein_g": 8.0, "carbs_g": 58.6, "fat_g": 3.1},
    {"name": "Pão de forma integral", "category": "Pães e massas", "group": "carb", "kcal": 253.0, "protein_g": 9.4, "carbs_g": 49.9, "fat_g": 3.7},
    {"name": "Macarrão cozido", "category": "Pães e massas", "group": "carb", "kcal": 125.0, "protein_g": 3.4, "carbs_g": 26.3, "fat_g": 0.5},
    {"name": "Macarrão integral cozido", "category": "Pães e massas", "group": "carb", "kcal": 124.0, "protein_g": 4.5, "carbs_g": 25.5, "fat_g": 0.9},
    {"name": "Quinoa cozida", "category": "Cereais e derivados", "group": "carb", "kcal": 120.0, "protein_g": 4.4, "carbs_g": 21.3, "fat_g": 1.9},
    {"name": "Batata-doce cozida", "category": "Tubérculos e raízes", "group": "carb", "kcal": 77.0, "protein_g": 0.6, "carbs_g": 18.4, "fat_g": 0.1},
    {"name": "Batata inglesa cozida", "category": "Tubérculos e raízes", "group": "carb", "kcal": 52.0, "protein_g": 1.2, "carbs_g": 11.9, "fat_g": 0.0},
    {"name": "Mandioca cozida", "category": "Tubérculos e raízes", "group": "carb", "kcal": 125.0, "protein_g": 0.6, "carbs_g": 30.1, "fat_g": 0.3},

    # Leguminosas
    {"name": "Feijão carioca cozido", "category": "Leguminosas", "group": "legume", "kcal": 76.0, "protein_g": 4.8, "carbs_g": 13.6, "fat_g": 0.5},
    {"name": "Feijão preto cozido", "category": "Leguminosas", "group": "legume", "kcal": 77.0, "protein_g": 4.5, "carbs_g": 14.0, "fat_g": 0.5},
    {"name": "Lentilha cozida", "category": "Leguminosas", "group": "legume", "kcal": 93.0, "protein_g": 6.3, "carbs_g": 16.3, "fat_g": 0.5},
    {"name": "Grão-de-bico cozido", "category": "Leguminosas", "group": "legume", "kcal": 164.0, "protein_g": 8.9, "carbs_g": 27.4, "fat_g": 2.6},
    {"name": "Homus (pasta de grão-de-bico)", "category": "Leguminosas", "group": "dairy_cheese", "kcal": 166.0, "protein_g": 7.9, "carbs_g": 14.3, "fat_g": 9.6},

    # Carnes, aves, peixes e ovos (proteínas principais)
    {"name": "Peito de frango grelhado", "category": "Carnes e aves", "group": "protein", "kcal": 159.0, "protein_g": 32.0, "carbs_g": 0.0, "fat_g": 2.5},
    {"name": "Frango desfiado cozido", "category": "Carnes e aves", "group": "protein", "kcal": 163.0, "protein_g": 31.5, "carbs_g": 0.0, "fat_g": 3.2},
    {"name": "Patinho moído cozido", "category": "Carnes e aves", "group": "protein", "kcal": 219.0, "protein_g": 35.9, "carbs_g": 0.0, "fat_g": 7.3},
    {"name": "Alcatra grelhada", "category": "Carnes e aves", "group": "protein", "kcal": 241.0, "protein_g": 31.9, "carbs_g": 0.0, "fat_g": 11.6},
    {"name": "Tilápia grelhada", "category": "Pescados", "group": "protein", "kcal": 128.0, "protein_g": 26.2, "carbs_g": 0.0, "fat_g": 2.7},
    {"name": "Salmão grelhado", "category": "Pescados", "group": "protein", "kcal": 243.0, "protein_g": 26.1, "carbs_g": 0.0, "fat_g": 14.5},
    {"name": "Atum em água escorrido", "category": "Pescados", "group": "protein", "kcal": 116.0, "protein_g": 25.5, "carbs_g": 0.0, "fat_g": 0.8},
    {"name": "Ovo cozido", "category": "Ovos", "group": "protein", "kcal": 146.0, "protein_g": 13.3, "carbs_g": 0.6, "fat_g": 9.5},
    {"name": "Ovo mexido", "category": "Ovos", "group": "protein", "kcal": 148.0, "protein_g": 10.0, "carbs_g": 1.6, "fat_g": 11.0},
    {"name": "Clara de ovo cozida", "category": "Ovos", "group": "protein", "kcal": 52.0, "protein_g": 10.9, "carbs_g": 0.7, "fat_g": 0.2},
    {"name": "Tofu firme", "category": "Proteína vegetal", "group": "protein", "kcal": 76.0, "protein_g": 8.1, "carbs_g": 1.9, "fat_g": 4.8},

    # Laticínios e queijos (recheios / fontes lácteas)
    {"name": "Queijo minas frescal", "category": "Laticínios", "group": "dairy_cheese", "kcal": 264.0, "protein_g": 17.4, "carbs_g": 3.2, "fat_g": 20.2},
    {"name": "Queijo cottage", "category": "Laticínios", "group": "dairy_cheese", "kcal": 98.0, "protein_g": 11.1, "carbs_g": 3.4, "fat_g": 4.3},
    {"name": "Ricota fresca", "category": "Laticínios", "group": "dairy_cheese", "kcal": 140.0, "protein_g": 12.6, "carbs_g": 3.8, "fat_g": 8.1},
    {"name": "Queijo mussarela", "category": "Laticínios", "group": "dairy_cheese", "kcal": 330.0, "protein_g": 22.6, "carbs_g": 3.0, "fat_g": 25.2},
    {"name": "Requeijão light", "category": "Laticínios", "group": "dairy_cheese", "kcal": 178.0, "protein_g": 10.5, "carbs_g": 3.5, "fat_g": 13.5},
    {"name": "Iogurte natural desnatado", "category": "Laticínios", "group": "dairy_drink", "kcal": 41.0, "protein_g": 3.8, "carbs_g": 5.8, "fat_g": 0.2},
    {"name": "Iogurte natural integral", "category": "Laticínios", "group": "dairy_drink", "kcal": 51.0, "protein_g": 4.1, "carbs_g": 1.9, "fat_g": 3.0},
    {"name": "Leite desnatado", "category": "Laticínios", "group": "dairy_drink", "kcal": 35.0, "protein_g": 3.4, "carbs_g": 4.9, "fat_g": 0.1},
    {"name": "Leite semidesnatado", "category": "Laticínios", "group": "dairy_drink", "kcal": 47.0, "protein_g": 3.3, "carbs_g": 4.8, "fat_g": 1.6},
    {"name": "Whey protein concentrado", "category": "Suplementos", "group": "protein", "kcal": 395.0, "protein_g": 78.0, "carbs_g": 8.0, "fat_g": 5.5},

    # Frutas
    {"name": "Banana prata", "category": "Frutas", "group": "fruit", "kcal": 98.0, "protein_g": 1.3, "carbs_g": 26.0, "fat_g": 0.1},
    {"name": "Banana nanica", "category": "Frutas", "group": "fruit", "kcal": 92.0, "protein_g": 1.4, "carbs_g": 23.8, "fat_g": 0.1},
    {"name": "Mamão papaia", "category": "Frutas", "group": "fruit", "kcal": 40.0, "protein_g": 0.5, "carbs_g": 10.4, "fat_g": 0.1},
    {"name": "Morango", "category": "Frutas", "group": "fruit", "kcal": 30.0, "protein_g": 0.9, "carbs_g": 6.8, "fat_g": 0.3},
    {"name": "Laranja pera", "category": "Frutas", "group": "fruit", "kcal": 37.0, "protein_g": 1.0, "carbs_g": 8.9, "fat_g": 0.1},
    {"name": "Melancia", "category": "Frutas", "group": "fruit", "kcal": 33.0, "protein_g": 0.9, "carbs_g": 8.1, "fat_g": 0.0},
    {"name": "Pera", "category": "Frutas", "group": "fruit", "kcal": 53.0, "protein_g": 0.6, "carbs_g": 14.0, "fat_g": 0.1},
    {"name": "Uva Itália", "category": "Frutas", "group": "fruit", "kcal": 53.0, "protein_g": 0.7, "carbs_g": 13.6, "fat_g": 0.2},

    # Gorduras boas e oleaginosas
    {"name": "Abacate", "category": "Frutas e gorduras boas", "group": "fat", "kcal": 96.0, "protein_g": 1.2, "carbs_g": 6.0, "fat_g": 8.4},
    {"name": "Azeite de oliva", "category": "Óleos e gorduras", "group": "fat", "kcal": 884.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0},
    {"name": "Pasta de amendoim integral", "category": "Oleaginosas", "group": "fat", "kcal": 588.0, "protein_g": 25.0, "carbs_g": 20.0, "fat_g": 50.0},
    {"name": "Castanha-do-pará", "category": "Oleaginosas", "group": "fat", "kcal": 643.0, "protein_g": 14.5, "carbs_g": 15.1, "fat_g": 63.5},

    # Verduras e legumes
    {"name": "Alface crespa", "category": "Verduras e legumes", "group": "vegetable", "kcal": 11.0, "protein_g": 1.3, "carbs_g": 1.7, "fat_g": 0.2},
    {"name": "Tomate", "category": "Verduras e legumes", "group": "vegetable", "kcal": 15.0, "protein_g": 1.1, "carbs_g": 3.1, "fat_g": 0.2},
    {"name": "Brócolis cozido", "category": "Verduras e legumes", "group": "vegetable", "kcal": 25.0, "protein_g": 2.1, "carbs_g": 4.4, "fat_g": 0.5},
    {"name": "Cenoura cozida", "category": "Verduras e legumes", "group": "vegetable", "kcal": 30.0, "protein_g": 0.8, "carbs_g": 6.7, "fat_g": 0.2},
    {"name": "Abobrinha cozida", "category": "Verduras e legumes", "group": "vegetable", "kcal": 15.0, "protein_g": 1.1, "carbs_g": 3.0, "fat_g": 0.2},
]

# Preferred healthy substitutes per nutritional group (ordered from healthiest/most practical)
HEALTHY_SUBSTITUTES_BY_GROUP: dict[str, list[str]] = {
    "dairy_cheese": [
        "Queijo cottage",
        "Ricota fresca",
        "Queijo minas frescal",
        "Ovo mexido",
        "Frango desfiado cozido",
        "Homus (pasta de grão-de-bico)",
    ],
    "protein": [
        "Peito de frango grelhado",
        "Tilápia grelhada",
        "Patinho moído cozido",
        "Ovo cozido",
        "Atum em água escorrido",
        "Tofu firme",
    ],
    "carb": [
        "Arroz integral",
        "Batata-doce cozida",
        "Mandioca cozida",
        "Cuscuz de milho cozido",
        "Pão de forma integral",
        "Aveia em flocos",
    ],
    "legume": [
        "Feijão carioca cozido",
        "Feijão preto cozido",
        "Lentilha cozida",
        "Grão-de-bico cozido",
    ],
    "dairy_drink": [
        "Iogurte natural desnatado",
        "Iogurte natural integral",
        "Leite desnatado",
        "Leite semidesnatado",
    ],
    "fruit": [
        "Banana prata",
        "Maçã",
        "Mamão papaia",
        "Morango",
        "Pera",
    ],
    "fat": [
        "Abacate",
        "Pasta de amendoim integral",
        "Castanha-do-pará",
        "Azeite de oliva",
    ],
    "vegetable": [
        "Brócolis cozido",
        "Abobrinha cozida",
        "Cenoura cozida",
        "Alface crespa",
        "Tomate",
    ],
}

GROUP_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("queijo", "mussarela", "ricota", "cottage", "requeijao", "creme de ricota", "minas"), "dairy_cheese"),
    (("frango", "carne", "patinho", "alcatra", "peixe", "tilapia", "salmao", "atum", "ovo", "clara", "tofu", "whey"), "protein"),
    (("arroz", "pao", "tapioca", "aveia", "cuscuz", "macarrao", "batata", "mandioca", "quinoa"), "carb"),
    (("feijao", "lentilha", "grao-de-bico", "grao de bico"), "legume"),
    (("iogurte", "leite"), "dairy_drink"),
    (("banana", "maca", "mamao", "morango", "laranja", "melancia", "pera", "uva"), "fruit"),
    (("abacate", "azeite", "pasta de amendoim", "castanha", "amendoim"), "fat"),
    (("alface", "tomate", "brocolis", "cenoura", "abobrinha", "salada"), "vegetable"),
]


@lru_cache(maxsize=1)
def _table() -> TabelaNutricional:
    return TabelaNutricional()


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold().strip()


@lru_cache(maxsize=1)
def _expanded_by_norm() -> dict[str, dict]:
    return {
        _normalize(entry["name"]): {
            "name": entry["name"],
            "category": entry["category"],
            "group": entry["group"],
            "kcal": float(entry["kcal"]),
            "protein_g": float(entry["protein_g"]),
            "carbs_g": float(entry["carbs_g"]),
            "fat_g": float(entry["fat_g"]),
            "source": "TACO",
            "micronutrients_available": False,
        }
        for entry in TACO_EXPANDED_FOODS
    }


def find_nutribr_food(name: str) -> dict | None:
    normalized_name = _normalize(name)
    for candidate in _table().listar_alimentos():
        if _normalize(candidate) != normalized_name:
            continue
        food = _table().buscar_por_nome(candidate)
        if food is None:
            continue
        return {
            "name": food.nome,
            "category": food.categoria,
            "kcal": float(food.energia_kcal),
            "protein_g": float(food.proteina_g),
            "carbs_g": float(food.carboidrato_g),
            "fat_g": float(food.lipideos_g),
            "source": "nutribr/TACO",
            "micronutrients_available": False,
        }

    return _expanded_by_norm().get(normalized_name)


def search_nutribr_foods(query: str, limit: int = 12) -> list[dict]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return []

    results: list[dict] = []
    seen_norms: set[str] = set()

    for name in _table().listar_alimentos():
        norm = _normalize(name)
        if normalized_query in norm and norm not in seen_norms:
            food = find_nutribr_food(name)
            if food is not None:
                results.append(food)
                seen_norms.add(norm)
                if len(results) >= limit:
                    return results

    for norm, food in _expanded_by_norm().items():
        if normalized_query in norm and norm not in seen_norms:
            results.append(food)
            seen_norms.add(norm)
            if len(results) >= limit:
                break

    return results


def infer_food_group(food_name: str) -> str | None:
    norm = _normalize(food_name)
    entry = _expanded_by_norm().get(norm)
    if entry:
        return entry["group"]
    for keywords, group in GROUP_KEYWORDS:
        if any(kw in norm for kw in keywords):
            return group
    return None


def find_healthy_substitutes(food_name: str, grams: float | None = None, limit: int = 4) -> list[dict]:
    group = infer_food_group(food_name)
    if not group:
        return []

    target_food = find_nutribr_food(food_name)
    norm_source = _normalize(food_name)
    candidates = []

    for candidate_name in HEALTHY_SUBSTITUTES_BY_GROUP.get(group, []):
        if _normalize(candidate_name) == norm_source:
            continue
        candidate = find_nutribr_food(candidate_name)
        if not candidate:
            continue

        suggested_grams = None
        if grams and grams > 0 and target_food:
            # Match protein for protein/dairy groups, or kcal for other groups.
            if group in ("protein", "dairy_cheese") and target_food["protein_g"] > 0 and candidate["protein_g"] > 0:
                target_protein = target_food["protein_g"] * (grams / 100.0)
                suggested_grams = round((target_protein / candidate["protein_g"]) * 100.0)
            elif target_food["kcal"] > 0 and candidate["kcal"] > 0:
                target_kcal = target_food["kcal"] * (grams / 100.0)
                suggested_grams = round((target_kcal / candidate["kcal"]) * 100.0)
            if suggested_grams is not None:
                suggested_grams = max(15, min(suggested_grams, 400))

        candidates.append({
            "name": candidate["name"],
            "kcal_per_100g": candidate["kcal"],
            "protein_per_100g": candidate["protein_g"],
            "carbs_per_100g": candidate["carbs_g"],
            "fat_per_100g": candidate["fat_g"],
            "suggested_qty": f"{suggested_grams} g" if suggested_grams else None,
        })
        if len(candidates) >= limit:
            break

    return candidates
