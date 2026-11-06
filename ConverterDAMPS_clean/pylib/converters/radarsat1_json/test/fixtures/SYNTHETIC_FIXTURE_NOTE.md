# RADARSAT-1 test fixtures

`synthetic_rs1/` holds four RADARSAT-1 CEOS deliveries, written by
`make_synthetic_rs1.py` (re-runnable on the real deliveries). The metadata
files (`.vol`, `.nvol`, `.sarl`, `.sart`, `.txt`) are the real ones, copied as
delivered; the image data file (`.sard`, hundreds of MB) is replaced by a
30 lines x 40 pixels synthetic one that keeps the real file descriptor (record
length, pixel and line counts patched) and the real record prefix.

| fixture | product type | what it covers |
|---|---|---|
| `01Jul98_13866_01` | L1_BSW_SGF | Data Set Summary in the leader, 16-bit detected image |
| `01Jul98_13866_02` | L1_BSW_SLC | complex (CI*4) image, slant range resolution |
| `08Dec99_21364_01` | L2_BM__SSG | Data Set Summary in the trailer, UTM map projection, no Processing Parameters record |
| `10Jul98_13990` (`M8067100_10Jul98_13990_SCN`) | L1_SCN____ | ScanSAR, 8-bit image, start/stop listed in reverse order in the scene description |

So the asserted metadata values are real-product values. The overview tests
only prove the image reading / scaling path on the three sample formats
(IU1, IU2, CI*4); the overviews of the real products were checked by eye on
the full images.

All ten product types of the specialization were converted end to end on
2026-10-09 from the ten real deliveries in
`NATIVI DA CONVERTIRE/RADARSAT-1` (`10 converted, 10 packaged, 0 failure(s)`).
