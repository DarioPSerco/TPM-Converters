# -*- coding: cp1252 -*-
#
# 
#
#
import imghdr
import logging
import os
import platform
import struct
import subprocess
import sys
import traceback

from pathlib import Path
from typing import Dict, List, Optional, Union

import pyvips

from .esaProducts import definitions_EoSip


# try to have PIL library
PilReady = 0
try:
    import PIL
    from PIL import Image, ImageEnhance, ImageFile, ImageOps
    from PIL.Image import Image as PILImage
    Image.MAX_IMAGE_PIXELS = None  # circumvent decompression bomb error
    ImageFile.LOAD_TRUNCATED_IMAGES = True  # circumvent broken data stream when reading image file error
    PilReady = 1
except:
    pass

# try to have GDAL library
GDALREADY = False
try:
    from osgeo import gdal
    from osgeo.gdalconst import *

    GDALREADY = True
except:
    pass


logging.getLogger('pyvips').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.WARNING)

OP_SYS = platform.uname().system.lower()
SUPPORTED_TYPE = ["JPEG", "JPG", "PNG"]
a = [definitions_EoSip.getDefinition(definitions_EoSip.FIXED__JPEG_EXT)]

# DEBUG
debug = False

# command line used to build the browse, when PIL is not used
if OP_SYS == 'windows':
    externalConverterCommand = "gm.exe convert -verbose "
else:
    externalConverterCommand = "/bin/sh -c \"/usr/bin/gm convert -verbose "

DEFAULT_BROWSE_IMAGE_SIZE = 1000

# get image dimension without external library
# work only for PNG, JPEG, GIF
def __get_image_size(fname):
    """Determine the image type of fhandle and return its size.
    from draco"""
    fhandle = open(fname, 'rb')
    head = fhandle.read(24)
    if len(head) != 24:
        raise Exception("can not read image header")
    if imghdr.what(fname) == 'png':
        check = struct.unpack('>i', head[4:8])[0]
        if check != 0x0d0a1a0a:
            return
        width, height = struct.unpack('>ii', head[16:24])
    elif imghdr.what(fname) == 'gif':
        width, height = struct.unpack('<HH', head[6:10])
    elif imghdr.what(fname) == 'jpeg':
        try:
            fhandle.seek(0)  # Read 0xff next
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                fhandle.seek(size, 1)
                byte = fhandle.read(1)
                while ord(byte) == 0xff:
                    byte = fhandle.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', fhandle.read(2))[0] - 2
            # We are at a SOFn block
            fhandle.seek(1, 1)  # Skip `precision' byte.
            height, width = struct.unpack('>HH', fhandle.read(4))
        except Exception:  # IGNORE:W0703
            return
    else:
        raise Exception("unknown image type:%s" % imghdr.what(fname))
    return width, height


#
# get tif image size using PIL
#
def __get_tif_size_pil(fname):
    if debug:
        print("__get_tif_size_pil on:%s" % fname)
    im = PIL.Image.open(fname)
    return im.size  # is a tuple


#
# get tif image size using GDAL
#
def __get_tif_size_gdal(fname):
    if debug:
        print("__get_tif_size_gdal on:%s" % fname)
    dataset = gdal.Open(fname, GA_ReadOnly)
    return dataset.RasterXSize, dataset.RasterYSize


#
# get image size using GDAL
#
def get_size_gdal(fname):
    # if DEBUG:
    print("get_size_gdal on:%s" % fname)
    dataset = gdal.Open(fname, GA_ReadOnly)
    # os._exit(0)
    return dataset.RasterXSize, dataset.RasterYSize


#
#
#
def get_image_size(fname):
    pos = fname.rfind('.')
    ext = ''
    if pos > 0:
        ext = fname[pos + 1:]
    if debug:
        print("get_image_size '%s' extension:%s" % (fname, ext))

    ext = ext.upper()
    if ext == 'PNG' or ext == 'GIF' or ext == 'JPEG' or ext == 'JPG':
        try:
            w, h = __get_image_size(fname)
            return __get_image_size(fname)
        except:
            if PilReady == 1:
                w, h = __get_tif_size_pil(fname)
                print(" get_image_size PIL found:%s %s" % (w, h))
                return w, h

    elif ext == 'TIF':
        if PilReady == 1:
            try:
                w, h = __get_tif_size_pil(fname)
                print(" get_image_size PIL found:%s %s" % (w, h))
                return w, h
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" USING PIL Error %s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc()))
                if GDALREADY:
                    w, h = __get_tif_size_gdal(fname)
                    print(" get_image_size GDAL found:%s %s" % (w, h))
                    return w, h
                else:
                    raise Exception('can not get image size: PIL failed and no GDAL')
        else:
            if GDALREADY:
                w, h = __get_tif_size_gdal(fname)
                print(" get_image_size GDAL found:%s %s" % (w, h))
                return w, h
            else:
                raise Exception('can not get image size: no PIL and GDAL failed')
    else:
        raise Exception('unknown extension:%s' % ext)


#
# make a browse image
#
def makeBrowse(type="JPEG", src=None, dest=None, resizePercent=-1, w=-1, h=-1, enhance=None, transparent=False,
               transparentThreshold=0):
    try:
        SUPPORTED_TYPE.index(type)
    except:
        raise Exception("unsupported browse type:%s" % type)
    #
    # convert to supported type
    #
    if type.lower() == "jpg":
        type = "JPEG"

    ok = False
    if PilReady == 1:
        try:
            ok = makeBrowsePil(type, src, dest, resizePercent, w, h, enhance, transparent, True, transparentThreshold)
        except Exception as e:
            print(" ######################################## 0 can not make browse using PIL:%s" % e)
            if debug:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exc(file=sys.stdout)
            try:
                ok = externalMakeBrowse(type, src, dest, resizePercent, transparent, False)
            except Exception as e:
                print(" ######################################## 1 Error making browse using external call:%s" % e)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exc(file=sys.stdout)
                raise e
                # pass
    else:
        try:
            ok = externalMakeBrowse(type, src, dest, resizePercent, transparent, False, transparentThreshold)
        except Exception as e:
            print(" ######################################## 2 Error making browse using external call:%s" % e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
            raise e
            # pass

    return ok


#
# run external command to generate the browse
#
def externalMakeBrowse(type="JPEG", src=None, dest=None, resizePercent=100, transparent=False, showTraceback=False,
                       transparentThreshold=0):
    try:
        src = src.replace("//", "/")
        dest = dest.replace("//", "/")
        if debug:
            print(" external resize image:%s into:%s" % (src, dest))
        if resizePercent == -1 or resizePercent == 100:
            command = "%s %s %s\"" % (externalConverterCommand, src, dest)
        else:
            command = "%s -scale %s%s %s %s\"" % (externalConverterCommand, resizePercent, '%', src, dest)
        # if DEBUG:
        print("command:'%s'" % command)
        retval = subprocess.call(command, shell=True)
        print(" ######################################## external make browse exit code:%s" % retval)
        if debug:
            print("  retval:%s" % retval)
        if retval != 0:
            raise Exception("Error externalMakeJpeg: subprocess exit code is not 0 but:%s" % retval)
        if debug:
            print("  browse saved as:%s" % dest)
        return True
    except Exception as e:
        print(" ######################################## 3 externalMakeBrowse error:%s" % e)
        if showTraceback:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
        raise e


#
# test
#
def splitBands(img=None):
    newIm = None
    try:
        r, g, b, a = img.split()
        if debug:
            print("  im splitted")
        newIm = Image.merge("RGB", (r, g, b))
    except:
        r, g, b = img.split()
        if debug:
            print("  im splitted")
        newIm = Image.merge("RGB", (r, g, b))
    return newIm


def resize_img_vips(src: Path, dest: Path, scale: float, raise_err: bool = False) -> int:
    import subprocess

    if type(src) == str:
        src = Path(src).resolve()
    if type(dest) == str:
        dest = Path(dest).resolve()

    with Image.open(src) as img:
        src_img_width, src_img_height = img.size
        img_bands = img.getbands()
        img_mode = img.mode

    w, h = int(round(src_img_width)), int(round(src_img_height))
    cmd = [
        'vips.exe' if OP_SYS == 'windows' else 'vips', "resize",
        str(src.resolve()), f"{w * scale}x{h * scale}", str(dest.resolve())
    ]

    print("resize_img_vips:: " + ' '.join(cmd))
    try:
        process = subprocess.run(cmd, check=False)
    except Exception as err:
        if raise_err:
            raise err
        print(f"resize_img_gm:: {type(err).__name__}: {err.args[0]}")
        return 1

    return process.returncode


def resize_img_pyvips(src: Path, dest: Path = None, scale: float = None, max_dim: int = None, raise_err: bool = False) -> pyvips.Image:
    import logging
    logging.basicConfig(level=logging.WARNING)

    if max_dim is None and scale is None:
        raise ValueError("Either one of max_dim, or scale, must be specified")

    try:
        import pyvips
    except (ModuleNotFoundError, OSError) as err:
        if raise_err:
            raise err
        print("resize_img_pyvips:: ModuleNotFoundError: pyvips not installed")
        return 1

    if type(src) == str:
        src = Path(src).resolve()
    if type(dest) == str:
        dest = Path(dest).resolve()

    try:
        if not isinstance(src, pyvips.Image):
            tmp_img = pyvips.Image.new_from_file(src, access="sequential")
        else:
            tmp_img = src

        if max_dim is not None:
            width, height = tmp_img.get('width'), tmp_img.get('height')
            scale = max_dim / max((width, height))

        tmp_img = tmp_img.resize(scale)
        if dest is not None:
            if dest.suffix.lower() == '.jp2':
                tmp_img.jp2ksave(dest, lossless=True)
            else:
                tmp_img.write_to_file(dest)

    except Exception as err:
        if raise_err:
            raise err
        print(f"resize_img_pyvips:: {type(err).__name__}: {err.args[0]}")
        # return 1
        return

    return tmp_img
    return 0 if dest.exists() else 1


def resize_img_gm(src: Path, dest: Path, scale: float, raise_err: bool = False) -> int:
    import platform
    import subprocess

    if type(src) == str:
        src = Path(src).resolve()
    if type(dest) == str:
        dest = Path(dest).resolve()

    with Image.open(src) as img:
        src_img_width, src_img_height = img.size
        img_bands = img.getbands()
        img_mode = img.mode

    w, h = int(round(src_img_width)), int(round(src_img_height))
    cmd = [
        'gm.exe', 'convert',
        str(src.resolve()), "-resize", f"{w * scale}x{h * scale}", str(dest.resolve())
    ][0 if OP_SYS == 'windows' else 1:]

    print("resize_img_gm:: " + ' '.join(cmd))
    try:
        process = subprocess.run(cmd, check=False)
    except Exception as err:
        if raise_err:
            raise err
        print(f"resize_img_gm:: {type(err).__name__}: {err.args[0]}")
        return 1

    return process.returncode


def resize_img_gdal(src: Path, dest: Path, scale: float, raise_err: bool = False) -> int:
    gdal_output_formats_mapping = {
        '.JP2': 'JP2OpenJPEG', '.PNG': 'PNG', '.TIF': 'GTiff'
    }

    try:
        input_format = gdal_output_formats_mapping.get(src.suffix.upper())
        output_format = gdal_output_formats_mapping.get(dest.suffix.upper())
        if output_format is None in (input_format, output_format):
            raise IOError(
                f"{dest.suffix} image type not recognised for gdal_translate"
            )
        cmd = ["gdal_translate", "-r", "lanczos", "-of", output_format, "-ot", "UInt16", "-if", input_format,
               "-outsize", f"{scale * 100}%", f"{scale * 100}%", str(src), str(dest)]
        print("resize_img_gdal:: " + ' '.join(cmd))
        process = subprocess.run(cmd, check=False)
    except Exception as err:
        if raise_err:
            raise err
        print(f"resize_img_gdal:: {type(err).__name__}: {err.args[0]}")
        return 1

    return process.returncode


def resize_img(src: Path, dest: Path, scale: float, raise_err: bool = False) -> int:
    if type(src) is str:
        src = Path(src)
    if type(dest) is str:
        dest = Path(dest)

    try:
        for resize_method in (resize_img_pyvips, resize_img_vips, resize_img_gm, resize_img_gdal):
            returncode = resize_method(src, dest, scale)
            if returncode == 0:
                return returncode
        else:
            raise RuntimeError("No resize methods succeeded")
    except RuntimeError as err:
        if raise_err:
            raise err
        print(f"resize_img:: {type(err).__name__}: {err.args[0]}")
        return 1

def get_nbands(image):
    import pyvips

    image = pyvips.Image.new_from_file(image, access="sequential")
    return image.get('bands')


def get_png_bit_depth(png_file_path):
    with open(png_file_path, "rb") as f:
        f.seek(24)  # Move to IHDR chunk's bit-depth position
        bit_depth = int.from_bytes(f.read(1), "big")
    return bit_depth


def extract_and_join_bands(input_image_path, output_image_path, band_indexes, color_mode=None):
    import pyvips

    if len(band_indexes) > 4:
        raise ValueError('unexpected number of bands requested')

    # Load the input image
    image = pyvips.Image.new_from_file(input_image_path, access="sequential")
    original_color_mode = image.get('interpretation')


    if color_mode is None:
        if len(band_indexes) in (1, 2):
            color_mode = pyvips.Interpretation.GREY16
        elif len(band_indexes) == 3:
            color_mode = pyvips.Interpretation.RGB if image.get('bits-per-sample') == 8 else pyvips.Interpretation.RGB16
        else:
            color_mode = pyvips.Interpretation.SRGB

    # Extract the bands
    bands = [image[idx].colourspace(color_mode)[0] for idx in band_indexes]

    merged_bands = bands[0]
    if len(bands) != 1:
        for band in bands[1:]:
            merged_bands = merged_bands.bandjoin(band)

    merged_bands = merged_bands.colourspace(color_mode)

    # Save the merged 3-band image
    output_image_path = Path(output_image_path) if isinstance(output_image_path, str) else output_image_path
    if output_image_path.suffix.lower() == '.jp2':
        merged_bands.jp2ksave(output_image_path, lossless=True)
    else:
        merged_bands.write_to_file(output_image_path)


def generate_temporary_image_name(directory: Union[str, Path], suffix: str) -> Path:
    from pathlib import Path
    import random

    if isinstance(directory, str):
        directory = Path(directory)

    rand_chars = "".join([chr(random.randint(65, 90)) for _ in range(8)])
    tmp_img_file = directory / f'tmp_img_{rand_chars}.{suffix}'
    while tmp_img_file.exists():
        rand_chars = "".join([chr(random.randint(65, 90)) for _ in range(8)])
        new_name = f'tmp_img_{rand_chars}.{suffix}'
        tmp_img_file = tmp_img_file.parent / new_name

    return tmp_img_file

def get_detailed_img_info(image_file: Union[Path, str]) -> Dict:
    from osgeo import gdal

    img = gdal.Open(str(image_file))

    return gdal.Info(img, options=gdal.InfoOptions(format='json'))


def _estimate_vips_disc_space_reqd(image_arr_2d, safety_factor=1.5):
    """
    Estimate a disc space required for processing of a 2D array of pyvips.Image objects

    image_arr_2d : list[list[pyvips.Image]]
        2D array of images (rows x cols)
    safety_factor : float
        Multiplier to account for intermediate operations
    """
    total_bytes = 0

    for row in image_arr_2d:
        for im in row:
            width = im.width
            height = im.height
            bands = im.bands
            bytes_per_band = im.get('bits-per-sample') / 8
            total_bytes += width * height * bands * bytes_per_band

    # Apply safety factor to account for intermediate operations
    return int(total_bytes * safety_factor)


def _dir_available_space_bytes(path):
    import os

    stats = os.statvfs(path)
    # f_frsize = fragment size, f_bavail = free blocks available to non-root
    return stats.f_frsize * stats.f_bavail


def _human_readable_bytes(num_bytes):
    for unit in ['B','K','M','G','T','P']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f}E"


def create_mosaic_pyvips(image_arr: List[List[Union[str, Path]]],
                         out_file: Union[str, Path],
                         resize: bool = True):
    """
    Create mosaic from array of individual images using pyvips

    Parameters
    ----------
    image_arr:
        2D array of full file paths to the image files to be mosaiced. Arrangement of file paths within 2D array should
        represent arrangement of their respective images within the output mosaic
    out_file:
        File to which to write the full mosaic
    resize:
        Whether to resize after mosaicing (will resize to imageUtil.DEFAULT_BROWSE_IMAGE_SIZE). Default is True

    Returns
    -------
    None
    """
    import pyvips

    n_rows, n_cols = len(image_arr), max(len(row) for row in image_arr)

    # Convert to pyvips.Image instances
    pyvips_image_arr = [
        [pyvips.Image.new_from_file(im_, memory=False, access=pyvips.Access.SEQUENTIAL) for im_ in row]
        # [pyvips.Image.new_from_file(im_) for im_ in row]
        for row in image_arr
    ]

    # Ensure that an adequate (in terms of space requirements) temp directory
    # is available for pyvips to do its work
    tmpdir_envvar_existed = 'TMPDIR' in os.environ
    previous_tmpdir_value = os.environ.get('TMPDIR')
    tmpdir = os.environ.get('TMPDIR')
    tmpdir = '/tmp' if tmpdir is None else tmpdir
    disc_space_reqd = _estimate_vips_disc_space_reqd(pyvips_image_arr, safety_factor=1.5)
    disc_space_in_tmp = _dir_available_space_bytes(tmpdir)

    if disc_space_in_tmp < disc_space_reqd:
        os.environ['TMPDIR'] = str(Path(image_arr[0][0]).parent.resolve())

        disc_space_in_tmp = _dir_available_space_bytes(os.environ['TMPDIR'])
        if disc_space_in_tmp < disc_space_reqd:
            logging.getLogger().warning(
                f"VIPS may use more space than available in {os.environ['TMPDIR']}. "
                f"Space required (+50%): {_human_readable_bytes(disc_space_reqd)}; "
                f"Space available: {_human_readable_bytes(disc_space_in_tmp)}"
            )

    # Flatten array as input to mosaic/join operation and assume no spacing/overlap
    im: pyvips.Image = pyvips.Image.arrayjoin(
        [im for row in pyvips_image_arr for im in row],
        across=n_cols, shim=0, background=0, hspacing=0, vspacing=0
    )

    # Calculate extent of covered area (arrayjoin pads on either right and bottom)
    x_dims = max(sum(im.width for im in row) for row in pyvips_image_arr)
    y_dims = max(sum(im.height for im in [row[i] for row in pyvips_image_arr]) for i in range(n_cols))

    # Crop to calculated image dimensions, resize if requested, then write to file
    im = im.crop(0, 0, x_dims, y_dims)

    if resize:
        im = im.resize(DEFAULT_BROWSE_IMAGE_SIZE / max((x_dims, y_dims)))

    out_file = Path(out_file) if isinstance(out_file, str) else out_file
    if out_file.suffix.lower() == '.jp2':
        im.jp2ksave(out_file, lossless=True)
    else:
        im.write_to_file(out_file)

    # Reset TMPDIR to previous existence/value
    if 'TMPDIR' in os.environ:
        if not tmpdir_envvar_existed:
            del os.environ['TMPDIR']
        else:
            os.environ['TMPDIR'] = previous_tmpdir_value


def numpy_rgb_to_grayscale(rgb_arr):
    import numpy as np

    coeffs = np.array([0.2989, 0.587, 0.114])
    return np.apply_along_axis(lambda x: np.sum(coeffs * x), axis=2, arr=rgb_arr)


def image_mean_and_std(input_img: Union[str, Path]) -> float:
    import PIL
    import numpy as np

    with PIL.Image.open(input_img) as img:
        if 'I;16' in img.mode:
            img = img.convert('L')
        img_mode = img.mode
        img_arr = np.asarray(img)

    if img_mode == 'L':
        mask = np.where(img_arr < 1, False, True)
    else:
        mask = np.where(np.sum(img_arr, axis=2) < 1, False, True)

    return img_arr[mask].mean(), img_arr[mask].std()


def boost_brightness_cv2(input_img, output_img, desired_img_mean=0.5):
    import cv2
    import numpy as np

    img_arr = cv2.imread(input_img, cv2.IMREAD_UNCHANGED)

    is_grayscale = len(img_arr.shape) == 2
    is_rgb = len(img_arr.shape) == 3
    is_rgba = len(img_arr.shape) == 4

    if is_grayscale:
        grey_img_arr = img_arr
    elif is_rgb:
        grey_img_arr = np.mean(img_arr, axis=2).round().astype(img_arr.dtype)
    else:
        raise ValueError("Cannot handle transparency yet")

    bit_depth = {'uint16': 16, 'uint8': 8}[str(img_arr.dtype)]

    if is_grayscale:
        mask = np.where(img_arr == 0, False, True)
    else:
        mask = np.where(np.sum(img_arr, axis=2) == 0, False, True)

    mean = grey_img_arr[mask].mean()

    diff = desired_img_mean * (255 if bit_depth == 8 else 65535) - mean
    if is_grayscale:
        new_img_arr = img_arr + diff
        new_img_arr = np.where(mask, new_img_arr, 0.0)
    else:
        # cv2 reads/writes in order BGR, not RGB!
        img_b_arr, img_g_arr, img_r_arr = img_arr[..., 0], img_arr[..., 1], img_arr[..., 2]

        # Avoid division by zero
        img_r_arr = np.where(img_r_arr < 1, 1, img_r_arr)
        img_g_arr = np.where(img_g_arr < 1, 1, img_g_arr)
        img_b_arr = np.where(img_b_arr < 1, 1, img_b_arr)

        # Calculate new RGB values for increased brightness, but maintaining hue
        new_img_r_arr = img_r_arr + 3. * diff / (1. + img_g_arr / img_r_arr + img_b_arr / img_r_arr)
        new_img_g_arr = img_g_arr + 3. * diff / (1. + img_r_arr / img_g_arr + img_b_arr / img_g_arr)
        new_img_b_arr = img_b_arr + 3. * diff / (1. + img_r_arr / img_b_arr + img_g_arr / img_b_arr)

        # Create new RGB image array
        new_img_arr = np.stack((new_img_b_arr, new_img_g_arr, new_img_r_arr), axis=-1)
        new_img_arr = np.where(mask[..., np.newaxis], new_img_arr, 0.0)

    # Ensure all values are within range 0 -> 255
    new_img_arr = np.where(np.isnan(new_img_arr), 0., new_img_arr)
    new_img_arr = np.where(new_img_arr > (255 if bit_depth == 8 else 65535), (255 if bit_depth == 8 else 65535), new_img_arr)
    new_img_arr = np.where(new_img_arr < 0, 0, new_img_arr).astype((np.uint8 if bit_depth == 8 else np.uint16))

    cv2.imwrite(output_img, new_img_arr)

def boost_brightness(input_img, output_img, desired_img_mean=50.0):
    import PIL
    import numpy as np

    with PIL.Image.open(input_img) as img:
        if 'I;16' in img.mode:
            img = img.convert('L')
        img_mode = img.mode
        img_arr = np.asarray(img)

    if img_mode == 'L':
        mask = np.where(img_arr < 1, False, True)
    else:
        mask = np.where(np.sum(img_arr, axis=2) < 1, False, True)

    mean = img_arr[mask].mean()

    diff = desired_img_mean - mean
    if img_mode == 'L':
        new_img_arr = img_arr + diff
        new_img_arr = np.where(mask, new_img_arr, 0.0)
    else:
        img_r_arr, img_g_arr, img_b_arr = img_arr[..., 0], img_arr[..., 1], img_arr[..., 2]

        # Avoid division by zero
        img_r_arr = np.where(img_r_arr < 1, 1, img_r_arr)
        img_g_arr = np.where(img_g_arr < 1, 1, img_g_arr)
        img_b_arr = np.where(img_b_arr < 1, 1, img_b_arr)

        # Calculate new RGB values for increased brightness, but maintaining hue
        new_img_r_arr = img_r_arr + 3. * diff / (1. + img_g_arr / img_r_arr + img_b_arr / img_r_arr)
        new_img_g_arr = img_g_arr + 3. * diff / (1. + img_r_arr / img_g_arr + img_b_arr / img_g_arr)
        new_img_b_arr = img_b_arr + 3. * diff / (1. + img_r_arr / img_b_arr + img_g_arr / img_b_arr)

        # Create new RGB image array
        new_img_arr = np.stack((new_img_r_arr, new_img_g_arr, new_img_b_arr), axis=-1)
        new_img_arr = np.where(mask[..., np.newaxis], new_img_arr, 0.0)

    # Ensure all values are within range 0 -> 255
    new_img_arr = np.where(np.isnan(new_img_arr), 0., new_img_arr)
    new_img_arr = np.where(new_img_arr > 255, 255, new_img_arr)
    new_img_arr = np.where(new_img_arr < 0, 0, new_img_arr).astype('uint8')

    with PIL.Image.fromarray(new_img_arr) as new_img:
        new_img.save(output_img)

def cv2_clahe(input_image, output_image):
    import numpy as np
    import cv2

    img = cv2.imread(input_image, cv2.IMREAD_UNCHANGED)
    img_grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    assert img is not None, "file could not be read, check with os.path.exists()"

    original_dtype = img.dtype

    # create a CLAHE object (Arguments are optional).
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(10, 10))
    # img_grey = np.mean(img, axis=2)
    cl1 = clahe.apply(img_grey)
    factors = cl1 / img_grey
    factors = np.where(np.logical_or(np.isnan(factors), np.isinf(factors)), 0., factors).astype(np.float64)
    img = img.astype(np.float64) * factors[..., np.newaxis]

    img = np.where(np.logical_or(np.isnan(img), np.isinf(img), img < 0), 0, img)

    max_poss_value = {'uint16': 65535, 'uint8': 255}[str(original_dtype)]
    img = np.where(img > max_poss_value, max_poss_value, img).astype(original_dtype)

    cv2.imwrite(output_image, img)


def makeBrowse_v2(type="JPEG", src=None, dest=None, resizePercent=-1,
                  w=-1, h=-1, enhance=None, transparent=False,
                  showTraceback=False, transparentThreshold=0,
                  hist_equalisation=False):
    import random
    import cv2
    import numpy as np
    import pyvips
    from PIL import Image

    image_path = Path(src)
    out_image = Path(dest)

    tmp = pyvips.Image.new_from_file(str(image_path), access='sequential')
    src_img_width, src_img_height = tmp.width, tmp.height
    del tmp

    if resizePercent > 0:
        scale = resizePercent / 100.0
    # Same scale on both axes to maintain aspect ratio
    elif w > 0 and h > 0:
        scale = min(
            w / src_img_width,
            h / src_img_height
        )
    else:
        # Default to DEFAULT_BROWSE_IMAGE_SIZE pixels on longest edge
        scale = min(
            DEFAULT_BROWSE_IMAGE_SIZE / src_img_width,
            DEFAULT_BROWSE_IMAGE_SIZE / src_img_height
        )

    # Load, rescale, and write to temporary image file with pyvips
    # (memory-efficient)
    rand_chars = "".join([chr(random.randint(65, 90)) for _ in range(8)])
    tmp_img_file = f'tmp_resized_img_{rand_chars}.PNG'
    tmp_img_file = image_path.parent / tmp_img_file
    try:
        resize_img(image_path, tmp_img_file, scale, raise_err=True)

        with Image.open(tmp_img_file) as img:
            img_bands = img.getbands()
            img_mode = img.mode

        # WARNING! PIL.Image (silently!) down-samples RGBA 16-bit input images
        # to 8-bit and there's no workaround within PIL itself!
        bit_depth = get_png_bit_depth(tmp_img_file)
        # if bit_depth == 16 and img_mode in ('RGB', 'RGBA'):
        # cv2 module required as it allows for 16-bit RGB/RGBA depths
        im_data = cv2.imread(str(tmp_img_file), cv2.IMREAD_UNCHANGED)

        # Get the current maximum pixel value
        max_value = im_data[:,:,:3].max() if img_mode == 'RGBA' else im_data.max()

        # Avoid division by zero
        if max_value > 0:
            # Scale pixel values and then reduce bit-depth to 8-bit for PIL
            scaled_image = (im_data * (255 / max_value))
            # Make pixel values == 256 for pixels that are not outside
            # boundary but are dark, so that upon conversion to 8-bit,
            # they have non-zero values
            scaled_image = np.where(np.logical_and(scaled_image > 0, scaled_image < 1), 1, scaled_image)
        else:
            scaled_image = im_data

        scaled_image = scaled_image.astype(np.uint8)
        bit_depth = 8

        cv2.imwrite(str(tmp_img_file), scaled_image)  # Keep alpha channel in case

        with Image.open(tmp_img_file) as resized_img:
            # Guard against incompatible transparency settings
            if transparent and (type.upper() != 'PNG' or len(img_bands) < 4):
                transparent = False

            if transparent:
                alpha_channel = resized_img.split()[3]
                alpha_mask = alpha_channel.point(lambda p: 255 if p > transparentThreshold else 0)
                resized_img = resized_img.convert('RGB')
                resized_img = ImageOps.autocontrast(
                    resized_img, mask=alpha_mask, cutoff=1, preserve_tone=False
                )
                resized_img = Image.merge(
                    'RGBA', (*resized_img.split()[:3], alpha_mask)
                )
            else:
                # Greyscale-images
                if len(resized_img.getbands()) == 1:
                    max_native_pixel_value = 2 ** bit_depth - 1

                    # Convert to numpy array for numerical processing
                    image_array = np.array(resized_img)

                    # Initially scale all values up so that the image maximum is equal to max_native_pixel_value and
                    # convert array type to relevant bit depth
                    # modified_array = (image_array / np.max(image_array) * max_native_pixel_value).astype(np.uint16 if bit_depth == 16 else np.uint8)
                    # Ensure values near zero, are zero (i.e. image boundary)
                    bbox_mask = np.where(image_array < np.max([2 ** (bit_depth - 8), 1]), True, False)
                    percentile_0_5_value = np.nanpercentile(
                        np.where(bbox_mask, np.nan, image_array), 0.5
                    )
                    percentile_99_5_value = np.nanpercentile(
                        np.where(bbox_mask, np.nan, image_array), 99.5
                    )

                    #modified_array = (image_array / percentile_99_5_value * max_native_pixel_value)
                    modified_array = ((image_array - percentile_0_5_value) / percentile_99_5_value * max_native_pixel_value)
                    modified_array = np.where(modified_array > max_native_pixel_value, max_native_pixel_value, modified_array)
                    modified_array = np.where(np.logical_or(modified_array < 0, bbox_mask), 0, modified_array)
                    modified_array = modified_array.astype(np.uint16 if bit_depth == 16 else np.uint8)

                    # Scale the image's mean pixel value up to 25% maximum (empirically-derived, 'good' value)
                    # current_mean_value = np.nanmean(
                    #     np.where(np.logical_and(~bbox_mask, modified_array < 255), modified_array, np.nan)
                    # )
                    # modified_array = (modified_array / (current_mean_value / (2 ** (bit_depth - 2) - 1))).astype(np.uint8)

                    # Ensure all pixel values are in the range 0 <= value <= max_native_pixel_value to avoid wrapping on
                    # conversion to different bit depths
                    # modified_array = np.where(modified_array > max_native_pixel_value, max_native_pixel_value, modified_array)

                    if bit_depth == 16:
                        modified_array = (np.array(modified_array) / 2 ** 8).astype(np.uint8)

                    # mask = Image.fromarray(np.where(modified_array < 1, 0, 1).astype(np.uint8) * 255).convert("1")

                    resized_img = Image.fromarray(modified_array)
                    #resized_img = ImageOps.equalize(resized_img, mask=mask)

                    # Create PIL.Image instance from numpy array and convert to appropriate PIL.Image mode
                    # resized_img = Image.fromarray(
                    #     modified_array.astype(np.uint16 if bit_depth == 16 else np.uint8)
                    # ).convert("I;16" if bit_depth == 16 else 'L')
                # Colour images
                else:
                    if resized_img.mode != 'RGB':
                        resized_img = resized_img.convert('RGB')

                    # Create mask (1-bit) to exclude near-zero values (i.e. image boundary)
                    mask = resized_img.point(lambda p: 255 if p > 1 else 0).convert("1")
                    # cloud_mask = (np.array(ImageOps.grayscale(resized_img)) > 128).astype(np.uint8) * 255
                    resized_img = ImageOps.autocontrast(
                        resized_img, mask=mask, cutoff=0.0, preserve_tone=False  #cutoff=1.0 for Pleiades-Neo!
                    )
                    if hist_equalisation:
                        cloud_mask = resized_img.point(lambda p: 255 if 1 < p < 192 else 0).convert("1")
                        resized_img = ImageOps.equalize(resized_img, cloud_mask)

            resized_img.save(out_image, format=type)

        return True

    except Exception as err:
        print(" ######################################## 4 Error making browse:%s" % err)
        if showTraceback:
            traceback.print_exc(file=sys.stdout)
        raise err

    finally:
        if tmp_img_file.exists():
            tmp_img_file.unlink()


def equalise_histogram(
        input_image: Union[str, Path, PILImage],
        output_file: Optional[Union[str, Path]] = None,
        mask_image: Optional[Union[str, Path, PILImage]] = None
    ) -> PILImage:
    """
    Equalise histogram for input_image and return as histogram-equalised
    PIL.Image. Optionally write to file, and/or mask bad pixels for
    equalisation
    """

    if any([isinstance(input_image, t) for t in (str, Path)]):
        input_image = Image.open(input_image)
    elif not isinstance(input_image, PILImage):
        raise TypeError(
            f"input_image must be a str, Path, or PIL.Image instance, "
            f"not a {type(input_image).__name__} instance"
        )
    img_bands = input_image.getbands()
    img_mode = input_image.mode

    if mask_image is not None:
        if any([isinstance(mask_image, t) for t in (str, Path)]):
            mask_image = Image.open(mask_image)
        elif not isinstance(mask_image, PILImage):
            raise TypeError(
                f"mask_image must be a str, Path, or PIL.Image instance, "
                f"not a {type(mask_image).__name__} instance"
            )
        mask_image = mask_image.convert("1")
    else:
        mask_image = input_image.point(lambda p: 255 if 1 < p < 192 else 0).convert("1")

    output_img = ImageOps.equalize(input_image, mask_image)
    if output_file is not None:
        output_img.save(output_file)

    return output_img


def measure_contrast_and_brightness(image_file: Union[Path, str]) -> Dict:
    if isinstance(image_file, str):
        image_file = Path(image_file).resolve()

    pass


def remove_tiled_separate_planes_gdal(image_file, out_image, raise_err=True):
    """Create a contiguous image from one composed of separate planes, using GDAL"""
    cmd = [
        'gdal_translate',
        "-co", "COMPRESS=DEFLATE",
        "-co", "INTERLEAVE=BAND",
        str(image_file.resolve()), str(out_image.resolve())
    ]

    print("remove_tiled_separate_planes_gdal:: " + ' '.join(cmd))
    try:
        process = subprocess.run(cmd, check=False)
    except Exception as err:
        if raise_err:
            raise err
        print(f"remove_tiled_separate_planes_gdal:: {type(err).__name__}: {err.args[0]}")
        return 1

    return process.returncode


#
# make a browse image using PIL
# w and h parameter not used at this time
#
def makeBrowsePil(type="JPEG", src=None, dest=None, resizePercent=-1,
                  w=-1, h=-1, enhance=None, transparent=False,
                  showTraceback=False, transparentThreshold=0):
    try:
        if debug:
            print(" internal resize image:%s into:%s; percent:%s" % (src, dest, resizePercent))
        im = Image.open(src)
        # SJDP: Changed below
        # im = im.convert('RGBA')
        im = im.convert('RGBA' if transparent else 'RGB')
        if debug:
            print("  src image read: %s" % im.info)

        img = None
        if enhance != None:
            converter = ImageEnhance.Contrast(im)
            newIm = converter.enhance(1.5)
            # r, g, b, a = img.split()
            # if DEBUG:
            #    print "  im splitted"
            # newIm = Image.merge("RGB", (r, g, b))
            # newIm = splitBands(img)
        else:
            # try:
            #    r, g, b, a = im.split()
            #    if DEBUG:
            #        print "  im splitted rgba"
            #    newIm = Image.merge("RGB", (r, g, b))
            # except:
            #    r, g, b = im.split()
            #    if DEBUG:
            #        print "  im splitted rgb"
            #    newIm = Image.merge("RGB", (r, g, b))
            newIm = im.copy()

        if debug:
            print("  newIm:%s" % newIm)

        # Calculator new dimensions
        width, height = newIm.size
        if resizePercent != -1:
            nw = width * resizePercent / 100
            nh = height * resizePercent / 100
        elif w > 0 and h > 0:
            nw, nh = w, h
        else:
            largest_dim, aspect = DEFAULT_BROWSE_IMAGE_SIZE, width / height
            if width <= largest_dim and height <= largest_dim:
                nw, nh = None, None
            elif width >= height:
                nw, nh = largest_dim, largest_dim / aspect
            else:
                nw, nh = largest_dim * aspect, largest_dim

        newSize = None if None in (nw, nh) else [round(_) for _ in (nw, nh)]

        if newSize is not None:
            newIm = newIm.resize(newSize, Image.BILINEAR)
            if debug:
                print("  newIm resized")
            if type == "PNG" and transparent:
                source = newIm.split()
                R, G, B, A = 0, 1, 2, 3
                mask = newIm.point(lambda i: i > transparentThreshold and 255)  # use black as transparent
                source[A].paste(mask)
                newIm = Image.merge(im.mode, source)  # build a new multiband image 
            newIm.save(dest, type)
        else:
            if type == "PNG" and transparent:
                source = newIm.split()
                R, G, B, A = 0, 1, 2, 3
                mask = newIm.point(lambda i: i > transparentThreshold and 255)  # use black as transparent
                source[A].paste(mask)
                newIm = Image.merge(im.mode, source)  # build a new multiband image
            newIm.save(dest, type)

        if debug:
            print("  browse saved as:%s" % dest)
        return True

    except Exception as e:
        print(" ######################################## 4 Error making browse:%s" % e)
        if showTraceback:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
        raise e


def overlay_mean_and_std(input_image, output_image, text_colour='red'):
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    import pyvips

    if isinstance(input_image, str):
        input_image = Path(input_image)

    # Open the image
    image: PIL.Image = Image.open(input_image)

    # Convert image to grayscale (optional, for mean/stddev calculations on a single channel)
    image_gray = image.convert('L')

    # Convert image to a numpy array for processing
    image_array = np.array(image_gray)
    image_array = np.where(image_array < 1, np.nan, image_array)

    # Calculate the mean and standard deviation
    mean = np.nanmean(image_array)
    std_dev = np.nanstd(image_array)

    if input_image.suffix.upper() == '.PNG':
        bit_depth = get_png_bit_depth(input_image)
    else:
        bit_depth = input_image.mode

    # Convert mean and standard deviation to strings
    mean_str = f'Mean: {mean:.1f}'
    std_dev_str = f'StdDev: {std_dev:.1f}'
    bit_depth_str = f'Bit Depth: {bit_depth}'

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Use a basic font (you may need to adjust the font path)
    font = ImageFont.load_default(32)

    # Get the bounding box of the text to calculate text size
    bbox = draw.textbbox((0, 0), f'{mean_str}\n{std_dev_str}\n{bit_depth_str}', font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Set the position for the text (top-right corner with padding)
    width, height = image.size
    x_pos = width - text_width - 10  # 10px padding from the right
    y_pos = 10  # 10px padding from the top

    # Set text colour to grey for greyscale images
    if image.mode in ('L', 'P'):
        text_color = 255
    # Set the text color to green (R, G, B)
    else:
        text_color = (0, 255, 0)

    # Write the mean and stddev values to the image
    draw.text((x_pos, y_pos), mean_str, font=font, fill=text_color)
    draw.text((x_pos, y_pos + text_height), std_dev_str, font=font, fill=text_color)

    # Save the resulting image
    image.save(output_image)


#
# all coords relate to top-left corner of the image
#
def cropImage(aSrcPath, aDestPath, left, top, width, height, type='PNG'):
    im = PIL.Image.open(aSrcPath)
    bbox = (left, top, left + width, top + height)
    cropped = im.crop(bbox)
    cropped.save(aDestPath, type)


if __name__ == '__main__':
    print("PilReady:%s" % PilReady)
    if len(sys.argv) > 1:
        print("res:%s %s" % get_image_size(sys.argv[1]))
    else:
        # src="/home/gilles/shared2/Lite/Worldview/diskA12695/053963563010_01/053963563010_01_P001_MUL/12MAR23110731-M2AS_R01C1-053963563010_01_P001.TIF"
        src1 = "/home/gilles/shared2/Datasets/Spot6-7/stranges-spot-5/imagery_known.tif"
        # src="C:/Users/glavaux/Shared/LITE/tmp/unzipped/imagery.tif"
        # src="C:/Users/glavaux/Shared/LITE/tmp/imagery_pb.tif"
        # dest="C:/Users/glavaux/Shared/LITE/tmp/test.png"
        # ok=makeBrowse("PNG", src, dest, 50, transparent=True)
        print("res:%s %s" % get_image_size(src1))

    # print a
