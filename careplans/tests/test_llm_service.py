from django.test import TestCase
from unittest.mock import patch
from careplans.services import generate_care_plan_from_llm


class TestLLMIntegration(TestCase):

    @patch('careplans.services.OpenAI')
    def test_llm_success(self, mock_llm):
        mock_llm.return_value.responses.create.return_value.output_text = "CARE PLAN"

        text, error = generate_care_plan_from_llm("clinical text", "IVIG")

        self.assertEqual(text, "CARE PLAN")
        self.assertIsNone(error)

    @patch('careplans.services.OpenAI')
    def test_llm_failure(self, mock_llm):
        mock_llm.side_effect = Exception("Connection failed")

        text, error = generate_care_plan_from_llm("clinical text", "IVIG")

        self.assertIsNone(text)
        self.assertIn("failed", error.lower())
