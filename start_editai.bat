@echo off
setlocal
title EditAI

cd /d "%~dp0"

echo.
echo  ============================================
echo   EditAI - Demarrage
echo  ============================================
echo.

:: -- Cherche Python ----------------------------------------------------------
where py >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=py" & goto :found_py )

where python >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=python" & goto :found_py )

where python3 >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=python3" & goto :found_py )

:: Cherche dans les emplacements d'installation standards de Python
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :found_py )
)
for /d %%D in ("%APPDATA%\Python\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :found_py )
)
for /d %%D in ("C:\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :found_py )
)
for /d %%D in ("C:\Program Files\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :found_py )
)
for /d %%D in ("C:\Program Files (x86)\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :found_py )
)

echo [ERREUR] Python introuvable sur ce PC.
echo.
echo   1. Va sur https://www.python.org/downloads/
echo   2. Telecharge Python 3.11 ou plus recent
echo   3. Lance l'installateur et COCHE "Add Python to PATH"
echo   4. Relance ce fichier
echo.
start https://www.python.org/downloads/
pause
exit /b 1

:found_py

:: -- Cree le venv si absent --------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creation de l'environnement Python local...
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERREUR] Impossible de creer le venv.
    pause
    exit /b 1
  )
)

:: -- Installe / met a jour les dependances -----------------------------------
echo [2/3] Verification des dependances ^(premiere fois = quelques minutes^)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-warn-script-location
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
  echo.
  echo [ERREUR] Echec installation dependances. Verifie ta connexion Internet.
  echo   Log disponible dans editai.log
  pause
  exit /b 1
)

:: -- Lance l'application -----------------------------------------------------
echo [3/3] Lancement d'EditAI...

:: Supprime le log precedent pour repartir propre
if exist "editai.log" del "editai.log"

:: Utilise pythonw si disponible (pas de console), sinon python normal
if exist ".venv\Scripts\pythonw.exe" (
  ".venv\Scripts\pythonw.exe" launcher.py
) else (
  start "EditAI" /B ".venv\Scripts\python.exe" launcher.py
)

:: Attends un peu et verifie si le log contient une erreur
timeout /t 5 /nobreak >nul 2>&1
if exist "editai.log" (
  for %%A in ("editai.log") do if %%~zA GTR 0 (
    echo.
    echo [ERREUR] EditAI a plante au demarrage. Details :
    echo -----------------------------------------------
    type "editai.log"
    echo -----------------------------------------------
    pause
  )
)

endlocal
