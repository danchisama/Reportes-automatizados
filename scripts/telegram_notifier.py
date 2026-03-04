import os
import requests
import logging

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def send_message(self, message):
        """Envía un mensaje a través de Telegram."""
        if not self.bot_token or not self.chat_id:
            logging.warning("[SKIP] Telegram Notifier: Credenciales no configuradas.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logging.info("[OK] Telegram: Mensaje enviado.")
                return True
            else:
                logging.error(f"[ERROR] Telegram: {response.text}")
                return False
        except Exception as e:
            logging.error(f"[ERROR] Telegram: {str(e)}")
            return False
