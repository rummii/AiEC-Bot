import os
import unittest
from unittest.mock import patch
from unittest.mock import Mock

import app


class TelegramAlertTests(unittest.TestCase):
    def test_send_telegram_alert_skips_without_credentials(self):
        with patch.object(app, "TELEGRAM_BOT_TOKEN", None), \
             patch.object(app, "TELEGRAM_CHAT_ID", None), \
             patch("builtins.print") as mock_print:
            result = app.send_telegram_alert("hello")

        self.assertFalse(result)
        self.assertEqual(mock_print.call_count, 2)
        self.assertIn("Valid credentials not found", mock_print.call_args_list[0].args[0])
        self.assertIn("missing TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID", mock_print.call_args_list[1].args[0])

    def test_get_setting_strips_whitespace_and_quotes(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": " 123:abc ", "TELEGRAM_CHAT_ID": '"6027602817"'}, clear=True):
            self.assertEqual(app.get_setting("TELEGRAM_BOT_TOKEN"), "123:abc")
            self.assertEqual(app.get_setting("TELEGRAM_CHAT_ID"), "6027602817")

    def test_register_telegram_webhook_uses_tunnel_url(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"ok": True, "result": True}

        with patch.object(app, "TELEGRAM_BOT_TOKEN", "123:abc"), \
             patch.object(app, "TELEGRAM_WEBHOOK_URL", "https://example-tunnel.ngrok-free.app"), \
             patch("app.requests.post", return_value=response) as mock_post:
            result = app.register_telegram_webhook()

        self.assertTrue(result)
        mock_post.assert_called_once()
        self.assertIn("/setWebhook", mock_post.call_args.args[0])
        self.assertEqual(mock_post.call_args.kwargs["json"]["url"], "https://example-tunnel.ngrok-free.app/webhook")


if __name__ == "__main__":
    unittest.main()
