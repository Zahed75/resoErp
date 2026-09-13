import base64
from unittest.mock import patch

from odoo.tests import common, tagged

from .test_data import AUDIO_OGG_B64
from odoo.addons.ai.utils.llm_api_service import LLMApiService


@tagged("post_install", "-at_install")
class TestLLMApiService(common.TransactionCase):

    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService._get_api_token")
    @patch("odoo.addons.ai.utils.llm_api_service.LLMApiService._request")
    def test_deprecated_model_is_replaced_by_an_available_one(self, mock_request_llm, mock_get_api_token):
        mock_get_api_token.return_value = "test-gemini-key"
        mock_request_llm.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Hello"}]}}],
        }
        # gemini-1.5-flash is deprecated and should be replaced by a non deprecated one in LLMApiService
        LLMApiService(self.env, "google").request_llm("gemini-1.5-flash", "", [])
        request_url = mock_request_llm.call_args.kwargs["endpoint"]
        self.assertNotIn("gemini-1.5-flash", request_url, "The deprecated model should not be used")
        self.assertIn("gemini-3-flash-preview", request_url, "The replacement model should be used")


@tagged("ai_external", "-standard", "post_install", "-at_install")
class TestLLMApiServiceIntegration(common.TransactionCase):
    def test_transcribes_audio_via_external_api(self):
        service = LLMApiService(self.env)
        audio_bytes = base64.b64decode(AUDIO_OGG_B64)
        result = service.get_transcription(audio_bytes, mimetype="audio/ogg")

        self.assertIsInstance(result, str, "Transcription result to be a string")
        self.assertGreater(len(result.strip()), 0, "Transcription result is empty")
        soft_matches = {"transcribing", "things", "transcribe", "thing"}
        score = 0
        for sm in soft_matches:
            if sm in result:
                score += 1
        score /= len(soft_matches)
        self.assertGreaterEqual(score, 0.5, f"Transcription quality is poor  Output: {result!r}")
