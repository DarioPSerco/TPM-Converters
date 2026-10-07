"""Write the SYNTHETIC PlanetScope native items used by the tests.

Re-runnable: python make_synthetic_psc.py (needs numpy + tifffile).
See SYNTHETIC_FIXTURE_NOTE.md for what each item proves.

Each item is the item metadata `<id>_metadata.json` (GeoJSON Feature, Planet
Data API properties), the asset XML `<id>_<asset>_metadata.xml` (Planet
`ps:EarthObservation`, reduced to the elements the converter reads plus their
usual neighbours) and tiny GeoTIFF rasters instead of the real ones.
"""
import json
import shutil
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_psc"

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ps:EarthObservation xmlns:ps="http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level"
    xmlns:eop="http://earth.esa.int/eop" xmlns:opt="http://earth.esa.int/opt"
    xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <gml:metaDataProperty>
    <ps:EarthObservationMetaData>
      <eop:identifier>{identifier}</eop:identifier>
      <eop:acquisitionType>NOMINAL</eop:acquisitionType>
      <eop:productType>{level}</eop:productType>
      <eop:status>ARCHIVED</eop:status>
      <eop:processing>
        <eop:ProcessingInformation>
          <eop:processorName>{processor}</eop:processorName>
          <eop:processorVersion>{version}</eop:processorVersion>
          <eop:nativeProductFormat>GeoTIFF</eop:nativeProductFormat>
        </eop:ProcessingInformation>
      </eop:processing>
      <ps:pixelFormat>{pixel_format}</ps:pixelFormat>
    </ps:EarthObservationMetaData>
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
          <eop:shortName>PlanetScope</eop:shortName>
          <eop:serialIdentifier>{satellite}</eop:serialIdentifier>
          <eop:orbitType>LEO</eop:orbitType>
        </eop:Platform>
      </eop:platform>
      <eop:instrument>
        <eop:Instrument>
          <eop:shortName>{instrument}</eop:shortName>
        </eop:Instrument>
      </eop:instrument>
      <eop:sensor>
        <ps:Sensor>
          <eop:sensorType>OPTICAL</eop:sensorType>
          <eop:resolution uom="m">{gsd}</eop:resolution>
          <eop:scanType>FRAME</eop:scanType>
        </ps:Sensor>
      </eop:sensor>
      <eop:acquisitionParameters>
        <ps:Acquisition>
          <eop:orbitDirection>{orbit}</eop:orbitDirection>
          <eop:incidenceAngle uom="deg">{incidence}</eop:incidenceAngle>
          <opt:illuminationAzimuthAngle uom="deg">{sun_az}</opt:illuminationAzimuthAngle>
          <opt:illuminationElevationAngle uom="deg">{sun_el}</opt:illuminationElevationAngle>
          <ps:azimuthAngle uom="deg">{sat_az}</ps:azimuthAngle>
          <ps:spaceCraftViewAngle uom="deg">{view}</ps:spaceCraftViewAngle>
          <ps:acquisitionDateTime>{begin}</ps:acquisitionDateTime>
        </ps:Acquisition>
      </eop:acquisitionParameters>
    </eop:EarthObservationEquipment>
  </gml:using>
  <gml:resultOf>
    <ps:EarthObservationResult>
      <eop:product>
        <ps:ProductInformation>
          <eop:fileName>{filename}</eop:fileName>
          <ps:productFormat>GeoTIFF</ps:productFormat>{srs}
          <ps:numRows>{rows}</ps:numRows>
          <ps:numColumns>{cols}</ps:numColumns>
          <ps:numBands>{bands}</ps:numBands>
          <ps:rowGsd>{gsd}</ps:rowGsd>
          <ps:columnGsd>{gsd}</ps:columnGsd>
        </ps:ProductInformation>
      </eop:product>
    </ps:EarthObservationResult>
  </gml:resultOf>
</ps:EarthObservation>
"""

SRS_TEMPLATE = """
          <ps:spatialReferenceSystem>
            <ps:epsgCode>{epsg}</ps:epsgCode>
            <ps:geodeticDatum>WGS_1984</ps:geodeticDatum>
          </ps:spatialReferenceSystem>"""

ROWS, COLS = 12, 16


def write_xml(path, image_name, epsg=None, **values):
    srs = SRS_TEMPLATE.format(epsg=epsg) if epsg else ""
    path.write_text(XML_TEMPLATE.format(filename=image_name, srs=srs, rows=ROWS,
                                        cols=COLS, **values), encoding="utf-8")


def write_item_json(path, item_id, geometry, **properties):
    feature = {"type": "Feature", "id": item_id, "geometry": geometry,
               "properties": properties}
    path.write_text(json.dumps(feature, indent=2), encoding="utf-8")


def ramp(bands, dtype, top):
    """Distinct band ramps; a zero (no-data) first column, as ortho scenes
    have around the footprint."""
    rows = np.arange(ROWS)[:, None]
    cols = np.arange(COLS)[None, :]
    data = np.stack([((rows + cols + 3 * b) % 11 + 1) * (top // 12) for b in range(bands)])
    data[:, :, 0] = 0
    return data.astype(dtype)


def write_planar(path, bands, dtype=np.uint16, top=4000):
    tifffile.imwrite(path, ramp(bands, dtype, top), photometric="minisblack",
                     planarconfig="separate")


def write_rgb8(path):
    tifffile.imwrite(path, np.moveaxis(ramp(3, np.uint8, 240), 0, -1), photometric="rgb")


def write_udm(path):
    tifffile.imwrite(path, np.ones((ROWS, COLS), dtype=np.uint8))


def make_orders_layout():
    """Orders API delivery: two items flat in one folder."""
    folder = ROOT / "order_7d1c" / "PSScene"
    folder.mkdir(parents=True)

    # Dove, visual product, values of the specialization's example manifest
    vo = "20170424_134911_0e19"
    write_rgb8(folder / ("%s_3B_Visual.tif" % vo))
    write_udm(folder / ("%s_3B_udm2.tif" % vo))
    write_xml(folder / ("%s_3B_Visual_metadata.xml" % vo), "%s_3B_Visual.tif" % vo,
              epsg=32719, identifier="%s_3B_Visual" % vo, level="L3B",
              processor="Planet Ortho Processor", version="4.1.0", pixel_format="8U",
              begin="2017-04-24T13:49:11+00:00", end="2017-04-24T13:51:11+00:00",
              satellite="0e19", instrument="PS2", gsd="3.7", orbit="DESCENDING",
              incidence="0.7", sun_az="33.3", sun_el="44.1", sat_az="98.2", view="0.6",
              bands=3)
    write_item_json(folder / ("%s_metadata.json" % vo), vo,
                    {"type": "Polygon", "coordinates": [[
                        [-66.44291264, -24.15261009], [-66.44136086, -24.23036597],
                        [-66.36391186, -24.22904374], [-66.36551048, -24.15129263],
                        [-66.44291264, -24.15261009]]]},
                    acquired="2017-04-24T13:49:11.806371Z", item_type="PSScene",
                    instrument="PS2", satellite_id="0e19", provider="planetscope",
                    pixel_resolution=3.0, gsd=3.7, sun_azimuth=33.3, sun_elevation=44.1,
                    view_angle=0.6, cloud_cover=0.0, quality_category="standard",
                    published="2017-04-25T02:10:33.000Z", updated="2017-05-02T10:11:12.000Z")

    # SuperDove, 8 bands surface reflectance
    sr = "20210314_070803_29_2262"
    write_planar(folder / ("%s_3B_AnalyticMS_SR_8b.tif" % sr), 8)
    write_udm(folder / ("%s_3B_udm2.tif" % sr))
    write_xml(folder / ("%s_3B_AnalyticMS_8b_metadata.xml" % sr), "%s_3B_AnalyticMS_8b.tif" % sr,
              epsg=32632, identifier="%s_3B_AnalyticMS_8b" % sr, level="L3B",
              processor="Planet Ortho Processor", version="4.3.2", pixel_format="16U",
              begin="2021-03-14T07:08:03.311795+00:00", end="2021-03-14T07:08:03.311795+00:00",
              satellite="2262", instrument="PSB.SD", gsd="3.9", orbit="DESCENDING",
              incidence="5.2", sun_az="141.7", sun_el="38.6", sat_az="101.4", view="4.6",
              bands=8)
    write_item_json(folder / ("%s_metadata.json" % sr), sr,
                    {"type": "Polygon", "coordinates": [[
                        [9.10, 45.40], [9.40, 45.40], [9.40, 45.60], [9.10, 45.60], [9.10, 45.40]]]},
                    acquired="2021-03-14T07:08:03.311795Z", item_type="PSScene",
                    instrument="PSB.SD", satellite_id="2262", provider="planetscope",
                    pixel_resolution=3.0, gsd=3.9, sun_azimuth=141.7, sun_elevation=38.6,
                    view_angle=4.6, cloud_cover=0.12, cloud_percent=12,
                    published="2021-03-14T12:30:00.000Z")
    # an order-level file, not part of any item
    (ROOT / "order_7d1c" / "manifest.json").write_text('{"name": "order_7d1c"}', encoding="utf-8")


def make_legacy_basic_layout():
    """Legacy Data API download: one folder per item, one sub-folder per
    asset; Dove-R basic (level 1B) 4-band scene, clockwise footprint."""
    item = "20190801_093015_1018"
    folder = ROOT / item
    (folder / "basic_analytic_4b").mkdir(parents=True)
    (folder / "basic_analytic_4b_xml").mkdir()
    (folder / "basic_analytic_4b_rpc").mkdir()
    write_planar(folder / "basic_analytic_4b" / ("%s_1B_AnalyticMS.tif" % item), 4)
    write_xml(folder / "basic_analytic_4b_xml" / ("%s_1B_AnalyticMS_metadata.xml" % item),
              "%s_1B_AnalyticMS.tif" % item, identifier="%s_1B_AnalyticMS" % item, level="L1B",
              processor="Planet Basic Processor", version="3.9.0", pixel_format="16U",
              begin="2019-08-01T09:30:15.500000+00:00", end="2019-08-01T09:30:16.250000+00:00",
              satellite="1018", instrument="PS2.SD", gsd="3.7", orbit="DESCENDING",
              incidence="3.1", sun_az="135.0", sun_el="55.5", sat_az="99.0", view="2.8",
              bands=4)
    (folder / "basic_analytic_4b_rpc" / ("%s_1B_AnalyticMS_RPC.TXT" % item)).write_text(
        "LINE_OFF: +000006.00 pixels\n", encoding="utf-8")
    write_item_json(folder / ("%s_metadata.json" % item), item,
                    {"type": "Polygon", "coordinates": [[
                        [12.40, 41.90], [12.40, 42.00], [12.55, 42.00], [12.55, 41.90], [12.40, 41.90]]]},
                    acquired="2019-08-01T09:30:15.500000Z", item_type="PSScene",
                    instrument="PS2.SD", satellite_id="1018", provider="planetscope",
                    gsd=3.7, sun_azimuth=135.0, sun_elevation=55.5, view_angle=2.8,
                    published="2019-08-01T15:00:00Z")


def make_ortho_tile():
    """PSOrthoTile, 4-band analytic, MultiPolygon footprint."""
    item = "1234567_3357220_2017-04-24_0e19"
    folder = ROOT / "ortho_tile" / item
    folder.mkdir(parents=True)
    write_planar(folder / ("%s_BGRN_Analytic.tif" % item), 4)
    write_udm(folder / ("%s_BGRN_DN_udm.tif" % item))
    write_xml(folder / ("%s_BGRN_Analytic_metadata.xml" % item), "%s_BGRN_Analytic.tif" % item,
              epsg=32633, identifier="%s_BGRN_Analytic" % item, level="L3A",
              processor="Planet Ortho Tile Processor", version="2.2.1", pixel_format="16U",
              begin="2017-04-24T10:05:00+00:00", end="2017-04-24T10:05:00+00:00",
              satellite="0e19", instrument="PS2", gsd="3.7", orbit="DESCENDING",
              incidence="1.2", sun_az="150.5", sun_el="50.0", sat_az="97.0", view="1.1",
              bands=4)
    write_item_json(folder / ("%s_metadata.json" % item), item,
                    {"type": "MultiPolygon", "coordinates": [
                        [[[15.00, 40.00], [15.10, 40.00], [15.10, 40.10], [15.00, 40.00]]],
                        [[[15.12, 40.02], [15.30, 40.02], [15.30, 40.20], [15.12, 40.02]]]]},
                    acquired="2017-04-24T10:05:00.123456Z", item_type="PSOrthoTile",
                    instrument="PS2", satellite_id="0e19", provider="planetscope",
                    pixel_resolution=3.125, gsd=3.7, sun_azimuth=150.5, sun_elevation=50.0,
                    view_angle=1.1, cloud_cover=0.05, published="2017-04-24T18:00:00.000Z")


if __name__ == "__main__":
    if ROOT.exists():
        shutil.rmtree(ROOT)
    make_orders_layout()
    make_legacy_basic_layout()
    make_ortho_tile()
    for p in sorted(ROOT.rglob("*")):
        if p.is_file():
            print("%8d  %s" % (p.stat().st_size, p.relative_to(HERE).as_posix()))
