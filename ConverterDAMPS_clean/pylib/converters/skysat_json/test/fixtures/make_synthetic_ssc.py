"""Write the SYNTHETIC SkySat native items used by the tests.

Re-runnable: python make_synthetic_ssc.py (needs numpy + tifffile).
See SYNTHETIC_FIXTURE_NOTE.md for what each item proves.

Each item is the item metadata `<id>_metadata.json` (GeoJSON Feature, Planet
Data API properties) and tiny GeoTIFF rasters instead of the real ones; the
ortho ones carry GeoKeys with their EPSG code. Planet ships no asset XML for
SkySat.
"""
import json
import shutil
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE / "synthetic_ssc"

ROWS, COLS = 12, 16

# the specialization's example footprint
EXAMPLE_RING = [[-66.44291264, -24.15261009], [-66.44136086, -24.23036597],
                [-66.36391186, -24.22904374], [-66.36551048, -24.15129263],
                [-66.44291264, -24.15261009]]


def geokeys(epsg):
    """GeoKeyDirectoryTag (34735): projected model, pixel-is-area, EPSG."""
    keys = [1, 1, 0, 3,
            1024, 0, 1, 1,      # GTModelTypeGeoKey = projected
            1025, 0, 1, 1,      # GTRasterTypeGeoKey = pixel is area
            3072, 0, 1, epsg]   # ProjectedCSTypeGeoKey
    return [(34735, 'H', len(keys), keys, True)]


def ramp(bands, dtype, top):
    """Distinct band ramps; a zero (no-data) first column, as ortho scenes
    have around the footprint."""
    rows = np.arange(ROWS)[:, None]
    cols = np.arange(COLS)[None, :]
    data = np.stack([((rows + cols + 3 * b) % 11 + 1) * (top // 12) for b in range(bands)])
    data[:, :, 0] = 0
    return data.astype(dtype)


def write_planar(path, bands, epsg=None, dtype=np.uint16, top=4000):
    data = ramp(bands, dtype, top)
    if bands == 1:
        tifffile.imwrite(path, data[0], photometric="minisblack",
                         extratags=geokeys(epsg) if epsg else ())
    else:
        tifffile.imwrite(path, data, photometric="minisblack", planarconfig="separate",
                         extratags=geokeys(epsg) if epsg else ())


def write_rgb8(path, epsg=None):
    tifffile.imwrite(path, np.moveaxis(ramp(3, np.uint8, 240), 0, -1), photometric="rgb",
                     extratags=geokeys(epsg) if epsg else ())


def write_udm(path):
    tifffile.imwrite(path, np.ones((ROWS, COLS), dtype=np.uint8))


def write_rpc(path):
    path.write_text("LINE_OFF: +000006.00 pixels\n", encoding="utf-8")


def write_item_json(path, item_id, geometry, **properties):
    feature = {"type": "Feature", "id": item_id, "geometry": geometry,
               "properties": properties}
    path.write_text(json.dumps(feature, indent=2), encoding="utf-8")


def make_orders_layout():
    """Orders API delivery: two SkySatScene items flat in one folder."""
    folder = ROOT / "order_5f3a" / "SkySatScene"
    folder.mkdir(parents=True)

    # ortho pansharpened scene with its visual asset, values of the
    # specialization's example manifests
    psh = "20180428_125611_ssc3d2_0017"
    write_planar(folder / ("%s_pansharpened.tif" % psh), 4, epsg=32719)
    write_rgb8(folder / ("%s_visual.tif" % psh), epsg=32719)
    write_udm(folder / ("%s_pansharpened_udm2.tif" % psh))
    write_item_json(folder / ("%s_metadata.json" % psh), psh,
                    {"type": "Polygon", "coordinates": [EXAMPLE_RING]},
                    acquired="2018-04-28T12:56:11.806371Z", item_type="SkySatScene",
                    satellite_id="SSC3", camera_id="d2", strip_id="s3_20180428T125611Z",
                    provider="skysat", pixel_resolution=0.5, gsd=0.8,
                    sun_azimuth=33.3, sun_elevation=44.1, view_angle=0.7,
                    satellite_azimuth=99.1, cloud_cover=0.56, cloud_percent=56,
                    quality_category="standard", ground_control=True,
                    published="2018-04-29T02:10:33.000Z", updated="2018-05-02T10:11:12.000Z")

    # ortho panchromatic DN scene
    pan = "20190612_101530_ssc7d3_0042"
    write_planar(folder / ("%s_panchromatic_dn.tif" % pan), 1, epsg=32632)
    write_udm(folder / ("%s_panchromatic_dn_udm.tif" % pan))
    write_item_json(folder / ("%s_metadata.json" % pan), pan,
                    {"type": "Polygon", "coordinates": [[
                        [9.10, 45.40], [9.14, 45.40], [9.14, 45.43], [9.10, 45.43], [9.10, 45.40]]]},
                    acquired="2019-06-12T10:15:30.123456Z", item_type="SkySatScene",
                    satellite_id="SSC7", camera_id="d3", provider="skysat",
                    pixel_resolution=0.5, gsd=0.72, sun_azimuth=141.7, sun_elevation=62.6,
                    view_angle=12.4, cloud_percent=3, published="2019-06-12T18:30:00.000Z")
    # an order-level file, not part of any item
    (ROOT / "order_5f3a" / "manifest.json").write_text('{"name": "order_5f3a"}', encoding="utf-8")


def make_legacy_basic_layout():
    """Legacy Data API download: one folder per item, one sub-folder per
    asset. Basic (level 1B) panchromatic + 4-band DN scene, clockwise
    footprint, no cloud cover."""
    item = "20160501_144606_ssc1d1_0005"
    folder = ROOT / item
    for sub in ("basic_panchromatic_dn", "basic_panchromatic_dn_rpc",
                "basic_analytic_dn", "basic_analytic_dn_rpc"):
        (folder / sub).mkdir(parents=True)
    write_planar(folder / "basic_panchromatic_dn" / ("%s_basic_panchromatic_dn.tif" % item), 1)
    write_rpc(folder / "basic_panchromatic_dn_rpc" / ("%s_basic_panchromatic_dn_rpc.txt" % item))
    write_planar(folder / "basic_analytic_dn" / ("%s_basic_analytic_dn.tif" % item), 4)
    write_rpc(folder / "basic_analytic_dn_rpc" / ("%s_basic_analytic_dn_rpc.txt" % item))
    write_item_json(folder / ("%s_metadata.json" % item), item,
                    {"type": "Polygon", "coordinates": [[
                        [12.40, 41.90], [12.40, 41.95], [12.47, 41.95], [12.47, 41.90], [12.40, 41.90]]]},
                    acquired="2016-05-01T14:46:06.806000Z", item_type="SkySatScene",
                    satellite_id="SSC1", camera_id="d1", provider="skysat",
                    gsd=0.86, sun_azimuth=135.0, sun_elevation=55.5, view_angle=18.2,
                    published="2016-05-01T20:00:00Z")


def make_l1a_layout():
    """Basic L1A super resolution panchromatic DN scene, values of the
    specialization's L1ABDN_PAN example manifest."""
    item = "20160501_144606_ssc1d1_0006"
    folder = ROOT / item
    folder.mkdir(parents=True)
    write_planar(folder / ("%s_basic_l1a_panchromatic_dn.tif" % item), 1)
    write_rpc(folder / ("%s_basic_l1a_panchromatic_dn_rpc.txt" % item))
    write_item_json(folder / ("%s_metadata.json" % item), item,
                    {"type": "Polygon", "coordinates": [EXAMPLE_RING]},
                    acquired="2016-05-01T14:46:06.806000Z", item_type="SkySatScene",
                    satellite_id="SSC1", camera_id="d1", provider="skysat",
                    pixel_resolution=0.5, gsd=0.86, sun_azimuth=33.3, sun_elevation=44.1,
                    view_angle=35.1, cloud_cover=0.56, published="2016-05-01T20:00:00Z")


def make_collect():
    """SkySatCollect: the four image kinds of the SYNORT_BDL bundle,
    MultiPolygon footprint."""
    item = "20200619_094518_ssc11_u0001"
    folder = ROOT / "collect" / item
    folder.mkdir(parents=True)
    write_rgb8(folder / ("%s_visual.tif" % item), epsg=32633)
    write_planar(folder / ("%s_pansharpened.tif" % item), 4, epsg=32633)
    write_planar(folder / ("%s_analytic.tif" % item), 4, epsg=32633)
    write_planar(folder / ("%s_panchromatic.tif" % item), 1, epsg=32633)
    write_udm(folder / ("%s_udm2.tif" % item))
    write_item_json(folder / ("%s_metadata.json" % item), item,
                    {"type": "MultiPolygon", "coordinates": [
                        [[[15.00, 40.00], [15.10, 40.00], [15.10, 40.10], [15.00, 40.00]]],
                        [[[15.12, 40.02], [15.30, 40.02], [15.30, 40.20], [15.12, 40.02]]]]},
                    acquired="2020-06-19T09:45:18.250000Z", item_type="SkySatCollect",
                    satellite_id="SSC11", provider="skysat", pixel_resolution=0.5, gsd=0.66,
                    sun_azimuth=150.5, sun_elevation=66.0, view_angle=0.7, cloud_cover=0.05,
                    published="2020-06-19T18:00:00.000Z")


if __name__ == "__main__":
    if ROOT.exists():
        shutil.rmtree(ROOT)
    make_orders_layout()
    make_legacy_basic_layout()
    make_l1a_layout()
    make_collect()
    for p in sorted(ROOT.rglob("*")):
        if p.is_file():
            print("%8d  %s" % (p.stat().st_size, p.relative_to(HERE).as_posix()))
