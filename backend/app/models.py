from datetime import date, datetime

from sqlalchemy import (
    BigInteger, String, Integer, Date, DateTime, Boolean, ForeignKey, Enum,
    UniqueConstraint, Index, JSON, DECIMAL, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

MEAL_KEYS = (
    "cafe",
    "lanche1",
    "almoco",
    "lanche2",
    "jantar",
    "pre_treino",
    "pos_treino",
    "pre_atividade",
    "pos_atividade",
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("nutritionist", "patient", name="user_role"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient_profile: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        foreign_keys="Patient.user_id",
    )


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    nutritionist_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    since: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    bonus_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="patient_profile")
    nutritionist: Mapped["User"] = relationship("User", foreign_keys=[nutritionist_id])

    diet_items: Mapped[list["DietItem"]] = relationship(
        "DietItem", back_populates="patient", cascade="all, delete-orphan"
    )
    overrides: Mapped[list["DietOverride"]] = relationship(
        "DietOverride", back_populates="patient", cascade="all, delete-orphan"
    )
    checkins: Mapped[list["Checkin"]] = relationship(
        "Checkin", back_populates="patient", cascade="all, delete-orphan"
    )
    messages: Mapped[list["BuddyMessage"]] = relationship(
        "BuddyMessage", back_populates="patient", cascade="all, delete-orphan"
    )
    meal_configs: Mapped[list["MealConfig"]] = relationship(
        "MealConfig", back_populates="patient", cascade="all, delete-orphan"
    )


class MealConfig(Base):
    __tablename__ = "meal_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    meal_key: Mapped[str] = mapped_column(Enum(*MEAL_KEYS, name="meal_key"), nullable=False)
    custom_label: Mapped[str] = mapped_column(String(80), nullable=False)
    custom_time: Mapped[str] = mapped_column(String(20), nullable=False)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="meal_configs")

    __table_args__ = (UniqueConstraint("patient_id", "meal_key", name="uq_meal_config"),)


class DietItem(Base):
    __tablename__ = "diet_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    meal_key: Mapped[str] = mapped_column(Enum(*MEAL_KEYS, name="meal_key"), nullable=False)
    food: Mapped[str] = mapped_column(String(160), nullable=False)
    qty: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="diet_items")

    __table_args__ = (Index("idx_diet_patient_meal", "patient_id", "meal_key"),)


class DietOverride(Base):
    __tablename__ = "diet_overrides"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    ref_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_key: Mapped[str] = mapped_column(Enum(*MEAL_KEYS, name="meal_key"), nullable=False)
    items_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="overrides")

    __table_args__ = (UniqueConstraint("patient_id", "ref_date", "meal_key", name="uq_override"),)


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    ref_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_key: Mapped[str] = mapped_column(Enum(*MEAL_KEYS, name="meal_key"), nullable=False)
    followed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="checkins")

    __table_args__ = (UniqueConstraint("patient_id", "ref_date", "meal_key", name="uq_checkin"),)


class BuddyMessage(Base):
    __tablename__ = "buddy_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    ref_date: Mapped[date] = mapped_column(Date, nullable=False)
    sender: Mapped[str] = mapped_column(Enum("buddy", "patient", name="msg_sender"), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped["Patient"] = relationship("Patient", back_populates="messages")

    __table_args__ = (Index("idx_msg_session", "patient_id", "ref_date"),)


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    kcal: Mapped[float | None] = mapped_column(DECIMAL(6, 1), nullable=True)
    protein: Mapped[float | None] = mapped_column(DECIMAL(5, 1), nullable=True)
    carbs: Mapped[float | None] = mapped_column(DECIMAL(5, 1), nullable=True)
    fat: Mapped[float | None] = mapped_column(DECIMAL(5, 1), nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="TACO")