"""Write the synthetic RADARSAT-2 test fixtures (no real product available).

Usage: python make_synthetic_rs2.py

Each fixture is a product folder named as MDA names them, holding:

- ``product.xml``: the RADARSAT-2 product annotation (default namespace
  ``http://www.rsi.ca/rs2/prod/xml/schemas``), reduced to the elements the
  converter reads, with invented but plausible values;
- ``BrowseImage.tif``: a small 8-bit grey gradient;
- ``imagery_<pol>.tif``: 16-byte placeholders;
- optionally a ``.prodReport`` holding the orbit number.
"""
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent / "synthetic_rs2"
NS = "http://www.rsi.ca/rs2/prod/xml/schemas"

PRODUCTS = [
    {   # Wide Fine, dual polarisation, single look complex, geodetic grid
        "folder": "RS2_OK10001_PK100001_DK100001_F0W2_20100527_231608_HH_HV_SLC",
        "beam": "F0W2", "acquisition": "Wide Fine", "type": "SLC",
        "pols": "HH HV", "pass": "Ascending", "pointing": "Right",
        "orbit_file": "13034_DEF.ORB",
        "first": "2010-05-27T23:16:08.123456Z", "last": "2010-05-27T23:16:12.987654Z",
        "processed": "2010-05-28T02:11:45.000000Z",
        "near": "35.12", "far": "39.88", "range_bw": "3.000000e+07", "azimuth_bw": "9.000000e+02",
        "corners": [(0, 0, 45.512, -73.701), (0, 2999, 45.598, -73.012),
                    (4999, 2999, 45.112, -72.901), (4999, 0, 45.031, -73.587)],
    },
    {   # Standard, single polarisation, path image, orbit from .prodReport
        "folder": "RS2_OK10002_PK100002_DK100002_S3_20120705_050236_HH_SGF",
        "beam": "S3", "acquisition": "Standard", "type": "SGF",
        "pols": "HH", "pass": "Descending", "pointing": "Right",
        "orbit_file": "DEF_ORBIT", "prod_report_orbit": "23861",
        "first": "2012-07-05T05:02:36.734596Z", "last": "2012-07-05T05:02:52.112233Z",
        "processed": "2012-07-05T09:30:00.500000Z",
        "near": "30.02", "far": "36.71", "range_bw": "1.158000e+07", "azimuth_bw": "2.600000e+02",
        "corners": [(0, 0, 38.881, 15.606), (0, 7999, 38.982, 16.701),
                    (9999, 7999, 37.902, 16.988), (9999, 0, 37.801, 15.889)],
    },
    {   # Fine Quad-Pol, quad polarisation, map image in UTM 33N
        "folder": "RS2_OK10003_PK100003_DK100003_FQ14_20140310_170512_HH_VV_HV_VH_SSG",
        "beam": "FQ14", "acquisition": "Fine Quad Polarization", "type": "SSG",
        "pols": "HH VV HV VH", "pass": "Ascending", "pointing": "Right",
        "orbit_file": "32850_DEF.ORB",
        "first": "2014-03-10T17:05:12.000100Z", "last": "2014-03-10T17:05:15.500100Z",
        "processed": "2014-03-11T08:00:00.000000Z",
        "near": "33.20", "far": "34.90", "range_bw": "3.000000e+07", "azimuth_bw": "9.200000e+02",
        "utm": ("33", "North"),
        "corners": [(0, 0, 41.950, 12.402), (0, 4999, 41.981, 12.661),
                    (5999, 4999, 41.781, 12.700), (5999, 0, 41.751, 12.441)],
    },
    {   # ScanSAR Wide, dual polarisation, left looking
        "folder": "RS2_OK10004_PK100004_DK100004_SCWA_20160812_101010_VV_VH_SCW",
        "beam": "SCWA", "acquisition": "ScanSAR Wide", "type": "SCW",
        "pols": "VV VH", "pass": "Descending", "pointing": "Left",
        "orbit_file": "45110_DEF.ORB",
        "first": "2016-08-12T10:10:10.000000Z", "last": "2016-08-12T10:11:40.000000Z",
        "processed": "2016-08-12T12:00:00.000000Z",
        "near": "20.00", "far": "49.00", "range_bw": "1.158000e+07", "azimuth_bw": "6.000000e+01",
        "corners": [(0, 0, 70.012, 20.101), (0, 9999, 69.512, 32.012),
                    (11999, 9999, 65.201, 30.512), (11999, 0, 65.801, 19.312)],
    },
]


def product_xml(p):
    images = "\n".join('    <fullResolutionImageData pole="%s">imagery_%s.tif</fullResolutionImageData>'
                       % (pol, pol) for pol in p["pols"].split())
    ties = "\n".join(
        "        <imageTiePoint><imageCoordinate><line>%d</line><pixel>%d</pixel></imageCoordinate>"
        '<geodeticCoordinate><latitude units="deg">%s</latitude><longitude units="deg">%s</longitude>'
        '<height units="m">100.0</height></geodeticCoordinate></imageTiePoint>' % c
        for c in p["corners"])
    projection = ""
    if "utm" in p:
        projection = ("\n      <mapProjection><mapProjectionDescriptor>UTM 33N WGS 1984</mapProjectionDescriptor>"
                      "<utmProjectionParameters><utmZone>%s</utmZone><hemisphere>%s</hemisphere>"
                      "</utmProjectionParameters></mapProjection>" % p["utm"])
    return """<?xml version="1.0" encoding="UTF-8"?>
<!-- SYNTHETIC RADARSAT-2 product annotation, NOT real data: see ../../SYNTHETIC_FIXTURE_NOTE.md -->
<product xmlns="%(ns)s">
  <productId>PDS_SYNTHETIC</productId>
  <sourceAttributes>
    <satellite>RADARSAT-2</satellite>
    <sensor>SAR</sensor>
    <beamModeMnemonic>%(beam)s</beamModeMnemonic>
    <radarParameters>
      <acquisitionType>%(acquisition)s</acquisitionType>
      <beams>%(beam)s</beams>
      <polarizations>%(pols)s</polarizations>
      <radarCenterFrequency units="Hz">5.405000454334350e+09</radarCenterFrequency>
      <antennaPointing>%(pointing)s</antennaPointing>
    </radarParameters>
    <orbitAndAttitude>
      <orbitInformation>
        <passDirection>%(pass)s</passDirection>
        <orbitDataSource>Definitive</orbitDataSource>
        <orbitDataFile>%(orbit_file)s</orbitDataFile>
        <stateVector>
          <timeStamp>%(first)s</timeStamp>
          <xPosition units="m">-2.1e+06</xPosition><yPosition units="m">-5.3e+06</yPosition><zPosition units="m">4.4e+06</zPosition>
          <xVelocity units="m/s">-1.2e+03</xVelocity><yVelocity units="m/s">-4.9e+03</yVelocity><zVelocity units="m/s">-5.5e+03</zVelocity>
        </stateVector>
      </orbitInformation>
    </orbitAndAttitude>
  </sourceAttributes>
  <imageGenerationParameters>
    <generalProcessingInformation>
      <productType>%(type)s</productType>
      <processingFacility>SYNTHETIC</processingFacility>
      <processingTime>%(processed)s</processingTime>
    </generalProcessingInformation>
    <sarProcessingInformation>
      <rangeLookBandwidth units="Hz">%(range_bw)s</rangeLookBandwidth>
      <azimuthLookBandwidth units="Hz">%(azimuth_bw)s</azimuthLookBandwidth>
      <zeroDopplerTimeFirstLine>%(first)s</zeroDopplerTimeFirstLine>
      <zeroDopplerTimeLastLine>%(last)s</zeroDopplerTimeLastLine>
      <incidenceAngleNearRange units="deg">%(near)s</incidenceAngleNearRange>
      <incidenceAngleFarRange units="deg">%(far)s</incidenceAngleFarRange>
      <satelliteHeight units="m">7.98e+05</satelliteHeight>
    </sarProcessingInformation>
  </imageGenerationParameters>
  <imageAttributes>
    <productFormat>GeoTIFF</productFormat>
%(images)s
    <geographicInformation>
      <geolocationGrid>
%(ties)s
      </geolocationGrid>
      <referenceEllipsoidParameters><ellipsoidName>WGS 1984</ellipsoidName></referenceEllipsoidParameters>%(projection)s
    </geographicInformation>
  </imageAttributes>
</product>
""" % dict(p, ns=NS, images=images, ties=ties, projection=projection)


def make_one(p):
    dest = HERE / p["folder"]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "product.xml").write_text(product_xml(p), encoding="utf-8")
    for pol in p["pols"].split():
        (dest / ("imagery_%s.tif" % pol)).write_bytes(b"SYNTHETIC IMAGE\n")
    Image.linear_gradient("L").resize((48, 32)).save(dest / "BrowseImage.tif")
    if "prod_report_orbit" in p:
        (dest / ("%s.prodReport" % p["folder"])).write_text(
            "Product Report (SYNTHETIC)\nOrbit Number                                   : %s\n"
            % p["prod_report_orbit"], encoding="utf-8")


if __name__ == "__main__":
    for product in PRODUCTS:
        make_one(product)
        print(HERE / product["folder"])
