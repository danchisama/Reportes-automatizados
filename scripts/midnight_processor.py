import os
import re
import pandas as pd
from datetime import datetime

class MidnightProcessor:
    def __init__(self):
        # Patrones de extracción afinados (de insertar_midnight_v2.7)
        self.patrones = [
            # Patrón 3 (El más completo): formato tipo "Partición fue puesto en Armado..."
            re.compile(
                r"""
                ^\ufeff?(?:\[External\]|Subject:)\s+             # Encabezado (acepta BOM opcional, External o Subject)
                (?P<tienda>\d+\s*-\s*[^:]+?)\s*:\s+              # Código - Tienda (espacio flexible antes de :)
                (?:El\s+)?(?:Partici[oó]n|Partition|Panel)       # "Partition", "Partición" o "Panel"
                (?:\s+\d+)?\s+                                   # Número opcional (Partition 1)
                (?:fue\s+puesto\s+en\s+Armado|se\s+arm[oó])      # Acción flexible (puesto en Armado / se armó)
                (?:\s+\((?P<modo>[^)]+)\))?\s+                   # Modo opcional (Salir/Quedarse)
                (?:por\s+(?P<nombre>(?:\d+\s*-\s*)?[^\d]+?)\s+)? # "por <nombre>" opcional
                a\s+las\s+(?P<hora>\d{1,2}:\d{2})\s*             # Hora
                (?P<ampm>a\.?\s*\.?m\.?|p\.?\s*\.?m\.?)\s*       # Acepta "a.m.", "a. m.", "am"
                (?:\((?P<origen>[^)]+)\))?                       # Origen opcional en paréntesis
                """,
                re.IGNORECASE | re.VERBOSE | re.MULTILINE
            ),
            # Patrones antiguos como respaldo
            re.compile(r"^\[External\]\s+(?P<tienda>\d+\s*-\s*[^:]+):\s+.*?por\s+(?P<nombre>[^\d]+?)\s+a\s+las\s+(?P<hora>\d{1,2}:\d{2})", re.IGNORECASE | re.MULTILINE),
            re.compile(r"^\[External\]\s+(?P<tienda>\d+\s*-\s*[^:]+):\s+(?P<entrevista>.*?)\s+por\s+(?P<nombre>.*?)\s+a\s+las\s+(?P<hora>\d{1,2}:\d{2})", re.IGNORECASE | re.MULTILINE)
        ]

    def extraer_datos(self, texto, nombre_archivo):
        texto = texto.replace('\u00A0', ' ').replace('\u202F', ' ').replace('\xa0', ' ')
        
        fecha_match = re.search(r'midnight-(\d{4}-\d{2}-\d{2})', nombre_archivo)
        if not fecha_match:
            return None
        
        fecha_obj = datetime.strptime(fecha_match.group(1), '%Y-%m-%d')
        fecha_formateada = fecha_obj.strftime('%d/%m/%Y')

        for patron in self.patrones:
            match = patron.search(texto)
            if match:
                res = match.groupdict()
                tienda = res.get('tienda', '').strip()
                hora = res.get('hora', '').strip()
                
                ampm = 'a.m.'
                if 'ampm' in res and res['ampm']:
                    raw_ampm = res['ampm'].lower().replace(' ', '').replace('.', '')
                    if 'p' in raw_ampm: ampm = 'p.m.'
                    else: ampm = 'a.m.'
                
                hora_completa = f"{hora} {ampm}"

                if 'origen' in res and res['origen']:
                    nombre = f"Centro de control ({res['origen'].strip()})"
                elif 'nombre' in res and res['nombre']:
                    nombre = res['nombre'].strip()
                else:
                    nombre = "Centro de control"

                return {
                    'Fecha': fecha_formateada,
                    'Hora': hora_completa,
                    'Tienda': tienda,
                    'Evento': 'Armado',
                    'Nombre': nombre
                }
        return None

    def procesar_carpeta(self, ruta_midnight):
        resultados = []
        if not os.path.exists(ruta_midnight):
            return resultados

        for fname in os.listdir(ruta_midnight):
            if fname.endswith(".txt"):
                ruta_completa = os.path.join(ruta_midnight, fname)
                with open(ruta_completa, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                    data = self.extraer_datos(contenido, fname)
                    if data:
                        resultados.append(data)
        
        return resultados

if __name__ == "__main__":
    pass
