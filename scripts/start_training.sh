#!/bin/bash
#
#
# An install script for composer (https://github.com/galacticglum/composer).
# Run with: bash start_training.sh <data-dir> <dataset-name> <restore-checkpoint>

function die () {
    echo >&2 "$@"
    exit 1
}

# Require argument
[ "$#" -eq 3 ] || die "3 arguments required, $# provided"

python ../stylegan2/run_training.py \
    --num-gpus=1 \
    --data-dir=$(realpath "$1") \
    --config=config-f \
    --dataset=$(realpath "$2") \
    --mirror-augment=True \
    --result-dir="../output/checkpoints/" \
    --resume=$(realpath "$3")