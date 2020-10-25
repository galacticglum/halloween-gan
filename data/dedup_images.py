"""Removes exact or near duplicate images."""

import cv2
import tqdm
import shutil
import argparse
from enum import Enum
from pathlib import Path

from imagededup import methods
from imagededup.utils import plot_duplicates

class DedupMethod(Enum):
    """The method for duplicate removal."""
    CNN = 'cnn'
    PHASH = 'phash'
    DHASH = 'dhash'
    WHASH = 'whash'
    AHASH = 'ahash'

    def get_method_class(self):
        """Gets the `imagededup` method class."""
        return {
            DedupMethod.CNN: methods.CNN,
            DedupMethod.PHASH: methods.PHash,
            DedupMethod.DHASH: methods.DHash,
            DedupMethod.WHASH: methods.WHash,
            DedupMethod.AHASH: methods.AHash
        }[self]

parser = argparse.ArgumentParser(description='Removes exact or near duplicae images.')
parser.add_argument('source_directory', type=Path, help='The folder to search for duplicates.')
parser.add_argument('destination_directory', type=Path, help='The folder to save all unique images.')
parser.add_argument('--summary', '-s', action='store_true', dest='summarise',
                    help='Summarise the results of the deduplication.')
parser.add_argument('--method', '-m', type=DedupMethod, choices=list(DedupMethod), default=DedupMethod.PHASH,
                    help='The method to use for duplicate removal. Defaults to the perceptual hashing algorithm.')
parser.add_argument('--min-similarity-threshold', type=float, default=0.9, help='The minimum cosine similarity to consider '
                    'an image as a duplicate (used for the CNN method).')
parser.add_argument('--max-distance-threshold', type=float, default=8, help='The maximum hamming distance to consider'
                    'an image as a duplicate (used for hashing methods).')
args = parser.parse_args()

def get_all_image_filepaths(directory):
    """Return the filepath of every image in the given directory."""
    images = []
    directory = Path(directory)
    for filename in directory.glob('**/*'):
        # Check if OpenCV can read the image file,
        # if it can, the file is an image.
        image = cv2.imread(str(filename.absolute()))
        if image is None: continue
        images.append(filename)

    return images

def main():
    """Main entrypoint when running this module from the terminal."""
    method_class = args.method.get_method_class()
    method = method_class()

    find_duplicates_kwargs = {}
    if args.method == DedupMethod.CNN:
        find_duplicates_kwargs['min_similarity_threshold'] = args.min_similarity_threshold
    else:
        find_duplicates_kwargs['max_distance_threshold'] = args.max_distance_threshold

    duplicates = set(method.find_duplicates_to_remove(
        image_dir=str(args.source_directory.absolute()),
        **find_duplicates_kwargs
    ))

    # Copy non-duplicates to a new folder
    print(f'Copying non-duplicates to "{args.destination_directory}"')

    args.destination_directory.mkdir(parents=True, exist_ok=True)
    all_image_filepaths = get_all_image_filepaths(args.source_directory)
    for image_filepath in tqdm.tqdm(all_image_filepaths):
        if image_filepath.name in duplicates: continue
        new_filepath = args.destination_directory / (image_filepath.name)
        shutil.copyfile(image_filepath, new_filepath)

    if args.summarise:
        total_duplicates = len(duplicates)
        total_images = len(all_image_filepaths)
        percent_duplicates = total_duplicates / total_images * 100
        report = f'Found {total_duplicates} (out of {total_images} images; {percent_duplicates:.2f}%) duplicates.'
        divider_length = len(report)

        print('_' * divider_length)
        print('‾' * divider_length)
        print(report)

if __name__ == '__main__':
    main()