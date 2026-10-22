# SYNTHETIC FIXTURE — NOT REAL DATA

`synthetic_pl1/DIM_PHR1A_MS_SYNTH.XML` is a hand-written DIMAP product
document and `synthetic_pl1/STRIP_DS_SYNTH_DIM.XML` a hand-written lineage
strip document. Their structure is copied from a real DIMAP 2.15 Pleiades
delivery, reduced to the fields `product_pleiades.py` reads; their values are
invented (the specialization's example values where it has them).

The test derives the other product types from the MS document (PAN, PMS,
ortho / projected, bundle P + MS) by replacing a few values, and zips each
one with a PIL-generated preview JPG, a dummy image file and the strip
document into a fake native delivery, laid out as a real one
(`<job>/IMG_PHR1A_<kind>_001/...`).

It proves pipeline + JSON structure ONLY. The converter has also been run on
one real L3 PMS delivery of `TDS/PLEIADES/INBOX`.
