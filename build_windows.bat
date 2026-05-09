@echo off
setlocal enabledelayedexpansion

title editAI - Build Windows Standalone
cd /d "%~dp0"

echo.
echo  ████████╗██████╗ ██╗████████╗ █████╗ ██╗
echo  ██╔════╝██╔══██╗██║╚══██╔══╝██╔══██╗██║
echo  █████╗  ██║  ██║██║   ██║   ███████║██║
echo  ██╔══╝  ██║  ██║██║   ██║   ██╔══██║██║
echo  ███████╗██████╔╝██║   ██║   ██║  ██║██║
echo  ╚══════╝╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝
echo.
echo  Build Windows Standalone ^| Sans Python requis
echo ─────────────────────────────────────────────
echo.

:: 1. Vérification Python
where py >nul 2>nul
if %ERRORLEVEL%==0 ( set "PY=py" ) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 ( set "PY=python" ) else (
        echo [ERREUR] Python introuvable. Installe Python 3.11+ puis relance.
        pause & exit /b 1
    )
)
echo [1/5] Python detecte: %PY%

:: 2. Venv build dédié
if not exist ".build_venv\Scripts\python.exe" (
    echo [2/5] Creation venv build...
    %PY% -m venv .build_venv
) else (
    echo [2/5] Venv build existant, OK.
)

set "BUILDPY=.build_venv\Scripts\python.exe"
set "BUILDPIP=.build_venv\Scripts\pip.exe"

:: 3. Installation dépendances + PyInstaller
echo [3/5] Installation dependances et PyInstaller...
"%BUILDPIP%" install --upgrade pip --quiet
"%BUILDPIP%" install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
    echo [ERREUR] Echec installation dependances.
    pause & exit /b 1
)
echo        OK.

:: 4. Build PyInstaller
echo [4/5] Construction executable (peut prendre 2-5 minutes)...
if exist "dist\editAI" rmdir /s /q "dist\editAI"
"%BUILDPY%" -m PyInstaller editai.spec --noconfirm --clean
if errorlevel 1 (
    echo [ERREUR] PyInstaller a echoue. Voir la sortie ci-dessus.
    pause & exit /b 1
)
echo        Executable genere dans dist\editAI\

:: 5. Copier les données de travail + ffmpeg si disponible
echo [5/5] Finalisation du dossier distribution...
xcopy /e /i /y "workspace_data" "dist\editAI\workspace_data" >nul 2>nul

:: Copier ffmpeg si trouvé via winget
set "FFMPEG_SRC="
for /f "delims=" %%F in ('dir /s /b "%LOCALAPPDATA%\Microsoft\WinGet\Packages\*ffmpeg.exe" 2^>nul') do (
    if not defined FFMPEG_SRC set "FFMPEG_SRC=%%~dpF"
)
if defined FFMPEG_SRC (
    echo        Copie ffmpeg depuis %FFMPEG_SRC%...
    xcopy /y "%FFMPEG_SRC%ffmpeg.exe"  "dist\editAI\_internal\" >nul 2>nul
    xcopy /y "%FFMPEG_SRC%ffprobe.exe" "dist\editAI\_internal\" >nul 2>nul
    echo        ffmpeg inclus dans le build.
) else (
    echo        [ATTENTION] ffmpeg non trouve. L'utilisateur devra l'installer.
)

:: Créer lanceur VBS (sans fenêtre console noire)
echo Set ws = CreateObject("WScript.Shell")> "dist\editAI\Lancer_editAI.vbs"
echo ws.Run Chr(34) ^& Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) ^& "editAI.exe" ^& Chr(34), 0, False>> "dist\editAI\Lancer_editAI.vbs"

echo.
echo ═══════════════════════════════════════════════
echo  Build termine avec succes!
echo  Distribution: dist\editAI\
echo  Lancer:       dist\editAI\editAI.exe
echo               ou dist\editAI\Lancer_editAI.vbs
echo ═══════════════════════════════════════════════
echo.
pause
