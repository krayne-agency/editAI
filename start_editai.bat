@echo off
setlocal enabledelayedexpansion
title EditAI
cd /d "%~dp0"

echo.
echo  ==========================================
echo   EditAI - Demarrage
echo  ==========================================
echo.

:: ============================================================
::  1. CHERCHE PYTHON (toutes les sources connues)
:: ============================================================
set "PY_CMD="

where py      >nul 2>nul && set "PY_CMD=py"      && goto :make_venv
where python  >nul 2>nul && set "PY_CMD=python"  && goto :make_venv
where python3 >nul 2>nul && set "PY_CMD=python3" && goto :make_venv

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" ( set "PY_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" & goto :make_venv )
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"  ( set "PY_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"  & goto :make_venv )

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)
for /d %%D in ("C:\Python3*" "C:\Program Files\Python3*" "C:\Program Files (x86)\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)

:: ============================================================
::  2. PYTHON ABSENT : essaie winget, sinon Python portable
:: ============================================================
echo [!] Python introuvable. Installation automatique...
echo.

where winget >nul 2>nul
if %ERRORLEVEL%==0 (
  echo [1/3] Installation de Python via winget (peut prendre 2-3 min)...
  winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
  )
  where py >nul 2>nul && set "PY_CMD=py" && goto :make_venv
)

set "EMBED_DIR=%~dp0python-embed"
set "EMBED_PY=%EMBED_DIR%\python.exe"

if exist "%EMBED_PY%" goto :embed_pip

echo [1/3] Telechargement de Python portable...
curl -L --progress-bar -o "%~dp0python-embed.zip" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
if errorlevel 1 (
  echo [ERREUR] Telecharger Python manuellement : https://www.python.org/downloads/
  echo Coche "Add Python to PATH" puis relance ce fichier.
  start https://www.python.org/downloads/
  pause & exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%~dp0python-embed.zip' -DestinationPath '%EMBED_DIR%' -Force"
del "%~dp0python-embed.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem '%EMBED_DIR%\python*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#import site','import site' | Set-Content $_.FullName }"

:embed_pip
if not exist "%EMBED_DIR%\Scripts\pip.exe" (
  echo [2/3] Installation de pip...
  curl -L -o "%EMBED_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py"
  "%EMBED_PY%" "%EMBED_DIR%\get-pip.py" --quiet
  del "%EMBED_DIR%\get-pip.py"
)

set "PY_CMD=%EMBED_PY%"
echo [3/3] Installation des dependances...
"%EMBED_PY%" -m pip install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )
goto :launch

:: ============================================================
::  3. CREE LE VENV (Python systeme disponible)
:: ============================================================
:make_venv
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creation de l'environnement local...
  "%PY_CMD%" -m venv .venv
  if errorlevel 1 ( echo [ERREUR] Impossible de creer le venv. & pause & exit /b 1 )
)

echo [2/3] Mise a jour des dependances...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-warn-script-location
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )

:: ============================================================
::  4. LANCE L'APP
:: ============================================================
:launch
echo [3/3] Lancement d'EditAI...
if exist "editai.log" del "editai.log"

if exist ".venv\Scripts\pythonw.exe" (
  ".venv\Scripts\pythonw.exe" launcher.py
) else (
  "%PY_CMD%" launcher.py
)

timeout /t 6 /nobreak >nul 2>&1
if exist "editai.log" (
  for %%A in ("editai.log") do if %%~zA GTR 0 (
    echo.
    echo [ERREUR] EditAI a plante :
    echo -------------------------------------------
    type "editai.log"
    echo -------------------------------------------
    pause
  )
)

endlocal
