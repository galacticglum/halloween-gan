"""Process and clean a raw dataset of halloween costumes."""

import os
import time
import tqdm
import click
import shutil
import argparse
from PIL import Image
from pathlib import Path
from face_detection import FaceDetector
from u2net_wrapper import U2Net, InvalidImageError

class ReadableDirectory(argparse.Action):
    """Makes sure that a directory argument is a valid path and readable."""
    def __call__(self, parser, namespace, value, option_string=None):
        if not value.is_dir():
            raise argparse.ArgumentTypeError(f'\'{value.resolve()}\' is not a valid path!')

        if not os.access(value, os.R_OK):
            raise argparse.ArgumentTypeError(f'\'{value.resolve()}\' is not a readable directory!')

        setattr(namespace, self.dest, value)

def get_files(source, patterns):
    """Get all the paths matching the given list of glob patterns."""

    for pattern in patterns:
        files = source.glob(f'**/{pattern}')
        for file in files:
            yield file

def _rmtree(path, ignore_errors=False, onerror=None, timeout=10):
    """
    A wrapper method for 'shutil.rmtree' that waits up to the specified
    `timeout` period, in seconds.
    """
    shutil.rmtree(path, ignore_errors, onerror)

    if path.is_dir():
        print(f'shutil.rmtree - Waiting for \'{path}\' to be removed...')
        # The destination path has yet to be deleted. Wait, at most, the timeout period.
        timeout_time = time.time() + timeout
        while time.time() <= timeout_time:
            if not path.is_dir():
                break

def main():
    """Main entrypoint when running this module from the terminal."""

    parser = argparse.ArgumentParser(description='Process and a clean a raw dataset of halloween costumes')
    parser.add_argument('dataset_source', help='The path to the directory containing the source dataset.', type=Path, action=ReadableDirectory)
    parser.add_argument('--destination', '-d', dest='dataset_destination', help='The path to the directory which the cleaned '
                        'dataset should be saved. If this is not specified, the cleaned files are saved in the same parent '
                        'folder as the source.', type=Path, default=None)
    parser.add_argument('--file-glob-patterns', nargs='+', type=str, default=['*.png', '*.jpeg', '*.jpg'],
                        help='The glob patterns to use to find files in the source directory.')
    parser.add_argument('--no-remove-transparency', action='store_false', dest='remove_transparency',
                        help='Remove transparency and replace it with a colour.')
    parser.add_argument('--bg-colour', type=str, default='WHITE', help='The colour to replace transparency with.')
    parser.add_argument('--u2net-size', type=str, default='large', help='The size of the pretrained U-2-net model. Either \'large\' or \'small\'.')
    parser.add_argument('--face_image_ratio_threshold', type=float, default=0.05, help='The maximum face-to-image area ratio that is allowed.')
    parser.add_argument('--crop-faces', dest='crop_faces', action='store_true', help='Crop out faces.')
    parser.add_argument('--yes', '-y', action='store_true', help='Yes to all.')
    args = parser.parse_args()

    # Create a destination path if none was provided.
    if args.dataset_destination is None:
        args.dataset_destination = args.dataset_source.parent / (args.dataset_source.stem + '_cleaned')

    if args.dataset_destination.exists() and any(args.dataset_destination.iterdir()):
        if not args.yes:
            click.confirm(
                f'The destination path (\'{args.dataset_destination.resolve()}\') '
                'already exists! Would you like to continue? This will overwrite the directory.',
                abort=True
            )

        _rmtree(args.dataset_destination)

    args.dataset_destination.mkdir(exist_ok=True, parents=True)

    u2net = U2Net(pretrained_model_name=args.u2net_size)
    face_detector = FaceDetector()

    files = list(get_files(args.dataset_source, args.file_glob_patterns))
    with tqdm.tqdm(files) as progress:
        for file in progress:
            progress.set_description(f'Processing {file.name}')

            # Skip images that don't have a single face in them...
            face_detection_results = face_detector.detect_faces(file)
            if len(face_detection_results) != 1:
                continue

            segmentation_map = u2net.segment_image(file)

            try:
                # Remove background from image (using U2Net)
                image = u2net.remove_background(file, segmentation_map)
                old_image_width, old_image_height = image.size
            except InvalidImageError as e:
                continue

            # Crop image to bounding box (using U2Net)
            bounding_box = u2net.get_bounding_box(segmentation_map)
            image = image.crop(bounding_box)

            # Tuple of the form (x1, y1, x2, y2)
            fbb = face_detection_results[0].bounding_box
            fbb_width = (fbb[2] - fbb[0])
            fbb_height = (fbb[3] - fbb[1])

            image_width, image_height = image.size
            # Compute the face-to-image area ratio.
            # This is used as a heuristic to filter out portrait images
            # (i.e. when the face takes up more than a certain percentage of the total image).
            face_image_ratio = (fbb_width * fbb_height) / (image_width * image_height)
            if face_image_ratio > args.face_image_ratio_threshold:
                continue

            if args.crop_faces:
                # Crop out the face...
                # This assumes that the image is of a person standing vertically.

                # Convert the bottom-right y-coordinate of the face bounding box
                # into the coordinate system AFTER cropping.
                adjusted_fbb_y2 = fbb[3] - bounding_box[1]
                image = image.crop((0, adjusted_fbb_y2 - fbb_height * 0.10, image_width, image_height))

            if args.remove_transparency:
                # Replace transparency with colour
                background_image = Image.new('RGBA', image.size, args.bg_colour)
                background_image.paste(image, (0, 0), image)
                image = background_image.convert('RGB')

            # Output processed image
            destination = args.dataset_destination / (file.stem + '.png')
            image.save(str(destination))

if __name__ == '__main__':
    main()
