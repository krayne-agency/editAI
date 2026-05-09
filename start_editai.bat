@echo off
setlocal
title EditAI
cd /d "%~dp0"

echo.
echo  ==========================================
echo   EditAI - Demarrage
echo  ==========================================
echo.

:: 1. CHERCHE PYTHON
set "PY_CMD="

where py >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=py" & goto :make_venv )

where python >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=python" & goto :make_venv )

where python3 >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY_CMD=python3" & goto :make_venv )

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" (
  set "PY_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" & goto :make_venv
)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
  set "PY_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" & goto :make_venv
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

:: 2. PYTHON ABSENT
echo [!] Python introuvable. Installation automatique...
echo.

where winget >nul 2>nul
if %ERRORLEVEL%==0 (
  echo [1/3] Installation Python via winget...
  winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set "PY_CMD=%%D\python.exe" & goto :make_venv )
  )
  where py >nul 2>nul
  if %ERRORLEVEL%==0 ( set "PY_CMD=py" & goto :make_venv )
)

echo [1/3] Telechargement Python portable...
set "EMBED_DIR=%~dp0python-embed"
set "EMBED_PY=%EMBED_DIR%\python.exe"

if exist "%EMBED_PY%" goto :embed_pip

curl -L --progress-bar -o "%~dp0python-embed.zip" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
if %ERRORLEVEL% neq 0 (
  echo [ERREUR] Echec telechargement. Va sur https://www.python.org/downloads/
  start https://www.python.org/downloads/
  pause & exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%~dp0python-embed.zip' -DestinationPath '%EMBED_DIR%' -Force"
del "%~dp0python-embed.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem '%EMBED_DIR%\python*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#import site','import site' | Set-Content $_.FullName }"

:embed_pip
if not exist "%EMBED_DIR%\Scripts\pip.exe" (
  echo [2/3] Installation pip...
  curl -L -o "%EMBED_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py"
  "%EMBED_PY%" "%EMBED_DIR%\get-pip.py" --quiet
  del "%EMBED_DIR%\get-pip.py"
)
echo [3/3] Installation dependances...
"%EMBED_PY%" -m pip install -r requirements.txt --quiet --no-warn-script-location
if %ERRORLEVEL% neq 0 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )
set "LAUNCH_PY=%EMBED_PY%"
goto :launch

:: 3. CREE LE VENV
:make_venv
echo     Python detecte : %PY_CMD%
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creation environnement local...
  "%PY_CMD%" -m venv .venv
  if %ERRORLEVEL% neq 0 ( echo [ERREUR] venv echoue. & pause & exit /b 1 )
)
echo [2/3] Installation dependances...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-warn-script-location
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet --no-warn-script-location
if %ERRORLEVEL% neq 0 ( echo [ERREUR] Echec dependances. & pause & exit /b 1 )
if exist ".venv\Scripts\pythonw.exe" (
  set "LAUNCH_PY=.venv\Scripts\pythonw.exe"
) else (
  set "LAUNCH_PY=.venv\Scripts\python.exe"
)

:: 4. LANCE
:launch
echo [3/3] Lancement EditAI...
if exist "editai.log" del "editai.log"
"%LAUNCH_PY%" launcher.py
timeout /t 8 /nobreak >nul 2>&1
if exist "editai.log" (
  for %%A in ("editai.log") do if %%~zA GTR 0 (
    echo.
    echo [ERREUR] EditAI a plante - details ci-dessous :
    echo -------------------------------------------
    type "editai.log"
    echo -------------------------------------------
    pause
  )
)
endlocal