from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date
from pydantic import BaseModel, Field

from ..deps import get_db, require_role
from ..models import User, Patient, BuddyMessage, DietOverride, MEAL_KEYS
from ..services import buddy_brain, ollama_service
from ..services.diet_context import build_diet_context_data

router = APIRouter(prefix="/buddy", tags=["buddy"])

class BuddyMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)



def _apply_today_changes(db: Session, patient_id: int, today: date, changes: list[dict]) -> bool:
    for change in changes:
        if change["meal_key"] not in MEAL_KEYS:
            raise HTTPException(status_code=502, detail="O Buddy retornou uma refeição inválida")
        daily_override = db.scalar(select(DietOverride).where(
            DietOverride.patient_id == patient_id,
            DietOverride.ref_date == today,
            DietOverride.meal_key == change["meal_key"],
        ))
        if daily_override:
            daily_override.items_json = change["items"]
        else:
            db.add(DietOverride(
                patient_id=patient_id,
                ref_date=today,
                meal_key=change["meal_key"],
                items_json=change["items"],
            ))
    return bool(changes)


@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient"))
):
    patient = db.scalar(select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    messages = db.scalars(
        select(BuddyMessage)
        .where(BuddyMessage.patient_id == patient.id, BuddyMessage.ref_date == date.today())
        .order_by(BuddyMessage.created_at, BuddyMessage.id)
    ).all()
    return [
        {
            "id": message.id,
            "from": "user" if message.sender == "patient" else "buddy",
            "text": message.content,
            "needs_nutritionist": (message.payload or {}).get("needs_nutritionist", False),
            "ai_unavailable": (message.payload or {}).get("ai_unavailable", False),
            "quick_replies": (message.payload or {}).get("quick_replies", []),
        }
        for message in messages
    ]

@router.post("/chat")
def chat(
    payload: BuddyMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient"))
):
    patient = db.scalar(select(Patient).where(Patient.user_id == current_user.id))
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    today = date.today()

    historico_db = db.scalars(
        select(BuddyMessage)
        .where(BuddyMessage.patient_id == patient.id, BuddyMessage.ref_date == today)
        .order_by(BuddyMessage.created_at, BuddyMessage.id)
    ).all()

    history_formatted = []
    last_buddy_message = None
    for msg in historico_db:
        role = "user" if msg.sender == "patient" else "assistant"
        history_formatted.append({"role": role, "content": msg.content})
        if msg.sender == "buddy":
            last_buddy_message = msg

    db.add(BuddyMessage(
        patient_id=patient.id, ref_date=today, sender="patient", content=payload.content
    ))
    db.commit()

    # O estado da conversa (refeição, item, opções, proposta) fica na última resposta do Buddy.
    # Assim a confirmação aplica exatamente a proposta mostrada ao paciente.
    state = (last_buddy_message.payload or {}).get("buddy_state") if last_buddy_message else None
    context = build_diet_context_data(db, patient, today)
    response = buddy_brain.respond(
        payload.content,
        context,
        state,
        history_formatted,
        ollama_service.format_plan_for_llm(context),
    )

    # Uma troca confirmada vai só para o override do dia, nunca para DietItem.
    changes = response.get("day_changes", [])
    response["applied_today_only"] = _apply_today_changes(db, patient.id, today, changes)

    db.add(BuddyMessage(
        patient_id=patient.id, ref_date=today, sender="buddy",
        content=response.get("message", "")[:2000], payload=response
    ))
    db.commit()

    return response
