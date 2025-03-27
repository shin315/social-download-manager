from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Thu thập tất cả các sub-modules của PyQt6
hiddenimports = collect_submodules('PyQt6')

# Thu thập tất cả các files dữ liệu của PyQt6
datas = collect_data_files('PyQt6') 