"""Write the SYNTHETIC IRS-P5 / IRS-P6 native deliveries used by the tests.

Re-runnable: python make_synthetic_ir5.py (needs numpy + tifffile).
See SYNTHETIC_FIXTURE_NOTE.md for what each delivery proves.

Each delivery has the file set, file names and metadata elements of the real
deliveries, with synthetic values and 16x12 rasters instead of the real ones.
"""
import shutil
import struct
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_ir5"

ROWS, COLS = 12, 16

# IOGP Guidance Note 7-2 LAEA example point: EPSG:3035 (3962799.45,
# 2999718.85) is 5E 50N - the top-left corner of the IR5 rasters
X0, Y0 = 3962799.45, 2999718.85

# GeoKey ids
GT_MODEL_TYPE, GT_RASTER_TYPE, GT_CITATION = 1024, 1025, 1026
GEOGRAPHIC_TYPE, GEOG_CITATION, GEOG_DATUM, GEOG_ANGULAR_UNITS = 2048, 2049, 2050, 2054
GEOG_SEMI_MAJOR, GEOG_INV_FLATTENING, GEOG_PRIME_MERIDIAN_LONG = 2057, 2059, 2061
PROJECTED_CS_TYPE, PROJECTION, PROJ_COORD_TRANS, PROJ_LINEAR_UNITS = 3072, 3074, 3075, 3076
PROJ_FALSE_EASTING, PROJ_FALSE_NORTHING, PROJ_CENTER_LONG, PROJ_CENTER_LAT = 3082, 3083, 3088, 3089
USER_DEFINED = 32767


def geo_tags(keys, pixel, x0=X0, y0=Y0, nodata=None):
    """GeoTIFF extratags: keys is {key id: int | float | str}; ints go in the
    directory, floats in GeoDoubleParams, strings in GeoAsciiParams."""
    directory, doubles, ascii_params = [], [], ""
    for key in sorted(keys):
        value = keys[key]
        if isinstance(value, str):
            text = value + "|"
            directory += [key, 34737, len(text), len(ascii_params)]
            ascii_params += text
        elif isinstance(value, float):
            directory += [key, 34736, 1, len(doubles)]
            doubles.append(value)
        else:
            directory += [key, 0, 1, value]
    tags = [(34735, "H", 4 + len(directory), [1, 1, 0, len(keys)] + directory, True),
            (33550, "d", 3, (pixel, pixel, 0.0), True),
            (33922, "d", 6, (0.0, 0.0, 0.0, x0, y0, 0.0), True)]
    if doubles:
        tags.append((34736, "d", len(doubles), doubles, True))
    if ascii_params:
        tags.append((34737, "s", 0, ascii_params, True))
    if nodata is not None:
        tags.append((42113, "s", 0, str(nodata), True))
    return tags


# the user-defined CRS of the Euro-Maps orthoimages: ETRS89 / LAEA parameters
LAEA_USER_DEFINED = {
    GT_MODEL_TYPE: 1, GT_RASTER_TYPE: 1, GT_CITATION: "ETRS89_ETRS_LAEA",
    GEOGRAPHIC_TYPE: USER_DEFINED,
    GEOG_CITATION: "GCS Name = GCS_ETRS89|Ellipsoid = GRS_1980|Primem = Greenwich",
    GEOG_DATUM: 6258, GEOG_ANGULAR_UNITS: 9102,
    GEOG_SEMI_MAJOR: 6378137.0, GEOG_INV_FLATTENING: 298.257222101, GEOG_PRIME_MERIDIAN_LONG: 0.0,
    PROJECTED_CS_TYPE: USER_DEFINED, PROJECTION: USER_DEFINED, PROJ_COORD_TRANS: 10,
    PROJ_LINEAR_UNITS: 9001, PROJ_FALSE_EASTING: 4321000.0, PROJ_FALSE_NORTHING: 3210000.0,
    PROJ_CENTER_LONG: 10.0, PROJ_CENTER_LAT: 52.0,
}
# the EPSG-coded CRS of the Euro-Maps 3D tiles
LAEA_3035 = {GT_MODEL_TYPE: 1, GT_RASTER_TYPE: 1, GT_CITATION: "ETRS89 / LAEA Europe",
             PROJECTED_CS_TYPE: 3035, PROJ_LINEAR_UNITS: 9001}


def ramp(dtype, nodata=0, bands=1):
    """(rows, cols[, bands]) ramp whose first column is no-data."""
    data = np.fromfunction(lambda r, c, b: 100 + r * 3 + c * 2 + b * 5, (ROWS, COLS, bands))
    data[:, 0, :] = nodata
    data = data.astype(dtype)
    return data[:, :, 0] if bands == 1 else data


def write_geotiff(path, data, keys, pixel, x0=X0, nodata=None):
    tifffile.imwrite(path, data, photometric="minisblack",
                     extratags=geo_tags(keys, pixel, x0=x0, nodata=nodata))


ORTHO_XML = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Document lang="en" xml:lang="en-us" xsi:noNamespaceSchemaLocation="EM_XML_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Production>
  <DATASET_NAME>{name}</DATASET_NAME>
  <DATASET_PRODUCER_NAME>SYNTHETIC</DATASET_PRODUCER_NAME>
  <DATASET_PRODUCTION_DATE>{production}</DATASET_PRODUCTION_DATE>
  <DATASET_PRODUCT_LEVEL>3O</DATASET_PRODUCT_LEVEL>
  <DATASET_PRODUCT_TYPE>Orthoimage</DATASET_PRODUCT_TYPE>
  <DATASET_REFERENCE>Synthetic</DATASET_REFERENCE>
  <DATASET_ORIGIN>{delivery}</DATASET_ORIGIN>
  <DATASET_MISSION>IR05</DATASET_MISSION>
  <DATASET_SENSOR>PAN</DATASET_SENSOR>
  <DATASET_SENSOR_MODE>{mode}</DATASET_SENSOR_MODE>
</Production>
  <Image>
  <BITS_PER_PIXEL>16</BITS_PER_PIXEL>
  <COLUMNS>16</COLUMNS>
  <ROWS>12</ROWS>
  <CHANNELS>1</CHANNELS>
</Image>
  <GeoInformation>
  <PROJECTION>LAEA-ETRS89</PROJECTION>
  <PROJ_DEFINITION>PROJCS["ETRS89_ETRS_LAEA",GEOGCS["GCS_ETRS89",DATUM["D_ETRS_1989",SPHEROID["GRS_1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["latitude_of_origin",52],PARAMETER["central_meridian",10],PARAMETER["false_easting",4321000],PARAMETER["false_northing",3210000],UNIT["Meter",1]]</PROJ_DEFINITION>
  <XGEOREF>{xgeoref}</XGEOREF>
  <YGEOREF>{ygeoref}</YGEOREF>
  <XCELLRES>2.5</XCELLRES>
  <YCELLRES>2.5</YCELLRES>
</GeoInformation>
  <Acquisition>
  <ACQUISITION_TABLES version="4.2">OPTICAL</ACQUISITION_TABLES>
{parameters}
</Acquisition>
</Document>
"""

ACQUISITION_PARAMETER = """  <Acquisition_Parameter>
    <ACQUISITION_PARAMETER_DESC>{desc}</ACQUISITION_PARAMETER_DESC>
    <ACQUISITION_PARAMETER_CODE>{code}</ACQUISITION_PARAMETER_CODE>
    <ACQUISITION_PARAMETER_VALUE unit="{unit}">{value}</ACQUISITION_PARAMETER_VALUE>
  </Acquisition_Parameter>"""


def ortho_xml(delivery, name, orbit, x0, sun_azimuth, sun_elevation, mode="PF"):
    params = "\n".join(ACQUISITION_PARAMETER.format(desc=d, code=c, unit=u, value=v) for d, c, u, v in (
        ("Imaging Orbit No", "Orbit_no", "no unit", orbit),
        ("Sun Aziumth at Center", "Sun_azimuth", "deg.", sun_azimuth),
        ("Sun Elevation at Center", "Sun_elevation", "deg.", sun_elevation),
        ("Tiltangle", "Tilt_angle", "deg.", "0.0000000")))
    return ORTHO_XML.format(name=name, production="2011-01-02", delivery=delivery, mode=mode,
                            xgeoref=x0 + 1.25, ygeoref=Y0 - 1.25, parameters=params)


def ortho_delivery(folder, delivery, images):
    """IRS-P5 ortho delivery <folder>/: <delivery>_oid.txt, _ql.tif + .tfw and
    one EM_Ortho_Image_<n>/ per (dataset name, orbit, x0, sun azimuth, sun
    elevation) of images."""
    folder.mkdir(parents=True)
    (folder / (delivery + "_oid.txt")).write_text(
        "OID_version=1.0\n\nOID_EM_order_no='00000'\nOID_EM_item_no='1'\n"
        "OID_CLIENT_order_ref='SYNTHETIC'\nOID_CLIENT_product_ref='Synthetic'\n", encoding="utf-8")
    width = COLS * 2.5 * len(images) / COLS  # one quicklook over every image
    write_geotiff(folder / (delivery + "_ql.tif"), ramp(np.uint16), LAEA_USER_DEFINED, width, nodata=0)
    (folder / (delivery + "_ql.tfw")).write_text(
        "%.10f\n0.0\n0.0\n%.10f\n%.10f\n%.10f\n" % (width, -width, X0 + width / 2, Y0 - width / 2),
        encoding="utf-8")
    for n, (name, orbit, x0, sun_azimuth, sun_elevation) in enumerate(images, start=1):
        image = folder / ("EM_Ortho_Image_%d" % n)
        image.mkdir()
        write_geotiff(image / (delivery + "_imagery.tif"), ramp(np.uint16), LAEA_USER_DEFINED, 2.5,
                      x0=x0, nodata=0)
        (image / (delivery + "_metadata.xml")).write_text(
            ortho_xml(delivery, name, orbit, x0, sun_azimuth, sun_elevation), encoding="ISO-8859-1")


def dsm_tile(folder, tile):
    """IRS-P5 Euro-Maps 3D tile <folder>/p5bproductformatter/em3d_*.tif."""
    layers = folder / "p5bproductformatter"
    layers.mkdir(parents=True)
    stem = "em3d_100001_20200402_%s" % tile
    write_geotiff(layers / (stem + "_dsm.tif"), ramp(np.int16, nodata=-32767), LAEA_3035, 5.0,
                  nodata=-32767)
    for layer, nodata in (("acv", 255), ("num", 255), ("qc", 255), ("src", 0)):
        write_geotiff(layers / ("%s_%s.tif" % (stem, layer)), ramp(np.uint8, nodata=nodata) % 12,
                      LAEA_3035, 5.0, nodata=nodata)


P6_XML = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xml:lang="en" lang="en">
  <Production>
    <DATASET_NAME>IR06_LI3_ORT_1O_20060320T094438_20060320T094500_DLR_12345_PRCS.BIL.ZIP</DATASET_NAME>
    <DATASET_PRODUCER_NAME>SYNTHETIC</DATASET_PRODUCER_NAME>
    <DATASET_PRODUCTION_DATE>2007-10-28</DATASET_PRODUCTION_DATE>
    <DATASET_PRODUCTION_TYPE>Orthoimage</DATASET_PRODUCTION_TYPE>
    <DATASET_ORIGIN>060320P6036037L0030S3.ZIP</DATASET_ORIGIN>
    <DATASET_SENSOR>IRS-P6-LISS III</DATASET_SENSOR>
  </Production>
  <Image>
    <BITS_PER_PIXEL>8</BITS_PER_PIXEL>
    <CHANNELS>4</CHANNELS>
    <COLUMNS>16</COLUMNS>
    <ROWS>12</ROWS>
    <FORMAT>BIL</FORMAT>
  </Image>
  <GeoInformation>
    <PROJECTION>CS</PROJECTION>
    <XGEOREF>7262270.00000000000000</XGEOREF>
    <YGEOREF>5050390.00000000000000</YGEOREF>
    <XCELLRES>20.00000000000000</XCELLRES>
    <YCELLRES>20.00000000000000</YCELLRES>
  </GeoInformation>
</Document>
"""

# Euromap ssd dump fields: (field no, start, end, format, description, value)
SSD_HEADER_FIELDS = [
    (6, 21, 28, "I8   ", "Path Number                             ", "      36"),
    (14, 149, 164, "F16.7", "Left top corner geographic location of scene (lat) (deg)", "      45.5000000"),
    (15, 165, 180, "F16,7", "Left top corner geographic location of scene (long) (deg)", "      18.5000000"),
    (16, 181, 188, "I8   ", "Left top corner location in scene (line no.)", "       1"),
    (18, 197, 212, "F16.7", "Right top corner geographic location of scene (lat)", "      45.2000000"),
    (19, 213, 228, "F16,7", "Right top corner geographic location of scene (long)", "      20.2000000"),
    (22, 245, 260, "F16.7", "Left bottom corner geographic location of scene (lat)", "      44.3000000"),
    (23, 261, 276, "F16,7", "Left bottom corner geographic location of scene (long)", "      18.0000000"),
    (26, 293, 308, "F16.7", "Right bottom corner geographic location of scene (lat)", "      44.0000000"),
    (27, 309, 324, "F16,7", "Right bottom corner geographic location of scene (long)", "      19.7000000"),
    (47, 502, 517, "F16,7", "Satellite heading angle (deg)           ", "     200.9000000"),
    (48, 518, 525, "I8   ", "Orbit number                            ", "   12345"),
    (51, 574, 589, "F16.7", "Sun angle (Azimuth) (deg)               ", "     157.2000000"),
    (52, 590, 605, "F16.7", "Sun angle (elevation) (deg)             ", "      42.8000000"),
]


def ssd_text():
    lines = ["# Euromap provides this file to help you with IRS products in Super",
             "# Structure format (SYNTHETIC).", "", "VOLUME DIRECTORY FILE ....", "",
             "Volume Descriptor Record ....", "",
             " 20  113  120 A8   Logical volume creation date            >20070815<",
             "Header Record ....", ""]
    for number, start, end, fmt, desc, value in SSD_HEADER_FIELDS:
        lines.append("%3d %4d %4d %s%s>%s<" % (number, start, end, fmt, desc, value))
    # a later record with an orbit number of its own: not the header's
    lines += ["Ephemeries/Attitude Record ....", "",
              " 48  518  525 I8   Orbit number                            >   99999<"]
    return "\n".join(lines) + "\n"


def p6_delivery(folder):
    """IRS-P6 flat delivery, as unpacked from its ZIP into <zip stem>/."""
    folder.mkdir(parents=True)
    (folder / "metadata.xml").write_text(P6_XML, encoding="ISO-8859-1")
    # BIL: per row, the four bands (green, red, NIR, SWIR) one after the other
    data = ramp(np.uint8, bands=4)                     # (rows, cols, bands)
    (folder / "imagery.bil").write_bytes(np.ascontiguousarray(np.moveaxis(data, -1, 1)).tobytes())
    (folder / "imagery.hdr").write_text(
        "BYTEORDER     M\nLAYOUT        BIL\nNROWS         %d\nNCOLS         %d\n"
        "NBANDS        4\nNBITS         8\nSKIPBYTES     0\n" % (ROWS, COLS), encoding="utf-8")
    (folder / "imagery.blw").write_text(
        "20.0\n0.0\n0.0\n-20.0\n7262270.0\n5050390.0\n", encoding="utf-8")
    (folder / "geolayer.bil").write_bytes(struct.pack(">4f", 0.0, 0.0, 0.0, 0.0))
    (folder / "calib.dat").write_text("SYNTHETIC calibration\n", encoding="utf-8")
    (folder / "060320P6036037L0030S3_ssd.txt").write_text(ssd_text(), encoding="latin-1")


if __name__ == "__main__":
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ortho_delivery(ROOT / "ort1" / "delivery", "100527P500000000PF_00O4", [
        ("IR05_PAN_PF__3O_20100527T101520_20100527T101524_NSG_01234_C22F.TIF", 1234, X0, 152.5, 50.25)])
    ortho_delivery(ROOT / "ort2" / "delivery", "100528P500000000PF_00O4", [
        ("IR05_PAN_PF__3O_20100528T101530_20100528T101534_NSG_01249_C22F.TIF", 1249, X0, 150.0, 51.0),
        ("IR05_PAN_PF__3O_20100528T101520_20100528T101525_NSG_01249_C22F.TIF", 1249, X0 + COLS * 2.5,
         150.5, 51.5)])
    dsm_tile(ROOT / "dsm" / "tile_a", "005E050NPA")
    dsm_tile(ROOT / "dsm" / "tile_b", "005E050NPB")
    p6_delivery(ROOT / "ir6" / "delivery")
    print("written:", ROOT)
