@echo off
REM Xungungo - Script de entrada para Windows
REM Este script activa el entorno virtual y ejecuta la aplicacion

setlocal EnableDelayedExpansion

REM Obtener el directorio donde esta este script
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM Verificar si el venv existe
if not exist "%APP_DIR%venv\Scripts\activate.bat" (
    echo Primera ejecucion - Configurando entorno...
    call "%APP_DIR%setup-env.bat"
    if errorlevel 1 (
        echo Error al configurar el entorno.
        pause
        exit /b 1
    )
)

REM Activar venv y ejecutar la aplicacion
call "%APP_DIR%venv\Scripts\activate.bat"
cd /d "%APP_DIR%app"
python run.py

endlocal