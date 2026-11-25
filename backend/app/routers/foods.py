from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..deps import get_current_user
from ..models import User
from ..services.nutrition_catalog import search_nutribr_foods


router = APIRouter(prefix="/foods", tags=["foods"])


class FoodSearchResult(BaseModel):
    name: str
    category: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    source: str
    micronutrients_available: bool


@router.get("/search", response_model=list[FoodSearchResult])
def search_foods(
    q: str = Query(min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Informe um alimento para pesquisar")
    return search_nutribr_foods(query)
