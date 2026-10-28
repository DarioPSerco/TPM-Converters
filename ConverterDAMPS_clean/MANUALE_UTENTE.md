# Manuale utente

## 1. Scopo

Il progetto converte dataset satellitari nei manifest JSON definiti dai template TDS e crea un delivery ZIP contenente:

- il manifest JSON;
- il prodotto nativo nella cartella `measurements/`;
- il quicklook PNG nella cartella `preview/overviews/`.

Le missioni supportate sono:

- GeoEye-1: `geoeye1`
- WorldView: `worldview`
- QuickBird-2: `quickbird`
- ICEYE: `iceye`
- Pleiades: `pleiades`
- Pleiades NEO: `pneo`
- COSMO-SkyMed: `cosmoskymed`
- PlanetScope: `planetscope`
- SkySat: `skysat`
- Beijing-1, NigeriaSat-1, UK-DMC-1: `dmc`

## 2. Prerequisiti

Aprire PowerShell e posizionarsi nella root del progetto:

```powershell
cd "C:\Users\DPACCHIAROTT\ptojects\TPM-Converters\ConverterDAMPS_clean"
```

Verificare Python:

```powershell
py --version
```

In questo ambiente Windows il comando `python` può non essere disponibile. Usare `py` oppure l'interprete del virtual environment:

```powershell
..\..\.venv\Scripts\python.exe --version
```

Se il virtual environment non è ancora configurato:

```powershell
py -m venv ..\..\.venv
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\..\.venv\Scripts\python.exe -m pip install -e .\pylib\eoSip_converter
```

Verificare che venga importato il package del progetto:

```powershell
..\..\.venv\Scripts\python.exe -c "import eoSip_converter; print(eoSip_converter.__file__)"
```

Il percorso stampato deve puntare a `ConverterDAMPS_clean\pylib\eoSip_converter`.

## 3. Struttura delle cartelle

Ogni missione deve avere questa struttura sotto `TDS`:

```text
TDS\<MISSIONE>\
├── DONESPACE\
├── FAILEDSPACE\
├── INBOX\
├── OUTSPACE\
├── PRODUCTS\
└── TMPSPACE\
```

Esempi:

```text
TDS\GEOEYE\INBOX\
TDS\ICEYE\INBOX\
TDS\PLEIADES\INBOX\
```

Le cartelle sono usate nel modo seguente:

| Cartella | Contenuto |
|---|---|
| `INBOX` | Dataset da convertire |
| `TMPSPACE` | File temporanei e prodotti in elaborazione |
| `OUTSPACE` | Manifest JSON generati |
| `PRODUCTS` | Delivery ZIP finali |
| `DONESPACE` | Dataset convertiti e impacchettati correttamente |
| `FAILEDSPACE` | Dataset per cui conversione o packaging hanno fallito |

## 4. Preparazione del dataset

Il dataset può essere copiato in `INBOX` come cartella estratta oppure come archivio `.zip`.

Un `.zip` posto direttamente in `INBOX` viene estratto dal runner all'inizio dello stage `convert`, in `TMPSPACE\STAGE_<nome zip>\`. Se lo ZIP contiene una sola cartella, quella cartella è il dataset; altrimenti i file vengono raccolti in `STAGE_<nome zip>\<nome zip>\`. A fine run in `DONESPACE` finisce solo il dataset estratto: l'archivio originale viene cancellato. Se la conversione o il packaging falliscono, l'archivio originale viene invece spostato in `FAILEDSPACE` insieme al dataset estratto. Uno ZIP corrotto resta in `INBOX` e il runner stampa `unzip: ... FAILED`. Se lo ZIP estratto non contiene nessun file di ingresso (per esempio uno ZIP che contiene altri ZIP), il dataset non viene convertito né segnalato come failure: resta in `TMPSPACE\STAGE_<nome zip>\` e va controllato a mano.

PLEIADES e PNEO usano già lo ZIP come formato nativo: per queste missioni lo ZIP non viene estratto.

Copiare l'intera cartella del prodotto (o il suo ZIP), mantenendo i file nativi e i file metadata.

Esempi di file di ingresso:

| Missione | File individuato |
|---|---|
| GeoEye-1 | `*_README.XML` |
| WorldView | secondo il pattern configurato nella missione |
| QuickBird-2 | secondo il pattern configurato nella missione |
| ICEYE | `*.xml` |
| Pleiades | secondo il pattern configurato nella missione |
| Pleiades NEO | secondo il pattern configurato nella missione |
| COSMO-SkyMed | `*.h5` oppure `*.tgz` |
| PlanetScope | `<item id>_metadata.json` |
| SkySat | `<item id>_metadata.json` |
| Beijing-1 / NigeriaSat-1 / UK-DMC-1 | `<dataset>.dim` |

Esempio GeoEye:

```text
TDS\GEOEYE\INBOX\GE1_OPER_...\050372013030_01\050372013030_01_README.XML
```

Esempio ICEYE:

```text
TDS\ICEYE\INBOX\ICE_OPER_...\SLH_...\ICEYE_...GRD....xml
```

Il nome e l'estensione del metadata devono rispettare il `[Search]` del file `ingest_<missione>.cfg`.

## 5. Conversione completa

Il comando consigliato esegue in sequenza conversione, packaging e archiviazione:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py geoeye1
```

Sostituire `geoeye1` con la missione desiderata:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py worldview
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py quickbird
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py iceye
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py pleiades
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py pneo
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py cosmoskymed
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py planetscope
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py skysat
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py dmc
```

È possibile usare anche `py` se l'ambiente globale contiene tutte le dipendenze:

```powershell
py pylib\converters\run_mission.py geoeye1
```

## 6. Stadi separati

Il runner supporta quattro modalità:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py <missione> --stage convert
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py <missione> --stage package
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py <missione> --stage move
```

- `convert`: genera solo i manifest JSON.
- `package`: crea i delivery ZIP usando i manifest in `OUTSPACE`.
- `move`: archivia i dataset per i quali esistono sia JSON sia ZIP.
- `all`: esegue tutti i passaggi ed è il valore predefinito.

Per una diagnosi è utile eseguire prima:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py iceye --stage convert
```

## 7. Risultati attesi

In caso di successo il terminale mostra un riepilogo simile:

```text
== geoeye1: 1 converted, 1 packaged, 0 failure(s) ==
```

I file risultanti sono:

```text
TDS\GEOEYE\OUTSPACE\<PRODUCT_ID>.JSON
TDS\GEOEYE\PRODUCTS\<PRODUCT_ID>.ZIP
TDS\GEOEYE\DONESPACE\<dataset originale>\
```

Il delivery ZIP ha questa struttura:

```text
<PRODUCT_ID>.ZIP
├── <PRODUCT_ID>.JSON
├── measurements\
└── preview\overviews\<PRODUCT_ID>.PNG
```

Il JSON deve avere la struttura del template della missione in `TDS\template\`. Per GeoEye, WorldView, QuickBird e ICEYE, i template aggiornati usano array nei nodi previsti, ad esempio:

```json
"acquisitionInformation": [
  {
    "acquisitionParameters": [
      {}
    ]
  }
]
```

## 8. Gestione dei failure

Se il runner mostra `failure(s)`, controllare il riepilogo:

```text
converted
packaged
failure(s)
```

Un dataset può essere convertito correttamente ma fallire nel packaging. In quel caso il JSON può essere presente in `OUTSPACE`, mentre il ZIP non viene creato.

Controllare:

```text
TDS\<MISSIONE>\OUTSPACE\
TDS\<MISSIONE>\PRODUCTS\
TDS\<MISSIONE>\FAILEDSPACE\
log\<missione>\<YYYY-MM-DD>\
```

Per ritentare una conversione, spostare l'intera cartella del dataset da `FAILEDSPACE` a `INBOX`, non solo il JSON:

```powershell
Move-Item `
  "TDS\GEOEYE\FAILEDSPACE\<dataset>" `
  "TDS\GEOEYE\INBOX\"
```

Poi rilanciare il comando della missione.

Un JSON già presente in `FAILEDSPACE` può essere un artefatto di una run precedente. Per verificare il formato effettivamente prodotto, leggere il JSON in `OUTSPACE` dopo una nuova conversione.

## 9. Errori comuni

### `Python was not found`

Usare:

```powershell
py --version
py pylib\converters\run_mission.py geoeye1
```

Oppure:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py geoeye1
```

### `invalid choice: 'geoeye'`

Il nome accettato dal runner è `geoeye1`:

```powershell
py pylib\converters\run_mission.py geoeye1
```

### `0 entries`

Il runner non ha trovato un file di ingresso. Verificare:

- ZIP valido, posto direttamente in `INBOX` (non in una sottocartella);
- cartella missione corretta;
- presenza del file metadata;
- nome ed estensione conformi al file `.cfg`;
- ZIP che contiene altri ZIP invece dei file del prodotto: resta in `TMPSPACE\STAGE_*`;
- esecuzione dalla root `ConverterDAMPS_clean`.

### JSON presente ma `0 packaged`

Il packager non trova il dataset nativo. Verificare che il dataset sia in `INBOX`, `TMPSPACE\STAGE_*` o `DONESPACE` e che la `citation` del JSON punti al file metadata corretto.

### Il JSON ha oggetti invece di array

Non usare un JSON rimasto in `FAILEDSPACE` da una run precedente. Eseguire una nuova conversione e controllare il file appena creato in `OUTSPACE`.

## 10. Test automatici del codice

Dalla root del progetto:

```powershell
..\..\.venv\Scripts\python.exe -m pytest pylib\converters -q
```

Il test verifica emitter, template, struttura JSON e packaging logico. Un risultato positivo atteso è:

```text
50 passed
```

## 11. Conversione manuale di un singolo prodotto

Per eseguire solo l'ingester GeoEye su un metadata specifico:

```powershell
$root = (Get-Location).Path
$env:PYTHONPATH = "$root\pylib\xml_nodes\v101;$root\pylib\converters"

..\..\.venv\Scripts\python.exe `
  pylib\converters\geoeye1_json\ingester_geoeye1.py `
  -c pylib\converters\geoeye1_json\ingest_geoeye1.cfg `
  --single "TDS\GEOEYE\INBOX\<dataset>\<metadata>.XML"
```

Per ICEYE il comando equivalente è:

```powershell
..\..\.venv\Scripts\python.exe `
  pylib\converters\iceye_json\ingester_iceye.py `
  -c pylib\converters\iceye_json\ingest_iceye.cfg `
  --single "TDS\ICEYE\INBOX\<dataset>\<metadata>.xml"
```

Il runner resta preferibile perché imposta automaticamente il `PYTHONPATH`, esegue il packaging e gestisce l'archiviazione.

## 12. Checklist operativa

- [ ] Sono nella root `ConverterDAMPS_clean`.
- [ ] Python funziona con `py` o con `.venv`.
- [ ] Il dataset è estratto.
- [ ] Il dataset è nella `INBOX` della missione corretta.
- [ ] Il file metadata rispetta il pattern del relativo `.cfg`.
- [ ] Ho usato il nome missione corretto.
- [ ] Il comando termina con `0 failure(s)`.
- [ ] Il JSON è presente in `OUTSPACE`.
- [ ] Il ZIP è presente in `PRODUCTS`.
- [ ] Il dataset è stato spostato in `DONESPACE`.

## 13. COSMO-SkyMed

Il prodotto nativo COSMO-SkyMed e' la cartella di consegna, con il file prodotto
piu' la nota di consegna DFDN, la scheda DFAS e il checksum. Va copiata dentro
`TDS\COSMO SKYMED\INBOX`. Sono gestiti due formati di consegna.

Consegna HDF5, file di ingresso `.h5`:

```text
TDS\COSMO SKYMED\INBOX\CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301\
    736299-502923\
        CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301.h5
        DFDN_CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301.h5.xml
        DFAS_736299_CSK_AccompanyingSheet.xml
        SHA256_736299_1-1.sha256.sec
```

Consegna GeoTIFF, file di ingresso `.tgz`:

```text
TDS\COSMO SKYMED\INBOX\CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732\
    1008699-756540\
        CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732.tgz
        DFDN_CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732.h5.xml
        DFAS_1008699_CSK_AccompanyingSheet.xml
        SHA256_1008699_1-1.sha256.sec
```

Il `.tgz` non va scompattato a mano: lo legge il convertitore e lo espande il
packager. Dentro ci sono `<nome>.MBI.tif` con il suo `.tfw`, `<nome>.QLK.tif` e
`<nome>.attribs.xml`.

I metadati del manifest vengono sempre dagli attributi del prodotto: l'albero di
attributi HDF5 nel caso `.h5`, il suo dump XML `<nome>.attribs.xml` nel caso
`.tgz`. I nomi degli attributi sono identici nei due casi. Per il formato HDF5
serve `h5py`, incluso in `requirements.txt`.

Conversione completa:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py cosmoskymed
```

Risultato:

- `TDS\COSMO SKYMED\OUTSPACE\<ID>.JSON`, il manifest;
- `TDS\COSMO SKYMED\OUTSPACE\<ID>.PNG`, l'overview, presa dal dataset HDF5
  `S0n/QLK` oppure dal `<nome>.QLK.tif` dentro il `.tgz`;
- `TDS\COSMO SKYMED\PRODUCTS\<ID>.ZIP`, il delivery. In `measurements/` finisce
  il nativo decompresso: il contenuto del `.tgz` viene espanso, come chiede la
  specifica.

`<ID>` segue la convenzione della specializzazione EOPF-EOS, per esempio
`CS__OPER_L1BSM__DGM_20170515T172253_20170515T172301_0001` oppure
`CS__OPER_L1CSC__GEC_20171007T160717_20171007T160732_0001`.

### Codice di tipo prodotto

I dieci codici ammessi dalla specifica, per famiglia di modo (STRIPMAP HIMAGE e
PINGPONG danno SM, SCANSAR WIDEREGION e HUGEREGION danno SC):

| livello | STRIPMAP | SCANSAR |
|---|---|---|
| 1A SCS non bilanciato | `L1ASMU_SCS` | `L1ASCU_SCS` |
| 1A SCS bilanciato | `L1ASMB_SCS` | `L1ASCB_SCS` |
| 1B DGM | `L1BSM__DGM` | `L1BSC__DGM` |
| 1C GEC | `L1CSM__GEC` | `L1CSC__GEC` |
| 1D GTC | `L1DSM__GTC` | `L1DSC__GTC` |

Un tipo prodotto nativo o un modo di acquisizione non previsti fanno fallire la
conversione, senza inventare un codice.

### Limiti attuali

- Provati su dati reali: HIMAGE DGM_B (1B, consegna HDF5) e WIDEREGION GEC_B
  (1C, consegna GeoTIFF in `.tgz`).
- Nessun prodotto PINGPONG ne' Second Generation (CSG) e' stato ancora provato
  su dati reali: le mappature esistono e sono verificate dai test, ma non da una
  conversione.
- L'overview mantiene l'orientamento nativo del quicklook, senza riorientamento.

## 14. PlanetScope

Il prodotto nativo PlanetScope e' un *item* Planet: il file metadata
`<item id>_metadata.json` piu' gli asset con lo stesso prefisso (GeoTIFF
immagine, XML `<item id>_<asset>_metadata.xml`, maschere `udm`/`udm2`, RPC).
Va copiato dentro `TDS\PLANETSCOPE\INBOX`. Sono gestiti due layout di consegna.

Consegna Orders API, piu' item nella stessa cartella:

```text
TDS\PLANETSCOPE\INBOX\order_7d1c\
    manifest.json
    PSScene\
        20170424_134911_0e19_metadata.json
        20170424_134911_0e19_3B_Visual.tif
        20170424_134911_0e19_3B_Visual_metadata.xml
        20170424_134911_0e19_3B_udm2.tif
        20210314_070803_29_2262_metadata.json
        20210314_070803_29_2262_3B_AnalyticMS_SR_8b.tif
        20210314_070803_29_2262_3B_AnalyticMS_8b_metadata.xml
        20210314_070803_29_2262_3B_udm2.tif
```

Consegna Data API (legacy), una sottocartella per asset:

```text
TDS\PLANETSCOPE\INBOX\20190801_093015_1018\
    20190801_093015_1018_metadata.json
    basic_analytic_4b\20190801_093015_1018_1B_AnalyticMS.tif
    basic_analytic_4b_xml\20190801_093015_1018_1B_AnalyticMS_metadata.xml
    basic_analytic_4b_rpc\20190801_093015_1018_1B_AnalyticMS_RPC.TXT
```

Ogni `<item id>_metadata.json` produce un prodotto EOPF-EOS. In
`measurements/` finiscono SOLO i file il cui nome inizia con l'id dell'item,
con la loro struttura di sottocartelle: gli altri item della stessa cartella e
i file d'ordine (`manifest.json`) restano fuori.

I metadati vengono dal JSON dell'item (footprint, istante di acquisizione,
strumento, angoli solari, view angle, cloud cover, risoluzione, data di
pubblicazione) e dall'XML dell'asset (periodo di validita', orbit direction,
angolo di incidenza, nome e versione del processore, livello nativo, numero di
bande, codice EPSG). L'XML e' obbligatorio: senza, la conversione fallisce.

Conversione completa:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py planetscope
```

Risultato:

- `TDS\PLANETSCOPE\OUTSPACE\<ID>.JSON`, il manifest;
- `TDS\PLANETSCOPE\OUTSPACE\<ID>.PNG`, l'overview: Planet non consegna un
  browse, quindi viene generata dal GeoTIFF dell'item (l'asset Visual se
  presente, altrimenti bande rosso/verde/blu dell'immagine principale con
  stretch 2-98 percentile; i pixel no-data diventano trasparenti). Serve
  `tifffile` (con `imagecodecs` per i GeoTIFF compressi), in `requirements.txt`;
- `TDS\PLANETSCOPE\PRODUCTS\<ID>.ZIP`, il delivery.

`<ID>` segue la convenzione della specializzazione EOPF-EOS, per esempio
`PSC_OPER_L3_VO__MS__20170424T134911_20170424T135111_0001`.

### Codice di tipo prodotto

Deciso dall'asset immagine principale dell'item. Se un item ha piu' asset
immagine vale il primo di questa lista (gli altri finiscono comunque in
`measurements/`):

| asset immagine | tipo prodotto | modo |
|---|---|---|
| `_3B_AnalyticMS_8b.tif` | `L3_AO__MS_` | MS8B |
| `_3B_AnalyticMS_SR_8b.tif` | `L3_SRO_MS_` | MS8B |
| `_1B_AnalyticMS_8b.tif` | `L1BAB__MS_` | MS8B |
| `_1A_AnalyticMS_8b.tif` | `L1AAB__MS_` | MS8B |
| `_3B_AnalyticMS.tif` | `L3_AO__MS_` | MS4B |
| `_3B_AnalyticMS_SR.tif` | `L3_SRO_MS_` | MS4B |
| `_1B_AnalyticMS.tif` | `L1BAB__MS_` | MS4B |
| `_1A_AnalyticMS.tif` | `L1AAB__MS_` | MS4B |
| `_3B_Analytic.tif` | `L3_AO__MS_` | MS3B |
| `_3B_Visual.tif` | `L3_VO__MS_` | MS3B |
| `_BGRN_Analytic.tif` / `_BGRN_SR.tif` (item `PSOrthoTile`) | `L3_OT__MS_` | MS4B |

Un item senza nessuno di questi asset, o con livello/bande dell'XML in
contrasto con l'asset, fa fallire la conversione.

### Limiti attuali

- Nessun prodotto PlanetScope reale e' stato ancora convertito: converter e
  packager sono provati solo su item sintetici (vedi
  `planetscope_json\test\fixtures\SYNTHETIC_FIXTURE_NOTE.md`).
- Il nome dell'asset L1A (`_1A_AnalyticMS`) non e' confermato da un prodotto
  reale.

## 15. SkySat

Il prodotto nativo SkySat e' un *item* Planet, come per PlanetScope: il file
metadata `<item id>_metadata.json` piu' gli asset con lo stesso prefisso
(GeoTIFF immagine, maschere `udm`/`udm2`, RPC dei prodotti basic). L'item
puo' essere una scena (`SkySatScene`) o una collect (`SkySatCollect`). Va
copiato dentro `TDS\SKYSAT\INBOX`. Valgono gli stessi due layout di consegna
di PlanetScope (Orders API con piu' item nella stessa cartella, Data API con
una sottocartella per asset), per esempio:

```text
TDS\SKYSAT\INBOX\order_5f3a\
    manifest.json
    SkySatScene\
        20180428_125611_ssc3d2_0017_metadata.json
        20180428_125611_ssc3d2_0017_pansharpened.tif
        20180428_125611_ssc3d2_0017_visual.tif
        20180428_125611_ssc3d2_0017_pansharpened_udm2.tif
TDS\SKYSAT\INBOX\20200619_094518_ssc11_u0001\
    20200619_094518_ssc11_u0001_metadata.json
    20200619_094518_ssc11_u0001_visual.tif
    20200619_094518_ssc11_u0001_pansharpened.tif
    20200619_094518_ssc11_u0001_analytic.tif
    20200619_094518_ssc11_u0001_panchromatic.tif
```

Planet non consegna XML per SkySat: tutti i metadati vengono dal JSON
dell'item (footprint, istante di acquisizione, angoli solari, view angle usato
come angolo di incidenza, cloud cover, risoluzione, data di pubblicazione). Il
codice EPSG dei prodotti ortho viene letto dal GeoTIFF.

Conversione completa:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py skysat
```

Risultato:

- `TDS\SKYSAT\OUTSPACE\<ID>.JSON`, il manifest;
- `TDS\SKYSAT\OUTSPACE\<ID>.PNG`, l'overview generata dal GeoTIFF (come per
  PlanetScope; un'immagine pancromatica da' un'overview in grigio). Per una
  collect `SYNORT_BDL` le overview sono quattro: `<ID>_PSH3B.PNG`,
  `<ID>_PSH4B.PNG`, `<ID>_MS.PNG`, `<ID>_PAN.PNG`;
- `TDS\SKYSAT\PRODUCTS\<ID>.ZIP`, il delivery, con le overview in
  `previews/overviews/`.

`<ID>` segue la convenzione della specializzazione, per esempio
`SSC_OPER_L3_ORT_PSH_20180428T125611_20180428T125611_0001`.

### Codice di tipo prodotto

Per una scena decide l'asset immagine principale, il primo trovato in questa
lista (gli altri file dell'item finiscono comunque in `measurements/`):

| asset immagine | tipo prodotto | modo |
|---|---|---|
| `_pansharpened.tif` | `L3_ORT_PSH` | MS |
| `_analytic_SR.tif` / `_analytic.tif` / `_analytic_dn.tif` | `L3_ORT_MS_` | MS |
| `_visual.tif` | `L3_ORTVMS_` | MS |
| `_panchromatic.tif` / `_panchromatic_dn.tif` | `L3_ORT_PAN` | PAN |
| `_basic_panchromatic[_dn].tif` (+ `_basic_analytic[_dn].tif`) | `L1BBDN_MSP` | MS |
| `_basic_analytic[_dn].tif` | `L1BBDN_MS_` | MS4B |
| `_basic_l1a_panchromatic_dn.tif` | `L1ABDN_PAN` | PAN |

Una collect (`SkySatCollect`) e' sempre `SYNORT_BDL`: un componente per ogni
immagine trovata tra visual (MS), pansharpened (MS), analytic (MS4B) e
panchromatic (PAN), ciascuno con i propri parametri di acquisizione, link
`measurements` e overview.

### Limiti attuali

- Nessun prodotto SkySat reale e' stato ancora convertito: converter e
  packager sono provati solo su item sintetici (vedi
  `skysat_json\test\fixtures\SYNTHETIC_FIXTURE_NOTE.md`).
- La corrispondenza asset Planet -> tipo prodotto e' un'interpretazione della
  specifica, che non nomina i file nativi; va confermata su dati reali.

## 16. Beijing-1, NigeriaSat-1 e UK-DMC-1

Un solo converter per i tre satelliti (sensore SLIM-6), secondo "EOPF-EOS
Specialization for Beijing-1, Nigeriasat-1 and UK-DMC-1 products" 1.0. Ogni
prodotto arriva come uno ZIP senza sottocartelle, da copiare cosi' com'e' in
`TDS\DMC\INBOX`, per esempio:

```text
TDS\DMC\INBOX\20071105000000000,DC00068e_000000_010499_p_L1R_FI.zip
    DC00068e_000000_010499_p_L1R_FI.dim        metadata DIMAP (file di ingresso)
    DC00068e_000000_010499_p_L1R_FI.tif        immagine
    DC00068e_000000_010499_p_L1R_FI_ql.jpg     quicklook
    DC00068e_000000_010499_p_L1R_FI_meta.sip   ZIP con repository.xml
    DC00068e_000000_010499_p_L1R_FI.htm / .xsl visualizzazione del .dim
```

I metadati vengono dal `.dim` (satellite, livello, istante centrale della
scena, footprint, angoli solari, sistema di riferimento, data di produzione);
risoluzione e cloud cover vengono da `repository.xml` dentro il `_meta.sip`.

Conversione completa:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py dmc
```

Risultato:

- `TDS\DMC\OUTSPACE\<ID>.JSON`, il manifest;
- `TDS\DMC\PRODUCTS\<ID>.ZIP`, il delivery: manifest, tutti i file dello ZIP
  originale in `measurements/` e il quicklook convertito in PNG in
  `previews/overviews/<ID>.PNG`;
- `TDS\DMC\DONESPACE\<nome zip>\`, il prodotto estratto (lo ZIP originale
  viene cancellato).

`<ID>` segue la convenzione della specializzazione, per esempio
`BJ1_OPER_L1_OPT_MS__20070808T082321_20070808T082321_0001`.

### Codice di tipo prodotto e contatore

| `.dim` | valore | risultato |
|---|---|---|
| `MISSION` / `MISSION_INDEX` | `BEIJING` / `1` | `BJ1`, Beijing-1 |
| `GEOMETRIC_PROCESSING` | `1R_...` | `L1R`, tipo `L1_OPT_MS_` |
| `GEOMETRIC_PROCESSING` | `1T_...` | `L1T`, tipo `L1_ORT_MS_` |

Le varianti della stessa acquisizione (vista `p` / `s`, regione `_FI` /
`_SE` / `_NO`, sistema di riferimento, copia QL) hanno lo stesso satellite,
livello e istante: le ultime quattro cifre del nome, `<bbvv>`, le
distinguono. `bb` e' la baseline (`00`), `vv` il contatore (`01`, `02`, ...).
Il primo prodotto che riceve un certo nome prende il contatore `01` (nome che
termina con `0001`), il successivo con lo stesso nome `02` (`0002`),
nell'ordine di elaborazione (ordine alfabetico dei nomi ZIP in una run). I
nomi assegnati sono registrati in
`TDS\DMC\dmc_names.json`: un prodotto convertito di nuovo riprende il suo
nome. Il file va conservato insieme ai risultati: se viene cancellato, un
nome gia' consegnato puo' essere riassegnato.
