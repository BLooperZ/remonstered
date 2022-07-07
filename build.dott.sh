pyinstaller --onefile \
    --add-data "dott/*.tbl:." \
    --add-data "dott/*.json:." \
    src/remonstered/scripts/remonster.py
mkdir dist
cp README.dott.md dist/README.md
