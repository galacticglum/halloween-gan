"""Process and clean a raw dataset of halloween costumes."""

import os
import click
import shutil
import argparse
from pathlib import Path

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
        files = args.dataset_source.glob(f'**/{pattern}')
        for file in files:
            yield file

def main():
    """Main entrypoint when running this module from the terminal."""

    parser = argparse.ArgumentParser(description='Process and a clean a raw dataset of halloween costumes')
    parser.add_argument('dataset_source', help='The path to the directory containing the source dataset.', type=Path, action=ReadableDirectory)
    parser.add_argument('--destination', '-d', dest='dataset_destination', help='The path to the directory which the cleaned '
                        'dataset should be saved. If this is not specified, the cleaned files are saved in the same parent '
                        'folder as the source.', type=Path, default=None)
    parser.add_argument('--file-glob-patterns', nargs='+', type=str, default=['*.png', '*.jpeg', '*.jpg'],
                        help='The glob patterns to use to find files in the source directory.')
    args = parser.parse_args()

    # Create a destination path if none was provided.
    if args.dataset_destination is None:
        args.dataset_destination = args.dataset_source.parent / (args.dataset_source.stem + '_cleaned')

    if args.dataset_destination.exists() and any(args.dataset_destination.iterdir()):
        click.confirm(
            f'The destination path (\'{args.dataset_destination.resolve()}\') '
            'already exists! Would you like to continue? This will overwrite the directory.',
            abort=True
        )

        shutil.rmtree(args.dataset_destination)

    args.dataset_destination.mkdir(exist_ok=True, parents=True)

    files = get_files(args.dataset_source, args.file_glob_patterns)
    for file in files:
        print(file.absolute())

if __name__ == '__main__':
    main()
