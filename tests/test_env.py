import os
import subprocess
import sys
from datetime import datetime
from configparser import ConfigParser

# ================= RUTAS Y CONFIGURACIÓN =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.ini')
# ========================================================

def run_test(fecha_manual):
    print(f"🚀 Iniciando Prueba End-to-End para la fecha: {fecha_manual}")
    
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Error: No se encontró config.ini en {CONFIG_DIR}")
        print("Asegúrate de copiar tu archivo config.ini a esa carpeta.")
        return

    # 1. Configurar config.ini para modo prueba y fecha manual
    config = ConfigParser()
    config.read(CONFIG_PATH)
    
    if 'General' not in config: config.add_section('General')
    if 'Fecha' not in config: config.add_section('Fecha')
    
    # Guardar valores originales para restaurar
    orig_test_mode = config.get('General', 'test_mode', fallback='False')
    orig_fecha_manual = config.get('Fecha', 'fecha_manual', fallback='')
    orig_usar_manual = config.get('Fecha', 'usar_fecha_manual', fallback='False')

    try:
        config.set('General', 'test_mode', 'True')
        config.set('Fecha', 'usar_fecha_manual', 'True')
        config.set('Fecha', 'fecha_manual', fecha_manual)
        
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
        
        print("✅ Configuración de prueba aplicada (test_mode=True, fecha_manual).")

        # 2. Ejecutar Descarga
        print("\n--- PASO 1: Descarga de correos ---")
        scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
        subprocess.run([sys.executable, os.path.join(scripts_dir, "raw_report.py")], check=True)

        # 3. Ejecutar Procesamiento
        print("\n--- PASO 2: Procesamiento y Notificación ---")
        subprocess.run([sys.executable, os.path.join(scripts_dir, "processed_report.py")], check=True)

        print("\n✨ Prueba completada con éxito.")
        print(f"Revisa el reporte final en: {os.path.join(PROJECT_ROOT, 'data', 'processed')}")

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
    
    finally:
        # Restaurar configuración
        config.set('General', 'test_mode', orig_test_mode)
        config.set('Fecha', 'usar_fecha_manual', orig_usar_manual)
        config.set('Fecha', 'fecha_manual', orig_fecha_manual)
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
        print("\n♻️ Configuración original restaurada.")

if __name__ == "__main__":
    # Pedir fecha al usuario
    fecha = input("Ingrese la fecha a probar (YYYY-MM-DD) [Default hoy]: ")
    if not fecha:
        fecha = datetime.now().strftime('%Y-%m-%d')
    
    run_test(fecha)
