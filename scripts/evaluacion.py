import os
import glob
import pandas as pd
from tabulate import tabulate

def evaluar_reportes():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, 'data', 'processed')
    archivos = glob.glob(os.path.join(processed_dir, 'Informe_estado_*.csv'))
    
    if not archivos:
        print("No hay archivos procesados para evaluar.")
        return
    
    tiendas_sin_armar_total = 0
    tiendas_armadas_por_centro_total = 0
    total_tiendas_analizadas = 0
    
    ranking_incidencias = {}
    
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
        except Exception as e:
            print(f"Error leyendo {archivo}: {e}")
            continue
            
        if 'Tienda' not in df.columns or 'Evento' not in df.columns or 'Nombre' not in df.columns:
            continue
            
        tiendas = df['Tienda'].unique()
        
        for tienda in tiendas:
            df_tienda = df[df['Tienda'] == tienda]
            eventos = df_tienda['Evento'].tolist()
            nombres = df_tienda[df_tienda['Evento'] == 'Armado']['Nombre'].tolist()
            
            total_tiendas_analizadas += 1
            
            # Inicializar rankings si no existen
            if tienda not in ranking_incidencias:
                ranking_incidencias[tienda] = {'no_armo': 0, 'armo_centro': 0}
                
            # a - Porcentaje de tiendas que no arman el sistema
            if 'Armado' not in eventos:
                tiendas_sin_armar_total += 1
                ranking_incidencias[tienda]['no_armo'] += 1
            else:
                # b - Porcentaje de tiendas que el armado lo hace el Centro de control
                armado_centro = any('centro de control' in str(nom).lower() for nom in nombres)
                if armado_centro:
                    tiendas_armadas_por_centro_total += 1
                    ranking_incidencias[tienda]['armo_centro'] += 1

    if total_tiendas_analizadas == 0:
        print("No se encontraron registros válidos para analizar.")
        return

    # a
    pct_no_arman = (tiendas_sin_armar_total / total_tiendas_analizadas) * 100
    # b
    pct_centro = (tiendas_armadas_por_centro_total / total_tiendas_analizadas) * 100
    
    print("\n" + "="*70)
    print(" EVALUACIÓN DE REPORTES DE TIENDAS - MÉTRICAS GLOBALES ")
    print("="*70)
    print(f"Total de registros de sucursales evaluados: {total_tiendas_analizadas}")
    print(f"Días de operación analizados: {len(archivos)}\n")
    
    print(f"a) Porcentaje de tiendas que NO arman el sistema al final del día:")
    print(f"   {pct_no_arman:.2f}%  ({tiendas_sin_armar_total} incidencias reportadas)")
    
    print(f"\nb) Porcentaje de tiendas cuyo armado lo asume el Centro de Control:")
    print(f"   {pct_centro:.2f}%  ({tiendas_armadas_por_centro_total} incidencias reportadas)")
    
    # c
    print(f"\nc) Ranking TOP 15 de tiendas con incidencias de cierre:")
    
    ranking_list = []
    for tienda, data in ranking_incidencias.items():
        total_incidencias = data['no_armo'] + data['armo_centro']
        if total_incidencias > 0:
            ranking_list.append([tienda, data['no_armo'], data['armo_centro'], total_incidencias])
            
    ranking_list.sort(key=lambda x: x[3], reverse=True)
    top_15 = ranking_list[:15]
    
    headers = ["Local / Tienda", "Veces sin armar", "Armadas por Centro", "TOTAL Incidencias"]
    print(tabulate(top_15, headers=headers, tablefmt="grid"))
    
    # d
    print("\n" + "-"*70)
    print("d) PUNTOS CLAVE PARA COMITÉ:")
    print(f" • Se consolidó el análisis de {len(archivos)} reportes procesados históricamente.")
    
    total_anomalias = tiendas_sin_armar_total + tiendas_armadas_por_centro_total
    pct_anomalias = (total_anomalias / total_tiendas_analizadas) * 100
    
    print(f" • El {pct_anomalias:.1f}% de las operaciones de cierre requieren intervención, lo que")
    print("   incrementa el riesgo y la saturación del equipo de monitoreo.")
    
    if tiendas_sin_armar_total > tiendas_armadas_por_centro_total:
        print(" • Existe una fuerte incidencia de descuido (NO armado), superando a la dependencia del centro.")
    else:
        print(" • Se evidencia que los locales dependen de que el centro de control las arme, ")
        print("   demostrando debilidad en el procedimiento operativo en tienda.")
        
    if top_15:
        peor_tienda = top_15[0]
        print(f" • La sucursal '{peor_tienda[0]}' lidera el nivel de fallos ({peor_tienda[3]} incidencias).")
        print(" • ALERTA: Se recomienda reentrenamiento urgente o amonestación en el Top 5 locales;")
        print("   sólo auditando este top 5 se reduciría significativamente la carga de monitoreo.")
    print("="*70 + "\n")

if __name__ == '__main__':
    evaluar_reportes()
