pyinstaller --onefile ^
    --add-data "ft\*.tbl;." ^
    --add-data "ft\*.json;." ^
    src/remonstered/scripts/remonster.py
mkdir dist
copy README.ft.md dist\README.md
