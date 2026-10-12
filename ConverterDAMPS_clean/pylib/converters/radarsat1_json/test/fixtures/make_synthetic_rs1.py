"""Build the synthetic RADARSAT-1 fixtures from real deliveries.

Usage: python make_synthetic_rs1.py <folder holding the real scene folders>

The metadata files (.vol, .nvol, .sarl, .sart, .txt) are copied as delivered.
The image data file (.sard, hundreds of MB) is replaced by a small one: the
real file descriptor, with the record length and the pixel count patched,
followed by LINES records of PIXELS samples (a ramp, so the overview is not
flat) behind the real 192-byte record prefix of the first image line.
"""
import shutil
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent / "synthetic_rs1"
SCENES = ("01Jul98_13866_01", "01Jul98_13866_02", "08Dec99_21364_01", "10Jul98_13990")
METADATA_SUFFIXES = (".vol", ".nvol", ".sarl", ".sart", ".txt")
LINES, PIXELS = 30, 40


def patch(record, first, last, value):
    width = last - first + 1
    text = ("%*d" % (width, value)).encode("latin1")
    assert len(text) == width
    return record[:first - 1] + text + record[last:]


def synthetic_image(real, dest):
    with open(real, "rb") as fd:
        head = fd.read(12)
        descriptor_length = struct.unpack(">I", head[8:12])[0]
        fd.seek(0)
        descriptor = fd.read(descriptor_length)
        old_record_length = int(descriptor[186:192])
        prefix = fd.read(old_record_length)[:192]
    bytes_per_pixel = int(descriptor[224:228])
    sample_format = descriptor[428:432].decode("latin1").strip()
    record_length = 192 + PIXELS * bytes_per_pixel
    descriptor = patch(descriptor, 187, 192, record_length)
    descriptor = patch(descriptor, 249, 256, PIXELS)
    descriptor = patch(descriptor, 181, 186, LINES)
    descriptor = patch(descriptor, 237, 244, LINES)
    with open(dest, "wb") as fd:
        fd.write(descriptor)
        for line in range(LINES):
            ramp = np.arange(PIXELS) + line + 1
            if sample_format == "IU1":
                data = ramp.astype(np.uint8).tobytes()
            elif sample_format == "IU2":
                data = ramp.astype(">u2").tobytes()
            else:  # CI*4: I, Q pairs
                data = np.stack([ramp, ramp]).T.astype(">i2").tobytes()
            record = struct.pack(">I", line + 2) + prefix[4:8] + struct.pack(">I", record_length) + prefix[12:]
            fd.write(record + data)


def main(source):
    for scene in SCENES:
        src = Path(source) / scene
        dst = HERE / scene
        dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(src.iterdir()):
            if path.suffix in METADATA_SUFFIXES:
                shutil.copyfile(path, dst / path.name)
            elif path.suffix == ".sard":
                synthetic_image(path, dst / path.name)
        print("written", dst)


if __name__ == "__main__":
    main(sys.argv[1])
