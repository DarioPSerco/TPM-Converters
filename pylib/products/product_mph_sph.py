# -*- coding: cp1252 -*-
from . import browse_metadata
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .product import Product

debug = 0

REF_DS_NAME = 'DS_NAME'
REF_DS_OFFSET = 'DS_OFFSET'
REF_DS_SIZE = 'DS_SIZE'
REF_NUM_DSR = 'NUM_DSR'
REF_DSR_SIZE = 'DSR_SIZE'


#
#  convert number like : +0049648227<10-6degE>
#
#
def mphDegreeEeeToNumber(s):
    if debug != 0:
        print("mphEeeToNumber:%s" % s)
    s = s.replace('<10', 'e')
    s = s.replace('degE>', '')
    s = s.replace('degN>', '')
    if debug != 0:
        print(" mphEeeToNumber stipped s:%s" % s)
    return formatUtils.EEEtoNumber(s)


#
#  convert number like : +0049648227<10-6degE>
#
#
def mphEeeToNumber(s):
    if debug != 0:
        print("mphEeeToNumber:%s" % s)
    s = s.replace('<10', 'e')
    s = s.replace('degE>', '')
    s = s.replace('degN>', '')
    if debug != 0:
        print(" mphEeeToNumber stipped s:%s" % s)
    return formatUtils.EEEtoNumber(s)


#
#  convert from '"SPH OF LEVEL 2 PRODUCT      "'  to 'SPH OF LEVEL 2 PRODUCT'
#
#
def mphStripString(s):
    if debug != 0:
        print("mpStripString:'%s'" % s)
    old = s
    if s[0] == '"':
        s = s[1:]
    if s[-1] == '"':
        s = s[0:-1]

    pos = len(s) - 1
    while s[pos] == ' ':
        s = s[0:pos]
        pos = pos - 1
    if debug != 0:
        print("  mpStripString:'%s' result='%s'" % (old, s))
    return s


#
#  convert from '+00000000000050914520<bytes>'  to '+00000000000050914520'
#
#
def mphStripByteUnit(s):
    # print "mpStripByteUnit:%s" % s
    s = s.replace('<bytes>', '')
    # print "  mpStripByteUnit: result=%s" % s
    return s


#
#  convert from '+1234<m/s>'  to '+1234'
#
#
def mphStripMpersecUnit(s):
    # print "mphStripMpersecUnit:%s" % s
    s = s.replace('<m/s>', '')
    # print "  mphStripMpersecUnit: result=%s" % s
    return s


#
#  convert from '+1234<m>'  to '+1234'
#
#
def mphStripMeterUnit(s):
    # print "mphStripMeterUnit:%s" % s
    s = s.replace('<m>', '')
    # print "  mphStripMeterUnit: result=%s" % s
    return s


#
#  convert like like 17-NOV-2003 07:39:19.493783 into 2003-11-17T07:39:19.49Z
#
#
def mphFormatDate(s, msecPrecision=2):
    if debug != 0:
        print("mphFormatDate:%s; msecPrecision:%s" % (s, msecPrecision))

    pos = s.find('.')
    if pos > 0:
        s = s[0:pos + msecPrecision + 1]

    toks = s.split(' ')
    yToks = toks[0].split('-')

    if len(yToks[1]) == 3:
        tmp = formatUtils.getMonth2DigitFromMonthString(yToks[1])
        s = "%s-%s-%sT%s" % (yToks[2], tmp, yToks[0], toks[1])
    else:
        s = "%s-%s-%sT%s" % (yToks[2], yToks[1], yToks[0], toks[1])

    pos = s.find('Z')
    if pos < 0:
        s = s + "Z"
    if debug != 0:
        print(" mphFormatDate stipped s:'%s'" % s)
    return s


class Product_Mph_Sph(Product):
    #
    # syntax is: sectionName|[key][+nLine,+nLine...]
    #
    xmlMapping = {metadata.METADATA_PRODUCTNAME: 'MPH|PRODUCT',
                  metadata.METADATA_ACQUISITION_CENTER: 'MPH|ACQUISITION_STATION',
                  metadata.METADATA_PROCESSING_CENTER: 'MPH|PROC_CENTER',
                  metadata.METADATA_PROCESSING_TIME: 'MPH|PROC_TIME',
                  metadata.METADATA_SOFTWARE_NAME: 'MPH|SOFTWARE_VER',
                  metadata.METADATA_START_DATE: 'MPH|SENSING_START',
                  metadata.METADATA_STOP_DATE: 'MPH|SENSING_STOP',
                  metadata.METADATA_PHASE_NUMBER: 'MPH|PHASE',
                  metadata.METADATA_CYCLE: 'MPH|CYCLE',
                  metadata.METADATA_TRACK: 'MPH|REL_ORBIT',
                  metadata.METADATA_ORBIT: 'MPH|ABS_ORBIT',
                  metadata.METADATA_PRODUCT_SIZE: 'MPH|TOT_SIZE'
                  }

    #
    #
    #
    def __init__(self, p=None):
        Product.__init__(self, p)
        print(" init class Product_Mph_Sph, path=%s" % p)
        self.type = Product.TYPE_MPH_SPH
        # block size
        self.MPH_SIZE = 1247
        self.SPH_SIZE = -1
        self.NUM_DSD = -1
        self.DSD_SIZE = -1
        self.FIRST_DSD_OFFSET = -1
        self.mphData = None
        self.sphData = None
        self.sphHeaderData = None
        # formatting options
        self.wantedTimeMsecPrecision = 2

    #
    # set the wantedTimeMsecPrecision
    #
    def setWantedTimeMsecPrecision(self, p):
        print('############################# setWantedTimeMsecPrecision to:%s' % p)
        self.wantedTimeMsecPrecision = p

    #
    # extract the content into workfolder
    #
    def extractToPath(self, folder=None, dont_extract=False):
        pass

    #
    # from MPH
    #
    def getSphSize(self):
        tmp = self.findInMphData('SPH_SIZE')
        if self.debug != 0:
            print(" getSphSize 0:%s" % tmp)
        tmp = tmp.replace('<bytes>', '')
        s = int(tmp)
        if self.debug != 0:
            print(" getSphSize 1:%s" % s)
        return s

    #
    # from MPH
    #
    def getDsdSize(self):
        tmp = self.findInMphData('DSD_SIZE')
        if self.debug != 0:
            print(" getDsdSize 0:%s" % tmp)
        tmp = tmp.replace('<bytes>', '')
        s = int(tmp)
        if self.debug != 0:
            print(" getDsdSize 1:%s" % s)
        return s

    #
    # from MPH
    #
    def getNumDsd(self):
        tmp = self.findInMphData('NUM_DSD')
        if self.debug != 0:
            print(" getNumDsd 0:%s" % tmp)
        s = int(tmp)
        if self.debug != 0:
            print(" getNumDsd 1:%s" % s)
        return s

    #
    # return the content of a DSD 
    #
    def getDsdContent(self, num):
        if self.debug != 0:
            print(" getDsdContent 0 num:%s" % num)
        data = self.sphData[
               self.FIRST_DSD_OFFSET + (num * self.DSD_SIZE): self.FIRST_DSD_OFFSET + ((num + 1) * self.DSD_SIZE)]
        if self.debug != 0:
            print(" getDsdContent 1 num:%s\n%s" % (num, data))
        return data

    #
    # return 4 offset and dimension values, given a DSD name
    #
    def getDsdOffsetInfoyName(self, name):
        #
        if self.debug != 0:
            print(" getDsdOffsetInfoyName DS_NAME=name:%s" % name)

        # loop in all DSD
        found = False
        data = None
        for n in range(self.getNumDsd()):
            if self.debug != 0:
                print(" getDsdOffsetInfoyName test DSD[%d]:" % n)
            data = self.getDsdContent(n)

            found = self.test_dsd_name(data, name)
            if found:
                break

        if found:
            offset = int(mphStripByteUnit(self.findInLinesData(data, REF_DS_OFFSET)))
            size = int(mphStripByteUnit(self.findInLinesData(data, REF_DS_SIZE)))
            num_dsr = int(self.findInLinesData(data, REF_NUM_DSR))
            dsr_size = int(mphStripByteUnit(self.findInLinesData(data, REF_DSR_SIZE)))
            if self.debug != 0:
                print(" getDsdOffsetInfoyName: offset=%s; size=%s; num_dsr=%s; dsr_size=%s" % (
                    offset, size, num_dsr, dsr_size))
            return offset, size, num_dsr, dsr_size
        else:
            raise Exception("name not found:%s" % name)

    #
    # return a value from a DSD line, given a DSD name and a key value
    #
    def findInDsdByName(self, name, key):
        #
        if self.debug != 0:
            print(" findInDsd DS_NAME=name:%s; key=%s" % (name, key))

        # loop in all DSD
        found = False
        data = None
        for n in range(self.getNumDsd()):
            if self.debug != 0:
                print(" findInDsd test DSD[%d]:" % n)
            data = self.getDsdContent(n)

            found = self.test_dsd_name(data, name)
            if found:
                break

        if found:
            offset = int(mphStripByteUnit(self.findInLinesData(data, REF_DS_OFFSET)))
            size = int(mphStripByteUnit(self.findInLinesData(data, REF_DS_SIZE)))
            num_dsr = int(self.findInLinesData(data, REF_NUM_DSR))
            dsr_size = int(mphStripByteUnit(self.findInLinesData(data, REF_DSR_SIZE)))
            if self.debug != 0:
                print(" findInDsd: offset=%s; size=%s; num_dsr=%s; dsr_size=%s" % (offset, size, num_dsr, dsr_size))

            if key == REF_DS_OFFSET:
                res = offset
            elif key == REF_DS_SIZE:
                res = size
            elif key == REF_NUM_DSR:
                res = num_dsr
            elif key == REF_DSR_SIZE:
                res = dsr_size
            else:
                raise Exception("unknown key:%s" % key)
        else:
            raise Exception("name not found:%s" % name)

        if self.debug != 0:
            print(" findInDsd: result=%s" % res)
        return res

    #
    # return a value from a DSD line, given a DSD number
    #
    def findInDsdByNum(self, name, num):
        raise Exception('not implemented')

    #
    #
    #
    def test_dsd_name(self, data, name):
        line = data.split('\n')[0]
        ok = False
        if line.find(REF_DS_NAME + '=') == 0:
            value = line[len(REF_DS_NAME) + 1:].replace('"', '')
            if self.debug != 0:
                print(" test_dsd_name value:%s" % value)
            if value.find(name) == 0:
                if self.debug != 0:
                    print(" test_dsd_name: good one")
                ok = True
        return ok

    #
    #
    #
    def findInLinesData(self, data, key):
        for line in data.split('\n'):
            if line.find(key + '=') == 0:
                value = line[len(key) + 1:].replace('"', '')
                if self.debug != 0:
                    print(" findInLinesData found:%s" % value)
                break
        return value

    #
    # return a value from a MPH line
    #
    def findInMphData(self, key):
        if self.debug != 0:
            print(" findInMphData key:%s" % key)
        value = None
        for line in self.mphData.split('\n'):
            # print "test MPH line:%s" % line
            if line.find(key + '=') == 0:
                value = line[len(key) + 1:].replace('"', '')
                if self.debug != 0:
                    print(" findInMphData found:%s" % value)
                break
        return value

    #
    #
    #
    def findInSphData(self, key):
        if self.debug != 0:
            print(" findInSphData key:%s" % key)
        value = None
        for line in self.sphData.split('\n'):
            # print "test SPH line:%s" % line
            if line.find(key) == 0:
                value = line[len(key) + 1:].replace('"', '')
                if self.debug != 0:
                    print(" findInSphData found:%s" % value)
                break
        return value

    #
    #
    #
    def getSphData(self):
        return self.sphData

    #
    #
    #
    # def getMphSize(self):
    #    return self.MPH_SIZE

    #
    #
    #
    # def getSphSize(self):
    #    return self.SPH_SIZE

    #
    #
    #
    # def getNumDsd(self):
    #    return self.NUM_DSD

    #
    #
    #
    # def getDsdSize(self):
    #    return self.DSD_SIZE

    #
    #
    #
    def getMetadataInfo(self):
        print(" getMetadataInfo")
        self.mphData = self.read(self.MPH_SIZE)
        if self.debug != 0:
            print(" self.mphData:%s" % self.mphData)
        if self.MPH_SIZE == None:
            raise Exception('can not find SPH size in MPH')
        self.SPH_SIZE = self.getSphSize()
        self.NUM_DSD = self.getNumDsd()
        self.DSD_SIZE = self.getDsdSize()
        self.FIRST_DSD_OFFSET = self.SPH_SIZE - (self.DSD_SIZE * self.NUM_DSD)
        self.sphData = self.read(self.SPH_SIZE, self.MPH_SIZE)
        self.sphHeaderData = self.sphData[0:self.FIRST_DSD_OFFSET]
        print(" extract metadata:  self.SPH_SIZE=%s; self.NUM_DSD=%s; self.DSD_SIZE=%s; self.FIRST_DSD_OFFSET:%s" % (
            self.SPH_SIZE, self.NUM_DSD, self.DSD_SIZE, self.FIRST_DSD_OFFSET))
        #
        # for i in range(self.NUM_DSD):
        #    print "%s" % self.getDsdContent(i)

        if self.debug != 0:
            print("\n\nself.sphHeaderData:\n%s\n\n" % self.sphHeaderData)

        if self.debug != 0:
            print(" extract metadata info:\n#### MPH:\n%s### END MPH\n### SPH:\n%s\n### END SPH" % (
                self.mphData, self.sphData))
        return None

    #
    #
    #
    def extractMetadata(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        # set some evident values
        met.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.origName)

        # use what contains the metadata file
        metContent = self.getMetadataInfo()

        # get fields
        num_added = 0

        for field in self.xmlMapping:
            rule = self.xmlMapping[field]
            aValue = None
            if self.debug != 0:
                print(" ##### handle metadata:%s; rule=%s" % (field, rule))

            section = rule.split('|')[0]
            key = rule.split('|')[1]
            if section == "MPH":
                for line in self.mphData.split('\n'):
                    # print "test MPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:]  # .replace('"','')
                        if self.debug != 0:
                            print(" found:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break

            elif section == "SPH":
                for line in self.sphData.split('\n'):
                    # print "test SPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:]  # .replace('"','')
                        if self.debug != 0:
                            print(" found:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break
            else:
                raise Exception("bad field rule:%s" % rule)

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        self.metadata = met

        return num_added

    #
    # refine the metada, should perform in order:
    # - normalise date and time
    # - normalise numbers
    # get footprint coords
    #
    def refineMetadata(self):

        if self.debug != 0:
            print("refineMetadata met dump:%s" % self.metadata.toString())
            print("self.wantedTimeMsecPrecision:%s" % self.wantedTimeMsecPrecision)

        # processing time
        tmp = mphFormatDate(mphStripString(self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)),
                            self.wantedTimeMsecPrecision)
        tmp = formatUtils.normaliseDateString(mphStripString(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        # processing center
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, mphStripString(tmp).strip())

        # start
        tmp = mphFormatDate(mphStripString(self.metadata.getMetadataValue(metadata.METADATA_START_DATE)),
                            self.wantedTimeMsecPrecision)
        tmp = formatUtils.normaliseDateString(mphStripString(tmp))
        pos = tmp.find('T')
        date = None
        time = None
        if pos > 0:
            date = tmp[0:pos]
            time = tmp[pos + 1:].replace('Z', '')
            # just 2 decimal after second
            # pos2 = time.find('.')
            # if pos2>0:
            #    time = time[0:(pos2+3)]
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, time)
        else:
            raise Exception("invalid start date:" + tmp)

        # stop
        tmp = mphFormatDate(mphStripString(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)),
                            self.wantedTimeMsecPrecision)
        tmp = formatUtils.normaliseDateString(mphStripString(tmp))
        pos = tmp.find('T')
        date = None
        time = None
        if pos > 0:
            date = tmp[0:pos]
            time = tmp[pos + 1:].replace('Z', '')
            # just 2 decimal after second
            # pos2 = time.find('.')
            # if pos2>0:
            #    time = time[0:(pos2+3)]
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, time)
        else:
            raise Exception("invalid start date:" + tmp)

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # convert coords from mph coords notations
        # if 1 == 2:  # commented, should be in specialized class
        #     tmp = self.metadata.getMetadataValue('FIRST_NEAR_LAT')
        #     self.metadata.setMetadataPair('FIRST_NEAR_LAT', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('FIRST_NEAR_LONG')
        #     self.metadata.setMetadataPair('FIRST_NEAR_LONG', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('FIRST_FAR_LAT')
        #     self.metadata.setMetadataPair('FIRST_FAR_LAT', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('FIRST_FAR_LONG')
        #     self.metadata.setMetadataPair('FIRST_FAR_LONG', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('LAST_NEAR_LAT')
        #     self.metadata.setMetadataPair('LAST_NEAR_LAT', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('LAST_NEAR_LONG')
        #     self.metadata.setMetadataPair('LAST_NEAR_LONG', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('LAST_FAR_LAT')
        #     self.metadata.setMetadataPair('LAST_FAR_LAT', mphEeeToNumber(tmp))
        #
        #     tmp = self.metadata.getMetadataValue('LAST_FAR_LONG')
        #     self.metadata.setMetadataPair('LAST_FAR_LONG', mphEeeToNumber(tmp))

        # orbit direction
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, tmp.strip())

        # orbit
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, "%s" % int(tmp))

        # size
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)
        tmp = int(tmp.replace('<bytes>', ''))
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, tmp)

        # cycle
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CYCLE)
        self.metadata.setMetadataPair(metadata.METADATA_CYCLE, "%s" % int(tmp))

        # track
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TRACK)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, "%s" % int(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED,
                                      formatUtils.normaliseNumber("%s" % int(tmp), 3, '0'))

        # acq station
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, mphStripString(tmp).strip())

        # software name
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_NAME)
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, mphStripString(tmp).strip())

    #
    #
    #
    def getTypeCode(self):
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp[0:10])

    #
    #
    #
    def extractFootprint(self):
        return
        return "code commented"
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        footprint = None
        if tmp == "DESCENDING":
            # UL=FIRST_NEAR_LAT, LONG
            # UR=FIRST_FAR_LAT, LONG
            # BL=LAST_NEAR_LAT, LONG
            # BR=LAST_FAR_LAT, LONG
            # we want CCW footprint, start top left
            footprint = "%s %s %s %s %s %s %s %s %s %s" % (self.metadata.getMetadataValue('FIRST_NEAR_LAT'),
                                                           self.metadata.getMetadataValue('FIRST_NEAR_LONG'),

                                                           self.metadata.getMetadataValue('LAST_NEAR_LAT'),
                                                           self.metadata.getMetadataValue('LAST_NEAR_LONG'),

                                                           self.metadata.getMetadataValue('LAST_FAR_LAT'),
                                                           self.metadata.getMetadataValue('LAST_FAR_LONG'),

                                                           self.metadata.getMetadataValue('FIRST_FAR_LAT'),
                                                           self.metadata.getMetadataValue('FIRST_FAR_LONG'),

                                                           self.metadata.getMetadataValue('FIRST_NEAR_LAT'),
                                                           self.metadata.getMetadataValue('FIRST_NEAR_LONG'))

            print("FOOTPRINT:%s" % footprint)
            # self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)


        elif tmp == "ASCENDING":
            # BR=FIRST_NEAR_LAT, LONG
            # BL=FIRST_FAR_LAT, LONG
            # UR=LAST_NEAR_LAT, LONG
            # UL=LAST_FAR_LAT, LONG
            # we want CCW footprint, start top left
            footprint = "%s %s %s %s %s %s %s %s %s %s" % (self.metadata.getMetadataValue('LAST_FAR_LAT'),
                                                           self.metadata.getMetadataValue('LAST_FAR_LONG'),

                                                           self.metadata.getMetadataValue('FIRST_FAR_LAT'),
                                                           self.metadata.getMetadataValue('FIRST_FAR_LONG'),

                                                           self.metadata.getMetadataValue('FIRST_NEAR_LAT'),
                                                           self.metadata.getMetadataValue('FIRST_NEAR_LONG'),

                                                           self.metadata.getMetadataValue('LAST_NEAR_LAT'),
                                                           self.metadata.getMetadataValue('LAST_NEAR_LONG'),

                                                           self.metadata.getMetadataValue('LAST_FAR_LAT'),
                                                           self.metadata.getMetadataValue('LAST_FAR_LONG'))
            print("FOOTPRINT:%s" % footprint)
            # self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        else:
            raise Exception("Invalid orbit direction:'%s'" % tmp)

        rowCol = ""
        browseIm = BrowseImage()
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        # browseIm.setColRowList(rowCol)
        print("browseIm:%s" % browseIm.info())
        if not browseIm.getIsCCW():
            # keep for eolisa
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.getFootprint())

            # and reverse
            print("############### reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
            browseIm.reverseFootprint()
            print("###############             after;%s; colRowList:%s" % (
                browseIm.getFootprint(), browseIm.getColRowList()))
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, browseIm.getColRowList())
        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, rowCol)

            # reverse for eolisa
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT_CW, browseIm.reverseSomeFootprint(footprint))

        lat, lon = browseIm.calculateCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lat, lon))

        # boundingBox is needed in the localAttributes
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        self.metadata.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, '5')

        # closedBoundingBox = "%s %s %s" % (browseIm.boondingBox, browseIm.boondingBox.split(" ")[0], browseIm.boondingBox.split(" ")[1])
        # self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX_CW_CLOSED, browseIm.reverseSomeFootprint(closedBoundingBox))
        self.metadata.addLocalAttribute("boundingBox", self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

# if __name__ == '__main__':
#     print "start"
#     logging.basicConfig(level=logging.WARNING)
#     log = logging.getLogger('example')
#     try:
#         # p=Product_Mph_Sph("C:/Users/glavaux/Shared/LITE/testData/asar-gm\ASA_GM1_1POLRA20031117_073919_000001812021_00393_08964_0000.N1")
#         p = Product_Mph_Sph(
#             "/home/gilles/shared2/Datasets/IDEAS/ifremer/MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1")
#         p.getMetadataInfo()
#         met = metadata.Metadata()
#         p.extractMetadata(met)
#
#         mphEeeToNumber('+0049648227<10-6degE>')
#
#         a = '1234       '
#         print "mphStripString:'%s'" % mphStripString(a)
#
#         print "\n\nmetadata:%s" % met.dump()
#     except Exception, err:
#         print " Error"
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         traceback.print_exc(file=sys.stdout)
