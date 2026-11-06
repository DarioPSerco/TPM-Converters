"""Write the SYNTHETIC Beijing-1 native products used by the tests.

Re-runnable: python make_synthetic_dmc.py (needs Pillow).
See SYNTHETIC_FIXTURE_NOTE.md for what each product proves.

Each product is the unzipped delivery: the DIMAP header <dataset>.dim (the
element paths of the real deliveries, only the ones the converter reads and
their parents), the _meta.sip zip with a minimal repository.xml, a tiny
quicklook JPEG and placeholder .tif / .htm / .xsl bytes (never read).
Values are synthetic test values. Folder and file names are short
(Windows 260-character path limit); the dataset name the converter reads
is the DATASET_NAME inside the .dim.
"""
import io
import shutil
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_dmc"

DIM = """<?xml version="1.0" encoding="ISO-8859-1"?>
<?xml-stylesheet type="text/xsl" href="{file}.xsl"?>
<Dimap_Document xmlns:dim="http://www.spotimage.fr/Dimap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Metadata_Id>
        <METADATA_FORMAT version="1.1">DIMAP</METADATA_FORMAT>
    </Metadata_Id>
    <Dataset_Id>
        <DATASET_NAME>{name}</DATASET_NAME>
        <DATASET_QL_PATH href="{file}_ql.jpg"/>
    </Dataset_Id>
    <Production>
        <DATASET_PRODUCTION_DATE>{produced}</DATASET_PRODUCTION_DATE>
    </Production>
    <Data_Processing>
        <GEOMETRIC_PROCESSING>{geometric}</GEOMETRIC_PROCESSING>
    </Data_Processing>
{crs}    <Dataset_Frame>
{vertices}    </Dataset_Frame>
    <Data_Access>
        <DATA_FILE_FORMAT>GEOTIFF</DATA_FILE_FORMAT>
        <Data_File>
            <DATA_FILE_PATH href="{file}.tif"/>
        </Data_File>
    </Data_Access>
    <Dataset_Sources>
        <Source_Information>
            <Scene_Source>
                <MISSION>{mission}</MISSION>
{mission_index_element}                <INSTRUMENT>SLIM-6</INSTRUMENT>
                <VIEWING_ANGLE unit="DEG">0.25</VIEWING_ANGLE>
                <SUN_AZIMUTH unit="DEG">{sun_azimuth}</SUN_AZIMUTH>
                <SUN_ELEVATION unit="DEG">{sun_elevation}</SUN_ELEVATION>
            </Scene_Source>
        </Source_Information>
    </Dataset_Sources>
    <Data_Strip>
        <Sensor_Configuration>
            <Time_Stamp>
                <SCENE_CENTER_TIME>{center_time}</SCENE_CENTER_TIME>
            </Time_Stamp>
        </Sensor_Configuration>
    </Data_Strip>
</Dimap_Document>
"""

CRS = """    <Coordinate_Reference_System>
        <GEO_TABLES>EPSG</GEO_TABLES>
        <Horizontal_CS>
            <HORIZONTAL_CS_CODE>EPSG:{epsg}</HORIZONTAL_CS_CODE>
            <HORIZONTAL_CS_TYPE>{cs_type}</HORIZONTAL_CS_TYPE>
        </Horizontal_CS>
    </Coordinate_Reference_System>
"""

# Beijing-1 only: NigeriaSat-1 / UK-DMC-1 .dim files have no MISSION_INDEX
MISSION_INDEX = """                <MISSION_INDEX>{mission_index}</MISSION_INDEX>
"""

# geographic product: the corners in degrees as FRAME_X / FRAME_Y
VERTEX = """        <Vertex>
            <FRAME_X unit="DEG">{x}</FRAME_X>
            <FRAME_Y unit="DEG">{y}</FRAME_Y>
        </Vertex>
"""

# projected product: degrees as FRAME_LON / FRAME_LAT, metres as FRAME_X /
# FRAME_Y (as the real EPSG:2393 L1T delivery)
VERTEX_PROJECTED = """        <Vertex>
            <FRAME_LON unit="DEG">{x}</FRAME_LON>
            <FRAME_LAT unit="DEG">{y}</FRAME_LAT>
            <FRAME_X unit="M">{mx}</FRAME_X>
            <FRAME_Y unit="M">{my}</FRAME_Y>
        </Vertex>
"""

REPOSITORY = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Spacemetric_Repository version="1.0" id="sip201">
    <OBJECT ref="1" type="GeoImage">
        <Name>{name}</Name>
        <Resolution>{resolution}</Resolution>
        <ProductionDate>2010-01-01</ProductionDate>
        <CloudCoverPercent>{cloud}</CloudCoverPercent>
        <CoordinateSystemCode>{epsg}</CoordinateSystemCode>
    </OBJECT>
</Spacemetric_Repository>
"""

PRODUCTS = [
    # reference: every value read, counter 01, CRS, no cloud cover
    dict(file="l1r_p", name="DS00001a_000000_010499_p_L1R_AA", produced="2009-03-02",
         geometric="1R_AA", mission="BEIJING", mission_index="1",
         sun_azimuth="140.5", sun_elevation="35.25",
         center_time="2009-02-10 10:11:12", crs=True, epsg=4326, cs_type="GEOGRAPHIC",
         # counter-clockwise, as the real deliveries
         frame=[(10.0, 50.0), (11.0, 47.0), (15.0, 47.5), (14.0, 50.5)],
         resolution="32.5", cloud="", colour=(20, 180, 40)),
    # same scene time, view s -> counter 02, cloud cover filled, clockwise
    # frame (turned counter-clockwise)
    dict(file="l1r_s", name="DS00001a_000000_010499_s_L1R_BB", produced="2009-03-03",
         geometric="1R_BB", mission="BEIJING", mission_index="1",
         sun_azimuth="138.0", sun_elevation="34.0",
         center_time="2009-02-10 10:11:12", crs=True, epsg=4326, cs_type="GEOGRAPHIC",
         frame=[(6.0, 49.5), (10.0, 50.0), (11.0, 47.0), (7.0, 46.5)],
         resolution="32.5", cloud="12.5", colour=(200, 40, 40)),
    # L1T, geographic CRS other than WGS 84, counter 01
    dict(file="l1t_p", name="DS00002b_000000_010499_p_L1T_EPSG_4258_CC", produced="2009-06-01",
         geometric="1T_EPSG_4258_CC", mission="BEIJING", mission_index="1",
         sun_azimuth="130.0", sun_elevation="30.5",
         center_time="2009-05-06 07:08:09", crs=True, epsg=4258, cs_type="GEOGRAPHIC",
         frame=[(24.0, 68.0), (20.0, 67.5), (21.0, 66.0), (25.0, 66.5)],
         resolution="21.9", cloud="", colour=(40, 40, 200)),
    # its reduced-resolution QL copy: same scene time, counter 02; projected
    # CRS, footprint from FRAME_LON / FRAME_LAT, not the metres
    dict(file="l1t_ql", name="DS00002b_000000_010499_p_L1T_QL_EPSG_2393_CC", produced="2009-06-01",
         geometric="1T_QL_EPSG_2393_CC", mission="BEIJING", mission_index="1",
         sun_azimuth="130.0", sun_elevation="30.5",
         center_time="2009-05-06 07:08:09", crs=True, epsg=2393, cs_type="PROJECTED",
         frame=[(24.0, 68.0), (20.0, 67.5), (21.0, 66.0), (25.0, 66.5)],
         frame_m=[(3400000.0, 7550000.0), (3240000.0, 7500000.0),
                  (3280000.0, 7330000.0), (3440000.0, 7380000.0)],
         resolution="320.0", cloud="", colour=(200, 200, 40)),
    # NigeriaSat-1: no MISSION_INDEX in the .dim (as the real deliveries)
    dict(file="ng_t", name="DS00003c_L1T_EPSG_4258_DD", produced="2009-07-01",
         geometric="1T_EPSG_4258_DD", mission="NIGERIASAT", mission_index=None,
         sun_azimuth="125.0", sun_elevation="41.0",
         center_time="2009-04-03 08:09:10", crs=True, epsg=4258, cs_type="GEOGRAPHIC",
         frame=[(10.0, 55.0), (0.5, 53.5), (1.5, 51.5), (11.0, 53.0)],
         resolution="25.6", cloud="", colour=(40, 200, 200)),
    # UK-DMC-1: no MISSION_INDEX; projected CRS, footprint from FRAME_LON /
    # FRAME_LAT, not the metres
    dict(file="uk_t", name="DS00004d_L1T_EPSG_2190_EE", produced="2009-08-01",
         geometric="1T_EPSG_2190_EE", mission="UK-DMC", mission_index=None,
         sun_azimuth="107.0", sun_elevation="50.5",
         center_time="2009-07-27 11:07:39", crs=True, epsg=2190, cs_type="PROJECTED",
         frame=[(-24.0, 39.5), (-28.5, 38.5), (-27.5, 36.5), (-23.0, 37.5)],
         frame_m=[(765000.0, 4366000.0), (375000.0, 4277000.0),
                  (438000.0, 4036000.0), (829000.0, 4124000.0)],
         resolution="32.0", cloud="", colour=(200, 40, 200)),
]


def jpeg_bytes(colour):
    buf = io.BytesIO()
    Image.new("RGB", (16, 12), colour).save(buf, "JPEG")
    return buf.getvalue()


def write_product(p):
    folder = ROOT / p["file"]
    folder.mkdir(parents=True)
    if "frame_m" in p:
        vertices = "".join(VERTEX_PROJECTED.format(x=x, y=y, mx=mx, my=my)
                           for (x, y), (mx, my) in zip(p["frame"], p["frame_m"]))
    else:
        vertices = "".join(VERTEX.format(x=x, y=y) for x, y in p["frame"])
    index = (MISSION_INDEX.format(**p) if p["mission_index"] is not None else "")
    values = dict(p, vertices=vertices, crs=CRS.format(**p) if p["crs"] else "",
                  mission_index_element=index)
    (folder / (p["file"] + ".dim")).write_text(DIM.format(**values), encoding="ISO-8859-1")
    (folder / (p["file"] + "_ql.jpg")).write_bytes(jpeg_bytes(p["colour"]))
    with zipfile.ZipFile(folder / (p["file"] + "_meta.sip"), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("overview1.tif", b"synthetic overview placeholder")
        zf.writestr("repository.xml", REPOSITORY.format(**p))
    (folder / (p["file"] + ".tif")).write_bytes(b"synthetic image placeholder")
    (folder / (p["file"] + ".htm")).write_text("<html>synthetic placeholder</html>")
    (folder / (p["file"] + ".xsl")).write_text("<xsl>synthetic placeholder</xsl>")


if __name__ == "__main__":
    shutil.rmtree(ROOT, ignore_errors=True)
    for product in PRODUCTS:
        write_product(product)
    print("written:", ", ".join(p["file"] for p in PRODUCTS))
