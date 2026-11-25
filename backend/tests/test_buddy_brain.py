import unittest
from unittest.mock import patch

from app.services import buddy_brain
from app.services.substitution_engine import evaluate, find_equivalents, resolve_food, totals

PLAN = {
    "almoco": [
        {"food": "Tilápia grelhada", "qty": "206g"},
        {"food": "Arroz integral", "qty": "245g"},
        {"food": "Salada de folhas", "qty": "à vontade"},
        {"food": "Azeite de oliva", "qty": "1 fio"},
    ],
    "jantar": [
        {"food": "Ovo cozido", "qty": "150g"},
        {"food": "Arroz integral", "qty": "245g"},
        {"food": "Brócolis cozido", "qty": "100g"},
    ],
    "cafe": [
        {"food": "Pão de forma integral", "qty": "50g"},
        {"food": "Queijo minas frescal", "qty": "30g"},
    ],
}


class Conversation:
    def __init__(self, plan=None):
        self.context = {"effective_plan_for_today": {k: list(v) for k, v in (plan or PLAN).items()}}
        self.state = None

    def say(self, text: str) -> dict:
        with patch("app.services.ollama_service.chat_reply", return_value=None):
            reply = buddy_brain.respond(text, self.context, self.state, [])
        self.state = reply["buddy_state"]
        for change in reply["day_changes"]:
            self.context["effective_plan_for_today"][change["meal_key"]] = change["items"]
        return reply


def meal_totals(items):
    total = {"kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for item in items:
        grams = float(item["qty"].rstrip("g ").strip()) if item["qty"].rstrip().endswith("g") else None
        food = resolve_food(item["food"])
        if grams and food:
            for key, value in totals(food, grams).items():
                total[key] += value
    return total


class SubstitutionEngineTests(unittest.TestCase):
    def test_equivalents_keep_calories_and_protein_close(self):
        tilapia = resolve_food("Tilápia grelhada")
        options = find_equivalents(tilapia, 203, "jantar")
        self.assertGreaterEqual(len(options), 2)
        for option in options:
            self.assertLessEqual(option["kcal_diff"], 0.15)
            self.assertLessEqual(option["primary_diff"], 0.15)

    def test_never_suggests_absurd_portions(self):
        tilapia = resolve_food("Tilápia grelhada")
        result = evaluate(tilapia, 203, resolve_food("Ovo cozido"))
        # O bot antigo sugeriu 400 g de ovo; aqui isso precisa ser rejeitado.
        self.assertFalse(result["ok"])

    def test_breakfast_bread_is_not_swapped_for_rice(self):
        bread = resolve_food("Pão de forma integral")
        names = [opt["food"] for opt in find_equivalents(bread, 50, "cafe")]
        self.assertNotIn("Arroz integral", names)
        self.assertNotIn("Macarrão integral cozido", names)

    def test_free_text_plan_names_are_resolved(self):
        self.assertEqual(resolve_food("Frango")["group"], "protein")


class BuddyConversationTests(unittest.TestCase):
    def test_original_bug_report_flow_now_swaps_only_the_protein_for_chicken(self):
        chat = Conversation()
        first = chat.say("Quero jantar outra coisa")
        self.assertIn("Ovo cozido", first["message"])
        self.assertEqual(first["day_changes"], [])

        proposal = chat.say("Eu gosto de frango")
        self.assertTrue(proposal["awaiting_confirmation"])
        self.assertIn("frango", proposal["message"].lower())

        applied = chat.say("Sim")
        self.assertEqual(len(applied["day_changes"]), 1)
        change = applied["day_changes"][0]
        self.assertEqual(change["meal_key"], "jantar")
        foods = [item["food"] for item in change["items"]]
        self.assertIn("Peito de frango grelhado", foods)
        self.assertNotIn("Ovo cozido", foods)
        # O resto do prato não muda.
        self.assertIn({"food": "Arroz integral", "qty": "245g"}, change["items"])
        self.assertIn({"food": "Brócolis cozido", "qty": "100g"}, change["items"])

        before = meal_totals(PLAN["jantar"])
        after = meal_totals(change["items"])
        self.assertLess(abs(after["kcal"] - before["kcal"]) / before["kcal"], 0.08)
        self.assertLess(abs(after["protein_g"] - before["protein_g"]) / before["protein_g"], 0.08)

    def test_confirmation_applies_exactly_the_proposal_shown(self):
        chat = Conversation()
        chat.say("posso trocar a tilápia do almoço?")
        options = chat.state["options"]
        proposal = chat.say("2")
        self.assertIn(options[1], proposal["message"])
        applied = chat.say("sim, troca!")
        self.assertEqual(applied["day_changes"][0]["items"], proposal["buddy_state"]["items"])

    def test_unbalanced_request_is_explained_and_alternatives_offered(self):
        chat = Conversation()
        reply = chat.say("posso trocar a tilápia por salmão?")
        self.assertIn("não fecha a conta", reply["message"])
        self.assertEqual(reply["buddy_state"]["stage"], "pick_option")
        self.assertEqual(reply["day_changes"], [])

    def test_wrong_food_group_is_not_swapped(self):
        chat = Conversation()
        chat.say("quero trocar o pão do café")
        reply = chat.say("banana")
        self.assertIn("faz o papel da fruta", reply["message"])
        self.assertEqual(reply["day_changes"], [])

    def test_declining_keeps_the_plan(self):
        chat = Conversation()
        chat.say("quero frango no jantar")
        reply = chat.say("não")
        self.assertEqual(reply["day_changes"], [])
        self.assertEqual(reply["buddy_state"].get("stage"), None)

    def test_disliked_food_is_never_suggested(self):
        chat = Conversation()
        chat.say("quero trocar a tilápia do almoço")
        reply = chat.say("não gosto de frango")
        self.assertNotIn("1) 🍗", reply["message"])
        self.assertNotIn("frango", " ".join(reply["buddy_state"]["options"]).lower())

    def test_ambiguous_food_asks_which_meal(self):
        chat = Conversation()
        reply = chat.say("trocar o arroz")
        self.assertIn("mais de uma refeição", reply["message"])
        reply = chat.say("almoço")
        self.assertEqual(reply["buddy_state"]["meal_key"], "almoco")

    def test_household_measures_are_not_guessed(self):
        chat = Conversation()
        reply = chat.say("quero trocar o azeite do almoço")
        self.assertIn("medida caseira", reply["message"])
        self.assertEqual(reply["day_changes"], [])

    def test_compensation_and_clinical_questions_bypass_swaps(self):
        chat = Conversation()
        self.assertIn("Nada de compensar", chat.say("Comi doce, devo cortar carboidratos pra compensar?")["message"])
        clinical = chat.say("tô com dor de barriga, posso trocar o jantar?")
        self.assertTrue(clinical["needs_nutritionist"])
        self.assertEqual(clinical["day_changes"], [])

    def test_words_containing_dor_are_not_clinical(self):
        chat = Conversation()
        reply = chat.say("adoro frango, quero no jantar")
        self.assertFalse(reply["needs_nutritionist"])
        self.assertTrue(reply["awaiting_confirmation"])

    # --- Regressões da conversa real com o plano do Diego -------------------------
    DIEGO = {
        "cafe": [{"food": "Pão francês", "qty": "100g"}, {"food": "Ovo mexido", "qty": "150g"},
                 {"food": "Queijo minas frescal", "qty": "30g"}, {"food": "Banana prata", "qty": "100g"}],
        "lanche1": [{"food": "Iogurte natural integral", "qty": "170g"}, {"food": "Aveia em flocos", "qty": "30g"},
                    {"food": "Uva Itália", "qty": "100g"}],
        "almoco": [{"food": "Arroz branco cozido", "qty": "250g"}, {"food": "Feijão carioca cozido", "qty": "140g"},
                   {"food": "Alcatra grelhada", "qty": "160g"}, {"food": "Brócolis cozido", "qty": "100g"},
                   {"food": "Azeite de oliva", "qty": "10g"}],
    }

    def test_negated_food_is_the_target_never_the_suggestion(self):
        chat = Conversation(self.DIEGO)
        reply = chat.say("Não quero carne no almoço")
        self.assertEqual(reply["buddy_state"]["target_food"], "Alcatra grelhada")
        self.assertNotIn("Patinho moído cozido", reply["buddy_state"]["options"])
        more = chat.say("Ver outras opções")
        self.assertNotIn("Patinho", more["message"])

    def test_food_missing_from_named_meal_points_to_where_it_is(self):
        chat = Conversation(self.DIEGO)
        reply = chat.say("Não quero comer aveia no café")
        self.assertEqual(reply["day_changes"], [])
        self.assertFalse(reply["awaiting_confirmation"])
        self.assertIn("lanche da manhã", reply["message"])
        follow = chat.say("No lanche eu quis dizer")
        self.assertEqual(follow["buddy_state"].get("target_food"), "Aveia em flocos")

    def test_refusing_the_complement_recalculates_without_it(self):
        chat = Conversation(self.DIEGO)
        chat.say("Não quero carne no almoço")
        chat.say("1")
        reply = chat.say("Não quero azeite")
        self.assertIn("azeite", reply["buddy_state"]["disliked"])
        self.assertNotIn("+ azeite", reply["message"])
        # Continua falando do almoço, não pula para outra refeição.
        self.assertNotIn("lanche", reply["message"])

    def test_unknown_food_is_named_instead_of_not_understood(self):
        chat = Conversation(self.DIEGO)
        chat.say("Não quero comer aveia no lanche da manhã")
        reply = chat.say("Prefiro granola")
        self.assertIn("granola", reply["message"])
        self.assertEqual(reply["buddy_state"]["stage"], "pick_option")

    def test_exhausted_options_are_not_repeated_as_new(self):
        chat = Conversation(self.DIEGO)
        chat.say("Não quero comer aveia no lanche da manhã")
        reply = chat.say("Outras opções")
        self.assertIn("únicas trocas", reply["message"])

    def test_declining_with_no_pending_swap_is_friendly(self):
        chat = Conversation(self.DIEGO)
        reply = chat.say("Deixa como está")
        self.assertFalse(reply["ai_unavailable"])

    def test_vegetarian_profile_never_gets_meat_or_fish(self):
        chat = Conversation({"almoco": [{"food": "Tofu firme", "qty": "120g"}, {"food": "Quinoa cozida", "qty": "150g"}]})
        chat.context["patient_goal_from_nutritionist"] = "Vegetariana — manutenção"
        reply = chat.say("não tenho tofu")
        meat = {"frango", "tilápia", "atum", "salmão", "patinho", "alcatra"}
        self.assertFalse(any(word in reply["message"].lower() for word in meat))
        asked = chat.say("quero frango")
        self.assertIn("vegetariano", asked["message"])
        self.assertEqual(asked["day_changes"], [])
        self.assertFalse(asked["awaiting_confirmation"])

    def test_free_chat_never_claims_plan_changes(self):
        chat = Conversation()
        with patch("app.services.ollama_service.chat_reply", return_value="Troquei seu jantar por pizza!"):
            reply = buddy_brain.respond("me conta uma curiosidade", chat.context, None, [])
        self.assertNotIn("pizza", reply["message"])
        self.assertEqual(reply["day_changes"], [])


if __name__ == "__main__":
    unittest.main()
