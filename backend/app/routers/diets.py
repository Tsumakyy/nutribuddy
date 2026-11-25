from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from datetime import date

from ..deps import get_db, get_current_user
from ..models import User, Patient, DietItem, DietOverride, Food, MealConfig, MEAL_KEYS
from ..schemas import (
    DietItemIn, DietItemOut, DietOut, MealConfigIn, MealConfigOut, MealNutritionOut,
)
from ..services.diet_context import GRAM_QUANTITY, MEAL_DEFAULTS, NUTRIENT_FIELDS
from ..services.nutrition_catalog import find_nutribr_food

router = APIRouter(prefix="/patients/{patient_id}/diet", tags=["diets"])


def _compute_meals_nutrition(
    db: Session,
    meals_map: dict[str, list[DietItemOut]],
) -> dict[str, MealNutritionOut]:
    food_names = {
        item.food.casefold()
        for meal_items in meals_map.values()
        for item in meal_items
    }
    food_rows = db.scalars(
        select(Food).where(func.lower(Food.name).in_(food_names))
    ).all() if food_names else []
    foods_by_name = {food.name.casefold(): food for food in food_rows}

    nutrition_by_meal: dict[str, MealNutritionOut] = {}
    for meal_key, meal_items in meals_map.items():
        totals = {field: 0.0 for field in NUTRIENT_FIELDS}
        matched = 0
        for item in meal_items:
            match = GRAM_QUANTITY.fullmatch(item.qty)
            if not match:
                continue
            food = foods_by_name.get(item.food.casefold())
            if food and (food.source or "").upper() == "TACO":
                values = [getattr(food, field) for field in NUTRIENT_FIELDS]
            else:
                catalog_food = find_nutribr_food(item.food)
                if not catalog_food:
                    continue
                values = [
                    catalog_food["kcal"],
                    catalog_food["protein_g"],
                    catalog_food["carbs_g"],
                    catalog_food["fat_g"],
                ]
            if any(v is None for v in values):
                continue
            factor = float(match.group(1).replace(",", ".")) / 100.0
            item.kcal = round(float(values[0]) * factor, 1)
            for field, value in zip(NUTRIENT_FIELDS, values):
                totals[field] += float(value) * factor
            matched += 1

        nutrition_by_meal[meal_key] = MealNutritionOut(
            kcal=round(totals["kcal"], 1),
            protein_g=round(totals["protein"], 1),
            carbs_g=round(totals["carbs"], 1),
            fat_g=round(totals["fat"], 1),
            matched_items=matched,
            total_items=len(meal_items),
            complete=bool(meal_items) and matched == len(meal_items),
        )
    return nutrition_by_meal

def get_patient_or_404(db: Session, patient_id: int, current_user: User) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    # Nutri pode ver a dieta do seu paciente. O paciente pode ver a própria.
    if current_user.role == "nutritionist" and patient.nutritionist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a este paciente")
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return patient

@router.get("", response_model=DietOut)
def get_diet(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = get_patient_or_404(db, patient_id, current_user)
    
    # Pega todos os itens e agrupa por refeição
    items = db.scalars(select(DietItem).where(DietItem.patient_id == patient.id).order_by(DietItem.meal_key, DietItem.position)).all()
    
    meals = {k: [] for k in MEAL_KEYS}
    for item in items:
        meals[item.meal_key].append(DietItemOut.model_validate(item))

    today_meals = {key: list(meal_items) for key, meal_items in meals.items()}
    overrides = db.scalars(
        select(DietOverride).where(
            DietOverride.patient_id == patient.id,
            DietOverride.ref_date == date.today(),
        )
    ).all()
    for override in overrides:
        today_meals[override.meal_key] = [
            DietItemOut(
                id=-(index + 1),
                meal_key=override.meal_key,
                food=item["food"],
                qty=item["qty"],
                position=index,
            )
            for index, item in enumerate(override.items_json)
        ]

    configs = db.scalars(select(MealConfig).where(MealConfig.patient_id == patient.id)).all()
    meal_configs = {
        key: MealConfigOut(label=MEAL_DEFAULTS[key][0], time=MEAL_DEFAULTS[key][1])
        for key in MEAL_KEYS
    }
    for cfg in configs:
        meal_configs[cfg.meal_key] = MealConfigOut(label=cfg.custom_label, time=cfg.custom_time)

    meal_nutrition = _compute_meals_nutrition(db, meals)
    today_meal_nutrition = _compute_meals_nutrition(db, today_meals)

    return DietOut(
        patient_id=patient.id,
        meals=meals,
        today_meals=today_meals,
        meal_configs=meal_configs,
        meal_nutrition=meal_nutrition,
        today_meal_nutrition=today_meal_nutrition,
    )


@router.put("/{meal_key}/config", response_model=MealConfigOut)
def update_meal_config(
    patient_id: int,
    meal_key: str,
    payload: MealConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "nutritionist":
        raise HTTPException(status_code=403, detail="Apenas nutricionistas podem configurar refeições")
    if meal_key not in MEAL_KEYS:
        raise HTTPException(status_code=400, detail="Refeição inválida")

    patient = get_patient_or_404(db, patient_id, current_user)
    cfg = db.scalar(
        select(MealConfig).where(MealConfig.patient_id == patient.id, MealConfig.meal_key == meal_key)
    )
    if cfg:
        cfg.custom_label = payload.label.strip()
        cfg.custom_time = payload.time.strip()
    else:
        cfg = MealConfig(
            patient_id=patient.id,
            meal_key=meal_key,
            custom_label=payload.label.strip(),
            custom_time=payload.time.strip(),
        )
        db.add(cfg)
    db.commit()
    return MealConfigOut(label=cfg.custom_label, time=cfg.custom_time)

@router.post("/{meal_key}", response_model=DietItemOut, status_code=status.HTTP_201_CREATED)
def add_diet_item(
    patient_id: int,
    meal_key: str,
    payload: DietItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "nutritionist":
        raise HTTPException(status_code=403, detail="Apenas nutricionistas podem editar a dieta")
    if meal_key not in MEAL_KEYS:
        raise HTTPException(status_code=400, detail="Refeição inválida")
        
    patient = get_patient_or_404(db, patient_id, current_user)
    
    # Conta os itens atuais para definir a posição
    count = len(db.scalars(select(DietItem).where(DietItem.patient_id == patient.id, DietItem.meal_key == meal_key)).all())
    
    item = DietItem(
        patient_id=patient.id,
        meal_key=meal_key,
        food=payload.food,
        qty=payload.qty,
        position=count
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{meal_key}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_diet_item(
    patient_id: int,
    meal_key: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "nutritionist":
        raise HTTPException(status_code=403, detail="Apenas nutricionistas podem editar a dieta")
        
    patient = get_patient_or_404(db, patient_id, current_user)
    
    item = db.get(DietItem, item_id)
    if not item or item.patient_id != patient.id or item.meal_key != meal_key:
        raise HTTPException(status_code=404, detail="Item não encontrado")
        
    db.delete(item)
    db.commit()