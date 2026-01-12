from django.test import TestCase
from unittest.mock import patch, MagicMock
from careplans.services import generate_care_plan_from_llm

class TestLLMIntegration(TestCase):

    @patch('careplans.services.OpenAI')
    def test_llm_success(self, mock_openai_class):
        # 1. Setup the mock client instance
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # 2. Mock the nested response path for Chat Completions
        # This mirrors: response.choices[0].message.content
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="CARE PLAN"))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # 3. Call the service
        text, error = generate_care_plan_from_llm("clinical text", "IVIG")

        # 4. Assertions
        self.assertEqual(text, "CARE PLAN")
        self.assertIsNone(error)

    @patch('careplans.services.OpenAI')
    def test_llm_failure(self, mock_openai_class):
        # 1. Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # 2. Add "[TEST]" prefix to the simulated error
        mock_client.chat.completions.create.side_effect = Exception("[TEST] Simulated Connection Failure")

        # 3. Call the service
        text, error = generate_care_plan_from_llm("clinical text", "IVIG")

        # 4. Assertions
        self.assertIsNone(text)
        self.assertIn("unavailable", error.lower())