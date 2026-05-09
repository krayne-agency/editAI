@echo off
setlocal

cd /d "%~dp0"

echo [editAI] Initialisation environnement Python...

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY_CMD=py"
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    set "PY_CMD=python"
  ) else (
    echo [editAI] Python introuvable. Installe Python 3.11+ puis relance.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [editAI] Creation du venv local...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [editAI] Echec creation venv.
    pause
    exit /b 1
  )
)

echo [editAI] Installation/mise a jour des dependances...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo [editAI] Echec installation dependances.
  pause
  exit /b 1
)

echo [editAI] Lancement de la fenetre...
".venv\Scripts\pythonw.exe" launcher.py

endlocal
