# Bitácora de Cambios - Proyecto Reportes DC

Este documento resume la evolución del sistema, los problemas detectados y las soluciones implementadas para garantizar la integridad de los datos.

---

## [2026-03-04] - Robustez y Alertas en Tiempo Real

### Problema: Reportes Incompletos por Retraso de Correos
*   **Descripción**: Si los correos de Alarm.com llegaban después de las 06:00 AM, el script generaba un reporte solo con datos de "Midnight", resultando en archivos de ~10 filas.
*   **Solución**: 
    - Se implementó un **Ciclo de Espera (Wait Loop)** en `processed_report.py`. Ahora reintenta cada 5 minutos (hasta por 3 horas) y gatilla automáticamente la descarga de Gmail en cada ciclo.
    - Se añadió una alerta de **"Reporte Pequeño"** si el resultado tiene menos de 50 filas.

### Problema: Falta de Monitoreo Proactivo
*   **Descripción**: No se sabía si el reporte fallaba sin entrar al servidor.
*   **Solución**: 
    - **Telegram Bot**: Notificaciones instantáneas de éxito, fallos y alertas de retraso (si a las 07:30 AM aún faltan archivos).
    - **Notion Sync**: Log automático en base de datos para historial de ejecuciones.

### Problema: Error de Validación en Notion (UUID vs URL)
*   **Descripción**: Al pegar la URL completa de Notion en el `.env`, la API fallaba esperando solo el ID.
*   **Solución**: Se añadió limpieza automática en `NotionSync` para extraer el ID de 32 caracteres de cualquier URL o texto ingresado.

---

## [2026-02-16] - Migración y Producción

### Problema: Datos "Sucios" en Nombres de Tiendas
*   **Descripción**: Espacios adicionales o comillas en los CSV de origen causaban que el reporte no agrupara correctamente los eventos.
*   **Solución**: Se mejoró `limpiar_y_normalizar` para hacer un `strip()` agresivo en la columna "Tienda".

### Automatización
*   **Cambio**: Configuración del Programador de Tareas de Windows para ejecutar `run_report.bat` de forma desatendida.
*   **Modo Producción**: Activación de `test_mode = False` en `config.ini` para habilitar subidas reales por SFTP.

---

## [2026-02-12] - Cimientos y Seguridad

### Problema: Datos Sensibles Expuestos
*   **Descripción**: Credenciales y nombres de clientes estaban visibles en el código.
*   **Solución**: 
    - Implementación de archivo `.env` para variables de entorno.
    - Creación de `.gitignore` para evitar subir claves a GitHub.
    - Anonimización de la documentación y scripts de prueba.

### Problema: Nuevos Formatos de "Midnight"
*   **Descripción**: Los correos de medianoche cambiaron de formato (asuntos, descripciones en español).
*   **Solución**: Rediseño de RegEx en `MidnightProcessor` para capturar múltiples variantes de eventos de armado/desarmado.
