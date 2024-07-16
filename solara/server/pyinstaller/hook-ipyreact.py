from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("ipyreact")
datas = collect_data_files("ipyreact")  # codespell:ignore datas
datas += copy_metadata("ipyreact")  # codespell:ignore datas
