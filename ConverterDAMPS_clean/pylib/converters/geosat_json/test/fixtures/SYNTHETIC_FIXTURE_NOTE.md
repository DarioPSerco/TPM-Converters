# SYNTHETIC FIXTURE — NOT REAL DATA

`synthetic_geosat/DE2_PAN_L1C_SYNTH.dim` (GEOSAT-2) and
`synthetic_geosat/DE1_SL6_22P_1R_SYNTH.dim` (GEOSAT-1) are hand-written
DIMAP documents. No real GEOSAT delivery was available: their structure
follows the element paths the legacy eoSIP GEOSAT converter read
(`pylib/products/product_geosat.py` on `main`: `Dataset_Sources/
Source_Information/Scene_Source/*`, `Source_Frame/Vertex`,
`Quality_Assessment/Quality_Parameter` with the `GEOSAT:CCP` / `GEOSAT:ORD` /
`SPACEMETRIC:HEADING` codes, `Production/PRODUCT_TYPE`,
`Data_Access/Data_File/DATA_FILE_PATH`), reduced to the fields
`product_geosat.py` reads. Values are invented (the specialization's example
values where it has them: footprint, times, sun angles).

The test derives the other product types from these two documents (PAN /
MS4 / PSH / PS4, levels 1B / 1C / 1D; GEOSAT-1 1R / 1T / 2T; bundle as two
documents or as one PM4 document split by image; stereo pairs) by replacing
a few values, and zips each one with a PIL-generated quicklook PNG and a
dummy image file into a fake native delivery (`<name>/<name>.dim|.tif|_QL.png`).

It proves pipeline + JSON structure ONLY. To check on the first real GEOSAT
deliveries:
- the ZIP layout (one .dim per product or per component, quicklook names);
- how a bundle (PM4) and a stereo pair (STP) are delivered;
- where the orbit number sits (else the `..._DE2_<orbit>_<id>` name part,
  else the cfg fallback `METADATA_ORBIT`, with a WARNING); GEOSAT-1 names
  carry none;
- the resolution tags (`PIXEL_RESOLUTION_X` / `THEORETICAL_RESOLUTION`,
  else the nominal value of spec Tables 2 / 3);
- the `PRODUCT_TYPE` values (`L1R`, `L1T`, `L2T`, `L1B`, `L1C`, `L1D`).
