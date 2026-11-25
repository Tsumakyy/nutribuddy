from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from ..deps import get_db, require_role, get_current_user
from ..models import User, Patient, BuddyMessage
from ..schemas import PatientCreateIn, PatientOut
from ..security import hash_password

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/me", response_model=PatientOut)
def get_my_patient(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Acesso restrito a pacientes")

    patient = db.scalar(select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        raise HTTPException(status_code=404, detail="Perfil de paciente não encontrado")

    return PatientOut(
        id=patient.id, user_id=patient.user_id, nutritionist_id=patient.nutritionist_id,
        goal=patient.goal, since=patient.since, bonus_xp=patient.bonus_xp,
        name=current_user.name, email=current_user.email
    )

@router.get("", response_model=List[PatientOut])
def list_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nutritionist"))
):
    # Puxa os pacientes onde o nutricionista logado é o responsável
    patients = db.scalars(
        select(Patient).where(Patient.nutritionist_id == current_user.id)
    ).all()
    
    # Monta o retorno juntando com os dados do User
    result = []
    for p in patients:
        u = db.get(User, p.user_id)
        result.append(PatientOut(
            id=p.id, user_id=p.user_id, nutritionist_id=p.nutritionist_id,
            goal=p.goal, since=p.since, bonus_xp=p.bonus_xp,
            name=u.name, email=u.email
        ))
    return result

@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nutritionist"))
):
    # Verifica se email já existe
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    # Cria o User do paciente
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="patient",
        name=payload.name,
    )
    db.add(user)
    db.flush()

    # Cria o perfil de paciente vinculado ao nutricionista logado
    patient = Patient(
        user_id=user.id,
        nutritionist_id=current_user.id,
        goal=payload.goal,
        birth_date=None
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return PatientOut(
        id=patient.id, user_id=patient.user_id, nutritionist_id=patient.nutritionist_id,
        goal=patient.goal, since=patient.since, bonus_xp=patient.bonus_xp,
        name=user.name, email=user.email
    )

@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nutritionist"))
):
    patient = db.get(Patient, patient_id)
    if not patient or patient.nutritionist_id != current_user.id:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    user = db.get(User, patient.user_id)
    return PatientOut(
        id=patient.id, user_id=patient.user_id, nutritionist_id=patient.nutritionist_id,
        goal=patient.goal, since=patient.since, bonus_xp=patient.bonus_xp,
        name=user.name, email=user.email
    )

@router.get("/{patient_id}/buddy/requests")
def list_buddy_requests(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("nutritionist"))
):
    patient = db.get(Patient, patient_id)
    if not patient or patient.nutritionist_id != current_user.id:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    messages = db.scalars(
        select(BuddyMessage)
        .where(BuddyMessage.patient_id == patient.id)
        .order_by(BuddyMessage.created_at.desc(), BuddyMessage.id.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": message.id,
            "message": message.content,
            "created_at": message.created_at,
        }
        for message in messages
        if (message.payload or {}).get("needs_nutritionist")
    ]