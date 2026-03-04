import os
import sys

# Agregar el raíz al path para poder importar los módulos como paquetes
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.midnight_processor import MidnightProcessor

def test_processor():
    processor = MidnightProcessor()
    
    print("--- PROCESADOR DE PRUEBAS MIDNIGHT ---")
    print("1. Probar con un archivo específico")
    print("2. Ejecutar pruebas internas predefinidas")
    
    opcion = input("\nSeleccione una opción (1 o 2): ").strip()
    
    if opcion == "1":
        ruta = input("Ingrese la ruta completa del archivo .txt: ").strip().replace('"', '')
        if not os.path.exists(ruta):
            print(f"[ERROR] El archivo no existe: {ruta}")
            return
            
        nombre_archivo = os.path.basename(ruta)
        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
            
        print(f"\nAnalizando: {nombre_archivo}")
        result = processor.extraer_datos(contenido, nombre_archivo)
        if result:
            print("[OK] EXITO:")
            for k, v in result.items():
                print(f"  {k}: {v}")
        else:
            print("[ERROR] No se pudo extraer información. Revise el formato del archivo.")
            
    elif opcion == "2":
        test_cases = [
            {
                "name": "midnight-2026-02-09-test1.txt",
                "content": """Subject: 1234 - Tienda Modelo: Partition 1 fue puesto en Armado (Salir) a las 12:55 a.m. (centromonitoreo.cliente)
Date: 2026-02-09 00:55:39
--------------------
Partition 1 se armó (salir) (centromonitoreo.cliente)"""
            },
            {
                "name": "midnight-2026-02-12-test2.txt",
                "content": """Subject: 5678 - Local Central: El Partición 1 fue puesto en Armado (Salir) por 99999 - USUARIO EJEMPLO a las 12:17 a.m.
Date: 2026-02-12 00:17:56
--------------------
Partición 1 fue armado (salir) por 99999 - USUARIO EJEMPLO"""
            }
        ]

        print("\n--- EJECUTANDO PRUEBAS INTERNAS ---")
        for case in test_cases:
            print(f"\nProbando: {case['name']}")
            result = processor.extraer_datos(case['content'], case['name'])
            if result:
                print("[OK] EXITO:")
                for k, v in result.items():
                    print(f"  {k}: {v}")
            else:
                print("[ERROR] FALLO: No se pudo extraer informacion.")
    else:
        print("Opción no válida.")

if __name__ == "__main__":
    test_processor()
