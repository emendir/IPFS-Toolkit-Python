#!/bin/bash


# the absolute paths of this script and it's directory
SCRIPT_PATH=$(realpath -s "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
cd $SCRIPT_DIR

source ${SCRIPT_DIR}/paths.sh

rm -r $BUILD_DIR >/dev/null 2>&1
rm -r $API_REF_TEMPLATE/*.rst >/dev/null 2>&1

if [ "$1" = "--outputs" ]; then
  echo "deleting outputs..."
  rm -r $OUTPUT_FULL >/dev/null 2>&1
  rm -r $OUTPUT_API >/dev/null 2>&1
fi
exit 0
