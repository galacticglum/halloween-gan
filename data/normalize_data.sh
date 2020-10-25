#!/bin/bash
#
#
# Perform data set normalization on a cleaned dataset.
# Run with: bash normalize_data.sh <source_directory> <destination_directory> <target_width=512> <target_height=512> <quality=-1>

convertPNGToJPG() {
    filename="$(basename "$1")"
    target="$__DESTINATION_DIRECTORY/${filename%.*}"
    quality_flag=""
    if [[ $__QUALITY -gt 0 ]]; then
        quality_flag="-quality $__QUALITY"
    else
        quality_flag=""
    fi

    convert"$quality_flag" "$1" "$target".jpg;
}
export -f convertPNGToJPG

function die () {
    echo >&2 "$@"
    exit 1
}

# Require argument
[ "$#" -ge 2 ] || die "2 arguments required, $# provided"
export __QUALITY=${5:--1}
export __DESTINATION_DIRECTORY="$2"
mkdir -p "$__DESTINATION_DIRECTORY"

# Convert images to JPG
find $1 -type f -name "*.png" | parallel --progress convertPNGToJPG

# Crop images...
WIDTH=${3:-512}
HEIGHT=${4:-512}

dims=""$WIDTH"x"$HEIGHT""
images="$()"
find $2 -type f -name "*.jpg" | xargs --max-procs=16 -n 9000 \
    mogrify -resize "$dims"\> -extent "$dims"\> -gravity center -background white