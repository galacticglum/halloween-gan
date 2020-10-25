#!/bin/bash
#
#
# Perform data augmentation on a cleaned dataset.
# Run with: bash augment_dash.sh <source_directory> <destination_directory>

function dataAugment () {
    image="$1"
    target="$__DESTINATION_DIRECTORY$(basename "$1")"
    suffix="png"

    convert -deskew 50                     "$image" "$target".deskew."$suffix"
    convert -blue-shift 1.1                "$image" "$target".midnight."$suffix"
    convert -fill red -colorize 5%         "$image" "$target".red."$suffix"
    convert -fill orange -colorize 5%      "$image" "$target".orange."$suffix"
    convert -fill yellow -colorize 5%      "$image" "$target".yellow."$suffix"
    convert -fill green -colorize 5%       "$image" "$target".green."$suffix"
    convert -fill blue -colorize 5%        "$image" "$target".blue."$suffix"
    convert -fill purple -colorize 5%      "$image" "$target".purple."$suffix"
    convert -adaptive-blur 3x2             "$image" "$target".blur."$suffix"
    convert -adaptive-sharpen 4x2          "$image" "$target".sharpen."$suffix"
    convert -brightness-contrast 10        "$image" "$target".brighter."$suffix"
    convert -brightness-contrast 10x10     "$image" "$target".brightercontraster."$suffix"
    convert -brightness-contrast -10       "$image" "$target".darker."$suffix"
    convert -brightness-contrast -10x10    "$image" "$target".darkerlesscontrast."$suffix"
    convert +level 5%                      "$image" "$target".contraster."$suffix"
    convert -level 5%\!                    "$image" "$target".lesscontrast."$suffix"
}

export -f dataAugment

function die () {
    echo >&2 "$@"
    exit 1
}

# Require argument
[ "$#" -eq 2 ] || die "2 arguments required, $# provided"
export __DESTINATION_DIRECTORY="$2"
mkdir -p "$__DESTINATION_DIRECTORY"
find $1 -type f -print0 |
    # Filter for images only...
    xargs -0 file --mime-type |
    grep -F 'image/' |
    cut -d ':' -f 1 |
    # Pipe to data augmentation
    parallel --progress dataAugment
