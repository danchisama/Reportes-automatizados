import os
import re
import time
import pandas as pd
import logging
from datetime import datetime, timedelta
from configparser import ConfigParser
from midnight_processor import MidnightProcessor
from sftp_uploader import SFTPUploader
from notifier import GmailNotifier
from notion_sync import NotionSync
from telegram_notifier import TelegramNotifier
import raw_report

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ================= RUTAS Y CONFIGURACIÓN =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.ini')
TOKEN_PATH = os.path.join(CONFIG_DIR, 'token.json')

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIARIOS_DIR = os.path.join(DATA_DIR, "raw", "diarios")
RAW_MIDNIGHT_DIR = os.path.join(DATA_DIR, "raw", "midnight")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, 'procesamiento.log')

EMAIL_NOTIFICACION = 'dante.u.o@gmail.com' 
ARCHIVOS_ESPERADOS = 3
INTERVALO_REINTENTO = 300 # 5 minutos
TIMEOUT_MAXIMO = 3600 * 3 # 3 horas
MINIMO_FILAS_REPORTE = 50 # Umbral para alertar sobre reporte sospechosamente pequeño
# =========================================================

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

def limpiar_y_normalizar(df):
    """Limpieza y normalización de datos según requisitos estrictos."""
    if df.empty:
        return df
    
    # 1. Normalizar nombres de columnas
    if "Local" in df.columns and "Tienda" not in df.columns:
        df = df.rename(columns={"Local": "Tienda"})
    elif "Unidad" in df.columns and "Tienda" not in df.columns:
        df = df.rename(columns={"Unidad": "Tienda"})
    
    # 2. Parsear Fecha y Hora
    # Descartar nulos/vacíos
    df = df[df["Fecha"].notna() & (df["Fecha"].astype(str).str.strip() != "")].copy()
    
    # Normalización agresiva de am/pm para evitar fallos de parsing
    fechas_limpias = (
        df["Fecha"].astype(str)
        .str.lower()
        .str.replace("p. m.", "pm", regex=False)
        .str.replace("a. m.", "am", regex=False)
        .str.replace("p.m.", "pm", regex=False)
        .str.replace("a.m.", "am", regex=False)
        .str.replace("pm", " PM", regex=False)
        .str.replace("am", " AM", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )
    
    # Usar dayfirst=True y dejar que pandas detecte el formato (es más robusto con 5:52 vs 05:52)
    df["Fecha_DT"] = pd.to_datetime(fechas_limpias, dayfirst=True, errors="coerce")
    
    erros_n = df["Fecha_DT"].isna().sum()
    if erros_n > 0:
        logging.warning(f"Se descartaron {erros_n} filas por errores de formato de fecha.")
    
    # Eliminar filas donde la fecha no se pudo parsear
    df = df[df["Fecha_DT"].notna()].copy()

    # 3. Limpiar y Normalizar Evento y Nombre
    def extract_info(row):
        evento_raw = str(row.get("Evento", ""))
        nombre_ext = str(row.get("Nombre", "")) if "Nombre" in row and pd.notna(row["Nombre"]) else ""
        
        # Quitar prefijos molestos
        clean_ev = re.sub(r"^(Partici[oó]n|Partition|Panel)\s*\d*\s*", "", evento_raw, flags=re.IGNORECASE).strip()
        
        # Caso 1: Nombres en paréntesis "(OperadorXYZ)" - Puede haber varios
        parentheses = re.findall(r"\(([^)]+)\)", clean_ev)
        for content in parentheses:
            content_strip = content.strip()
            # Ignorar si es solo (Salir) o (Quedarse) que son estados, no nombres
            if content_strip.lower() not in ["salir", "quedarse"]:
                # Si encontramos un nombre real, lo guardamos (priorizando sobre lo que ya haya)
                nombre_ext = f"Centro de control ({content_strip})"
            
            # Siempre removemos el paréntesis del evento para limpiarlo
            clean_ev = clean_ev.replace(f"({content})", "").strip()

        # Caso 2: " por [Nombre]"
        if " por " in clean_ev:
            partes = clean_ev.split(" por ", 1)
            clean_ev = partes[0].strip()
            if not nombre_ext or "Centro de control" not in nombre_ext:
                nombre_ext = partes[1].strip()

        # Normalizar tipo de evento
        if "Desarmado" in clean_ev or "Desarmar" in clean_ev:
            clean_ev = "Desarmado"
        elif "Armado" in clean_ev or "Armar" in clean_ev:
            if "Quedarse" in clean_ev or "quedarse" in clean_ev:
                clean_ev = "ELIMINAR"
            else:
                clean_ev = "Armado"
        else:
            clean_ev = "ELIMINAR"
            
        # Refinar Nombre
        if clean_ev != "ELIMINAR":
            # Caso especial centro de alarmas
            if "centro" in nombre_ext.lower() and "control" not in nombre_ext:
                 nombre_ext = f"Centro de control ({nombre_ext})"
            
            # Valor por defecto para Armado
            if clean_ev == "Armado" and not nombre_ext:
                nombre_ext = "Armado automatico"
            elif clean_ev == "Desarmado" and not nombre_ext:
                nombre_ext = "Desarmado automatico"

        return clean_ev, nombre_ext.strip(", ").strip()

    if not df.empty:
        df[["Evento", "Nombre"]] = df.apply(lambda r: pd.Series(extract_info(r)), axis=1)
        # Limpiar Tienda de espacios sobrantes y comillas
        df["Tienda"] = df["Tienda"].astype(str).str.strip(' "').str.strip()
    
    # Filtros adicionales (según modificar_csv4.py)

    df = df[df["Evento"] != "ELIMINAR"].copy()
    
    return df

def seleccionar_eventos_primero_ultimo(df):
    """Selecciona el primer Desarmado y el último Armado por tienda."""
    if df.empty:
        return df

    resultado = []
    # Asegurar orden cronológico por tienda
    df = df.sort_values(by=['Tienda', 'Fecha_DT']).copy()
    
    tiendas = df['Tienda'].unique()
    logging.info(f"Seleccionando eventos para {len(tiendas)} tiendas.")
    
    for tienda in tiendas:
        group = df[df['Tienda'] == tienda]
        
        # Filtros de evento exactos
        desarmados = group[group['Evento'] == 'Desarmado']
        armados = group[group['Evento'] == 'Armado']
        
        row_desarmado = None
        row_armado = None
        
        # 1. Primer Desarmado del ciclo
        if not desarmados.empty:
            row_desarmado = desarmados.iloc[0]
            resultado.append(row_desarmado)
            
            # 2. Último Armado DESPUÉS del desarmado
            armados_post = armados[armados['Fecha_DT'] > row_desarmado['Fecha_DT']]
            if not armados_post.empty:
                row_armado = armados_post.iloc[-1]
                resultado.append(row_armado)
        else:
            # Si no hay desarmado, tomamos al menos el último armado (cierre sin apertura)
            if not armados.empty:
                row_armado = armados.iloc[-1]
                resultado.append(row_armado)
                
    final_df = pd.DataFrame(resultado)
    if not final_df.empty:
        print(f"[*] Reporte final compilado con {len(final_df)} filas ({len(tiendas)} tiendas procesadas)")
    return final_df

def main():
    logging.info("Iniciando procesamiento de reportes refined...")
    
    if not os.path.exists(TOKEN_PATH):
        print(f"[ERROR] No se encontró token.json")
        return
        
    notifier = GmailNotifier(TOKEN_PATH)
    notion = NotionSync()
    telegram = TelegramNotifier()
    file_count = 0
    
    try:
        config = ConfigParser()
        config.read(CONFIG_PATH)
        usar_manual = config.getboolean('Fecha', 'usar_fecha_manual', fallback=False)
        fecha_str = config.get('Fecha', 'fecha_manual') if usar_manual else datetime.now().strftime('%Y-%m-%d')
        
        # 1. Esperar archivos (Loop de reintento)
        inicio_espera = time.time()
        notifico_falta = False
        
        while True:
            # Intentar descargar correos primero en cada ciclo
            try:
                print(f"[*] Buscando nuevos correos en Gmail {fecha_str}...")
                raw_report.main()
            except Exception as e:
                logging.error(f"Error al intentar descargar correos: {e}")

            archivos_csv = [os.path.join(RAW_DIARIOS_DIR, f) for f in os.listdir(RAW_DIARIOS_DIR) 
                           if f.endswith('.csv') and f.startswith(fecha_str.replace('-', ''))]
            
            if len(archivos_csv) >= ARCHIVOS_ESPERADOS:
                print(f"[*] Archivos encontrados: {len(archivos_csv)}/{ARCHIVOS_ESPERADOS}")
                break
                
            # Verificar si ya pasaron las 7:30 AM para avisar por Telegram (si no es manual)
            ahora = datetime.now()
            if not usar_manual and ahora.hour == 7 and ahora.minute >= 30 and not notifico_falta:
                msg_aviso = f"ALERTA: El sistema sigue esperando archivos del día ({len(archivos_csv)}/{ARCHIVOS_ESPERADOS}) a las {ahora.strftime('%H:%M')}. El reporte se retrasará."
                telegram.send_message(f"⚠️ *ATENCIÓN*: {msg_aviso}") # Emoji solo para Telegram
                print(f"[!] {msg_aviso}")
                notifico_falta = True
            
            # Verificar timeout total
            if (time.time() - inicio_espera) > TIMEOUT_MAXIMO:
                logging.warning("Se alcanzó el tiempo máximo de espera sin encontrar todos los archivos.")
                break
                
            print(f"[*] Esperando archivos diarios del {fecha_str}... ({len(archivos_csv)}/{ARCHIVOS_ESPERADOS}). Reintento en {INTERVALO_REINTENTO}s...")
            time.sleep(INTERVALO_REINTENTO)
        
        # 2. Cargar archivos diarios (.csv)
        dfs = []
        for f in archivos_csv:
            try:
                # Intentar utf-8-sig primero (para BOM), luego latin-1 si falla
                try:
                    df_temp = pd.read_csv(f, encoding='utf-8-sig')
                except:
                    df_temp = pd.read_csv(f, encoding='latin-1')
                
                # Normalización inmediata de columnas (quitar BOMs o espacios)
                df_temp.columns = [str(c).replace('\ufeff', '').strip() for c in df_temp.columns]
                
                # Unificar nombres de columna de Tienda antes de concat
                col_map = {"Unidad": "Tienda", "Local": "Tienda", "unidad": "Tienda", "local": "Tienda"}
                df_temp = df_temp.rename(columns=col_map)
                
                if "Tienda" not in df_temp.columns:
                    # Cuando llega el reporte sin la columna Unidad, corresponde a:
                    df_temp["Tienda"] = "Juan Arona Oficinas administrativas"
                
                if not df_temp.empty:
                    dfs.append(df_temp)
                    print(f"[*] Cargado CSV: {os.path.basename(f)} ({len(df_temp)} filas)")
            except Exception as e:
                logging.error(f"Error leyendo {f}: {e}")

        # 3. Cargar notificaciones de medianoche (.txt)
        processor = MidnightProcessor()
        midnight_data = processor.procesar_carpeta(RAW_MIDNIGHT_DIR)
        
        if midnight_data:
            df_mid = pd.DataFrame(midnight_data)
            # Asegurar que midnight también tiene 'Tienda'
            df_mid = df_mid.rename(columns={"Unidad": "Tienda", "Local": "Tienda", "unidad": "Tienda", "local": "Tienda"})
            if "Fecha" in df_mid.columns and "Hora" in df_mid.columns:
                df_mid["Fecha"] = df_mid["Fecha"] + " " + df_mid["Hora"]
            dfs.append(df_mid)

        if not dfs:
            raise Exception("No hay datos para procesar.")

        df_total = pd.concat(dfs, ignore_index=True)
        print(f"[*] Total registros cargados: {len(df_total)}")
        
        # 4. Limpiar y Normalizar datos (incluye parsing de Fecha_DT)
        df_total = limpiar_y_normalizar(df_total)
        print(f"[*] Registros tras limpieza: {len(df_total)}")
        
        # 5. Aplicar filtro de ventana operacional (ciclo nocturno)
        target_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        prev_dt = target_dt - timedelta(days=1)
        
        df_operacional = df_total[
            (df_total["Fecha_DT"].dt.date == prev_dt) | 
            ((df_total["Fecha_DT"].dt.date == target_dt) & (df_total["Fecha_DT"].dt.hour < 8))
        ].copy()
        
        print(f"[*] Ventana operacional ({prev_dt} al {target_dt} madrugada): {len(df_operacional)} registros")
        if not df_operacional.empty:
            counts = df_operacional["Evento"].value_counts()
            print(f"[*] Conteo de eventos en ventana:\n{counts}")
            
        if df_operacional.empty:
            logging.warning(f"No hay registros en la ventana del {prev_dt} al {target_dt} (madrugada)")
            raise Exception(f"No se encontraron eventos para el ciclo operacional del {prev_dt}")

        # 6. Aplicar lógica de negocio (primer desarmado / último armado)
        df_final = seleccionar_eventos_primero_ultimo(df_operacional)
        
        if df_final.empty:
            raise Exception("El filtrado de negocio resultó en un reporte vacío.")

        # 7. Formatear y exportar reporte final (.csv)
        df_export = pd.DataFrame()
        # Formato: Fecha, Hora (con espacio tras la coma en el reporte final deseado)
        df_export['Fecha'] = df_final['Fecha_DT'].dt.strftime('%d/%m/%Y')
        
        def format_time(dt):
            # Notar el espacio extra solicitado "Fecha, Hora" -> "12/02/2026, 05:52 a.m."
            return dt.strftime(' %I:%M %p').lower().replace('pm', 'p.m.').replace('am', 'a.m.')
        
        df_export['Hora'] = df_final['Fecha_DT'].apply(format_time)
        df_export['Tienda'] = df_final['Tienda'].values
        df_export['Evento'] = df_final['Evento'].values
        df_export['Nombre'] = df_final['Nombre'].values

        # Asegurar orden exacto
        columnas_finales = ['Fecha', 'Hora', 'Tienda', 'Evento', 'Nombre']
        df_export = df_export[columnas_finales]
        
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        nombre_salida = f"Informe_estado_{fecha_str}.csv"
        ruta_salida = os.path.join(PROCESSED_DIR, nombre_salida)
        
        # Guardar con BOM para Excel
        df_export.to_csv(ruta_salida, index=False, encoding='utf-8-sig')
        
        logging.info(f"Reporte generado exitosamente: {ruta_salida}")
        print(f"[OK] Reporte generado: {nombre_salida}")

        # 8. Subir a SFTP y enviar notificaciones de éxito
        uploader = SFTPUploader(CONFIG_PATH)
        if uploader.subir_archivo(ruta_salida):
            file_count = len(df_export)
            
            # Notificaciones de éxito
            msg_exito = f"✅ *Reporte Generado*: `{nombre_salida}`\n📊 Registros: `{file_count}`\n📂 Subido a SFTP correctamente."
            
            # Alerta si el reporte es muy pequeño
            if file_count < MINIMO_FILAS_REPORTE:
                msg_exito += f"\n\n⚠️ *AVISO*: El reporte parece muy pequeño ({file_count} filas). Por favor verifique si faltan datos diarios."
            
            notifier.enviar_alerta(EMAIL_NOTIFICACION, f"[OK] Exito Reporte DC - {fecha_str}", msg_exito)
            notion.log_execution("Exitoso", f"Reporte {fecha_str} subido con {file_count} filas.", file_count)
            telegram.send_message(msg_exito)
        else:
            raise Exception("Error en la subida SFTP")

    except Exception as e:
        error_msg = f"Error en el proceso: {str(e)}"
        logging.error(error_msg)
        print(f"[ERROR] {error_msg}")
        notifier.enviar_alerta(EMAIL_NOTIFICACION, f"[!] ERROR Reporte DC", f"❌ {error_msg}")
        notion.log_execution("Fallido", error_msg, 0)
        
        # Obtener el objeto telegram localmente si falló antes de su creación
        try:
            telegram = TelegramNotifier()
            telegram.send_message(error_msg)
        except:
            pass


if __name__ == "__main__":
    main()
