@echo off
setlocal
title EditAI
cd /d "%~dp0"

echo.
echo  ==========================================
echo   EditAI - Demarrage
echo  ==========================================
echo.

:: ============================================================
::  1. CHERCHE PYTHON  (filtre les stubs Microsoft Store)
:: ============================================================
set "PY_CMD="

for /f "tokens=*" %%P in ('where py 2^>nul') do (
  echo %%P | findstr /i /c:"WindowsApps" >nul 2>nul
  if errorlevel 1 ( set "PY_CMD=%%P" & goto :make_venv )
)
for /f "tokens=*" %%P in ('where python 2^>nul') do (
  echo %%P | findstr /i /c:"WindowsApps" >nul 2>nul
  if errorlevel 1 ( set "PY_CMD=%%P" & goto :make_venv )
)
for /f "tokens=*" %%P in ('where python3 2^>nul') do (
  echo %%P | findstr /i /c:"WindowsApps" >nul 2>nul
  if errorlevel 1 ( set "PY_CMD=%%P" & goto :make_venv )
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)
for /d %%D in ("C:\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)
for /d %%D in ("C:\Program Files\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)
for /d %%D in ("C:\Program Files (x86)\Python3*") do (
  if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
)

:: ============================================================
::  2. PYTHON ABSENT
:: ============================================================
echo [!] Python introuvable. Tentative d installation automatique...
echo.

where winget >nul 2>nul
if %ERRORLEVEL%==0 (
  echo  Etape 1 : Installation via winget...
  winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
  )
  for /f "tokens=*" %%P in ('where py 2^>nul') do (
    echo %%P | findstr /i /c:"WindowsApps" >nul 2>nul
    if errorlevel 1 ( set "PY_CMD=%%P" & goto :make_venv )
  )
)

echo  Etape 1 : Telechargement Python portable...
set "EMBED_DIR=%~dp0python-embed"
set "EMBED_PY=%EMBED_DIR%\python.exe"

if exist "%EMBED_PY%" goto :embed_pip

curl -L --progress-bar -o "%~dp0python-embed.zip" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
if %ERRORLEVEL% neq 0 (
  echo [ERREUR] Echec telechargement.
  echo Installer Python manuellement : https://www.python.org/downloads/
  start https://www.python.org/downloads/
  pause & exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%~dp0python-embed.zip' -DestinationPath '%EMBED_DIR%' -Force"
del "%~dp0python-embed.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem '%EMBED_DIR%\python*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#import site','import site' | Set-Content $_.FullName }"

:embed_pip
if not exist "%EMBED_DIR%\Scripts\pip.exe" (
  echo  Etape 2 : Installation pip...
  curl -L -o "%EMBED_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py"
  "%EMBED_PY%" "%EMBED_DIR%\get-pip.py" --quiet
  del "%EMBED_DIR%\get-pip.py"
)
echo  Etape 3 : Installation dependances...
"%EMBED_PY%" -m pip install -r requirements.txt --quiet --no-warn-script-location
if %ERRORLEVEL% neq 0 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )
set "LAUNCH_PY=%EMBED_PY%"
goto :launch

:: ============================================================
::  3. VENV
:: ============================================================
:make_venv
echo     Python : %PY_CMD%

:: Valider le venv existant (peut etre corrompu si sync OneDrive inter-PC)
if not exist ".venv\Scripts\python.exe" goto :create_venv
".venv\Scripts\python.exe" --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo  Venv corrompu detecte ^(sync OneDrive inter-PC ?^). Suppression...
  rmdir /s /q ".venv"
)

:create_venv
if exist ".venv\Scripts\python.exe" goto :do_install

echo [1/3] Creation de l environnement local...
"%PY_CMD%" -m venv .venv
if %ERRORLEVEL% neq 0 ( echo [ERREUR] Echec creation venv. & pause & exit /b 1 )
if not exist ".venv\Scripts\python.exe" (
  echo [ERREUR] python.exe introuvable dans le venv.
  echo Cause probable : stub Microsoft Store utilise au lieu du vrai Python.
  echo Solution : https://www.python.org/downloads/ ^(cocher "Add Python to PATH"^)
  pause & exit /b 1
)

:do_install
echo [2/3] Installation dependances...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-warn-script-location
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --no-warn-script-location
if %ERRORLEVEL% neq 0 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )

if exist ".venv\Scripts\pythonw.exe" (
  set "LAUNCH_PY=.venv\Scripts\pythonw.exe"
) else (
  set "LAUNCH_PY=.venv\Scripts\python.exe"
)

:: ============================================================
::  4. LANCE
:: ============================================================
:launch
echo [3/3] Lancement EditAI...
if exist "editai.log" del "editai.log"
"%LAUNCH_PY%" launcher.py
timeout /t 8 /nobreak >nul 2>&1
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
