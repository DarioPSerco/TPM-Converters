# RapidEye test fixtures

`synthetic_re/` holds three SYNTHETIC native RapidEye products, written by
`make_synthetic_re.py` (re-runnable, needs `tifffile`). Each product is the
metadata `<stem>_metadata.xml` (`re:EarthObservation`, reduced to the elements
the converter reads and their usual neighbours) and 16x12 rasters instead of
the real ones, so the whole extraction -> manifest -> overview pipeline runs
in a test.

| product | layout | image | product type | proves |
|---|---|---|---|---|
| `2017-04-24T134911_RE1_3A-NAC_12345678_123456` | `delivery_re/`, shared folder | `<stem>.tif`, 5 bands | `L3_ORT_MS_` | values of the specialization's example manifest (footprint, times, sun angles); overview rendered from the GeoTIFF; product files picked by prefix out of a shared folder |
| `1234567_2016-08-12_RE3_3A_654321` | same folder as above | `<stem>.tif`, 3 bands | `L3_ORT_MS_` | VIS wavelengths only, native browse, cloud cover `-1` left out, no view angle left out, empty end time set to the start |
| `2012-03-05T101530_RE5_1B-NAC_22334455_778899` | `basic_re/` | `<stem>_band1..5.ntf` | `L1BOPT_MS_` | one image per band, no CRS (left out), clockwise footprint turned counter-clockwise, overview from the browse |

The `.ntf` files are stubs: the converter carries them but never opens them.

Real-product provenance: NONE. No real RapidEye product has been converted
yet, and the specialization does not describe the native format. The file names
and the XML are written from memory of the Planet/BlackBridge RapidEye product
documentation; they have to be checked against a real delivery. In particular:

- the name of the element holding the processing date: the converter reads
  `processingDate`, else `archivingDate`, and fails if neither exists;
- `spaceCraftViewAngle` as the source of `acrossTrackIncidenceAngle`;
- the `gml:coordinates` order (read as `lon,lat`);
- band order in a 3-band image (read as R,G,B) and in a 5-band image (read as
  B,G,R,RE,NIR), used for the overview only;
- a `cloudCoverPercentage` outside 0-100 meaning "not assessed".
