"""Write the SYNTHETIC KOMPSAT native products used by the tests.

Re-runnable: python make_synthetic_ko.py (needs numpy + tifffile + pillow).
See SYNTHETIC_FIXTURE_NOTE.md for what each product proves.

Each product is the ASCII AUX metadata <image stem>.txt of each component and
tiny rasters instead of the real ones.
"""
import shutil
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_ko"

# footprint of the specialization's example manifests: corner -> (lon, lat)
CORNERS = {"TL": (-66.44291264, -24.15261009), "TR": (-66.36551048, -24.15129263),
           "BR": (-66.36391186, -24.22904374), "BL": (-66.44136086, -24.23036597)}


def corner_lines(style="IMAGE"):
    lines = []
    for corner, (lon, lat) in CORNERS.items():
        if style == "IMAGE":
            lines.append("AUX_IMAGE_%s_LATITUDE_DEC    %.8f" % (corner, lat))
            lines.append("AUX_IMAGE_%s_LONGITUDE_DEC   %.8f" % (corner, lon))
            # integer-degree companion keys: must not win over the decimal ones
            lines.append("AUX_IMAGE_%s_LATITUDE_DEG    %d" % (corner, int(lat)))
            lines.append("AUX_IMAGE_%s_LONGITUDE_DEG   %d" % (corner, int(lon)))
        else:  # UL/UR/LR/LL style
            alias = {"TL": "UL", "TR": "UR", "BR": "LR", "BL": "LL"}[corner]
            lines.append("AUX_CORNER_%s_LAT = %.8f" % (alias, lat))
            lines.append("AUX_CORNER_%s_LON = %.8f" % (alias, lon))
    return lines


def aux_text(satellite, sensor, level, orbit, date, start, end, extra=(), corners="IMAGE",
             grouped=False):
    head = ["AUX_SATELLITE_NAME          %s" % satellite,
            "AUX_SATELLITE_SENSOR        %s" % sensor,
            "AUX_PROCESSING_LEVEL        %s" % level]
    body = ["AUX_ORBIT_NUMBER            %s" % orbit,
            "AUX_STRIP_ACQ_DATE_UT       %s" % date,
            "AUX_STRIP_ACQ_START_UT      %s" % start]
    if end:
        body.append("AUX_STRIP_ACQ_END_UT        %s" % end)
    body += list(extra) + corner_lines(corners)
    if grouped:
        body = ["BEGIN_IMAGE"] + ["  " + line for line in body] + ["END_IMAGE"]
    return "\n".join(["# KOMPSAT auxiliary data (SYNTHETIC)"] + head + body) + "\n"


def raster(bands, dtype=np.uint16):
    """(rows, cols[, bands]) ramp with an all-zero (no-data) first column."""
    rows, cols = 12, 16
    ramp = np.fromfunction(lambda r, c, b: 100 + r * 3 + c * 2 + b * 5,
                           (rows, cols, bands), dtype=float)
    ramp[:, 0, :] = 0
    data = ramp.astype(dtype)
    return data[:, :, 0] if bands == 1 else data


def write_tif(path, data):
    extra = None if data.ndim == 2 else ["unspecified"] * (data.shape[-1] - 1)
    tifffile.imwrite(path, data, photometric="minisblack", planarconfig="contig",
                     extrasamples=extra)


K2_EXTRA = ["AUX_ORBIT_DIRECTION         DESCENDING",
            "AUX_PROCESSING_DATE         20100608",
            "AUX_PROCESSING_TIME         10:20:30",
            "AUX_SUN_AZIMUTH_ANGLE_DEG   33.3",
            "AUX_SUN_ELEVATION_ANGLE_DEG 44.1",
            "AUX_ALONG_TRACK_INCIDENCE_ANGLE_DEG  0.7",
            "AUX_ACROSS_TRACK_INCIDENCE_ANGLE_DEG 0.8",
            "AUX_CLOUD_STATUS            10"]


def k2_flat_bundle(folder):
    """L1_GEO_BDL: PAN + one 4-band MS image in one folder, plus an RPC text."""
    pan = "MSC_100607044108_21000_10731074PN11_1G"
    ms = "MSC_100607044108_21000_10731074MS11_1G"
    (folder / (pan + ".txt")).write_text(aux_text(
        "KOMPSAT-2", "MSC", "1G", 21000, "20100607", "04:41:08.800000", "04:41:12.300000",
        K2_EXTRA), encoding="utf-8")
    (folder / (ms + ".txt")).write_text(aux_text(
        "KOMPSAT-2", "MSC", "1G", 21000, "20100607", "04:41:08.900000", "04:41:12.400000",
        K2_EXTRA), encoding="utf-8")
    (folder / (pan + "_rpc.txt")).write_text("LINE_OFF: 6\nSAMP_OFF: 8\n", encoding="utf-8")
    write_tif(folder / (pan + ".tif"), raster(1))
    write_tif(folder / (ms + ".tif"), raster(4))


def k2_split_bundle(folder):
    """L1_OPT_BDL: <scene>/PAN/ + <scene>/MS/ with one image per MS band, a
    native browse, grouped AUX keys, UL/UR/LR/LL corners, no end time, no
    processing date, no angles, cloud cover not assessed."""
    scene = folder / "MSC_090415014422_15130_11831188_1R"
    (scene / "PAN").mkdir(parents=True)
    (scene / "MS").mkdir()
    pan = "MSC_090415014422_15130_11831188PN00_1R"
    extra = ["AUX_ORBIT_DIRECTION         A", "AUX_CLOUD_STATUS            -1"]
    (scene / "PAN" / (pan + ".txt")).write_text(aux_text(
        "KOMPSAT-2", "MSC", "1R", 15130, "2009-04-15", "01:44:22.5", None, extra,
        corners="CORNER", grouped=True), encoding="utf-8")
    write_tif(scene / "PAN" / (pan + ".tif"), raster(1))
    Image.fromarray(np.full((12, 16, 3), 128, dtype=np.uint8)).save(
        scene / "PAN" / (pan + "_br.jpg"))
    for band in (1, 2, 3, 4):
        name = "MSC_090415014422_15130_11831188M%d00_1R" % band
        write_tif(scene / "MS" / (name + ".tif"), raster(1))
    (scene / "MS" / "MSC_090415014422_15130_11831188M100_1R.txt").write_text(aux_text(
        "KOMPSAT-2", "MSC", "1R", 15130, "20090415", "01:44:22.600000", "01:44:25.100000",
        extra, corners="CORNER"), encoding="utf-8")


def k1_ortho(folder):
    """L1BORT_PAN: KOMPSAT-1 EOC, one PAN GeoTIFF."""
    stem = "EOC_020101121314_00042_L1B"
    extra = ["AUX_ORBIT_DIRECTION         DESCENDING",
             "AUX_SUN_AZIMUTH_ANGLE_DEG   33.3",
             "AUX_SUN_ELEVATION_ANGLE_DEG 44.1",
             "AUX_CLOUD_STATUS            0"]
    (folder / (stem + ".txt")).write_text(aux_text(
        "KOMPSAT-1", "EOC", "1B", 42, "20020101", "12:13:14.800", "12:14:17.800", extra),
        encoding="utf-8")
    write_tif(folder / (stem + ".tif"), raster(1, np.uint8))


if __name__ == "__main__":
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for name, writer in (("k2_flat", k2_flat_bundle), ("k2_split", k2_split_bundle),
                         ("k1_ortho", k1_ortho)):
        folder = ROOT / name
        folder.mkdir(parents=True)
        writer(folder)
    print("written:", ROOT)
