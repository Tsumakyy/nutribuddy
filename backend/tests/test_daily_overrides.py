import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DietItem, DietOverride, Patient
from app.routers.buddy import _apply_today_changes


class DailyOverrideTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.next_override_id = 1
        event.listen(self.session, "before_flush", self._assign_sqlite_override_ids)
        self.patient = Patient(id=1, user_id=10, nutritionist_id=20, goal=None)
        self.base_item = DietItem(
            id=1,
            patient_id=1,
            meal_key="almoco",
            food="Frango",
            qty="120 g",
            position=0,
        )
        self.session.add_all([self.patient, self.base_item])
        self.session.commit()

    def _assign_sqlite_override_ids(self, session, flush_context, instances):
        for item in session.new:
            if isinstance(item, DietOverride) and item.id is None:
                item.id = self.next_override_id
                self.next_override_id += 1

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_confirmed_changes_upsert_only_today_and_leave_the_prescription_unchanged(self):
        today = date.today()
        first_change = [{
            "meal_key": "almoco",
            "items": [{"food": "Peixe", "qty": "120 g"}],
        }]
        self.assertTrue(_apply_today_changes(self.session, self.patient.id, today, first_change))
        self.session.commit()

        updated_change = [{
            "meal_key": "almoco",
            "items": [{"food": "Ovo", "qty": "2 unidades"}],
        }]
        _apply_today_changes(self.session, self.patient.id, today, updated_change)
        self.session.commit()

        saved = self.session.scalar(select(DietOverride).where(
            DietOverride.patient_id == self.patient.id,
            DietOverride.ref_date == today,
            DietOverride.meal_key == "almoco",
        ))
        self.assertEqual(saved.items_json, updated_change[0]["items"])
        self.assertEqual(
            self.session.scalar(select(func.count()).select_from(DietOverride)),
            1,
        )
        self.assertIsNone(self.session.scalar(select(DietOverride).where(
            DietOverride.patient_id == self.patient.id,
            DietOverride.ref_date == today + timedelta(days=1),
        )))
        self.assertEqual(self.session.get(DietItem, self.base_item.id).food, "Frango")


if __name__ == "__main__":
    unittest.main()
