# -*- coding: cp1252 -*-
#
# represent the EoSip naming convention
#
# first namingConvention created
#
#
#

import logging
import sys
import traceback
from io import StringIO

#
from . import base_metadata
from . import formatUtils
from . import metadata

#
debug = 0

INSTANCE_ID_TOKEN = 'instance ID'
EXTENSION = 'extension'


class NamingConvention:
    #
    # following used at start in NGEO branch
    PATTERN = '<SSS>_<CCCC>_<TTTTTTTTTT>_<instance ID>.<extension>'
    PATTERN_INSTANCE_NONE = ''
    PATTERN_INSTANCE_GENERIC_DDV = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<vvvv>'
    PATTERN_INSTANCE_WRS_SCENE_DDOTFV = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>_<vvvv>'
    PATTERN_INSTANCE_WRS_STRIPLINE_DDOTV = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<vvvv>'
    #
    # following used in OGC branch:
    PATTERN_INSTANCE_OGC_DDOTF = '<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<oooooo>_<tttt>_<ffff>'

    #
    #
    POSSIBLE_PATTERN = [PATTERN_INSTANCE_GENERIC_DDV, PATTERN_INSTANCE_WRS_SCENE_DDOTFV,
                        PATTERN_INSTANCE_WRS_STRIPLINE_DDOTV, PATTERN_INSTANCE_OGC_DDOTF]

    #
    #
    usedBase = None
    usedPattern = None

    #
    # init
    # build list of possible instance pattern than can be used
    #
    def __init__(self, p=PATTERN_INSTANCE_NONE, fromSuper=False):
        self.debug = debug
        if self.debug != 0:
            print("## NamingConvention init: pattern=%s; fromSuper=%s" % (p, fromSuper))

        #
        self.possible_pattern = []

        # the possible pattern used
        for item in self.POSSIBLE_PATTERN:
            self.possible_pattern.append(item)

        if self.debug != 0:
            print("#### NamingConvention p=%s\n#### possible length:%s\n#### possible=%s" % (
            p, len(self.possible_pattern), self.possible_pattern))

        self.usedBase = NamingConvention.PATTERN
        if len(p) == 0:
            self.usedPattern = None
        elif p[0] != '<':
            if self.debug != 0:
                print(" NamingConvention init case 0: pattern=%s" % p)
            try:
                self.usedPattern = eval("NamingConvention.%s" % p)
            except:
                if fromSuper == True:
                    pass
                else:
                    raise Exception("pattern not found:%s" % p)
            if self.debug != 0:
                print(" NamingConvention usedPattern=%s" % self.usedPattern)
        else:
            #
            self.usedPattern = p
            if self.debug != 0:
                print(" NamingConvention init case 1: usedPattern=%s" % self.usedPattern)

    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    #
    def getDebug(self):
        return self.debug

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
    # build a token of defined length, taking value from metadata
    # if value not present, return #### string of correct length
    #
    # @param padChar: char to be used for filling when no value
    # @param padChar2: char to be used for filling when value exists
    #
    def buildToken(self, met, metadataName, length, padChar='#', padChar2='0'):
        if self.debug != 0:
            print(" NamingConvention.buildToken, padChar:%s; padChar2:%s" % (padChar, padChar2))
        aa = met.getMetadataValue(metadataName)
        # print("#### buildToken for:'%s'; value='%s'" % (metadataName, aa))
        if aa == base_metadata.VALUE_NOT_PRESENT:
            tmp = formatUtils.normaliseNumber(padChar, length, padChar, 1).upper()
        else:
            tmp = formatUtils.normaliseNumber(aa, length, padChar2, 1).upper()
        return tmp

    #
    # build the product name based on the metadata values
    #
    def buildProductName(self, met=None, ext=None):
        # print("naming convention debug:%s" % self.debug)
        # os._exit(1)
        if self.debug != 0:
            print("\n\n NamingConvention.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
        toks = self.PATTERN.split('_')
        res = ''
        for tok in toks:
            if self.debug != 0:
                print("doing token:%s" % tok)
            if tok == '<SSS>':

                # if the wanted 2 first digits are not like the platform 2 first diggits: use METADATA_PLATFORM_2DIGITS_ALIAS
                twoDigitAlias = met.getMetadataValue(metadata.METADATA_PLATFORM_2DIGITS_ALIAS)
                if twoDigitAlias != base_metadata.VALUE_NOT_PRESENT:
                    if self.debug != 0:
                        print("use METADATA_PLATFORM_2DIGITS_ALIAS:%s" % res)
                    tmp = twoDigitAlias
                else:
                    tmp = self.buildToken(met, metadata.METADATA_PLATFORM, 2, '#')

                platFormId = met.getMetadataValue(metadata.METADATA_PLATFORM_ID)
                # if we dont want the platform_id
                if platFormId == base_metadata.VALUE_NONE:
                    if self.debug != 0:
                        print("don't want the platform ID")
                        res = tmp
                else:
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
            elif tok == '<vvvv>':
                tmp = self.buildToken(met, metadata.METADATA_PRODUCT_VERSION, len(tok) - 2, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)

            elif tok == '<VVVV>':
                tmp = self.buildToken(met, metadata.METADATA_SIP_VERSION, len(tok) - 2, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)

            elif tok == '<oooooo>':
                tmp = met.getMetadataValue(metadata.METADATA_ORBIT)
                tmp = self.buildToken(met, metadata.METADATA_ORBIT, len(tok) - 2, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resO is now:%s" % res)
            elif tok == '<tttt>':
                tmp = self.buildToken(met, metadata.METADATA_TRACK, len(tok) - 2, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resT is now:%s" % res)
            elif tok == '<ffff>':
                tmp = self.buildToken(met, metadata.METADATA_FRAME, len(tok) - 2, '#', '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resF is now:%s" % res)
            else:
                raise Exception("unknown naming instance pattern:%s" % tok)
        return res

    #
    # return the length of the fileName. not including the extension
    #
    def getFilenameLength(self):
        return self.usedPattern.replace('<', '').replace('>', '')

    #
    # test if file has the correct length. extension should not be given
    #
    def isFileLengthOk(self, name):
        n = self.getFilenameLength()
        if len(name) == n:
            if self.debug != 0:
                print("filename:%s has corect length:%d" % (name, len(name)))
            return True
        else:
            if self.debug != 0:
                print("filename:%s has incorect length:%d vs %s" % (name, len(name), n))
            return False

    #
    # get the filename length, as the used base and pattern define it
    #
    def getFilenameLength(self):
        base = len(self.usedBase.replace('<instance ID>.<extension>', '').replace('<', '').replace('>', ''))
        instance = len(self.usedPattern.replace('<', '').replace('>', ''))
        return base + instance

    #
    # try to identify the (instance) pattern used
    #
    def guessPatternUsed(self, filename, possiblePattern):
        # cut out the base
        if self.debug != 0:
            print(" guessPatternUsed of:%s" % filename)
            print(" self.usedBase:%s" % self.usedBase)
        strippedBase = self.usedBase.replace('<instance ID>.<extension>', '').replace('<', '').replace('>', '')
        if self.debug != 0:
            print(" strippedBase:%s" % strippedBase)
        tmp = filename[len(strippedBase):]
        print(" instance part:%s" % tmp)
        # look how many _ we have
        numSepFilename = tmp.count('_')
        res = []
        n = 0
        for item in possiblePattern:
            if item.count('_') == numSepFilename:
                if self.debug != 0:
                    print("   possible pattern[%s]:%s" % (n, item))
                res.append(item)
                n = n + 1

        return res

    #
    # get an element of the filename, giving the pattern block
    #
    def getFilenameElement(self, fileName, pattern, patternBlock):
        # is it instance or global pattern?
        if pattern.find(INSTANCE_ID_TOKEN) >= 0:
            print(" global pattern")
        else:
            print(" instance pattern")
            pattern = self.usedBase.replace(INSTANCE_ID_TOKEN, pattern)

        print('pattern used:%s' % pattern)
        tmp = pattern
        if tmp.find('>') >= 0 or tmp.find('<') >= 0:
            tmp = tmp.replace('<', '').replace('>', '')
        if tmp.find('|') >= 0:
            tmp = tmp.replace('|', '')
        # else:
        #    raise Exception("unknown pattern:%s" % pattern)
        if self.debug != 0:
            print("##### get patternBlock %s on fileName=%s; pattern=%s" % (patternBlock, fileName, tmp))

        if patternBlock == EXTENSION:
            raise Exception("to be implemented")

        pos = tmp.find(patternBlock)
        # print "##### fileName='%s'" % fileName
        # print "##### length=%s" % len(fileName)
        # print "##### POS=%s" % pos
        if pos < 0:
            raise Exception("pattern block not found:%s in pattern:%s" % (patternBlock, tmp))
        pos2 = pos + len(patternBlock)
        # print "##### POS2=%s" % pos2
        return fileName[pos:pos2]

    #
    #
    #
    def toString(self):
        out = StringIO()
        print("NamingConvention\n", file=out)
        print(" usedBase:%s\n" % self.usedBase, file=out)
        print(" usedPattern:%s\n" % self.usedPattern, file=out)
        print(" possible instance pattern:\n", file=out)
        n = 0
        for item in self.possible_pattern:
            print("   %s\n" % item, file=out)
            n = n + 1
        return out.getvalue()

    #
    #
    #


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        n = NamingConvention('PATTERN_INSTANCE_OGC_DDOTF')

        print("namingConvention dump:%s" % n.toString())
        met = metadata.Metadata()
        # met.setMetadataPair(metadata.METADATA_PLATFORM,"AL")
        # met.setMetadataPair(metadata.METADATA_PLATFORM_ID,"1")
        # met.setMetadataPair(metadata.METADATA_FILECLASS,"OPER")
        # met.setMetadataPair(metadata.METADATA_START_DATE,"20140302")
        # met.setMetadataPair(metadata.METADATA_START_TIME,"01:02:03")
        # met.setMetadataPair(metadata.METADATA_STOP_DATE,"20150302")
        # met.setMetadataPair(metadata.METADATA_STOP_TIME,"21:02:03")
        # met.setMetadataPair(metadata.METADATA_FILECLASS,"OPER")
        met.setMetadataPair(metadata.METADATA_ORBIT, "1000")
        met.setMetadataPair(metadata.METADATA_TRACK, "273")
        met.setMetadataPair(metadata.METADATA_FRAME, "34")
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "0000000001")
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "0000000001")
        # met.setMetadataPair(metadata.METADATA_TYPECODE,"HRV__X__1A")
        print("builded name:%s" % n.buildProductName(met))

        name = n.buildProductName(met)
        print("\n\nbuilded name:%s" % name)

        ptype = n.getFilenameElement(name, n.PATTERN, 'TTTTTTTTTT')
        print("\n\nptype:%s" % ptype)

        track = n.getFilenameElement(name, n.PATTERN_INSTANCE_OGC_DDOTF, 'tttt')
        print("\n\ntrack:%s" % track)

        if not isinstance(n, NamingConvention):
            print("instance not recognized")

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
