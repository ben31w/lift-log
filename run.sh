#!/usr/bin/env bash
# *nix Run Script Usage:
# ./run.sh

export PYTHONPATH=$PYTHONPATH:./src
source .venv/bin/activate
python src/app.py