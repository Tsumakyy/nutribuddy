from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import select

from ..deps import get_db, require_role
from ..models import User, Patient, Checkin, MEAL_KEYS
from ..schemas import CheckinIn

router = APIRouter(prefix="/checkins", tags=["checkins"])

@router.get("/today")
def get_today_checkins(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient"))
):
    patient = db.scalar(select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente não encontrado")

    rows = db.scalars(
        select(Checkin).where(Checkin.patient_id == patient.id, Checkin.ref_date == date.today())
    ).all()
    return {row.meal_key: row.followed for row in rows}

@router.post("", status_code=status.HTTP_200_OK)
def do_checkin(
    payload: CheckinIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient"))
):
    if payload.meal_key not in MEAL_KEYS:
        raise HTTPException(status_code=400, detail="Refeição inválida")

    patient = db.scalar(select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente não encontrado")

    today = date.today()

    checkin = db.scalar(select(Checkin).where(
        Checkin.patient_id == patient.id,
        Checkin.ref_date == today,
        Checkin.meal_key == payload.meal_key,
    ))
    if checkin:
        checkin.followed = payload.followed
    else:
        db.add(Checkin(
            patient_id=patient.id,
            ref_date=today,
            meal_key=payload.meal_key,
            followed=payload.followed,
        ))
    db.commit()
    
    return {"status": "ok", "meal": payload.meal_key, "followed": payload.followed}