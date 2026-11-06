# TerraSAR-X / TanDEM-X test fixtures

`synthetic_tsx/` holds five TerraSAR-X / TanDEM-X Level 1B products, written
by `make_synthetic_tsx.py` (re-runnable on the real DIMS deliveries). Each
fixture folder has a short name (`<variant>_<mode>`): the real product folder
name, repeated in the annotation file name, would bring the paths near the
Windows 260-character limit.

- The main annotation `<product name>.xml` is the real one, cut down to the
  elements the converter reads (generalHeader, productComponents,
  productInfo, and productSpecific/geocodedImageInfo/mapProjection for a
  geocoded product). Values are unchanged.
- `PREVIEW/BROWSE.tif` is the real browse image shrunk to at most 64 pixels.
- The image data files (`IMAGEDATA/*.cos` / `*.tif`, hundreds of MB) are
  16-byte placeholders with the real names.

| fixture | product | product type | what it covers |
|---|---|---|---|
| `SSC_SL` | TSX1_SAR__SSC______SL_S_SRA_20080311T141859_20080311T141900 | L1BSL__SLC | spotlight, COSAR image, EPSG:4326 |
| `SSC_HS` | TSX1_SAR__SSC______HS_S_SRA_20071129T170732_20071129T170732 | L1BSL__SLC | high resolution spotlight -> SL |
| `MGD_SL` | TDX1_SAR__MGD_RE___SL_S_SRA_20210802T165358_20210802T165359 | L1BSL__MGC | TanDEM-X (TDX / TOR), GeoTIFF image |
| `GEC_SC` | TSX1_SAR__GEC_RE___SC_S_SRA_20090130T013245_20090130T013307 | L1BSC__GEC | ScanSAR, UTM zone 11N, corners without row / column |
| `EEC_SC` | TSX1_SAR__EEC_RE___SC_S_SRA_20080902T115911_20080902T115933 | L1BSC__EEC | ScanSAR, UTM zone 16N, descending orbit |

So the asserted metadata values are real-product values. No StripMap, Wide
ScanSAR, staring spotlight or multi-polarisation product was available: those
mappings are covered by the type table test and the dual-polarisation test
only.

The five products were converted end to end on 2026-10-09 from the five real
deliveries in `TDS/TERRASAR-X/INBOX` (`5 converted, 5 packaged, 0
failure(s)`).
