"""This is an installation testing utility
For the ASAR to MDP tool

it will check that the following is ok:
- check python version: has to be delivered !!CUSTOMIZED!! anaconda version 2.7.6 minimum
- check tool import
- check xml import (need LXML)
- check image utils (need PIL)
- check that we use our !!CUSTOMIZED!! anaconda: has Gdal, NumPy,Netcdf4, Pyro4

Serco 12/2015
Lavaux Gilles
"""
import sys
import traceback
from importlib import import_module

REQUIRED_PYTHON_VERSION = (3, 6, 1)

tool = 'stripline_to_mdp'
xml = 'xmlHelper'
image = 'imageUtil'
ourAnaconda_1 = 'Pyro4'
ourAnaconda_2 = 'osgeo.gdal'
ourAnaconda_3 = 'numpy'

if __name__ == '__main__':
    exitCode = -1

    try:
        print(
            "\nWill test current python against requirement for ASAR to MDP "
            "converter tool...\n need to be run INSIDE the tool folder!\n you "
            "should see NO WARNING OR ERROR!!\n\n"
        )

        # python version
        if sys.version_info < REQUIRED_PYTHON_VERSION:
            raise Exception("Minimum python version not ok: %s < %s" % (sys.version_info, REQUIRED_PYTHON_VERSION))
        print(" - test python minimum version %s: ok" % (REQUIRED_PYTHON_VERSION,))

        # can import converter tool
        import_module(f'eoSip_converter.{tool}')
        print(" - test importing tool %s: ok" % tool)

        # can import xml helper
        import_module(f'eoSip_converter.{xml}')
        print(" - test importing xml helper ok")

        # can import image utils
        import_module(f'eoSip_converter.{image}')
        print(" - test importing image utils ok")

        # use our customized anaconda package
        try:
            #
            import_module(ourAnaconda_1)
            print(" - test python is our customized anaconda part1: ok")
            import_module(ourAnaconda_2)
            print(" - test python is our customized anaconda part2: ok")
            import_module(ourAnaconda_3)
            print(" - test python is our customized anaconda part3: ok")
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" Error: %s; %s" % (exc_type, exc_obj))
            traceback.print_exc(file=sys.stdout)
            raise Exception("Error: the anaconda installed is NOT the delivered customized one!")

        print("\n test finished, all ok")
        exitCode = 0
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)

    sys.exit(exitCode)
