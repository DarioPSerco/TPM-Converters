# -*- coding: cp1252 -*-
#
# represent an EoSip naming convention where the destination product filename is identical to the source product
#

import logging
import sys
import traceback

#
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention


class NamingConvention_AsSource(NamingConvention):
    #
    PATTERN = 'PATTERN_IDENTICAL'
    PATTERN_INSTANCE_IDENTICAL = 'PATTERN_INSTANCE_IDENTICAL'

    #
    #
    POSSIBLE_PATTERN = [PATTERN_INSTANCE_IDENTICAL]

    #
    #
    usedBase = None
    usedPattern = None

    debug = 0

    #
    # init
    # build list of possible instance pattern than can be used
    #
    def __init__(self, p=PATTERN_INSTANCE_IDENTICAL, fromSuper=False):
        NamingConvention.__init__(self, p, True)
        print("## NamingConvention_AsSource init: pattern=%s; fromSuper=%s" % (p, fromSuper))
        #
        self.possible_pattern = []

        # the possible pattern used
        for item in self.POSSIBLE_PATTERN:
            self.possible_pattern.append(item)

        if self.debug != 0:
            print("#### NamingConvention_AsSource p=%s\n#### possible length:%s\n#### possible=%s" % (
            p, len(self.possible_pattern), self.possible_pattern))

        self.usedBase = NamingConvention_AsSource.PATTERN
        if p[0] != '<':
            if self.debug != 0:
                print(" NamingConvention_AsSource init case 0: pattern=%s" % p)
            try:
                self.usedPattern = eval("NamingConvention_AsSource.%s" % p)
            except:
                if fromSuper == True:
                    pass
                else:
                    raise Exception("pattern not found:%s" % p)
            # if self.DEBUG!=0:
            print(" NamingConvention_AsSource usedPattern=%s" % self.usedPattern)
        else:
            #
            self.usedPattern = p
            # if self.DEBUG!=0:
            print(" NamingConvention_AsSource init case 1: usedPattern=%s" % self.usedPattern)

    #
    # use a instance pattern, provide the string value like '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<vvvv>'
    #
    def usePatternvalue(self, value):
        res = []
        for item in self.possible_pattern:
            if value == item:
                res.append(item)
        if len(res) == 1:
            return res[0]
        elif len(res) == 0:
            raise Exception("can not find instance pattern with value:%s" % value)
        elif len(res) > 1:
            raise Exception("several instance pattern match:%s" % res)

    #
    #
    #
    # def setDebug(self, d):
    #    self.debug=d

    #
    # build the product name based on the metadata values
    #
    def buildProductName(self, met=None, ext=None):
        if self.debug != 0:
            print("\n\n NamingConvention_AsSource.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
        origName = met.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
        srcName = origName
        # change ext if different
        if ext is not None:
            # how many . do we have in the name?
            nDot = len(origName.split('.')) - 1
            # print " #### NamingConvention_AsSource.buildProductName, nDot:%s" % (nDot)
            pos = origName.find('.')
            if pos > 0:
                src = origName[0:pos]
                srcExt = origName[pos + 1:]
                if srcExt != ext:
                    srcName = "%s.%s" % (src, ext)
                    if self.debug != 0:
                        print(" NamingConvention_AsSource.buildProductName, changed ext from name:%s to %s" % (
                        origName, srcName))

        # print " #### NamingConvention_AsSource.buildProductName, return:%s" % (srcName)
        # os._exit(1)
        return srcName


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    filename = 'EN1_NPDE_ASA_APH_0P_20050919T034114_20050919T034155_018581_0491.ZIP'
    try:
        n = NamingConvention_AsSource()
        print("namingConvention dump:%s" % n.toString())

        met = metadata.Metadata()
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
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "00001")
        met.setMetadataPair(metadata.METADATA_TYPECODE, "HRV__X__1A")
        met.setMetadataPair(metadata.METADATA_ORIGINAL_NAME,
                            "EN1_OPDK_ASA_IM__0P_20021115T131741_20021115T131943_003714_0153.ZIP")
        print("builded name:%s" % n.buildProductName(met))
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
