import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
import logging
import os
from google.oauth2.credentials import Credentials

class GmailNotifier:
    def __init__(self, token_path):
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"No se encontró token.json en {token_path}")
            
        self.token_path = token_path
        self.creds = Credentials.from_authorized_user_file(self.token_path)
        self.service = build('gmail', 'v1', credentials=self.creds)

    def enviar_alerta(self, destinatario, asunto, mensaje):
        try:
            message = MIMEText(mensaje)
            message['to'] = destinatario
            message['subject'] = asunto
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(userId='me', body={'raw': raw}).execute()
            print(f"[*] Alerta enviada a: {destinatario}")
            logging.info(f"Alerta enviada: {asunto}")
        except Exception as e:
            logging.error(f"Error enviando alerta: {e}")
            print(f"[ERROR] Error al enviar alerta: {e}")

if __name__ == "__main__":
    pass
