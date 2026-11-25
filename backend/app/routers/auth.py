from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..deps import get_db, get_current_user
from ..models import User, Patient
from ..schemas import RegisterIn, TokenOut, UserOut
from ..security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        name=payload.name,
    )
    db.add(user)
    db.flush()

    if payload.role == "patient":
        # Sem nutricionista vinculado ainda: usamos o próprio user_id como placeholder
        # (o vínculo real será feito depois via endpoint do nutricionista)
        db.add(Patient(user_id=user.id, nutritionist_id=user.id, goal=None))

    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenOut(access_token=token, role=user.role, user_id=user.id, name=user.name)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenOut(access_token=token, role=user.role, user_id=user.id, name=user.name)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current