import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

import raw_report
import processed_report

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(PROJECT_ROOT, "tests", "reporte")
TEST_RAW_DIARIOS = os.path.join(TEST_DIR, "raw", "diarios")
TEST_RAW_MIDNIGHT = os.path.join(TEST_DIR, "raw", "midnight")
TEST_PROCESSED = os.path.join(TEST_DIR, "processed")

# Crear directorios de prueba
os.makedirs(TEST_RAW_DIARIOS, exist_ok=True)
os.makedirs(TEST_RAW_MIDNIGHT, exist_ok=True)
os.makedirs(TEST_PROCESSED, exist_ok=True)

class SFTPMock:
    def __init__(self, *args, **kwargs):
        pass
    def subir_archivo(self, *args, **kwargs):
        print("[TEST MOCK] Archivo subido. (FALSO SFTP)")
        return True

# Aplicando patches para desviar rutas a tests/reporte y apagar notificaciones
patchers = [
    patch('raw_report.CARPETA_RAW_DIARIOS', TEST_RAW_DIARIOS),
    patch('raw_report.CARPETA_RAW_MIDNIGHT', TEST_RAW_MIDNIGHT),
    patch('raw_report.DESCARGADOS_FILE', os.path.join(TEST_DIR, 'descargados.txt')),
    patch('processed_report.RAW_DIARIOS_DIR', TEST_RAW_DIARIOS),
    patch('processed_report.RAW_MIDNIGHT_DIR', TEST_RAW_MIDNIGHT),
    patch('processed_report.PROCESSED_DIR', TEST_PROCESSED),
    patch('processed_report.SFTPUploader', SFTPMock),
    patch('processed_report.GmailNotifier'),
    patch('processed_report.NotionSync'),
    patch('processed_report.TelegramNotifier'),
    patch('processed_report.INTERVALO_REINTENTO', 1),
    patch('processed_report.TIMEOUT_MAXIMO', 10)
]

for p in patchers:
    p.start()

print("=======================================================================")
print("[TEST] Iniciando processed_report.main() en entorno simulado...")
print(f"[TEST] Directorio destino: {TEST_DIR}")
print("=======================================================================")

try:
    processed_report.main()
finally:
    for p in patchers:
        try:
            p.stop()
        except:
            pass
    print("=======================================================================")
    print("[TEST] Proceso Finalizado. Chequea los resultados en tests/reporte/")
    print("=======================================================================")
