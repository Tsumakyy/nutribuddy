import json
import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DietItem, DietOverride, Food, Patient
from app.services.diet_context import build_diet_context


class DietContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.patient = Patient(
            id=1,
            user_id=10,
            nutritionist_id=20,
            goal="Acompanhamento geral",
        )
        self.session.add_all([
            self.patient,
            Food(id=1, name="Arroz integral", kcal=130, protein=2.7, carbs=28, fat=1, source="TACO"),
            Food(id=2, name="Peixe", kcal=110, protein=20, carbs=0, fat=3, source="TACO"),
            DietItem(
                id=1,
                patient_id=1,
                meal_key="almoco",
                food="Arroz integral",
                qty="150 g",
                position=0,
            ),
            DietItem(
                id=2,
                patient_id=1,
                meal_key="almoco",
                food="Salada",
                qty="1 porção",
                position=1,
            ),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_context_calculates_only_matched_gram_portions_and_marks_partial_meals(self):
        context = json.loads(build_diet_context(self.session, self.patient, date.today()))
        lunch = context["estimated_macros_for_today"]["almoco"]

        self.assertEqual(lunch["totals_for_matched_items"]["kcal"], 195.0)
        self.assertEqual(lunch["totals_for_matched_items"]["protein_g"], 4.1)
        self.assertEqual(lunch["matched_items"], 1)
        self.assertEqual(lunch["total_items"], 2)
        self.assertFalse(lunch["complete_meal_total"])
        self.assertFalse(lunch["micronutrients_available"])
        self.assertIn("no micronutrient data", context["nutrient_data_limits"])

    def test_context_uses_nutribr_for_exact_gram_matches_when_database_has_no_food(self):
        self.session.add(DietItem(
            id=3,
            patient_id=self.patient.id,
            meal_key="cafe",
            food="Arroz",
            qty="100 g",
            position=0,
        ))
        self.session.commit()

        context = json.loads(build_diet_context(self.session, self.patient, date.today()))
        breakfast = context["estimated_macros_for_today"]["cafe"]

        self.assertEqual(breakfast["totals_for_matched_items"]["kcal"], 130.0)
        self.assertEqual(breakfast["totals_for_matched_items"]["carbohydrates_g"], 28.0)
        self.assertTrue(breakfast["complete_meal_total"])
        self.assertEqual(breakfast["sources"], ["nutribr/TACO"])

    def test_today_override_is_used_today_but_never_replaces_permanent_plan(self):
        today = date.today()
        self.session.add(DietOverride(
            id=1,
            patient_id=self.patient.id,
            ref_date=today,
            meal_key="almoco",
            items_json=[{"food": "Peixe", "qty": "120 g"}],
        ))
        self.session.commit()

        today_context = json.loads(build_diet_context(self.session, self.patient, today))
        next_day_context = json.loads(build_diet_context(self.session, self.patient, today + timedelta(days=1)))

        self.assertEqual(today_context["permanent_plan_reference_only"]["almoco"][0]["food"], "Arroz integral")
        self.assertEqual(today_context["effective_plan_for_today"]["almoco"][0]["food"], "Peixe")
        self.assertEqual(next_day_context["effective_plan_for_today"]["almoco"][0]["food"], "Arroz integral")


if __name__ == "__main__":
    unittest.main()
