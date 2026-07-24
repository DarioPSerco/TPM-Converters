eoSip_converter
=================
---
# Installation
## System libraries
System libraries for GDAL are required for the installation of the `gdal` python package. Please ensure that the GDAL libraries are >= 3.4.1.

### Linux
```sh
# RHEL/CentOS
yum install gdal
yum install gdal-devel

# Ubuntu/Debian
apt-get install python3-pip
apt-get install gdal-bin
apt-get install libgdal30
```

Alsot, ensure that both `python` and `pip` package manager are installed on the system you are using:
```shell
# RHEL/CentOS
yum install python3 python3-pip

# Ubuntu/Debian
apt-get install python3 python3-pip
```

### Windows
Depending on which windows package manager you are using (i.e. `choco` or `winget`), the installation of the GDAL libraries will be either: 
```PowerShell
choco install -y osgeo4w
# or
winget install osgeo4w
```

## EO-SIP Converter
### Virtual environment
Create a virtual environment for the `eoSip_converter` package:
```shell
VENV_CONVERTER_DIR=/path/to/create/virtual/environment
cd $VENV_CONVERTER_DIR
python3 -m venv venv_converter_py3

# Activate the virtual environment to install the required packages within it
source venv_converter_py3/bin/activate
```

### Installing the converter
Download the repository as a `.zip` file and install it using (after activating the virtual environment, if used):
```bash
CONVERTER_REPO_DIR=/directory/to/store/converter/repository
cd $CONVERTER_REPO_DIR
unzip /path/to/UDATA_EOSIP.zip -d .
cd eoSip_converter
pip install .
```

### Concurrent development and use
With `pip` the `eoSip_converter` package can be installed in development mode, allowing you to modify the code and use it at the same time. To do so, clone the repository, then use the `pip install` command as above, but including the `-e` flag:
```bash
pip install -e .
```

#### Checking the installation
To check that the package has been installed correctly, run the following command:
```bash
$VENV_CONVERTER_DIR/bin/python -c "import eoSip_converter"
```
If no errors are returned, the package has been installed correctly.

---
# Use
Currently, this library is used by the following missions' converters:
- ICEYE
- Planetscope
- Pleiades
- Pleiades-Neo
- TerraSAR-X

### Prerequisites
#### Including the EO-SIP XML specification
In general, multiple EO-SIP specification definitions are used for defining the expected structure of XML files. Within the ingester configuration file, this is defined by the `VERSION` key in the `[eoSip]` section and currently can either take the value `100`, `101`, or `200`. Thus, we must ensure that the relevant python libraries for each of these version definition is located in our `PYTHONPATH`. This can be done by:
```bash
CONVERTER_DIR=`$VENV_CONVERTER_DIR/bin/python -c "import eoSip_converter as m;from pathlib import Path;print(Path(m.__file__).parent)"`
SIP_VERSION=100  # One of 100, 101, 200
export PYTHONPATH=$CONVERTER_DIR/esaProducts/definitions_EoSip/v$SIP_VERSION:$PYTHONPATH
```
**TODO**: _Ensuring import-access to the EO-SIP XML specification module by manually setting the `PYTHONPATH` needs to be addressed in the future i.e. importing the relevant version should be done on the bassi of the configuraiotn file settings._ 

#### XML-validation service
When running a conversion, the `VALIDATE_XML` key of the `[Workflow]` section in the ingester configuration file allows the user to set whether the XML is checked via the XML-validation service. Thus, if set to `True`, the XML-validation service must be running or the conversion will fail.  

##### Running the XML-Validation service
There are two scripts required to run the XML-validation service:
- `eoSip_converter/addon_converter/addon_converter/env`: A script that sets the environment variables pointing to configuration files required for the service to run. Also attempts to set `$JAVA_HOME`
- `eoSip_converter/addon_converter/addon_converter/run_xmlValidatorServer.sh`: Runs the XML validator server (`eoSip_converter/addon_converter/serviceServer/webServer-with-handlers.jar`)

By default, the XML validation server will run on port `27000`. This port can be changed by modifying the `serverPort` key in the `eoSip_converter/addon_converter/serviceServer/TestXmlValidatorRequestHandler.props` file.

In order to run the server using a `screen` session:
```shell
screen -S xmlValidatorServer
bash $CONVERTER_DIR/addon_converter/addon_converter/run_xmlValidatorServer.sh
```

#### Setting up the proxy
In the case that a proxy is used by the server for internet access (required for pulling XML schema) proxy-settings must be set for the XML validation service. The configuration file for the XML validation service is located at `eosip_converter/addon_converter/serviceServer/TestXmlValidatorRequestHandler.props`. The proxy settings are set in the following way:
```properties 
Proxy.port=3128
Proxy.host=proxy-dmz.esa.atcms.net
```

## Development of new ingester
To start, import the abstract base class, `Ingester` from `eosip_converter.base.ingester` and create the new ingester child-class:
```python
from eoSip_converter.base.ingester import Ingester

class NewSatelliteIngester(Ingester):
    ...
```

When the new ingester has been created, place it in `$INGESTERS_DIR` and create a configuration file for it in `$CONFIG_DIR`.

---

# TODO
- [X] Move all mission-specific `eoSip_converter/esaProducts/product_XXX.py` into relevant mission's `ingester` directory.
- [ ] Move `eoSip_converter/esaProducts/data` out of `eoSip_converter` library and into relevant mission's converter package.
- [ ] Develop appropriate dynamic importing of `xml_nodes` versions (specified by ingester configuration files) throughout `eoSip_converter` library (see `xml_nodes_consolidation` branch).


---
# Legacy documentation
The following material is legacy material present in old `eosip_converter` codebases. It specifies ports used by the services present in the `addon_converter` directory:

| Service                                                   | Port  |
|-----------------------------------------------------------|-------|
| TestPolygonShapeFileWfsRequestHandler.props               | 7000  |
| TestXmlValidatorRequestHandler.props                      | 27000 |
| TestPolygonToTownWfsRequestHandler.props                  | 27004 |
| TestPolygonToCountryWfsRequestHandler.props               | 27001 |
| TestPolygonShapeFileWfsRequestHandler_spot5_take5.props   | 27003 |
| TestPolygonShapeFileWfsRequestHandler_spot5_take5.props   | 27002 |
| TestWorldviewLuzResolverRequestHandler.props              | 27005 |
