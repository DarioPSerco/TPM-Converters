# -*- coding: cp1252 -*-
#
# represent the Envisat naming convention
#

import sys
import traceback

from eoSip_converter.esaProducts import formatUtils
#
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention


class NamingConvention_Dccm(NamingConvention):
    #
    # dccm pattern
    DCCM_PATTERN = '<SatelliteID>_<instance ID>.extension'  #
    DCCM_PATTERN_INSTANCE_DEFAULT = '<Aux/Product type code>_<originalproductname>_<YYYYMMDDHHMMSS>'  #

    #
    DCCM_POSSIBLE_PATTERN = [DCCM_PATTERN_INSTANCE_DEFAULT]

    #
    usedBase = None
    usedPattern = None

    debug = 0

    #
    #
    #
    def __init__(self, p=DCCM_PATTERN_INSTANCE_DEFAULT, fromSuper=False):
        NamingConvention.__init__(self, p, True)
        print("## NamingConvention_Dccm init: pattern=%s; fromSuper=%s" % (p, fromSuper))

        # the possible pattern used
        for item in self.DCCM_PATTERN_INSTANCE_DEFAULT:
            try:
                self.possible_pattern.index(item)
            except:
                self.possible_pattern.append(item)

        if self.debug != 0:
            print(" #### NamingConvention_Dccm p=%s" % p)

        if p[0] != '<':
            if self.debug != 0:
                print("NamingConvention init case 0: pattern=%s" % p)
            self.usedPattern = eval("NamingConvention_Dccm.%s" % p)
            self.usedBase = NamingConvention_Dccm.DCCM_PATTERN
            print(" NamingConvention_Dccm usedPattern=%s" % self.usedPattern)
        else:
            self.usedPattern = p
            self.usedBase = NamingConvention_Dccm.DCCM_PATTERN
            print(" NamingConvention_Dccm init case 1: usedPattern=%s" % self.usedPattern)

    #
    #
    #
    def buildProductName(self, met=None, ext=None):
        if self.debug != 0:
            print("\n\n NamingConvention_Dccm.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
        toks = self.DCCM_PATTERN.split('_')
        res = ''
        for tok in toks:
            if self.debug != 0:
                print("doing token:%s" % tok)
            if tok == '<SatelliteID>':
                platform = met.getMetadataValue(metadata.METADATA_PLATFORM)
                platformId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)

                res = "%s%s" % (platform[0:2], platformId[0])
                if self.debug != 0:
                    print("res is now:%s" % res)
            elif tok == '<instance ID>.extension':
                tmp = self.buildInstance(met)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res3 is now:%s" % res)
            else:
                raise Exception("unknown naming pattern:'%s'" % tok)

        if ext is not None:
            res = "%s.%s" % (res, ext)
        return res

    #
    #
    #
    def buildInstance(self, met=None):
        res = ''
        for tok in self.usedPattern.split('_'):
            if self.debug != 0:
                print("doing instance token:%s" % tok)
            if tok == '<Aux/Product type code>':
                tmp = formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_TYPECODE), 10)
                res = "%s" % tmp
                if self.debug != 0:
                    print("res4 is now:%s" % res)
            elif tok == '<originalproductname>':
                tmp = met.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res5 is now:%s" % res)
            elif tok == '<YYYYMMDDHHMMSS>':
                tmp = met.getMetadataValue(metadata.METADATA_GENERATION_TIME)
                tmp = tmp.replace('T', '').replace(':', '').replace('-', '')
                tmp = formatUtils.normaliseDate(tmp, 14)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res5 is now:%s" % res)
            else:
                raise Exception("unknown naming instance pattern:%s" % tok)
        return res


if __name__ == '__main__':
    print("start")
    filename = 'EN1_ASA_APC_0P_ASAAPC0P_20150505143000.xml'
    try:
        n = NamingConvention_Dccm()
        print("namingConvention dump:%s" % n.toString())

        res = n.guessPatternUsed(filename, n.possible_pattern)
        if len(res) == 1:
            n.usePatternvalue(res[0])
        else:
            print("can not find instance pattern...")

        # ptype=n.getFilenameElement(filename, NamingConvention_Dccm.DCCM_PATTERN, 'TTTTTTTTTT')
        # print "productType=%s" % ptype

        met = metadata.Metadata()
        met.setMetadataPair(metadata.METADATA_GENERATION_TIME, '1992-08-29T11:35:32.51Z')
        met.setMetadataPair(metadata.METADATA_PLATFORM, "AL")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, "1")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_START_DATE, "20140302")
        met.setMetadataPair(metadata.METADATA_START_TIME, "01:02:03")
        met.setMetadataPair(metadata.METADATA_STOP_DATE, "20150302")
        met.setMetadataPair(metadata.METADATA_STOP_TIME, "21:02:03")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_ORBIT, "1000")
        met.setMetadataPair(metadata.METADATA_TRACK, "273")
        met.setMetadataPair(metadata.METADATA_FRAME, "34")
        # met.setMetadataPair(metadata.METADATA_DURATION,"120.2054987654")
        met.setMetadataPair(metadata.METADATA_DURATION, "1.23")
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "00001")
        met.setMetadataPair(metadata.METADATA_TYPECODE, "HRV__X__1A")
        print("buildname result:%s" % n.buildProductName(met))
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
