import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.database import Base
from app.deps import get_current_user, get_db
from app.main import app
from app.models import BuddyMessage, DietItem, DietOverride, Patient, User


class BuddyRouteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.next_sqlite_id = 1
        event.listen(self.session, "before_flush", self._assign_sqlite_ids)
        self.patient_user = User(
            id=101,
            email="patient@example.test",
            password_hash="unused",
            role="patient",
            name="Paciente",
        )
        self.patient = Patient(
            id=201,
            user_id=self.patient_user.id,
            nutritionist_id=102,
            goal="Acompanhamento geral",
        )
        self.permanent_item = DietItem(
            id=301,
            patient_id=self.patient.id,
            meal_key="almoco",
            food="Frango",
            qty="120 g",
            position=0,
        )
        self.session.add_all([self.patient_user, self.patient, self.permanent_item])
        self.session.commit()

        def override_db():
            yield self.session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.patient_user
        self.client = TestClient(app)

    def _assign_sqlite_ids(self, session, flush_context, instances):
        for item in session.new:
            if isinstance(item, (BuddyMessage, DietOverride)) and item.id is None:
                item.id = self.next_sqlite_id
                self.next_sqlite_id += 1

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()

    def test_change_is_asked_first_then_applied_only_to_today_effective_diet(self):
        with patch("app.services.ollama_service.chat_reply", return_value=None):
            first = self.client.post("/buddy/chat", json={"content": "Posso trocar o frango por tilápia?"})
            second = self.client.post("/buddy/chat", json={"content": "Sim, pode aplicar hoje."})

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["awaiting_confirmation"])
        self.assertFalse(first.json()["applied_today_only"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["applied_today_only"])

        override = self.session.scalar(select(DietOverride).where(
            DietOverride.patient_id == self.patient.id,
            DietOverride.ref_date == date.today(),
            DietOverride.meal_key == "almoco",
        ))
        # Exatamente a proposta mostrada na primeira resposta.
        self.assertEqual(override.items_json, first.json()["buddy_state"]["items"])
        self.assertEqual(override.items_json[0]["food"], "Tilápia grelhada")
        self.assertEqual(self.session.get(DietItem, self.permanent_item.id).food, "Frango")

        diet = self.client.get(f"/patients/{self.patient.id}/diet").json()
        self.assertEqual(diet["meals"]["almoco"][0]["food"], "Frango")
        self.assertEqual(diet["today_meals"]["almoco"][0]["food"], "Tilápia grelhada")

        history = self.client.get("/buddy/history").json()
        self.assertEqual(len(history), 4)

    def test_confirmation_without_pending_proposal_changes_nothing(self):
        with patch("app.services.ollama_service.chat_reply", return_value="Oi! 🐣"):
            response = self.client.post("/buddy/chat", json={"content": "sim"})
        self.assertFalse(response.json()["applied_today_only"])
        self.assertIsNone(self.session.scalar(select(DietOverride)))


if __name__ == "__main__":
    unittest.main()
