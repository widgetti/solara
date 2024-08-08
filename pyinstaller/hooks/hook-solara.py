from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("solara")
datas = collect_data_files("solara")  # codespell:ignore datas
datas += collect_data_files("solara-ui")  # codespell:ignore datas
