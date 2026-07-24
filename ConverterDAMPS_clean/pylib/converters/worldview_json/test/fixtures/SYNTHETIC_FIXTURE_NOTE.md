# SYNTHETIC fixture — `synthetic_wv/`

**This is NOT real WorldView data.** No real native WorldView product was present in
either converter's tree (`pylib/converters/worldview/` or
`pylib/converters/to_be_converted/worldview2/` ship no test data), so this fixture
was hand-authored to be faithful to the native structure the modern converter
parses (`product_worldview.py`):

- `010787518010_01_README.XML` — top README metadata; only `<SATID>` is read by the
  converter (to detect WorldView Legion). `WV01` ⇒ not Legion.
- `19AUG22104421-M2AS-010787518010_01_P001.IMD` — DigitalGlobe-style `.IMD` text;
  the converter parses `key = value;` lines for acquisition times, sun angles, cloud
  cover, corner coordinates, spacings, level/descriptor, satId, bandId, and counts
  `BEGIN_GROUP = BAND_*` groups for the band count.

Values are plausible but invented. The product resolves to type code **WV6_PAN_2A**
(WorldView-1, panchromatic, Standard 2A), scene centred near N13 / W100.
