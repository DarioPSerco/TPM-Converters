#!/bin/bash

ENV_NAME="eosip_converter_py3"

# Create and activate the Conda environment
conda create -y --name $ENV_NAME python=3.11 pyro4 pip numpy
conda activate $ENV_NAME

conda install -y -c conda-forge gdal, h5py, lxml, netCDF4, pillow, watchdog

# Deactivate the Conda environment
conda deactivate
