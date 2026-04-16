import os
import requests
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class NotionSync:
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        raw_db_id = os.getenv("NOTION_DATABASE_ID")
        self.database_id = self._clean_id(raw_db_id)
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def _clean_id(self, db_id):
        """Extrae el UUID de 32 caracteres de una URL de Notion si es necesario."""
        if not db_id:
            return None
        # Eliminar espacios y comillas
        db_id = db_id.strip(' "').split('?')[0]
        # Si es una URL, tomar la última parte
        if "/" in db_id:
            db_id = db_id.split("/")[-1]
        # Quitar guiones si los tiene para normalizar
        return db_id.replace("-", "")

    def log_execution(self, status, message, file_count=0):
        """
        Registra una ejecución en la base de datos de Notion.
        """
        if not self.token or not self.database_id:
            print("[SKIP] Notion Sync: Credenciales no configuradas o ID inválido.")
            return

        if not self.token.startswith(("secret_", "ntn_")):
            print("[WARNING] Notion Sync: El token no parece ser válido (debe empezar con 'secret_' o 'ntn_').")

        url = "https://api.notion.com/v1/pages"
        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Nombre": {
                    "title": [{"text": {"content": f"Ejecución - {datetime.now().strftime('%Y-%m-%d %H:%M')}"}}]
                },
                "Estado": {
                    "select": {"name": status}
                },
                "Mensaje": {
                    "rich_text": [{"text": {"content": message}}]
                },
                "Archivos Procesados": {
                    "number": file_count
                },
                "Fecha": {
                    "date": {"start": datetime.now().isoformat()}
                }
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code == 200:
                print(f"[OK] Notion Sync: Ejecución registrada como {status}.")
            else:
                print(f"[ERROR] Notion Sync: {response.text}")
        except Exception as e:
            print(f"[ERROR] Notion Sync: {str(e)}")

if __name__ == "__main__":
    # Prueba rápida
    sync = NotionSync()
    sync.log_execution("Exitoso", "Prueba de sincronización manual", 5)
