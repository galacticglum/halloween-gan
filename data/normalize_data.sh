#!/bin/bash
#
#
# Perform data set normalization on a cleaned dataset.
# Run with: bash normalize_data.sh <source_directory> <destination_directory> <target_width=512> <target_height=512> <lossy_compression=33>

convertPNGToJPG() {
    filename="$(basename "$1")"
    target="$__DESTINATION_DIRECTORY/${filename%.*}"
    convert -quality "$__LOSSY_COMPRESSION_PERCENT" "$1" "$target".jpg;
}
export -f convertPNGToJPG

function die () {
    echo >&2 "$@"
    exit 1
}

# Require argument
[ "$#" -ge 2 ] || die "2 arguments required, $# provided"
export __LOSSY_COMPRESSION_PERCENT=${5:-33}
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