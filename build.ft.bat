pyinstaller --onefile ^
    --add-data "ft\*.tbl;." ^
    --add-data "ft\*.json;." ^
    remonster.py
mkdir dist
copy README.ft.md dist\README.md
