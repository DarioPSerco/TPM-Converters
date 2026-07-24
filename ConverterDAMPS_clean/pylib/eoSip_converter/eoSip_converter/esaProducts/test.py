import inspect
import os
import sys
import traceback

from . import landsat1_7_mdAdapter
from eoSip_converter.esaProducts import eosip_product_helper

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


class Cryosat_info:

    def __init__(self):
        self.typecode = None
        self.instrumentShortName = None
        self.sensorMode = None
        self.sensorType = None
        self.acqusitionType = None
        self.level = None
        self.hasQr = None

    # #instrument shortname|sensor type|sensor mode|acquisition type|typecode|QR|level
    def fromLine(self, line):
        if line[0] != '#':
            toks = line.strip().split('|')
            self.instrumentShortName = toks[0]
            self.sensorType = toks[1]
            self.sensorMode = toks[2]
            self.acqusitionType = toks[3]
            self.typecode = toks[4]
            self.hasQr = toks[5]
            self.level = toks[6]

    #
    def toString(self):
        res = "typecode:%s; instrumentShortName:%s; sensorType:%s; sensorMode:%s\n" % (
        self.typecode, self.instrumentShortName, self.sensorType, self.sensorMode)
        res = res + "  acqusitionType:%s; level:%s; hasQr=%s" % (self.acqusitionType, self.level, self.hasQr)
        return res


#
#
#
if __name__ == '__main__':
    exitCode = -1

    try:
        # EoSip
        from .product_EOSIP import Product_EOSIP
        from . import metadata

        try:
            eoSipProduct = Product_EOSIP(
                "/home/gilles/shared/WEB_TOOLS/MISSIONS/Landsat/TM_GEO_1P/LS05_RKSE_TM__GEO_1P_20110525T104102_20110525T104121_144838_0201_0022_2BBB.ZIP")
            # eoSipProduct = Product_EOSIP("/home/gilles/shared//WEB_TOOLS/MISSIONS/Landsat/TM_GTC_1P/L05_RKSE_TM__GTC_1P_19900721T104307_19900721T104335_033974_0206_0024_0001.SIP.ZIP")

            # eoSipProduct=Product_EOSIP("/home/gilles/shared/MDPs/EN1_OESR_ASA_IM__0P_20100204T002606_20100204T002748_041467_0331_0001.MDP.ZIP")
            eoSipProduct.setDebug(1)

            # try MTR
            if 1 == 1:
                # name of fileinside product ZIP
                mtrPath = 'LS05_RKSE_TM__GEO_1P_20110525T104102_20110525T104121_144838_0201_0022_2BBB.MTR.XML'
                # helper with MD alias set
                eoSipHelper = eosip_product_helper.Eosip_product_helper(eoSipProduct)
                eoSipHelper.setMdXmlAlias(mtrPath)
                # adapter
                adapter = landsat1_7_mdAdapter.Landsat1_7_mdAdapter()
                eoSipHelper.setXmlAdapter(adapter)
                eoSipProduct.eoSipHelper = eoSipHelper

            eoSipProduct.loadProduct()
            print("EoSip info:\n%s" % eoSipProduct.info())

            met = metadata.Metadata()
            numAdded, helper = eoSipProduct.extractMetadata(met)
            print("\n\n number of metadata added:%s" % numAdded)
            print("\n###\n###\n###\nMETADATA:%s\n###\n###\n###\n" % met.toString())

        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" Error: %s; %s" % (exc_type, exc_obj))
            traceback.print_exc(file=sys.stdout)

        os._exit(1)

        # SIRAL
        typeCodeAndInstrument = {}
        typeCodeAndSensor = {}
        typeCodeAndAcquisition = {}
        typeCodeAndLevel = {}
        # DORIS STR
        typeCodeAndOperationalMode = {}

        typeCodeInfo = {}

        SIR_data_path = 'data/cryosat2/SIRAL_TABLE.dat'
        DORIS_data_path = 'data/cryosat2/DORIS_STR_TABLE.dat'
        sirdata = None
        path = "%s/%s" % (currentdir, SIR_data_path)
        if not os.path.exists(path):
            raise Exception("can not find SIRAL data")
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        n = 0
        for line in lines:
            anInfo = Cryosat_info()
            anInfo.fromLine(line)
            print(" typecode info[%s]:%s" % (n, anInfo.toString()))
            typeCodeInfo[anInfo.typecode] = anInfo
            n += 1

        path = "%s/%s" % (currentdir, DORIS_data_path)
        if not os.path.exists(path):
            raise Exception("can not find DORIS data")
        fd = open(path, 'r')
        lines = fd.readlines()
        fd.close()
        for line in lines:
            anInfo = Cryosat_info()
            anInfo.fromLine(line)
            print(" typecode info[%s]:%s" % (n, anInfo.toString()))
            typeCodeInfo[anInfo.typecode] = anInfo
            n += 1
        print(" loaded %s typecodes info from files" % len(list(typeCodeInfo.keys())))

        exitCode = 0
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)

    sys.exit(exitCode)
