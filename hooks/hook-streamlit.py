"""Hook PyInstaller pour Streamlit - force l'inclusion des assets statiques."""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("streamlit", include_py_files=False)
hiddenimports = collect_submodules("streamlit")
