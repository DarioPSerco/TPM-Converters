# SYNTHETIC FIXTURE — NOT REAL DATA

`synthetic_pln/DIM_PNEO3_MS_SYNTH.XML` is a hand-written DIMAP product
document and `synthetic_pln/LINEAGE_SYNTH_DIM.XML` a hand-written lineage
document carrying the orbit. No real Pleiades NEO delivery was available:
their structure is the Pleiades DIMAP one (same Airbus DIMAP family, see
`pleiades_json/test/fixtures`), reduced to the fields `product_pneo.py`
reads, with the PNEO identifiers (`DIM_PNEO3_*`, `IMG_PNEO3_*`,
`MISSION_INDEX` 3). Values are invented (the specialization's example values
where it has them).

The test derives the other product types from the MS document (PAN, PMS and
their `-FS` / `-N` variants, projected / ortho, bundle PAN + MS) by
replacing a few values, and zips each one with a PIL-generated preview JPG,
a dummy image file and the lineage document into a fake native delivery
(`<job>/IMG_PNEO3_<kind>_001/...`).

It proves pipeline + JSON structure ONLY. To check on the first real PNEO
delivery: where the orbit number / direction sit (else the cfg fallback is
used), `Solar_Incidences` and `INCIDENCE_ANGLE` paths, `CLOUD_COVERAGE`,
and the `SPECTRAL_PROCESSING` values.
