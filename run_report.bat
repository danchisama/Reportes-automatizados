@echo off
set PROJECT_DIR=d:\Antigravity\Proyecto Reportes DC
set LOG_FILE=%PROJECT_DIR%\logs\scheduler.log

echo [%date% %time%] Iniciando procesamiento diario... >> "%LOG_FILE%"

cd /d "%PROJECT_DIR%"

:: 1. Descargar correos (Gmail)
echo [%date% %time%] Descargando correos raw... >> "%LOG_FILE%"
py scripts\raw_report.py >> "%LOG_FILE%" 2>&1

:: 2. Procesar y generar reporte final
echo [%date% %time%] Generando reporte procesado... >> "%LOG_FILE%"
py scripts\processed_report.py >> "%LOG_FILE%" 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: El script fallo con codigo %errorlevel% >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Procesamiento completado exitosamente. >> "%LOG_FILE%"
)

echo ---------------------------------------------------- >> "%LOG_FILE%"
