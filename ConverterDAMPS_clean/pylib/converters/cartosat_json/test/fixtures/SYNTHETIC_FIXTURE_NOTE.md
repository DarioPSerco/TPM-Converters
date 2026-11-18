# IRS-P5 / IRS-P6 test fixtures

`synthetic_ir5/` holds five SYNTHETIC native deliveries, written by
`make_synthetic_ir5.py` (re-runnable, needs `numpy` and `tifffile`). Each
delivery has the file set, file names and metadata elements of a real
delivery, with synthetic values and 16x12 rasters instead of the real ones,
so the whole extraction -> manifest -> overview -> package pipeline runs in a
test. Every raster has an all-no-data first column.

Folder names are short (`delivery`, `tile_a`, ...) to stay well inside the
Windows 260-character path limit; the file names are the real ones.

| folder | delivery | proves |
|---|---|---|
| `ort1/delivery/` | IRS-P5 ortho `100527P500000000PF_00O4`, one `EM_Ortho_Image_1/` | `L3_ORT_PAN`; times and orbit from `DATASET_NAME`, checked against `Orbit_no`; sun angles; production date; user-defined LAEA GeoTIFF CRS recognised as EPSG:3035; footprint corner at 5E 50N (the IOGP LAEA example point is the raster corner); orbit direction from the local solar time; overview from `_ql.tif` |
| `ort2/delivery/` | IRS-P5 ortho `100528P500000000PF_00O4`, `EM_Ortho_Image_1/` and `_2/` | two `acquisitionParameters` entries in one package; package times = earliest start (image 2) to latest end (image 1); footprint = the rectangle around both images |
| `dsm/tile_a/`, `dsm/tile_b/` | IRS-P5 DSM tiles `005E050NPA` and `005E050NPB` of one delivery date | `L3_DSM____` / `STER`; the five em3d layers; EPSG:3035 GeoTIFF CRS; times and processing date from the em3d name date; orbit number from the cfg, with a warning; same name fields, so the name registry gives counters `01` and `02` |
| `ir6/delivery/` | IRS-P6 LISS-III ortho, flat delivery as unpacked from its zip | `IR6`; lineage citation `<delivery folder>/metadata.xml`; `PROJECTION` `CS` -> EPSG:3909; footprint, sun angles and orbit direction (satellite heading) from the `_ssd.txt` header record, whose parser stops before a later record carrying another orbit number; 4-band BIL overview in false colour |

Real-product provenance: the layouts, file names, GeoTIFF geokeys, XML
elements and ssd line format are copied from the real deliveries in
`TDS/CARTOSAT/INBOX` (one IRS-P5 ortho delivery, six Euro-Maps 3D DSM tiles,
one IRS-P6 LISS-III delivery). Every value is synthetic. What the real
samples do not show, and the fixtures therefore cannot prove:

- an ortho delivery with more than one `EM_Ortho_Image_<n>/`;
- an ortho delivery without `_ql.tif`;
- IRS-P6 deliveries with a `PROJECTION` other than `CS`;
- the meaning of the em3d name tokens (`100001`, the tile code) and of the
  `acv` / `num` / `qc` / `src` layers, which the converter does not read.
