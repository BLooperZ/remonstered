pyinstaller --onefile ^
    --add-data "dott\*.tbl;." ^
    --add-data "dott\*.json;." ^
    src/scripts/remonster.py
mkdir dist
copy README.dott.md dist\README.md
