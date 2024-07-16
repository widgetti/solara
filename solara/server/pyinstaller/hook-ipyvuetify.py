from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("ipyvuetify")
datas = collect_data_files("ipyvuetify")  # codespell:ignore datas
datas += copy_metadata("ipyvuetify")  # codespell:ignore datas
