"""Write the SYNTHETIC RapidEye native products used by the tests.

Re-runnable: python make_synthetic_re.py (needs numpy + tifffile).
See SYNTHETIC_FIXTURE_NOTE.md for what each product proves.

Each product is the metadata `<stem>_metadata.xml` (`re:EarthObservation`,
reduced to the elements the converter reads plus their usual neighbours) and
tiny rasters instead of the real ones.
"""
import shutil
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_re"

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<re:EarthObservation xmlns:re="http://schemas.rapideye.de/products/productMetadata{schema}"
    xmlns:eop="http://earth.esa.int/eop" xmlns:opt="http://earth.esa.int/opt"
    xmlns:gml="http://www.opengis.net/gml" version="1.2.1">
  <gml:metaDataProperty>
    <re:EarthObservationMetaData>
      <eop:identifier>{stem}</eop:identifier>
      <eop:acquisitionType>NOMINAL</eop:acquisitionType>
      <eop:productType>{level}</eop:productType>
      <eop:status>ARCHIVED</eop:status>
      <eop:archivedIn>
        <eop:ArchivingInformation>
          <eop:archivingCenter>Brandenburg</eop:archivingCenter>
          <eop:archivingDate>{processed}</eop:archivingDate>
        </eop:ArchivingInformation>
      </eop:archivedIn>
      <re:pixelFormat>16U</re:pixelFormat>
    </re:EarthObservationMetaData>
  </gml:metaDataProperty>
  <gml:validTime>
    <gml:TimePeriod>
      <gml:beginPosition>{begin}</gml:beginPosition>
      <gml:endPosition>{end}</gml:endPosition>
    </gml:TimePeriod>
  </gml:validTime>
  <gml:using>
    <eop:EarthObservationEquipment>
      <eop:platform>
        <eop:Platform>
          <eop:shortName>RE</eop:shortName>
          <eop:serialIdentifier>{satellite}</eop:serialIdentifier>
          <eop:orbitType>LEO</eop:orbitType>
        </eop:Platform>
      </eop:platform>
      <eop:instrument>
        <eop:Instrument>
          <eop:shortName>MSI</eop:shortName>
        </eop:Instrument>
      </eop:instrument>
      <eop:sensor>
        <re:Sensor>
          <eop:sensorType>OPTICAL</eop:sensorType>
          <eop:resolution uom="m">6.5</eop:resolution>
          <eop:scanType>PUSHBROOM</eop:scanType>
        </re:Sensor>
      </eop:sensor>
      <eop:acquisitionParameters>
        <re:Acquisition>
          <eop:orbitDirection>{orbit}</eop:orbitDirection>
          <eop:incidenceAngle uom="deg">{incidence}</eop:incidenceAngle>
          <opt:illuminationAzimuthAngle uom="deg">{sun_az}</opt:illuminationAzimuthAngle>
          <opt:illuminationElevationAngle uom="deg">{sun_el}</opt:illuminationElevationAngle>
          <re:azimuthAngle uom="deg">101.2</re:azimuthAngle>{view}
          <re:acquisitionDateTime>{begin}</re:acquisitionDateTime>
        </re:Acquisition>
      </eop:acquisitionParameters>
    </eop:EarthObservationEquipment>
  </gml:using>
  <gml:target>
    <re:Footprint>
      <re:multiExtentOf>
        <gml:MultiSurface srsName="EPSG:4326">
          <gml:surfaceMembers>
            <gml:Polygon>
              <gml:outerBoundaryIs>
                <gml:LinearRing>
                  <gml:coordinates>{ring}</gml:coordinates>
                </gml:LinearRing>
              </gml:outerBoundaryIs>
            </gml:Polygon>
          </gml:surfaceMembers>
        </gml:MultiSurface>
      </re:multiExtentOf>
    </re:Footprint>
  </gml:target>
  <gml:resultOf>
    <re:EarthObservationResult>{cloud}
      <re:unusableDataPercentage uom="percentage">0.0</re:unusableDataPercentage>
      <eop:product>
        <re:ProductInformation>
          <eop:fileName>{image}</eop:fileName>
          <re:productFormat>{native_format}</re:productFormat>{srs}
          <re:numRows>12</re:numRows>
          <re:numColumns>16</re:numColumns>
          <re:numBands>{bands}</re:numBands>
          <re:rowGsd>{gsd}</re:rowGsd>
          <re:columnGsd>{gsd}</re:columnGsd>
        </re:ProductInformation>
      </eop:product>
    </re:EarthObservationResult>
  </gml:resultOf>
</re:EarthObservation>
"""

SRS = """
          <re:spatialReferenceSystem>
            <re:epsgCode>{}</re:epsgCode>
          </re:spatialReferenceSystem>"""


def raster(bands, dtype):
    """(rows, cols, bands) ramp with an all-zero (no-data) first column."""
    rows, cols = 12, 16
    ramp = np.fromfunction(lambda r, c, b: 100 + r * 3 + c * 2 + b * 5,
                           (rows, cols, bands), dtype=float)
    ramp[:, 0, :] = 0
    return ramp.astype(dtype)


def write_tif(path, data):
    tifffile.imwrite(path, data, photometric="rgb" if data.shape[-1] == 3 else "minisblack",
                     planarconfig="contig", extrasamples=None if data.shape[-1] == 3 else ["unspecified"] * (data.shape[-1] - 1))


def write_xml(folder, stem, **values):
    (folder / ("%s_metadata.xml" % stem)).write_text(
        XML_TEMPLATE.format(stem=stem, **values), encoding="utf-8")


def l3_five_bands(folder):
    """Values of the specialization's example manifest."""
    stem = "2017-04-24T134911_RE1_3A-NAC_12345678_123456"
    write_xml(folder, stem, schema="Geocorrected", level="L3A", processed="2017-04-25T02:10:33Z",
              begin="2017-04-24T13:49:11Z", end="2017-04-24T13:51:11Z", satellite="RE-1",
              orbit="DESCENDING", incidence="0.7", sun_az="33.3", sun_el="44.1",
              view='\n          <re:spaceCraftViewAngle uom="deg">-0.7</re:spaceCraftViewAngle>',
              ring="-66.44291264,-24.15261009 -66.44136086,-24.23036597 -66.36391186,-24.22904374 "
                   "-66.36551048,-24.15129263 -66.44291264,-24.15261009",
              cloud='\n      <opt:cloudCoverPercentage uom="percentage">0.0</opt:cloudCoverPercentage>',
              image="%s.tif" % stem, native_format="GeoTIFF", srs=SRS.format(32719), bands=5, gsd="5.00")
    write_tif(folder / ("%s.tif" % stem), raster(5, np.uint16))
    tifffile.imwrite(folder / ("%s_udm.tif" % stem), raster(1, np.uint8)[:, :, 0])
    (folder / ("%s_license.txt" % stem)).write_text("synthetic\n", encoding="utf-8")


def l3_three_bands(folder):
    """Other product of the same delivery folder: name of a newer delivery,
    native browse, cloud cover not assessed, no view angle, no end time."""
    stem = "1234567_2016-08-12_RE3_3A_654321"
    write_xml(folder, stem, schema="Geocorrected", level="L3A", processed="2016-08-13T01:00:00.250+00:00",
              begin="2016-08-12T10:05:00.500+00:00", end="", satellite="RE-3",
              orbit="ASCENDING", incidence="3.2", sun_az="155.5", sun_el="51.25", view="",
              ring="12.0,41.0 12.2,41.0 12.2,41.2 12.0,41.2 12.0,41.0",
              cloud='\n      <opt:cloudCoverPercentage uom="percentage">-1</opt:cloudCoverPercentage>',
              image="%s.tif" % stem, native_format="GeoTIFF", srs=SRS.format(32633), bands=3, gsd="5.00")
    write_tif(folder / ("%s.tif" % stem), raster(3, np.uint8))
    write_tif(folder / ("%s_browse.tif" % stem), raster(3, np.uint8))


def l1b(folder):
    """One NITF per band, native browse, no CRS, clockwise footprint."""
    stem = "2012-03-05T101530_RE5_1B-NAC_22334455_778899"
    write_xml(folder, stem, schema="", level="L1B", processed="2012-03-06T08:30:00Z",
              begin="2012-03-05T10:15:30Z", end="2012-03-05T10:15:42Z", satellite="RE-5",
              orbit="DESCENDING", incidence="8.4", sun_az="170.0", sun_el="35.0",
              view='\n          <re:spaceCraftViewAngle uom="deg">8.1</re:spaceCraftViewAngle>',
              ring="9.0,45.0 9.0,45.5 9.5,45.5 9.5,45.0 9.0,45.0",
              cloud='\n      <opt:cloudCoverPercentage uom="percentage">12.345</opt:cloudCoverPercentage>',
              image="%s_band1.ntf" % stem, native_format="NITF", srs="", bands=5, gsd="6.50")
    for band in range(1, 6):
        # the converter never opens a NITF: size and name are what it needs
        (folder / ("%s_band%d.ntf" % (stem, band))).write_bytes(b"NITF02.10" + bytes(32))
    write_tif(folder / ("%s_browse.tif" % stem), raster(3, np.uint8))
    tifffile.imwrite(folder / ("%s_udm.tif" % stem), raster(1, np.uint8)[:, :, 0])
    (folder / ("%s_sci.xml" % stem)).write_text("<sci/>\n", encoding="utf-8")


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    delivery = ROOT / "delivery_re"
    delivery.mkdir(parents=True)
    l3_five_bands(delivery)
    l3_three_bands(delivery)
    basic = ROOT / "basic_re"
    basic.mkdir()
    l1b(basic)
    print("written:", ROOT)


if __name__ == "__main__":
    main()
