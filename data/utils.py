"""Utility functions."""

import shutil
import argparse

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

def rmtree(path, ignore_errors=False, onerror=None, timeout=10):
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