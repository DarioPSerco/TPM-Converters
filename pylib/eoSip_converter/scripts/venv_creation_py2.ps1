$ENV_NAME = "eosip_converter_py2"
$GDAL_URL = "https://storage.googleapis.com/pypi.naturalcapitalproject.org/wheels/GDAL-2.2.4-cp27-cp27m-win_amd64.whl"

# Create and activate the Conda environment
conda create -y --name $ENV_NAME python=2.7 pyro4 pip numpy
conda activate $ENV_NAME

# Install lxml
pip install lxml

# GDAL installation from .whl file (conda/pip install gdal leads to errors 
# thrown by missing libraries)
$TMP_DIR = New-Item -ItemType Directory -Force (Join-Path $env:TEMP (New-Guid).Guid)
$GDAL_FILE = Join-Path $TMP_DIR ([System.IO.Path]::GetFileName($GDAL_URL))
Invoke-WebRequest -Uri $GDAL_URL -OutFile $GDAL_FILE
pip install $GDAL_FILE

# Clean up: delete the temporary directory
Remove-Item -Path $TMP_DIR -Recurse -Force

conda install -y -c conda-forge h5py, netCDF4, pillow, python-dateutil, watchdog

# Deactivate the Conda environment
conda deactivate