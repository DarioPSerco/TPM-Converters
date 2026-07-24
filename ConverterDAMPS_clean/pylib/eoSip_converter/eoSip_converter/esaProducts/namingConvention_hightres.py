# -*- coding: cp1252 -*-
#
# represent the EoSip naming convention
#

import logging
import sys
import traceback

from eoSip_converter.esaProducts import formatUtils
#
from eoSip_converter.esaProducts import metadata, base_metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention


class NamingConvention_HightRes(NamingConvention):
    #
    # Aeolus pattern
    HIGHTRES_PATTERN = '<SSS>_<CCCC>_<TTTTTTTTTT>_<instance ID>.<extension>'
    HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXVC = '<yyyymmddThhmmss>_<LLL>-<LLL>_<OOOO>-<OOO>_<vvvc>'
    HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXV2C =  '<yyyymmddThhmmss>_<LLL>-<LLL>_<OOOO>-<OOO>_<vc>'
    HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXvV =   '<yyyymmddThhmmss>_<LLL>-<LLL>_<OOOO>-<OOO>_<vvvc>_v<VVVV>'
    HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXv2V4 = '<yyyymmddThhmmss>_<LLL>-<LLL>_<OOOO>-<OOO>_<vc>_v<VVVV>'
    HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXv2V5 = '<yyyymmddThhmmss>_<LLL>-<LLL>_<OOOO>-<OOO>_<vv>_v<VVVV>'

    #
    HIGHRES_POSSIBLE_PATTERN = [HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXVC,
                                HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXV2C,
                                HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXvV,
                                HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXv2V4,
                                HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXv2V5
                                ]

    #
    usedBase = None
    usedPattern = None

    debug = 0

    #
    #
    #
    def __init__(self, p=HIGHTRES_PATTERN_INSTANCE_GENERIC_DTYXVC, fromSuper=False):
        NamingConvention.__init__(self, p, True)
        if self.debug != 0:
            print("## NamingConvention_HightRes init: pattern=%s; fromSuper=%s" % (p, fromSuper))
        # the possible pattern used
        for item in self.HIGHRES_POSSIBLE_PATTERN:
            try:
                self.possible_pattern.index(item)
            except:
                self.possible_pattern.append(item)

        if self.debug != 0:
            print(" #### NamingConvention_HightRes p=%s" % p)

        if p[0] != '<':
            if self.debug != 0:
                print("NamingConvention init case 0: pattern=%s" % p)
            self.usedPattern = eval("NamingConvention_HightRes.%s" % p)
            self.usedBase = NamingConvention_HightRes.HIGHTRES_PATTERN
            if self.debug != 0:
                print(" NamingConvention_HightRes usedPattern=%s" % self.usedPattern)
        else:
            self.usedPattern = p
            self.usedBase = NamingConvention_HightRes.HIGHTRES_PATTERN
            if self.debug != 0:
                print(" NamingConvention_HightRes init case 1: usedPattern=%s" % self.usedPattern)

    #
    # build the product name based on the metadata values
    #
    def buildProductName(self, met=None, ext=None):
        if self.debug != 0:
            print("\n\n NamingConvention.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
        toks = self.PATTERN.split('_')
        res = ''
        for tok in toks:
            if self.debug != 0:
                print("doing token:%s" % tok)
            if tok == '<SSS>':
                twoDigitAlias = met.getMetadataValue(metadata.METADATA_PLATFORM_2DIGITS_ALIAS)
                if twoDigitAlias != base_metadata.VALUE_NOT_PRESENT:
                    tmp = twoDigitAlias
                else:
                    tmp = self.buildToken(met, metadata.METADATA_PLATFORM, 2, '#')
                tmp1 = self.buildToken(met, metadata.METADATA_PLATFORM_ID, 1, '#')
                res = "%s%s" % (tmp, tmp1)
                if self.debug != 0:
                    print("res is now:%s" % res)
            elif tok == '<CCCC>':
                tmp = self.buildToken(met, metadata.METADATA_FILECLASS, 4, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res1 is now:%s" % res)
            elif tok == '<TTTTTTTTTT>':
                tmp = self.buildToken(met, metadata.METADATA_TYPECODE, 10, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res2 is now:%s" % res)
            elif tok == '<instance ID>.<extension>':
                tmp = self.buildInstance(met)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res3 is now:%s" % res)
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
            if tok == '<yyyymmddThhmmss>':
                tmp = formatUtils.normaliseDate(met.getMetadataValue(metadata.METADATA_START_DATE), 8, '#')
                tmp1 = formatUtils.normaliseTime(met.getMetadataValue(metadata.METADATA_START_TIME), 6, '#')
                res = "%sT%s" % (tmp, tmp1)
                if self.debug != 0:
                    print("res4 is now:%s" % res)
            elif tok == '<vvvv>':  # NOT USED???
                tmp = formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_SIP_VERSION), len(tok) - 2)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<LLL>-<LLL>':
                tmp = self.buildToken(met, metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, 3, '#')
                tmp1 = self.buildToken(met, metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, 3, '#')
                # res="%s_%s-%s" % (res, met.getMetadataValue(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED), met.getMetadataValue(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED))
                res = "%s_%s-%s" % (res, tmp, tmp1)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<OOOO>-<OOO>':
                tmp = self.buildToken(met, metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, 4, '#')
                tmp1 = self.buildToken(met, metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, 3, '#')
                # res="%s_%s-%s" % (res, met.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED), met.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED))
                res = "%s_%s-%s" % (res, tmp, tmp1)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<vvvc>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, 4, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<vc>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, 2, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<vv>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, 2, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == 'v<VVVV>':
                tmp = self.buildToken(met, metadata.METADATA_SIP_VERSION, 4, '#')
                res = "%s_v%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            else:
                raise Exception("unknown naming instance pattern:%s" % tok)

        return res


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    filename = 'AE_TEST_ALD_U_N_2B_20110409T064002_20110409T081238_0001.DBL'
    try:
        n = NamingConvention_HightRes()
        print("namingConvention dump:%s" % n.toString())

        if 1 == 2:
            res = n.guessPatternUsed(filename, n.possible_pattern)
            if len(res) == 1:
                n.usePatternvalue(res[0])
            else:
                print("can not find instance pattern...")

            ptype = n.getFilenameElement(filename, NamingConvention_HightRes.HIGHTRES_PATTERN, 'TTTTTTTTTT')
            print("productType=%s" % ptype)

        met = metadata.Metadata()
        met.setMetadataPair(metadata.METADATA_PLATFORM, "WV")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, "1")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_START_DATE, "2014-03-02")
        # met.setMetadataPair(metadata.METADATA_START_TIME,"01:02:03")
        met.setMetadataPair(metadata.METADATA_STOP_DATE, "20150302")
        met.setMetadataPair(metadata.METADATA_STOP_TIME, "21:02:03")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_ORBIT, "1000")
        met.setMetadataPair(metadata.METADATA_TRACK, "273")
        met.setMetadataPair(metadata.METADATA_FRAME, "34")
        # met.setMetadataPair(metadata.METADATA_SIP_VERSION,"0011")
        met.setMetadataPair(metadata.METADATA_TYPECODE, "VW_110__2A")

        # met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED,"E100")
        # met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,"123")
        # met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED,"N23")
        # met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,"456")

        print("builded name:%s" % n.buildProductName(met))
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
