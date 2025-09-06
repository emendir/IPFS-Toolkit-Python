#!/bin/bash

set -e # Exit if any command fails

# the absolute paths of this script and it's directory
SCRIPT_PATH=$(realpath -s "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
cd $SCRIPT_DIR

source ${SCRIPT_DIR}/paths.sh

mkdir -p "$BUILD_DIR"

## COPY FILES
# Find all subfolders of $DOCS_DIR that contain README.md and don't start with "_"
for dir in "$DOCS_DIR"/*/; do
    folder_name=$(basename "$dir")
    if [[ -f "$dir/README.md" && "$folder_name" != _* ]]; then
        echo "Copying $folder_name..."
        cp -r "$dir" "$BUILD_DIR/"
    fi
done

cp -r $SPHINX_CONF_DIR/* "$BUILD_DIR"

## Generate Docs
sphinx-build -b html $BUILD_DIR $OUTPUT_FULL

rm -r $BUILD_DIR
