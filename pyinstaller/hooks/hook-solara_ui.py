from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("solara-ui")
datas = collect_data_files("solara-ui")  # codespell:ignore datas
datas += copy_metadata("solara-ui")  # codespell:ignore datas
