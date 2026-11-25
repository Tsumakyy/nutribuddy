import unittest
from unittest.mock import MagicMock, patch

import httpx

from app.services.ollama_service import chat_reply, format_plan_for_llm


class OllamaChatTests(unittest.TestCase):
    def _mock_response(self, content: str):
        response = MagicMock()
        response.json.return_value = {"message": {"content": content}}
        response.raise_for_status.return_value = None
        return response

    def test_returns_plain_text_reply(self):
        with patch("app.services.ollama_service.httpx.post", return_value=self._mock_response("Oi! 🐣")):
            self.assertEqual(chat_reply([], "oi"), "Oi! 🐣")

    def test_unwraps_json_replies_from_small_models(self):
        with patch(
            "app.services.ollama_service.httpx.post",
            return_value=self._mock_response('{"message": "Bora beber água! 💧"}'),
        ):
            self.assertEqual(chat_reply([], "dica?"), "Bora beber água! 💧")

    def test_returns_none_when_ollama_is_down(self):
        with patch("app.services.ollama_service.httpx.post", side_effect=httpx.ConnectError("down")):
            self.assertIsNone(chat_reply([], "oi"))

    def test_plan_is_formatted_as_reference_text(self):
        text = format_plan_for_llm({
            "meal_schedule": {"jantar": "Jantar"},
            "effective_plan_for_today": {"jantar": [{"food": "Arroz integral", "qty": "100g"}], "cafe": []},
        })
        self.assertIn("Jantar: Arroz integral (100g)", text)


if __name__ == "__main__":
    unittest.main()
