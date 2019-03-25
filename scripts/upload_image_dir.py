#!/usr/bin/env python
import os
from glob import glob

from panoptes_utils.config import load_config
from panoptes_utils.google.storage import upload_observation_to_bucket
from panoptes_utils.images import fits as fits_utils
from panoptes_utils.images import make_timelapse
from panoptes_utils import error


def main(directory,
         upload=False,
         remove_jpgs=False,
         overwrite=False,
         make_timelapse=False,
         verbose=False,
         **kwargs):
    """Upload images from the given directory.

    See argparse help string below for details about parameters.
    """

    def _print(msg):
        if verbose:
            print(msg)

    config = load_config()
    try:
        pan_id = config['pan_id']
    except KeyError:
        raise error.GoogleCloudError("Can't upload without a valid pan_id in the config")

    _print("Cleaning observation directory: {}".format(directory))
    try:
        clean_observation_dir(directory,
                              remove_jpgs=remove_jpgs,
                              include_timelapse=make_timelapse,
                              timelapse_overwrite=overwrite,
                              verbose=verbose,
                              **kwargs)
    except Exception as e:
        raise error.PanError('Cannot clean observation dir: {}'.format(e))

    if upload:
        _print("Uploading to storage bucket")

        upload_observation_to_bucket(
            pan_id,
            directory,
            include_files='*',
            exclude_files='upload_manifest.log',
            verbose=verbose, **kwargs)

    return directory


def clean_observation_dir(dir_name,
                          remove_jpgs=False,
                          include_timelapse=True,
                          timelapse_overwrite=False,
                          **kwargs):
    """Clean an observation directory.

    For the given `dir_name`, will:
        * Compress FITS files
        * Remove `.solved` files
        * Create timelapse from JPG files if present (optional, default True)
        * Remove JPG files (optional, default False).

    Args:
        dir_name (str): Full path to observation directory.
        remove_jpgs (bool, optional): If JPGs should be removed after making timelapse,
            default False.
        include_timelapse (bool, optional): If a timelapse should be created, default True.
        timelapse_overwrite (bool, optional): If timelapse file should be overwritten,
            default False.
        **kwargs: Can include `verbose`.
    """
    verbose = kwargs.get('verbose', False)

    def _print(msg):
        if verbose:
            print(msg)

    def _glob(s):
        return glob(os.path.join(dir_name, s))

    _print("Cleaning dir: {}".format(dir_name))

    # Pack the fits files
    _print("Packing FITS files")
    for f in _glob('*.fits'):
        try:
            fits_utils.fpack(f)
        except Exception as e:  # pragma: no cover
            print('Could not compress fits file: {!r}'.format(e))

    # Remove .solved files
    _print('Removing .solved files')
    for f in _glob('*.solved'):
        try:
            os.remove(f)
        except OSError as e:  # pragma: no cover
            print('Could not delete file: {!r}'.format(e))

    try:
        jpg_list = _glob('*.jpg')

        if len(jpg_list) > 0:

            # Create timelapse
            if include_timelapse:
                try:
                    _print('Creating timelapse for {}'.format(dir_name))
                    video_file = make_timelapse(dir_name, overwrite=timelapse_overwrite)
                    _print('Timelapse created: {}'.format(video_file))
                except Exception as e:
                    _print("Problem creating timelapse: {}".format(e))

            # Remove jpgs
            if remove_jpgs:
                _print('Removing jpgs')
                for f in jpg_list:
                    try:
                        os.remove(f)
                    except OSError as e:
                        print('Could not delete file: {!r}'.format(e))
    except Exception as e:
        print('Problem with cleanup creating timelapse: {!r}'.format(e))


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description="Uploader for image directory")
    parser.add_argument('--directory', default=None,
                        help='Directory to be cleaned and uploaded.')
    parser.add_argument('--upload', default=False, action='store_true',
                        help='If images should be uploaded, default False.')
    parser.add_argument('--remove_jpgs', default=False, action='store_true',
                        help='If images should be removed after making timelapse, default False.')
    parser.add_argument('--make_timelapse', action='store_true', default=False,
                        help='Create a timelapse from the jpgs (requires ffmpeg), default False.')
    parser.add_argument('--overwrite', action='store_true', default=False,
                        help='Overwrite any existing files (such as timelapse), default False.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Verbose.')

    args = parser.parse_args()

    if not os.path.exists(args.directory):
        print("Directory does not exist:", args.directory)

    clean_dir = main(**vars(args))
    if args.verbose:
        print("Done cleaning for", clean_dir)
