from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import date, datetime


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(nutritionist|patient)$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: str
    name: str
    created_at: datetime


# ---------- Pacientes ----------
class PatientCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    age: int | None = None
    goal: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    nutritionist_id: int
    goal: str | None
    since: date
    bonus_xp: int
    name: str
    email: EmailStr


# ---------- Dietas ----------
class DietItemIn(BaseModel):
    food: str = Field(min_length=1, max_length=160)
    qty: str = Field(min_length=1, max_length=80)


class DietItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    meal_key: str
    food: str
    qty: str
    position: int
    kcal: float | None = None


class MealConfigIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    time: str = Field(default="", max_length=20)


class MealConfigOut(BaseModel):
    label: str
    time: str = ""


class MealNutritionOut(BaseModel):
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    matched_items: int
    total_items: int
    complete: bool


class DietOut(BaseModel):
    patient_id: int
    meals: dict[str, list[DietItemOut]]
    today_meals: dict[str, list[DietItemOut]]
    meal_configs: dict[str, MealConfigOut] = {}
    meal_nutrition: dict[str, MealNutritionOut] = {}
    today_meal_nutrition: dict[str, MealNutritionOut] = {}


# ---------- Check-ins ----------
class CheckinIn(BaseModel):
    meal_key: str
    followed: bool


# ---------- Métricas ----------
class MetricsOut(BaseModel):
    weekly_adherence: int
    streak: int
    level: int
    xp: int
    mood: str