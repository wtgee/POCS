import os
import subprocess

from pocs.utils import CountdownTimer
from pocs.utils import current_time
from pocs.utils import error
from pocs.utils.images import cr2 as cr2_utils
from pocs.camera import AbstractGPhotoCamera


class Camera(AbstractGPhotoCamera):

    def __init__(self, *args, **kwargs):
        kwargs['readout_time'] = 6.0
        kwargs['file_extension'] = 'cr2'
        super().__init__(*args, **kwargs)
        self.logger.debug("Connecting GPhoto2 camera")
        self.connect()
        self.logger.debug("{} connected".format(self.name))

    @property
    def is_exposing(self):
        """ True if an exposure is currently under way, otherwise False """
        return self._is_exposing

    def connect(self):
        """Connect to Canon DSLR

        Gets the serial number from the camera and sets various settings
        """
        self.logger.debug('Connecting to camera')

        # Get serial number
        _serial_number = self.get_property('serialnumber')
        if not _serial_number:
            raise error.CameraNotFound("Camera not responding: {}".format(self))

        self._serial_number = _serial_number

        # Properties to be set upon init.
        prop2index = {
            '/main/actions/viewfinder': 1,                # Screen off
            '/main/capturesettings/autoexposuremode': 3,  # 3 - Manual; 4 - Bulb
            '/main/capturesettings/continuousaf': 0,      # No auto-focus
            '/main/capturesettings/drivemode': 0,         # Single exposure
            '/main/capturesettings/focusmode': 0,         # Manual (don't try to focus)
            '/main/capturesettings/shutterspeed': 0,      # Bulb
            '/main/imgsettings/imageformat': 9,           # RAW
            '/main/imgsettings/imageformatcf': 9,         # RAW
            '/main/imgsettings/imageformatsd': 9,         # RAW
            '/main/imgsettings/iso': 1,                   # ISO 100
            '/main/settings/autopoweroff': 0,             # Don't power off
            '/main/settings/capturetarget': 0,            # Capture to RAM, for download
            '/main/settings/datetime': 'now',             # Current datetime
            '/main/settings/datetimeutc': 'now',          # Current datetime
            '/main/settings/reviewtime': 0,               # Screen off after taking pictures
        }

        owner_name = 'Project PANOPTES'
        artist_name = self.config.get('unit_id', owner_name)
        copyright = 'owner_name {}'.format(owner_name, current_time().datetime.year)

        prop2value = {
            '/main/settings/artist': artist_name,
            '/main/settings/copyright': copyright,
            '/main/settings/ownername': owner_name,
        }

        self.set_properties(prop2index, prop2value)
        self._connected = True

    def take_observation(self, *args, **kwargs):
        """Take an observation, see docs in `~pocs.camera.camera.Camera`.

        This is simply a thin-wrapper that changes the file names from CR2 to FITS.
        """
        args['filename'] = args['filename'].replace('.cr2', '.fits')
        return super().take_observation(*args, **kwargs)

    def _start_exposure(self, seconds, filename, dark, header, *args, **kwargs):
        """Take an exposure for given number of seconds and saves to provided filename

        Note:
            See `scripts/take_pic.sh`

            Tested With:
                * Canon EOS 100D

        Args:
            seconds (u.second, optional): Length of exposure
            filename (str, optional): Image is saved to this filename
        """
        script_path = '{}/scripts/take_pic.sh'.format(os.getenv('POCS'))

        run_cmd = [script_path, self.port, str(seconds), filename]

        # Take Picture
        try:
            self._is_exposing = True
            proc = subprocess.Popen(run_cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
        except error.InvalidCommand as e:
            self.logger.warning(e)
        except subprocess.TimeoutExpired:
            self.logger.debug("Still waiting for camera")
            proc.kill()
            outs, errs = proc.communicate(timeout=10)
            if errs is not None:
                self.logger.warning(errs)
        finally:
            readout_args = (filename, header)
            return readout_args

    def _poll_exposure(self, readout_args):
        """ Wait for exposure to complete.

        This is different from the parent in that it merely waits for a specified
        amount of time. Always marks `_is_exposing` as True.

        TODO: See #122

        """
        timer = CountdownTimer(duration=self._timeout)
        try:
            # Sleep for duration of exposure.
            timer.sleep()
        except Exception as err:
            self.logger.error('Error while waiting for exposure on {}: {}'.format(self, err))
            raise err
        else:
            # Camera type specific readout function
            self._readout(*readout_args)
        finally:
            self._exposure_event.set()  # Make sure this gets set regardless of readout errors
            self._is_exposing = False   # Mark exposure as complete.

    def _readout(self, cr2_path, info):
        """Reads out the image as a CR2 and converts to FITS"""
        self.logger.debug("Converting CR2 -> FITS: {}".format(cr2_path))
        fits_path = cr2_utils.cr2_to_fits(cr2_path, headers=info, remove_cr2=False)
        return fits_path
