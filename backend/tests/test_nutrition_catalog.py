import unittest

from app.services.nutrition_catalog import (
    find_healthy_substitutes,
    find_nutribr_food,
    search_nutribr_foods,
)


class NutritionCatalogTests(unittest.TestCase):
    def test_search_matches_names_without_accents_and_returns_macros_per_100g(self):
        foods = search_nutribr_foods("maca")

        self.assertGreaterEqual(len(foods), 1)
        self.assertEqual(foods[0]["name"], "Maçã")
        self.assertEqual(foods[0]["kcal"], 52.0)
        self.assertEqual(foods[0]["source"], "nutribr/TACO")
        self.assertFalse(foods[0]["micronutrients_available"])

    def test_exact_lookup_is_case_and_accent_insensitive(self):
        food = find_nutribr_food("FEIJAO")

        self.assertIsNotNone(food)
        self.assertEqual(food["name"], "Feijão")
        self.assertEqual(food["protein_g"], 4.8)

    def test_search_returns_multiple_rice_varieties(self):
        foods = search_nutribr_foods("arroz")
        names = [f["name"] for f in foods]

        self.assertIn("Arroz integral", names)
        self.assertIn("Arroz branco cozido", names)

    def test_healthy_substitutes_match_food_group(self):
        subs = find_healthy_substitutes("Queijo mussarela", grams=40)
        names = [s["name"] for s in subs]

        self.assertIn("Queijo cottage", names)
        self.assertIn("Ricota fresca", names)
        self.assertTrue(all(s["suggested_qty"] for s in subs))


if __name__ == "__main__":
    unittest.main()
