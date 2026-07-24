# -*- coding: cp1252 -*-
#
# represent the Envisat naming convention
#

import decimal
import sys
import traceback

from eoSip_converter.esaProducts import formatUtils
#
from eoSip_converter.esaProducts import metadata, base_metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention


# from product import Product
# import metadata
# import formatUtils
# from namingConvention import NamingConvention


class NamingConvention_Envisat(NamingConvention):
    #
    # pattern: 'TTTTTTTTTT|F|CET|<yyyymmdd>_<hhmmss>_<dddddddd><P><ccc>_<ooooo>_<OOOOO>_<NNNN>.extension'
    #
    # <dddddddd> Product duration in seconds
    # <P> Phase number within the mission phases
    # <ccc> Cycle number within the mission phase
    # <ooooo> Relative orbit
    # <OOOOO> Absolute orbit
    # <NNNN> Counter
    #
    ENVISAT_PATTERN = 'TTTTTTTTTT|F|CET|instance ID.extension'  # typecode|processingStageflag|processingCenter|
    # ENVISAT_PATTERN_INSTANCE_DEFAULT='<yyyymmdd>_<HHMMSS>_<DDDDDDDDDDDD>_<ttttt>_<ooooo>_<vvvv>' # year month day_hour min sec_duration_.... NO: see <P><ccc> above...._track_orbit_version
    ENVISAT_PATTERN_INSTANCE_DEFAULT = '<yyyymmdd>_<hhmmss>_<dddddddd><P><ccc>_<ooooo>_<OOOOO>_<NNNN>'

    #
    ENVISATS_POSSIBLE_PATTERN = [ENVISAT_PATTERN_INSTANCE_DEFAULT]

    #
    usedBase = None
    usedPattern = None

    debug = 0

    #
    #
    #
    def __init__(self, p=ENVISAT_PATTERN_INSTANCE_DEFAULT, fromSuper=False):
        NamingConvention.__init__(self, p, True)
        print("## NamingConvention_Envisat init: pattern=%s; fromSuper=%s" % (p, fromSuper))
        # the possible pattern used
        for item in self.ENVISATS_POSSIBLE_PATTERN:
            try:
                self.possible_pattern.index(item)
            except:
                self.possible_pattern.append(item)

        if self.debug != 0:
            print("#### NamingConvention_Envisat p=%s\n#### possible length:%s\n#### possible=%s" % (
            p, len(self.possible_pattern), self.possible_pattern))

        if p[0] != '<':
            if self.debug != 0:
                print(" NamingConvention_Envisat init case 0: pattern=%s" % p)
            self.usedPattern = eval("NamingConvention_Envisat.%s" % p)
            self.usedBase = NamingConvention_Envisat.ENVISAT_PATTERN
            if self.debug != 0:
                print(" NamingConvention_Envisat usedPattern=%s" % self.usedPattern)
        else:
            self.usedPattern = p
            self.usedBase = NamingConvention_Envisat.ENVISAT_PATTERN
            if self.debug != 0:
                print(" NamingConvention_Envisat init case 1: usedPattern=%s" % self.usedPattern)

    #
    #
    #
    def buildProductName(self, met=None, ext=None):
        if self.debug != 0:
            print("\n\n NamingConvention_Envisat.buildProductName, pattern used:%s, ext:%s" % (self.usedPattern, ext))
        toks = self.ENVISAT_PATTERN.split('|')
        res = ''
        for tok in toks:
            if self.debug != 0:
                print("doing token:%s" % tok)
            if tok == 'TTTTTTTTTT':
                # res=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_TYPECODE), len(tok))
                res = self.buildToken(met, metadata.METADATA_TYPECODE, 10, '#')
                if self.debug != 0:
                    print("res is now:%s" % res)
            elif tok == 'F':
                tmp = self.buildToken(met, metadata.METADATA_PROCESSING_STAGE_FLAG, 1, '#')
                # tmp=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_PROCESSING_STAGE_FLAG), len(tok))
                res = "%s%s" % (res, tmp)
                if self.debug != 0:
                    print("res1 is now:%s" % res)
            elif tok == 'CET':
                tmp = self.buildToken(met, metadata.METADATA_PROCESSING_CENTER, 3, '#')
                # tmp=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_PROCESSING_CENTER), len(tok))
                res = "%s%s" % (res, tmp)
                if self.debug != 0:
                    print("res2 is now:%s" % res)
            elif tok == 'instance ID.extension':
                tmp = self.buildInstance(met)
                res = "%s%s" % (res, tmp)
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
        date = None
        for tok in self.usedPattern.split('_'):
            if self.debug != 0:
                print("doing instance token:%s" % tok)
            if tok == '<yyyymmdd>':
                date = met.getMetadataValue(metadata.METADATA_START_DATE)
                tmp = formatUtils.normaliseDate(date, len(tok) - 2, '#')
                res = "%s" % tmp
                if self.debug != 0:
                    print("res4 is now:%s" % res)
            elif tok == '<hhmmss>':
                # should round the msec (if any) to closest second
                # for stripline to MDP: NO. round to bellow second
                v = met.getMetadataValue(metadata.METADATA_START_TIME)
                if v == None:
                    tmp = '######'
                else:
                    if self.debug != 0:
                        print("MSEC 0: v=%s" % v)
                    pos = v.find('.')
                    if pos > 0:  # some msec
                        msec = v[pos + 1:]
                        v1 = v[0:pos]
                        if self.debug != 0:
                            print("MSEC 1: msec; v1=%s; msec=%s" % (v1, msec))
                        if date == None:
                            raise Exception("NamingConvention_Envisat buildInstance: need date before handling time")
                        # use data function using msec
                        # v2=formatUtils.dateTimeMsecsStringToDecimalSecs("%sT%sZ" % (date, v))
                        # v3=formatUtils.secsDecimalToDateTimeMsecsString(round(v2))
                        # pos1=v3.find('T')
                        # pos2=v3.rfind('.')
                        # tmp=v3[pos1+1:pos2].replace(':','')
                        # if self.DEBUG!=0:
                        #    print "MSEC 2: msec; v2=%s; v3=%s; tmp=%s" % (v2, v3, tmp)

                        # just cut the msec
                        if self.debug != 0:
                            print("MSEC 2: just cut msec:%s" % v1)
                        tmp = formatUtils.normaliseTime(v1, len(tok) - 2)
                    else:
                        if self.debug != 0:
                            print("MSEC 1: no msec")
                        tmp = formatUtils.normaliseTime(met.getMetadataValue(metadata.METADATA_START_TIME),
                                                        len(tok) - 2)
                    # sys.exit(1)
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("res5 is now:%s" % res)

            elif tok == '<dddddddd><P><ccc>':
                # in sec + fractions; want it in 10th of msec
                duration = met.getMetadataValue(metadata.METADATA_DURATION)
                if duration == None or duration == base_metadata.VALUE_NOT_PRESENT:
                    tmp = '########'
                else:
                    d = decimal.Decimal(duration)
                    sec = int(d)
                    # fraction=int((d-int(d))*10000)
                    # if self.DEBUG!=0:
                    #    print "sec:%sFraction:%s" % (sec, fraction)
                    # tmp="%s%s" % (formatUtils.normaliseNumber("%s" % sec, 8, '0'), formatUtils.rightPadString("%s" % fraction, 4, '0'))
                    if self.debug != 0:
                        print("sec:%s" % sec)
                    tmp = "%s" % (formatUtils.normaliseNumber("%s" % sec, 8, '0'))
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resd is now:%s" % res)

                # add the <P><ccc>
                tmp = self.buildToken(met, metadata.METADATA_PHASE_NUMBER, 1, '#')
                tmp1 = self.buildToken(met, metadata.METADATA_CYCLE, 3, '#')
                res = "%s%s%s" % (res, tmp, tmp1)
                if self.debug != 0:
                    print("resdpc is now:%s" % res)

            elif tok == '<ooooo>':
                tmp = self.buildToken(met, metadata.METADATA_TRACK, 5, '#')
                # tmp=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_TRACK), len(tok)-2, '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resT is now:%s" % res)
            elif tok == '<OOOOO>':
                tmp = self.buildToken(met, metadata.METADATA_ORBIT, 5, '#')
                # tmp=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_ORBIT), len(tok)-2, '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resO is now:%s" % res)
            elif tok == '<NNNN>':
                tmp = self.buildToken(met, metadata.METADATA_SIP_VERSION, 4, '#')
                # tmp=formatUtils.normaliseNumber(met.getMetadataValue(metadata.METADATA_SIP_VERSION), len(tok)-2, '0')
                res = "%s_%s" % (res, tmp)
                if self.debug != 0:
                    print("resV is now:%s" % res)
            else:
                raise Exception("unknown naming instance pattern:'%s'" % tok)
        return res


if __name__ == '__main__':
    print("start")
    filename = 'ASA_WS__0PNIPA20070101_194625_000001202054_00200_25304_1441.ZIP'
    try:
        n = NamingConvention_Envisat()
        print("namingConvention dump:%s" % n.toString())

        res = n.guessPatternUsed(filename, n.possible_pattern)
        if len(res) == 1:
            n.usePatternvalue(res[0])
        else:
            print("can not find instance pattern...")

        ptype = n.getFilenameElement(filename, NamingConvention_Envisat.ENVISAT_PATTERN, 'TTTTTTTTTT')
        print("productType=%s" % ptype)

        met = metadata.Metadata()
        # met.setMetadataPair(metadata.METADATA_PROCESSING_CENTER,"ESR")
        # met.setMetadataPair(metadata.METADATA_PROCESSING_STAGE_FLAG,"N")
        # met.setMetadataPair(metadata.METADATA_START_DATE,"2014-03-02")
        # met.setMetadataPair(metadata.METADATA_START_TIME,"01:02:03.123")
        # met.setMetadataPair(metadata.METADATA_STOP_DATE,"2015-03-02")
        # met.setMetadataPair(metadata.METADATA_STOP_TIME,"21:02:03.123")
        # met.setMetadataPair(metadata.METADATA_ORBIT,"1000")
        # met.setMetadataPair(metadata.METADATA_TRACK,"273")
        # met.setMetadataPair(metadata.METADATA_FRAME,"34")
        met.setMetadataPair(metadata.METADATA_PHASE_NUMBER, '4')
        met.setMetadataPair(metadata.METADATA_CYCLE, '123')
        met.setMetadataPair(metadata.METADATA_DURATION, "12.23")
        # met.setMetadataPair(metadata.METADATA_SIP_VERSION,"00001")
        # met.setMetadataPair(metadata.METADATA_TYPECODE,"HRV__X__1A")

        name = n.buildProductName(met)
        print("\n\nbuilded name:%s" % name)

        track = n.getFilenameElement(name, n.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'OOOOO')
        print("\n\ntrack:%s" % track)

        flag = n.getFilenameElement(name, n.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'F')
        print("\n\nflag:%s" % flag)

        duration = n.getFilenameElement(name, n.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'dddddddd')
        print(" duration:%s" % duration)

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
