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

Estrarre il dataset prima di copiarlo in `INBOX`. Il runner non elabora direttamente un archivio ZIP lasciato in `INBOX`.

Copiare l'intera cartella del prodotto, mantenendo i file nativi e i file metadata.

Esempi di file di ingresso:

| Missione | File individuato |
|---|---|
| GeoEye-1 | `*_README.XML` |
| WorldView | secondo il pattern configurato nella missione |
| QuickBird-2 | secondo il pattern configurato nella missione |
| ICEYE | `*.xml` |
| Pleiades | secondo il pattern configurato nella missione |
| Pleiades NEO | secondo il pattern configurato nella missione |

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

- dataset estratto e non solo ZIP;
- cartella missione corretta;
- presenza del file metadata;
- nome ed estensione conformi al file `.cfg`;
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
20 passed
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

Il prodotto nativo COSMO-SkyMed e' la cartella di consegna che contiene il file
`.h5` piu' la nota di consegna DFDN, la scheda DFAS e il checksum. Va copiata
dentro `TDS\COSMO SKYMED\INBOX`, per esempio:

```text
TDS\COSMO SKYMED\INBOX\CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301\
    736299-502923\
        CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301.h5
        DFDN_CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301.h5.xml
        DFAS_736299_CSK_AccompanyingSheet.xml
        SHA256_736299_1-1.sha256.sec
```

Il file di ingresso e' il `.h5`: tutti i metadati del manifest vengono letti
dai suoi attributi HDF5. Serve `h5py`, incluso in `requirements.txt`.

Conversione completa:

```powershell
..\..\.venv\Scripts\python.exe pylib\converters\run_mission.py cosmoskymed
```

Risultato:

- `TDS\COSMO SKYMED\OUTSPACE\<ID>.JSON`, il manifest;
- `TDS\COSMO SKYMED\OUTSPACE\<ID>.PNG`, l'overview estratta dal dataset HDF5
  `S0n/QLK`, perche' COSMO-SkyMed non consegna un file quicklook separato;
- `TDS\COSMO SKYMED\PRODUCTS\<ID>.ZIP`, il delivery.

`<ID>` segue la convenzione della specializzazione EOPF-EOS, per esempio
`CS__OPER_L1BSM__DGM_20170515T172253_20170515T172301_0001`.

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

- Le consegne solo TIFF / GEOTIFF non sono gestite: il file di ingresso deve
  essere il `.h5`.
- Nessun prodotto SCANSAR, WIDEREGION o HUGEREGION, ne' Second Generation
  (CSG) e' stato ancora provato su dati reali: le mappature esistono e sono
  verificate dai test, ma non da una conversione.
