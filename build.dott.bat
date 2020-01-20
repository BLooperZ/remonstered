pyinstaller --onefile remonster.py
mkdir dist
copy dott\*.tbl dist\
copy dott\*.json dist\
copy README.dott.md dist\README.md
