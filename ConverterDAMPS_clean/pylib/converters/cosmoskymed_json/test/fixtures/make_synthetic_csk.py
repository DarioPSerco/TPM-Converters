"""Regenerate the synthetic COSMO-SkyMed HDF5 fixtures.

Run from this folder:
    python make_synthetic_csk.py

Two tiny .h5 files are written, carrying the attribute tree the converter
reads (root + S0n beam group + image dataset + QLK quicklook), with rasters of
a few pixels instead of the multi-gigabyte real ones:

synthetic_csk/CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301/
    736299-502923/<same>.h5        STRIPMAP HIMAGE, Level 1B, single pol
synthetic_csk/CSKS4_SCSU_PP_01_HH_RA_FF_20200704101010_20200704101020/
    800001/<same>.h5        STRIPMAP PINGPONG, Level 1A, dual pol
"""
import os

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

HIM_NAME = "CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301"
HIM_ORDER = "736299-502923"
SPP_NAME = "CSKS4_SCSU_PP_01_HH_RA_FF_20200704101010_20200704101020"
SPP_ORDER = "800001"


def corner(lat, lon):
    return np.array([lat, lon, 0.0])


def write_product(path, root_attrs, beams, image_attrs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with h5py.File(path, "w") as fd:
        for key, value in root_attrs.items():
            fd.attrs[key] = value
        for name, polarisation in beams:
            group = fd.create_group(name)
            group.attrs["Polarisation"] = np.bytes_(polarisation)
            group.attrs["Beam ID"] = np.bytes_("H4-01")
            quicklook = group.create_dataset(
                "QLK", data=np.arange(48, dtype=np.uint8).reshape(6, 8))
            quicklook.attrs["Quick Look Lines Order"] = np.bytes_("EARLY-LATE")
            quicklook.attrs["Quick Look Columns Order"] = np.bytes_("NEAR-FAR")
            image = group.create_dataset(
                "SBI", data=np.arange(16, dtype=np.uint16).reshape(4, 4))
            for key, value in image_attrs.items():
                image.attrs[key] = value
    print("written: %s" % path)


HIM_ROOT = {
    "Product Filename": np.bytes_("%s.h5" % HIM_NAME),
    "Product Type": np.bytes_("DGM_B"),
    "Acquisition Mode": np.bytes_("HIMAGE"),
    "Mission ID": np.bytes_("CSK"),
    "Satellite ID": np.bytes_("CSKS1"),
    "Look Side": np.bytes_("RIGHT"),
    "Orbit Direction": np.bytes_("DESCENDING"),
    "Orbit Number": np.int32(53764),
    "Scene Sensing Start UTC": np.bytes_("2017-05-15 17:22:53.648612599"),
    "Scene Sensing Stop UTC": np.bytes_("2017-05-15 17:23:01.196851995"),
    "Product Generation UTC": np.bytes_("2019-10-08 18:49:23.433719000"),
    "Azimuth Geometric Resolution": 5.0,
    "Ground Range Geometric Resolution": 5.0,
    "Radar Wavelength": 0.031228381041666666,
    "Radar Frequency": 9600000000.0,
    "Scene Centre Geodetic Coordinates": corner(55.65406595, 12.54334912),
    "Projection ID": np.bytes_("GROUND RANGE/AZIMUTH"),
    "Processing Centre": np.bytes_("ICUGS"),
}

HIM_IMAGE = {
    "Top Left Geodetic Coordinates": corner(55.82662432, 12.95517649),
    "Top Right Geodetic Coordinates": corner(55.90530060, 12.31845754),
    "Bottom Right Geodetic Coordinates": corner(55.48560816, 12.15654435),
    "Bottom Left Geodetic Coordinates": corner(55.40741178, 12.78627361),
    "Near Incidence Angle": 24.92166101000814,
    "Far Incidence Angle": 28.281491291803036,
    "Near Look Angle": 22.552000405724293,
    "Far Look Angle": 25.546103297406265,
    "Line Spacing": 2.5,
    "Column Spacing": 2.5,
}

SPP_ROOT = dict(HIM_ROOT)
SPP_ROOT.update({
    "Product Filename": np.bytes_("%s.h5" % SPP_NAME),
    "Product Type": np.bytes_("SCS_U"),
    "Acquisition Mode": np.bytes_("PINGPONG"),
    "Satellite ID": np.bytes_("CSKS4"),
    "Orbit Direction": np.bytes_("ASCENDING"),
    "Orbit Number": np.int32(12345),
    "Scene Sensing Start UTC": np.bytes_("2020-07-04 10:10:10.100000000"),
    "Scene Sensing Stop UTC": np.bytes_("2020-07-04 10:10:20.200000000"),
    "Product Generation UTC": np.bytes_("2020-07-05 08:00:00.000000000"),
    "Azimuth Geometric Resolution": 15.0,
    "Ground Range Geometric Resolution": 20.0,
})


if __name__ == "__main__":
    write_product(
        os.path.join(HERE, "synthetic_csk", HIM_NAME, HIM_ORDER, "%s.h5" % HIM_NAME),
        HIM_ROOT, [("S01", "HH")], HIM_IMAGE)
    write_product(
        os.path.join(HERE, "synthetic_csk", SPP_NAME, SPP_ORDER, "%s.h5" % SPP_NAME),
        SPP_ROOT, [("S01", "HH"), ("S02", "VV")], HIM_IMAGE)
