#!/bin/bash

set -e # Exit if any command fails

# the absolute paths of this script and it's directory
SCRIPT_PATH=$(realpath -s "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
cd $SCRIPT_DIR

source ${SCRIPT_DIR}/paths.sh

sphinx-apidoc -o $API_REF_TEMPLATE -e $SRC_DIR
sphinx-build -b html $API_REF_TEMPLATE $OUTPUT_API
