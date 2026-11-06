# SYNTHETIC FIXTURE — NOT REAL ICEYE DATA

`synthetic_ice/` is a hand-written, clearly synthetic ICEYE native product.
No ICEYE TDS was available when iceye_json was developed; this fixture exists
ONLY to prove the pipeline runs end-to-end and that the emitted JSON matches
`TDS/template/ICE-template.json` structurally.

- The metadata XML element names and shapes are inferred from
  `product_iceye.Product_Iceye.xmlMapping` and its refine/footprint code —
  NOT from a real ICEYE metadata file.
- The `.png` quicklook is a 1x1 dummy; the `.h5` is a placeholder byte file.
- All values (dates, coordinates, orbit, angles, spacings) are invented.

VALUE-CORRECTNESS ON REAL DATA IS PENDING until ICEYE TDS arrive. Do not use
this fixture to validate metadata values, native naming, or file layout.
