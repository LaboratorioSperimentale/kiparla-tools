import pathlib
import argparse

def valid_filepath(path):
    """Custom validation function to check if the path is a valid filepath."""
    if not pathlib.Path(path).is_file():
        raise argparse.ArgumentTypeError(f"'{path}' is not a valid file.")
    return pathlib.Path(path)

def valid_dirpath(path):
    """Custom validation function to check if the path is a valid dirpath."""
    if not pathlib.Path(path).is_dir():
        raise argparse.ArgumentTypeError(f"'{path}' is not a valid directory.")
    return pathlib.Path(path)