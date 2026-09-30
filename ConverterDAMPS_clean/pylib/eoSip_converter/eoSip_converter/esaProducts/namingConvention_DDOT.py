# -*- coding: cp1252 -*-
#
# represent a naming convention like datatime_datetime_orbit_track
#

import logging
import sys
import traceback

from eoSip_converter.esaProducts import formatUtils
#
from eoSip_converter.esaProducts import metadata, base_metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention


# from definitions_EoSip import sipBuilder


class NamingConvention_DDOT(NamingConvention):
    #
    # Aeolus pattern
    DDOT_PATTERN = '<SSS>_<CCCC>_<TTTTTTTTTT>_<instance ID>.<extension>'
    DDOT_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>'
    DDOTFv_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vvvv>'
    DDOTvV_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<vvvv>_v<VVVV>'
    DDOTv2_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vv>'
    DDOTv3_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vvv>'
    DDOTv2V4_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vv>_v<VVVV>'
    DDOTv3V4_PATTERN_INSTANCE = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vvv>_v<VVVV>'
    #
    DDOT_POSSIBLE_PATTERN = [DDOT_PATTERN_INSTANCE]

    #
    usedBase = None
    usedPattern = None

    #
    #
    #
    def __init__(self, p=DDOT_PATTERN_INSTANCE, fromSuper=False):
        NamingConvention.__init__(self, p, True)
        # print "## NamingConvention_DDOT init: pattern=%s; fromSuper=%s" % (p, fromSuper)

        # the possible pattern used
        for item in self.DDOT_POSSIBLE_PATTERN:
            try:
                self.possible_pattern.index(item)
            except:
                self.possible_pattern.append(item)

        if self.debug != 0:
            print(" #### NamingConvention_DDOT p=%s" % p)

        if p[0] != '<':
            if self.debug != 0:
                print("NamingConvention_DDOT init case 0: pattern=%s" % p)
            self.usedPattern = eval("NamingConvention_DDOT.%s" % p)
            self.usedBase = NamingConvention_DDOT.DDOT_PATTERN
            print(" NamingConvention_DDOT usedPattern=%s" % self.usedPattern)
        else:
            self.usedPattern = p
            self.usedBase = NamingConvention_DDOT.DDOT_PATTERN
            print(" NamingConvention_DDOT init case 1: usedPattern=%s" % self.usedPattern)

    #
    # build the product name based on the metadata values
    #
    def buildProductName(self, met=None, ext=None):
        # print("naming convention DEBUG:%s" % self.debug)
        # os._exit(1)
        if self.debug != 0:
            print("\n\n NamingConvention_DDOT.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
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
        # raise Exception("STOP")
        res = ''
        for tok in self.usedPattern.split('_'):
            if self.debug != 0:
                print("doing instance token:%s" % tok)
            if tok == '<yyyymmddThhmmss>':
                # supress -
                tmp = met.getMetadataValue(metadata.METADATA_START_DATE)
                tmp = formatUtils.normaliseDate(tmp, 8, '#')
                # tmp = formatUtils.normaliseDate(self.buildToken(met, metadata.METADATA_START_DATE, 8 , '#'))
                # supress :
                tmp1 = formatUtils.normaliseTime(met.getMetadataValue(metadata.METADATA_START_TIME), 6, '#')
                # tmp1 = formatUtils.normaliseNumber(tmp1, 6 , '#')
                res = "%sT%s" % (tmp, tmp1)
                if self.debug != 0:
                    print("res4 is now:%s" % res)
            elif tok == '<YYYYMMDDTHHMMSS>':
                # supress -
                tmp = met.getMetadataValue(metadata.METADATA_STOP_DATE)
                tmp = formatUtils.normaliseDate(tmp, 8, '#')
                # tmp = formatUtils.normaliseDate(self.buildToken(met, metadata.METADATA_STOP_DATE, 8 , '#'))
                # supress :
                tmp1 = formatUtils.normaliseTime(met.getMetadataValue(metadata.METADATA_STOP_TIME), 6, '#')
                # tmp1 = formatUtils.normaliseNumber(tmp1, 6 , '#')
                res = "%s_%sT%s" % (res, tmp, tmp1)
                if self.debug != 0:
                    print("res5 is now:%s" % res)
            elif tok == '<oooooo>':
                tmp = self.buildToken(met, metadata.METADATA_ORBIT, 6, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resO is now:%s" % res)
            elif tok == '<tttt>':
                tmp = self.buildToken(met, metadata.METADATA_TRACK, 4, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resT is now:%s" % res)
            elif tok == '<ffff>':
                tmp = self.buildToken(met, metadata.METADATA_FRAME, 4, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            elif tok == '<vvvv>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, 4, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)

            elif tok == '<vv>':
                tmp = self.buildToken(met, metadata.METADATA_NATIVE_PRODUCT_VERSION, 2, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)

            elif tok == '<vvv>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, 3, '#')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res is now:%s" % res)

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
    filename = 'EN1_NPDE_ASA_APH_0P_20050919T034114_20050919T034155_018581_0491.ZIP'
    try:
        n = NamingConvention_DDOT(NamingConvention_DDOT.DDOT_PATTERN_INSTANCE)
        n2 = NamingConvention_DDOT(NamingConvention_DDOT.DDOTvV_PATTERN_INSTANCE)
        print("namingConvention dump:%s" % n.toString())

        if 1 == 2:
            res = n.guessPatternUsed(filename, n.possible_pattern)
            if len(res) == 1:
                n.usePatternvalue(res[0])
            else:
                print("can not find instance pattern...")

            ptype = n.getFilenameElement(filename, NamingConvention_DDOT.DDOT_PATTERN, 'TTTTTTTTTT')
            print("productType=%s" % ptype)

            sys.exit(0)

        met = metadata.Metadata()
        met.setMetadataPair(metadata.METADATA_PLATFORM, "AL")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, "1")
        met.setMetadataPair(metadata.METADATA_START_DATE, "20140302")
        met.setMetadataPair(metadata.METADATA_START_TIME, "01:02:03")
        met.setMetadataPair(metadata.METADATA_STOP_DATE, "20150302")
        met.setMetadataPair(metadata.METADATA_STOP_TIME, "21:02:03")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_ORBIT, "1000")
        met.setMetadataPair(metadata.METADATA_TRACK, "273")
        met.setMetadataPair(metadata.METADATA_FRAME, "34")
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "0100")
        met.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, "9999")
        met.setMetadataPair(metadata.METADATA_TYPECODE, "HRV__X__1A")
        print("builded DDOT_PATTERN_INSTANCE name:%s" % n.buildProductName(met))
        print("builded DDOTvV_PATTERN_INSTANCE name:%s" % n2.buildProductName(met))
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
