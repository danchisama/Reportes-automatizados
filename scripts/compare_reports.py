import pandas as pd
import os
import sys

def normalize_tienda(val):
    return str(val).strip().split(' - ')[0] if ' - ' in str(val) else str(val).strip()

def compare(path_legacy, path_new):
    print(f"--- COMPARANDO REPORTES ---")
    print(f"Legacy: {path_legacy}")
    print(f"Nuevo:  {path_new}\n")

    if not os.path.exists(path_legacy):
        print(f"[ERROR] No se encuentra el archivo legacy en: {path_legacy}")
        return
    if not os.path.exists(path_new):
        print(f"[ERROR] No se encuentra el archivo nuevo en: {path_new}")
        return

    # Cargar datos
    df_l = pd.read_csv(path_legacy, encoding='latin-1')
    df_n = pd.read_csv(path_new, encoding='utf-8-sig')

    # Normalizar Columnas para comparación
    # Buscamos columnas equivalentes
    col_l = ["Tienda", "Evento", "Nombre"] 
    col_n = ["Tienda", "Evento", "Nombre"]

    # Normalizar IDs de tienda para cruce fácil
    df_l['ID_Tienda'] = df_l['Tienda'].apply(normalize_tienda)
    df_n['ID_Tienda'] = df_n['Tienda'].apply(normalize_tienda)

    # 1. Comparar cantidad de tiendas
    tiendas_l = set(df_l['ID_Tienda'].unique())
    tiendas_n = set(df_n['ID_Tienda'].unique())

    diff_solo_l = tiendas_l - tiendas_n
    diff_solo_n = tiendas_n - tiendas_l

    if diff_solo_l:
        print(f"⚠️ Tiendas en Legacy pero NO en Nuevo ({len(diff_solo_l)}):")
        print(f"   {list(diff_solo_l)[:10]}...")
    
    if diff_solo_n:
        print(f"✅ Tiendas nuevas detectadas ({len(diff_solo_n)}):")
        print(f"   {list(diff_solo_n)[:10]}...")

    # 2. Comparar eventos por tienda
    print(f"\nResumen de eventos:")
    print(f"Legacy total: {len(df_l)} filas")
    print(f"Nuevo total:  {len(df_n)} filas")

    # Re-cruzar para ver diferencias de Nombre o Evento
    joined = pd.merge(df_l, df_n, on=['ID_Tienda', 'Evento'], how='inner', suffixes=('_l', '_n'))
    
    # Esto es simplificado, en la vida real compararíamos Fecha/Hora exactas
    print(f"\n[OK] Comparación básica completada. Revise los CSVs para detalles manuales.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: py scripts/compare_reports.py ruta_legacy.csv ruta_nueva.csv")
    else:
        compare(sys.argv[1], sys.argv[2])
