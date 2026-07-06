# Bitácora de Cambios - Proyecto Reportes DC

Este documento resume la evolución del sistema, los problemas detectados y las soluciones implementadas para garantizar la integridad de los datos.

---

## [2026-07-06] - Refuerzo de Integridad de Datos y Estabilidad del Entorno

### Mejora: Timeout Ampliado en el Ciclo de Espera

* **Descripción**: El límite de espera de 3 horas era insuficiente para días con retrasos severos del proveedor.
* **Solución**: Se amplió `TIMEOUT_MAXIMO` de `3600 * 3` a `3600 * 5` (5 horas) en `processed_report.py`.
* **Impacto**: Menor riesgo de corte prematuro del proceso en días con alta latencia de correo.

### Mejora: Bloqueo de Envío por Reporte Insuficiente

* **Descripción**: El sistema enviaba por SFTP el reporte incluso cuando tenía menos de 50 filas (dato sospechoso), solo añadiendo una advertencia al mensaje de Telegram.
* **Solución**: Se convirtió la advertencia en un **bloqueo estricto** en `processed_report.py`. Si el reporte tiene `< MINIMO_FILAS_REPORTE` filas, el sistema:
  * Envía alerta crítica por Telegram y correo.
  * **Aborta el envío SFTP** para evitar que data incompleta llegue al cliente.
* **Impacto**: Se garantiza que únicamente reportes con datos suficientes sean publicados.

### Mejora: Manejo Crítico de Timeout con Notificación y Salida Limpia

* **Descripción**: Al alcanzarse el timeout máximo, el proceso terminaba silenciosamente con un `break`, sin notificar el fallo.
* **Solución**: Al agotar el tiempo máximo, el sistema ahora:
  * Registra el error en el log.
  * Envía alerta por Telegram y correo con mensaje `❌ CRÍTICO`.
  * Llama a `return` en lugar de `break` para salir limpiamente del flujo principal.

### Fix: Versión de Paramiko Fijada

* **Descripción**: La dependencia `paramiko` no tenía versión fijada, lo que podía causar incompatibilidades al actualizar el entorno.
* **Solución**: Se especificó `paramiko==3.5.0` en `requirements.txt` para garantizar reproducibilidad.

### Fix: Rutas y Entorno de Ejecución en `run_report.bat`

* **Descripción**: El script `.bat` usaba la ruta anterior del proyecto y el comando global `py` para ejecutar Python.
* **Solución**:
  * Se actualizó `PROJECT_DIR` a `C:\Proyectos\Proyecto_Reportes_DC`.
  * Se reemplazó `py` por `.venv\Scripts\python.exe` para asegurar que se use el entorno virtual del proyecto y no una instalación global de Python.

---

## [2026-04-16] - Correcciones de Ingesta y Nuevo Módulo de Análisis

### Problema: Correos/Archivos Duplicados

* **Descripción**: El sistema estaba descargando dos veces el mismo archivo porque el proveedor enviaba informes idénticos que generaban duplicidad al depender del `attachment_id` dinámico.
* **Solución**: Se modificó `raw_report.py` para usar el nombre del archivo (`filename`) junto al `msg['id']` como llave única, evitando la descarga redundante de reportes.

### Problema: Reporte de local "Juan Arona" sin columna de Tienda

* **Descripción**: Cuando el reporte del proveedor llegaba con datos de una sola tienda (Juan Arona), omitía la columna "Unidad", generando un archivo de 2 líneas que rompía la sintaxis y no era mapeado al local correspondiente.
* **Solución**: Se añadió lógica defensiva en `processed_report.py` para detectar automáticamente la ausencia de esta columna en archivos pequeños e inyectar el identificador `"Juan Arona Oficinas administrativas"`.

### Nueva Funcionalidad: Módulo de Evaluación de Métricas (`evaluacion.py`)

* **Descripción**: Se creó un script estadístico que procesa la historia completa de reportes.
* **Características**:
  * **a)** Porcentaje de sucursales que omiten el armado al final del día.
  * **b)** Porcentaje de sucursales que dependen del Centro de Control para su armado.
  * **c)** Tabla resumen y Ranking Top 15 de sucursales con mayores incidencias.
  * **d)** Conclusiones clave (bullets) para comités operativos enfocados en el reentrenamiento de personal.

---

## [2026-03-04] - Robustez y Alertas en Tiempo Real

### Problema: Reportes Incompletos por Retraso de Correos

* **Descripción**: Si los correos de Alarm.com llegaban después de las 06:00 AM, el script generaba un reporte solo con datos de "Midnight", resultando en archivos de ~10 filas.
* **Solución**:
  * Se implementó un **Ciclo de Espera (Wait Loop)** en `processed_report.py`. Ahora reintenta cada 5 minutos (hasta por 3 horas) y gatilla automáticamente la descarga de Gmail en cada ciclo.
  * Se añadió una alerta de **"Reporte Pequeño"** si el resultado tiene menos de 50 filas.

### Problema: Falta de Monitoreo Proactivo

* **Descripción**: No se sabía si el reporte fallaba sin entrar al servidor.
* **Solución**:
  * **Telegram Bot**: Notificaciones instantáneas de éxito, fallos y alertas de retraso (si a las 07:30 AM aún faltan archivos).
  * **Notion Sync**: Log automático en base de datos para historial de ejecuciones.

### Problema: Error de Validación en Notion (UUID vs URL)

* **Descripción**: Al pegar la URL completa de Notion en el `.env`, la API fallaba esperando solo el ID.
* **Solución**: Se añadió limpieza automática en `NotionSync` para extraer el ID de 32 caracteres de cualquier URL o texto ingresado.

---

## [2026-02-16] - Migración y Producción

### Problema: Datos "Sucios" en Nombres de Tiendas

* **Descripción**: Espacios adicionales o comillas en los CSV de origen causaban que el reporte no agrupara correctamente los eventos.
* **Solución**: Se mejoró `limpiar_y_normalizar` para hacer un `strip()` agresivo en la columna "Tienda".

### Automatización

* **Cambio**: Configuración del Programador de Tareas de Windows para ejecutar `run_report.bat` de forma desatendida.
* **Modo Producción**: Activación de `test_mode = False` en `config.ini` para habilitar subidas reales por SFTP.

---

## [2026-02-12] - Cimientos y Seguridad

### Problema: Datos Sensibles Expuestos

* **Descripción**: Credenciales y nombres de clientes estaban visibles en el código.
* **Solución**:
  * Implementación de archivo `.env` para variables de entorno.
  * Creación de `.gitignore` para evitar subir claves a GitHub.
  * Anonimización de la documentación y scripts de prueba.

### Problema: Nuevos Formatos de "Midnight"

* **Descripción**: Los correos de medianoche cambiaron de formato (asuntos, descripciones en español).
* **Solución**: Rediseño de RegEx en `MidnightProcessor` para capturar múltiples variantes de eventos de armado/desarmado.
