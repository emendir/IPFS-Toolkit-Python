#!/bin/bash

# the absolute path of this script's directory
script_dir="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $script_dir
pdoc3 ipfs_api.py --html --force -o Documentation --template-dir ../pdoc-templates
pdoc3 ipfs_datatransmission.py --html --force -o Documentation --template-dir ../pdoc-templates
