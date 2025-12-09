#!/bin/bash


set -euo pipefail # Exit if any command fails

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

TEST_SCRIPT=$SCRIPT_DIR/test_with_docker.py

tmpdir=$(mktemp -d)
cd $tmpdir

echo "Creating virtual environment..."
virtualenv -qq $tmpdir/venv
source $tmpdir/venv/bin/activate

echo "Installing Packages..."
pip install -qq ipfs-tk==0.1.5 ipfs-toolkit==0.6.0rc4 brenthy_docker walytis_beta_api==2.4.11 emtest  pytest

python $TEST_SCRIPT


rm -r $tmpdir
