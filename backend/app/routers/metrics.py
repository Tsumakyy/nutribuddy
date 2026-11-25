from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..deps import get_db, get_current_user
from ..models import User, Patient, Checkin, MEAL_KEYS
from ..schemas import MetricsOut

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/{patient_id}", response_model=MetricsOut)
def get_metrics(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
        
    if current_user.role == "nutritionist" and patient.nutritionist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if current_user.role == "patient" and patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    today = date.today()
    last_7_days = [today - timedelta(days=i) for i in range(7)]
    
    # Puxa todos os checkins dos últimos 7 dias
    checkins = db.scalars(
        select(Checkin).where(
            Checkin.patient_id == patient.id,
            Checkin.ref_date >= last_7_days[-1]
        )
    ).all()

    # --- 1. Weekly Adherence ---
    # Seguidos / (7 dias * 5 refeições)
    followed_count = sum(1 for c in checkins if c.followed)
    weekly_adherence = round((followed_count / (7 * len(MEAL_KEYS))) * 100)

    # --- 2. Streak (dias seguidos) ---
    # Agrupa checkins por dia
    days_with_checkin = {c.ref_date for c in checkins if c.followed}
    streak = 0
    current_check_date = today
    # Se hoje não tem checkin, começamos a contar de ontem
    if today not in days_with_checkin:
        current_check_date = today - timedelta(days=1)
    
    while current_check_date in days_with_checkin:
        streak += 1
        current_check_date -= timedelta(days=1)

    # --- 3. XP e Nível ---
    # XP = 10 por checkin seguido + bonus (que vem do banco)
    total_xp = (followed_count * 10) + patient.bonus_xp
    level = (total_xp // 100) + 1

    # --- 4. Humor ---
    # Pega os checkins de hoje
    today_checkins = [c for c in checkins if c.ref_date == today]
    if not today_checkins:
        mood = "fome"
    else:
        # Quantos seguidos dos que ele respondeu hoje
        answered = len(today_checkins)
        followed_today = sum(1 for c in today_checkins if c.followed)
        partial_pct = round((followed_today / answered) * 100) if answered > 0 else 0
        
        if partial_pct >= 80:
            mood = "feliz"
        elif partial_pct >= 40:
            mood = "tranquilo"
        else:
            mood = "tranquilo"

    return MetricsOut(
        weekly_adherence=weekly_adherence,
        streak=streak,
        level=level,
        xp=total_xp,
        mood=mood
    )