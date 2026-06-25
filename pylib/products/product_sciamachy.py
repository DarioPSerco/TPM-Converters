# -*- coding: cp1252 -*-
#
# this class represent a sciamachy L1b directory product
#
#  - 
#  - 
#
#
import gzip
import os
import shutil
import struct

from . import LUT_acquisition_stations as LUT_acquisition_stations
from . import LUT_acquisition_stations_mmmc as LUT_acquisition_stations_mmmc
#
from . import formatUtils as formatUtils
from . import metadata as metadata
from . import product_mph_sph
from .namingConvention_envisat import NamingConvention_Envisat
from .product_directory import Product_Directory
from .product_mph_sph import Product_Mph_Sph

#


# sciamachy DSR states
STATE_NONE = 'NONE_STATE'
STATE_NADIR = 'NADIR'
STATE_LIMB = 'LIMB'
STATE_OCCULTATION = 'OCCULTATION'
STATE_MONITORING = 'MONITORING'
STATE_NONE_index = 0
STATE_NADIR_index = 1
STATE_LIMB_index = 2
STATE_OCCULTATION_index = 3
STATE_MONITORING_index = 4
STATE_TYPE = [STATE_NONE, STATE_NADIR, STATE_LIMB, STATE_OCCULTATION, STATE_MONITORING]

# VAR NAMES
REF_DOCUMENT = 'referenceDocument'

#
debug = 0


#
# get state id uint16 (2 bytes) at offset 1116:1117
#
def readSciamachyStateBlock(data):
    s, = struct.unpack(">B", data[1116:1117])
    if debug != 0:
        print("state=%s" % s)
    return s


#
# read geolocation block
#
# for limb and occultation (state==2 and 3), swap corner 2 3  (0 1 unchanged) because of bow tie problem
#
def readSciamachyGeoBlock(data, state):
    if debug != 0:
        print("readSciamachyGeoBlock; length=%d" % len(data))
    # int32 + uint32 + uint32
    # d, = struct.unpack("i", data[0:4])
    d1, = struct.unpack(">i", data[0:4])

    # s, = struct.unpack("I", data[4:8])
    s1, = struct.unpack(">I", data[4:8])
    # ms, = struct.unpack("I", data[8:12])
    ms1, = struct.unpack(">I", data[8:12])
    # print "d=%d; s=%d; ms=%d" % (d, s, ms)
    print("d1=%d; s1=%d; ms1=%d" % (d1, s1, ms1))
    # sys.exit(0)

    day = "0.%s" % d1
    day = float(day)

    sec = "0.%s" % s1
    sec = float(sec)

    msec = "0.%s" % ms1
    msec = float(msec)
    if debug != 0:
        print("days 0=%s; sec=%s; msec=%s" % (day, sec, msec))

    v = day * 86400.0 + sec + msec
    if debug != 0:
        print("days 1=%s" % v)

    # 1 * uint8
    f, = struct.unpack(">b", data[12:13])
    if debug != 0:
        print("flag=%s" % f)

    corner = ''
    # 4 * 2 * int32
    corners = []
    for i in range(4):
        l1, = struct.unpack(">i", data[13 + (i * 8):17 + (i * 8)])
        l2, = struct.unpack(">i", data[17 + (i * 8):21 + (i * 8)])
        if debug != 0:
            print("l1=%s; l2=%s" % (l1, l2))
        lat = l1 / 1000000.0
        lon = l2 / 1000000.0
        if debug != 0:
            print(" lat[%s]=%s; lon[%s]=%s" % (i, lat, i, lon))
        # if len(corner)>0:
        #    corner = "%s " % corner
        # corner = "%s%s %s" % (corner, lat, lon)
        corners.append("%s %s" % (lat, lon))

    corner = ''
    if state == 2 or state == 3:
        print(" swap corner 2 3")
        corner = "%s %s %s %s %s" % (corners[0], corners[1], corners[3], corners[2], corners[0])
    else:
        corner = "%s %s %s %s %s" % (corners[0], corners[1], corners[2], corners[3], corners[0])

    # close footprint
    # toks = corner.split(' ')
    # if len(toks) > 2:
    #    corner = "%s %s %s" % (corner, toks[0], toks[1])
    return corner


class Product_Sciamachy(Product_Directory):

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_Sciamachy")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    #
    #
    def makeBrowses(self, processInfo):
        pass

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.mph_sphProduct_name = self.origName.replace('.gz', '')
        self.extractedPath = "%s/%s" % (folder, self.mph_sphProduct_name)
        print("will extract into:%s" % self.extractedPath)
        # if not os.path.exists(dest):
        #    os.makedirs(dest)

        # os._exit(1)

        with gzip.open(self.path, 'r') as f_in, open(self.extractedPath, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

        self.contentList.append(self.mph_sphProduct_name)

    #
    # change "09-DEC-2015 08:29:56.123456" into 2015-12-09 08:29:56.123
    #
    def formatDateString(self, s):
        # print " formatDateString:%s" % s
        tmp = product_mph_sph.mphFormatDate(s, 3)
        # print " formatDateString after mphFormatDate:%s" % tmp
        toks = tmp.split('T')
        toks2 = toks[0].split('-')
        month = toks2[1]
        monthNum = formatUtils.getMonth2DigitFromMonthString(month)
        tmp = "%s-%s-%s %s" % (toks2[0], monthNum, toks2[2], toks[1])
        if tmp.find('T') >= 0:
            tmp = tmp.replace('T', '')
        if tmp.find('Z') >= 0:
            tmp = tmp.replace('Z', '')
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos]
        return tmp

    #
    # change "+0032" into 32 and "-0043" into -43
    #
    def formatNumericString(self, s):
        if s[0] == '+':
            pos = 1
            while s[pos] == '0':
                pos += 1
            s = s[pos:]
        else:
            pos = 1
            while s[pos] == '0':
                pos += 1
            s = "-%s" % s[pos:]
        return s

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    #
    #
    def extractMetadata(self, met=None):
        print(" extractMetadata")

        # parse using a base peoduct instance
        self.mphSphPoduct = Product_Mph_Sph()
        self.mphSphPoduct.__init__(self.extractedPath)
        self.mphSphPoduct.setWantedTimeMsecPrecision(3)
        # self.mphSphPoduct.setDebug(1)
        self.mphSphPoduct.getMetadataInfo()
        num_added = self.mphSphPoduct.extractMetadata(met)
        print("  extracted from parent: %s" % num_added)
        print("\n\nself.mphSphPoduct metadata:%s" % self.mphSphPoduct.metadata.toString())

        # refine in parent
        self.mphSphPoduct.refineMetadata()
        self.metadata = self.mphSphPoduct.metadata
        print("  getMetadataInfo done")
        print(" TOTO 2: length contentList:%s" % len(self.contentList))

        # set typecode
        met.setMetadataPair(metadata.METADATA_TYPECODE, met.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)[0:10])

        # processor version
        tmp = product_mph_sph.mphStripString(met.getMetadataValue(metadata.METADATA_SOFTWARE_NAME))
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, tmp)

        # copy metadata that will be overwriten later
        tmp = product_mph_sph.mphStripString(met.getMetadataValue(metadata.METADATA_PRODUCTNAME))
        met.setMetadataPair('ProductName', tmp)

        # get some info from EO product in envisat format
        namingConvention = NamingConvention_Envisat()
        pos = tmp.find('.')
        if pos >= 0:
            tmp = tmp[0:pos]

        # processing stage flag
        flag = namingConvention.getFilenameElement(tmp, namingConvention.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'F')
        print(" processing stage flag:%s" % flag)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_STAGE_FLAG, flag)

        # duration as in filename
        duration = namingConvention.getFilenameElement(tmp, namingConvention.ENVISAT_PATTERN_INSTANCE_DEFAULT,
                                                       'dddddddd')
        print(" duration:%s" % duration)
        self.metadata.setMetadataPair(metadata.METADATA_DURATION, duration)

        # phase as in filename
        phase = namingConvention.getFilenameElement(tmp, namingConvention.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'P')
        print(" phase:%s" % phase)
        # set it in localAttribute
        met.addLocalAttribute('missionPhase', phase)

        # processing center 3 digit as in filename
        pac = namingConvention.getFilenameElement(tmp, namingConvention.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'CET')
        print(" pac:%s" % pac)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, pac)

        # version as in filename
        version = namingConvention.getFilenameElement(tmp, namingConvention.ENVISAT_PATTERN_INSTANCE_DEFAULT, 'NNNN')
        print(" version:%s" % version)
        # os._exit(1)
        self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION, version)

        # acquisition center 3 digit code from MPH value using MMMC + EO name LUTS
        acqStationName = met.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        print(" acqStationName:%s" % acqStationName)
        dg2 = LUT_acquisition_stations_mmmc.getCode2FromName(acqStationName)
        print(" dg2:%s" % dg2)
        dg3 = LUT_acquisition_stations.getCode3FromCode2(dg2)
        print(" dg3:%s" % dg3)
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, dg3)
        # os._exit(1)

        # reference document: in config file
        refDoc = met.getMetadataValue(REF_DOCUMENT)
        met.addLocalAttribute(REF_DOCUMENT, refDoc)
        # met.addLocalAttribute('referenceDocument','PGSI-GSEG-EOPG-TN-15-0007_1.0')

        self.extractFootprint()

        return num_added

    #
    # refine the metada
    #
    def refineMetadata_NOT_USED(self):
        self.metadata.setMetadataPair('ProductName',
                                      product_mph_sph.mphStripString(self.metadata.getMetadataValue('ProductName')))

        #
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)))
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)))

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME))
        tmp = "%sZ" % self.formatDateString(tmp).replace(' ', 'T')
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        #
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_NAME)))

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        tmp = self.formatDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, tmp.split(' ')[1])

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE))
        tmp = self.formatDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, tmp.split(' ')[1])

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_CYCLE))
        tmp = self.formatNumericString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_CYCLE, tmp)

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_ORBIT))
        tmp = self.formatNumericString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, tmp)

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_TRACK))
        print("rel orbit0:%s" % tmp)
        tmp = self.formatNumericString(tmp)
        print("rel orbit1:%s" % tmp)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, tmp)

        #
        tmp = product_mph_sph.mphStripByteUnit(self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE))
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, int(tmp))

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        self.extractFootprint()

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self):
        # read all dsd STATE records data
        offset, size, num_dsr, dsr_size = self.mphSphPoduct.getDsdOffsetInfoyName('STATES')
        data = self.mphSphPoduct.read(size, offset)
        print("\n STATE readed: length=%s" % len(data))
        states = []
        for n in range(num_dsr):
            block = data[dsr_size * n:dsr_size * (n + 1)]
            print("  block[%s]: length=%s" % (n, len(block)))
            state = readSciamachyStateBlock(block)
            print(" state[%d]:%s" % (n, state))
            states.append(state)

        # read all dsd GEOLOCATION records data
        offset, size, num_dsr, dsr_size = self.mphSphPoduct.getDsdOffsetInfoyName('GEOLOCATION')
        data = self.mphSphPoduct.read(size, offset)
        print("\n GEOLOCATION readed: length=%s" % len(data))

        nadir_footprint = ''
        limb_footprint = ''
        occultation_footprint = ''
        for n in range(num_dsr):
            block = data[dsr_size * n:dsr_size * (n + 1)]
            if debug != 0:
                print("\n\n  block[%s]: length=%s" % (n, len(block)))

            # corners = readSciamachyGeoBlock(block)
            state = states[n]
            corners = readSciamachyGeoBlock(block, state)
            if debug != 0:
                print(" state:%d; corner=%s" % (state, corners))

            if state == 0:
                pass
            if state == 1:
                if len(nadir_footprint) > 0:
                    nadir_footprint = "%s\n" % nadir_footprint
                nadir_footprint = "%s%s" % (nadir_footprint, corners)
            elif state == 2:
                if len(limb_footprint) > 0:
                    limb_footprint = "%s\n" % limb_footprint
                limb_footprint = "%s%s" % (limb_footprint, corners)
            elif state == 3:
                if len(occultation_footprint) > 0:
                    occultation_footprint = "%s\n" % occultation_footprint
                occultation_footprint = "%s%s" % (occultation_footprint, corners)
            elif state == 4:
                pass

        if debug != 0:
            print("\n\nnadir footprint:%s" % nadir_footprint)
            print("limb footprint:%s" % limb_footprint)
            print("occultation footprint:%s" % occultation_footprint)

        self.metadata.addLocalAttribute('limbStatesFootprint', limb_footprint.replace('\n', '|'))
        self.metadata.addLocalAttribute('nadirStatesFootprint', nadir_footprint.replace('\n', '|'))
        self.metadata.addLocalAttribute('occultationStatesFootprint', occultation_footprint.replace('\n', '|'))

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)
