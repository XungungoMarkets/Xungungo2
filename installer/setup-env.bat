@echo off
REM Xungungo - Script de configuracion del entorno
REM Crea el venv usando Python portable e instala dependencias

setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "PYTHON_DIR=%APP_DIR%python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

echo ============================================
echo   Xungungo - Configuracion del Entorno
echo ============================================
echo.

REM Verificar que Python portable existe
if not exist "%PYTHON_EXE%" (
    echo ERROR: No se encontro Python portable en:
    echo %PYTHON_EXE%
    echo.
    echo Por favor reinstale la aplicacion.
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
"%PYTHON_EXE%" -m venv "%APP_DIR%venv"
if errorlevel 1 (
    echo ERROR: Fallo al crear el entorno virtual.
    pause
    exit /b 1
)

echo [2/3] Activando entorno virtual...
call "%APP_DIR%venv\Scripts\activate.bat"

echo [3/3] Instalando dependencias (esto puede tardar varios minutos)...
pip install --upgrade pip
pip install -r "%APP_DIR%app\requirements.txt"
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Configuracion completada exitosamente!
echo ============================================
echo.

endlocal
exit /b 0