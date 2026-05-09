# editai.spec  –  PyInstaller spec pour editAI Windows standalone
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

# ── Données Streamlit (assets HTML/JS/CSS obligatoires) ──────────────────────
datas = []
datas += collect_data_files("streamlit", include_py_files=False)
datas += collect_data_files("altair")
datas += collect_data_files("pydeck")
datas += collect_data_files("pyarrow")
datas += collect_data_files("pandas")

# ── Fichiers applicatifs ──────────────────────────────────────────────────────
datas += [("app/", "app/")]
datas += [("workspace_data/", "workspace_data/")]

# ── Imports cachés nécessaires pour Streamlit ────────────────────────────────
hiddenimports = [
    "streamlit",
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.web.server",
    "streamlit.runtime",
    "streamlit.components.v1",
    "streamlit.delta_generator",
    "pandas",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.timestamps",
    "pandas._libs.skiplist",
    "numpy",
    "numpy.core._multiarray_umath",
    "altair",
    "pydeck",
    "pyarrow",
    "PIL",
    "PIL._tkinter_finder",
    "pkg_resources.extern",
    "importlib_metadata",
    "click",
    "rich",
    "watchdog.observers",
    "watchdog.observers.polling",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "starlette",
    "starlette.applications",
    "starlette.routing",
    "anyio",
    "anyio._backends._asyncio",
    "certifi",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["hooks/"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="editAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # pas de fenêtre console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="editAI",
)
