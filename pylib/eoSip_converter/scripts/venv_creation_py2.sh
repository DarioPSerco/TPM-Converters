#!/bin/bash

ENV_NAME="eosip_converter_py2"

# Create and activate the Conda environment
conda create -y --name $ENV_NAME python=2.7 pyro4 pip numpy
conda activate $ENV_NAME

conda install -y -c conda-forge h5py, netCDF4, pillow, watchdog

# Install lxml
pip install lxml
pip install gdal

# Deactivate the Conda environment
conda deactivate
