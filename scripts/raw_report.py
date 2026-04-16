import os
import base64
import logging
import uuid
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ================= RUTAS Y CONFIGURACIÓN =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(CONFIG_DIR, 'token.json')

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CARPETA_RAW_DIARIOS = os.path.join(DATA_DIR, "raw", "diarios")
CARPETA_RAW_MIDNIGHT = os.path.join(DATA_DIR, "raw", "midnight")

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DESCARGADOS_FILE = os.path.join(LOG_DIR, 'descargados.txt')
LOG_PATH = os.path.join(LOG_DIR, 'eventos.log')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]
LABEL_MIDNIGHT = 'Midnight'                 
FILTRO_ASUNTO = '¡Su Informe de armado/desarmado está listo!'             
FILTRO_REMITENTE = 'notifications@alarm.com'  
# ========================================================

# ===================== LOGGING RESILIENTE ==========================
def configurar_logging(ruta_log):
    try:
        logging.basicConfig(
            filename=ruta_log,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True,
            encoding='utf-8'
        )
    except PermissionError:
        timestamp = datetime.now().strftime('%H%M%S')
        ruta_alt = ruta_log.replace('.log', f'_{timestamp}.log')
        print(f"[!] El archivo de log {ruta_log} está bloqueado. Usando {ruta_alt}")
        logging.basicConfig(
            filename=ruta_alt,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True,
            encoding='utf-8'
        )

configurar_logging(LOG_PATH)
# ====================================================================

def cargar_descargados():
    if not os.path.exists(DESCARGADOS_FILE):
        return set()
    try:
        with open(DESCARGADOS_FILE, 'r') as f:
            return set(line.strip() for line in f.readlines())
    except Exception as e:
        logging.error(f"Error cargando descargados.txt: {e}")
        return set()

def guardar_descargados(clave):
    try:
        with open(DESCARGADOS_FILE, 'a') as f:
            f.write(clave + '\n')
    except Exception as e:
        logging.error(f"Error guardando en descargados.txt: {e}")

def autenticar_gmail():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"No se encontró credentials.json en {CONFIG_DIR}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def construir_query_diarios():
    hoy = datetime.now().date()
    manana = hoy + timedelta(days=1)
    query = f'after:{hoy.strftime("%Y/%m/%d")} before:{manana.strftime("%Y/%m/%d")}'
    query += f' from:{FILTRO_REMITENTE} subject:{FILTRO_ASUNTO} -label:{LABEL_MIDNIGHT}'
    return query

def construir_query_midnight():
    hoy = datetime.now().date()
    manana = hoy + timedelta(days=1)
    query = f'after:{hoy:%Y/%m/%d} before:{manana:%Y/%m/%d} from:{FILTRO_REMITENTE} label:{LABEL_MIDNIGHT}'
    return query

def obtener_fecha_correo(message):
    for h in message['payload']['headers']:
        if h['name'] == 'Date':
            try:
                date_str = h['value']
                if '(' in date_str:
                    date_str = date_str.split(' (')[0]
                return datetime.strptime(date_str[:25].strip(), '%a, %d %b %Y %H:%M:%S')
            except Exception:
                return datetime.now()
    return datetime.now()

def descargar_correos(query, carpeta_destino, tipo, es_adjunto=True):
    logging.info(f'Inicio descarga {tipo}')
    try:
        service = autenticar_gmail()
        results = service.users().messages().list(userId='me', q=query).execute()
    except Exception as e:
        logging.error(f"Error en comunicación con Gmail: {e}")
        return

    messages = results.get('messages', [])
    if not messages:
        logging.info(f'No hay correos {tipo}')
        return

    os.makedirs(carpeta_destino, exist_ok=True)
    descargados = cargar_descargados()

    for msg in messages:
        try:
            message = service.users().messages().get(userId='me', id=msg['id']).execute()
            fecha_correo = obtener_fecha_correo(message)
            clave_base = msg['id']
            
            if es_adjunto:
                parts = message['payload'].get('parts', [])
                if not parts and 'body' in message['payload']:
                    parts = [message['payload']]

                for part in parts:
                    filename = part.get('filename')
                    if not filename or not filename.endswith('.csv'):
                        continue    

                    attachment_id = part['body'].get('attachmentId')
                    clave_unica = f"{clave_base}|{filename}"

                    if clave_unica in descargados:
                        logging.info(f'Adjunto ya descargado: {filename}')
                        continue

                    attachment = service.users().messages().attachments().get(
                            userId='me', messageId=msg['id'], id=attachment_id
                        ).execute()

                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    timestamp = fecha_correo.strftime('%Y%m%d_%H%M%S%f')
                    nuevo_nombre = f"{timestamp}_{uuid.uuid4().hex[:6]}_{filename}"
                    ruta_archivo = os.path.join(carpeta_destino, nuevo_nombre)

                    with open(ruta_archivo, 'wb') as f:
                        f.write(file_data)

                    guardar_descargados(clave_unica)
                    descargados.add(clave_unica)
                    logging.info(f'{tipo} descargado: {ruta_archivo}')
                    print(f'[OK] Adjunto descargado: {filename}')
            else:
                if clave_base in descargados:
                    logging.info(f'Correo ya procesado: {clave_base}')
                    continue
                    
                body = ""
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                    if not body:
                         for part in message['payload']['parts']:
                            if part['mimeType'] == 'text/html':
                                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                break
                else:
                    body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

                if body:
                    timestamp = fecha_correo.strftime('%Y-%m-%d_%H-%M-%S')
                    subject = next((h['value'] for h in message['payload']['headers'] if h['name'] == 'Subject'), 'no_subject')
                    nuevo_nombre = f"midnight-{timestamp}-{clave_base}.txt"
                    ruta_archivo = os.path.join(carpeta_destino, nuevo_nombre)

                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        f.write(f"Subject: {subject}\nDate: {fecha_correo}\n{'-'*20}\n{body}")

                    guardar_descargados(clave_base)
                    descargados.add(clave_base)
                    logging.info(f'{tipo} guardado: {ruta_archivo}')
                    print(f'[OK] Notificación guardada: {nuevo_nombre}')
        except Exception as e:
            logging.error(f"Error procesando mensaje {msg['id']}: {e}")

    logging.info('Fin de ejecución')

def main():
    descargar_correos(construir_query_midnight(), CARPETA_RAW_MIDNIGHT, 'MIDNIGHT', es_adjunto=False)
    descargar_correos(construir_query_diarios(), CARPETA_RAW_DIARIOS, 'DIARIOS', es_adjunto=True)

if __name__ == '__main__':
    main()
