import json
import re
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import DietItem, DietOverride, Food, MEAL_KEYS, MealConfig, Patient
from .nutrition_catalog import find_healthy_substitutes, find_nutribr_food
from .substitution_engine import normalize


GRAM_QUANTITY = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramas?)\s*$", re.IGNORECASE)
NUTRIENT_FIELDS = ("kcal", "protein", "carbs", "fat")
MEAL_DEFAULTS = {
    "cafe": ("Café da manhã", ""),
    "lanche1": ("Lanche da manhã", ""),
    "almoco": ("Almoço", ""),
    "lanche2": ("Lanche da tarde", ""),
    "jantar": ("Jantar", ""),
    "pre_treino": ("Pré-treino", ""),
    "pos_treino": ("Pós-treino", ""),
    "pre_atividade": ("Pré-atividade física", ""),
    "pos_atividade": ("Pós-atividade física", ""),
}
MEAL_SCHEDULE = {
    key: f"{label} ({time})" if time else label for key, (label, time) in MEAL_DEFAULTS.items()
}


def _item_data(food: str, qty: str) -> dict[str, str] | None:
    if not isinstance(food, str) or not isinstance(qty, str):
        return None
    clean_food = food.strip()
    clean_qty = qty.strip()
    if not clean_food or not clean_qty:
        return None
    return {"food": clean_food, "qty": clean_qty}


def build_diet_context(db: Session, patient: Patient, today: date) -> str:
    context = build_diet_context_data(db, patient, today)
    context.pop("food_values", None)
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def build_diet_context_data(db: Session, patient: Patient, today: date) -> dict:
    base_items = db.scalars(
        select(DietItem)
        .where(DietItem.patient_id == patient.id)
        .order_by(DietItem.meal_key, DietItem.position)
    ).all()
    overrides = db.scalars(
        select(DietOverride).where(
            DietOverride.patient_id == patient.id,
            DietOverride.ref_date == today,
        )
    ).all()

    permanent_plan = {meal_key: [] for meal_key in MEAL_KEYS}
    for item in base_items:
        permanent_plan[item.meal_key].append({"food": item.food, "qty": item.qty})

    today_plan = {meal_key: list(items) for meal_key, items in permanent_plan.items()}
    for override in overrides:
        today_plan[override.meal_key] = [
            item for raw_item in override.items_json
            if isinstance(raw_item, dict)
            and (item := _item_data(raw_item.get("food"), raw_item.get("qty"))) is not None
        ]

    food_names = {
        item["food"].casefold()
        for meal_items in today_plan.values()
        for item in meal_items
    }
    food_rows = db.scalars(
        select(Food).where(func.lower(Food.name).in_(food_names))
    ).all() if food_names else []
    foods_by_name = {food.name.casefold(): food for food in food_rows}

    nutrition_by_meal = {}
    for meal_key in MEAL_KEYS:
        totals = {field: 0.0 for field in NUTRIENT_FIELDS}
        covered = 0
        sources = set()
        for item in today_plan[meal_key]:
            match = GRAM_QUANTITY.fullmatch(item["qty"])
            if not match:
                continue

            food = foods_by_name.get(item["food"].casefold())
            if food and (food.source or "").upper() == "TACO":
                values = [getattr(food, field) for field in NUTRIENT_FIELDS]
                source = food.source
            elif food:
                continue
            else:
                catalog_food = find_nutribr_food(item["food"])
                if not catalog_food:
                    continue
                values = [
                    catalog_food["kcal"],
                    catalog_food["protein_g"],
                    catalog_food["carbs_g"],
                    catalog_food["fat_g"],
                ]
                source = catalog_food["source"]

            if any(value is None for value in values):
                continue

            factor = float(match.group(1).replace(",", ".")) / 100
            for field, value in zip(NUTRIENT_FIELDS, values):
                totals[field] += float(value) * factor
            covered += 1
            sources.add(source)

        nutrition_by_meal[meal_key] = {
            "totals_for_matched_items": {
                "kcal": round(totals["kcal"], 1),
                "protein_g": round(totals["protein"], 1),
                "carbohydrates_g": round(totals["carbs"], 1),
                "fat_g": round(totals["fat"], 1),
            } if covered else None,
            "matched_items": covered,
            "total_items": len(today_plan[meal_key]),
            "complete_meal_total": bool(today_plan[meal_key]) and covered == len(today_plan[meal_key]),
            "micronutrients_available": False,
            "sources": sorted(sources),
            "source": "Values per 100 g; exact food-name match and gram quantity only",
        }

    configs = db.scalars(
        select(MealConfig).where(MealConfig.patient_id == patient.id)
    ).all()
    meal_schedule = dict(MEAL_SCHEDULE)
    for cfg in configs:
        meal_schedule[cfg.meal_key] = (
            f"{cfg.custom_label} ({cfg.custom_time})" if cfg.custom_time else cfg.custom_label
        )

    substitution_hints = {}
    for meal_key in MEAL_KEYS:
        for item in today_plan[meal_key]:
            match = GRAM_QUANTITY.fullmatch(item["qty"])
            grams = float(match.group(1).replace(",", ".")) if match else None
            subs = find_healthy_substitutes(item["food"], grams=grams, limit=4)
            if subs:
                substitution_hints[item["food"]] = subs

    # Valores TACO cadastrados no banco, usados pelo motor de substituições.
    food_values = {
        normalize(food.name): {
            "name": food.name,
            "kcal": float(food.kcal),
            "protein_g": float(food.protein),
            "carbs_g": float(food.carbs),
            "fat_g": float(food.fat),
        }
        for food in food_rows
        if (food.source or "").upper() == "TACO"
        and None not in (food.kcal, food.protein, food.carbs, food.fat)
    }

    return {
        "date": today.isoformat(),
        "local_time": datetime.now().astimezone().isoformat(timespec="minutes"),
        "meal_schedule": meal_schedule,
        "patient_goal_from_nutritionist": patient.goal,
        "permanent_plan_reference_only": permanent_plan,
        "effective_plan_for_today": today_plan,
        "estimated_macros_for_today": nutrition_by_meal,
        "healthy_substitution_candidates": substitution_hints,
        "nutrient_data_limits": (
            "Food table TACO records and nutribr 0.1.0 provide kcal, protein, carbohydrates and fat "
            "per 100 g. Estimates are included only for exact food-name matches with gram quantities. "
            "The nutribr package contains only five food records and no micronutrient data; never infer "
            "or invent missing values. Missing meal totals mean data is unavailable or partial."
        ),
        "food_values": food_values,
    }
