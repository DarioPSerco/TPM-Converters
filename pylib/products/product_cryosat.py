# -*- coding: cp1252 -*-
#
# For Esa/lite dissemination project
#
# Serco 03/2016 Lavaux Gilles
#
# this class represent a cryosat  product
#
# as per EoSip specESA-EOPG-MOM-SP-0003 V1.1 of 24/06/2016
#
#
import inspect
import os
import tarfile

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

#
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.esaProducts import formatUtils

from . import product_mph_sph
from .product_mph_sph import Product_Mph_Sph
from .product_directory import Product_Directory
from . import metadata as metadata

# station LUT not used because all is from KS station
# import LUT_acquisition_stations as LUT_acquisition_stations


#
# some values for control, in case there are strange string in the products
FIXED_DATETIME_STRING_LENGTH = len('2016-03-07T12:38:45Z')
FIXED_DATE_STRING_LENGTH = len('2016-03-07')
FIXED_TIME_STRING_LENGTH = len('12:38:45')
IS_SIR_METADATA_FLAG_NAME = 'IS_SIR_PRODUCT'


#
#
#
def testDateTimeStringLength(tmp):
    if len(tmp) != FIXED_DATETIME_STRING_LENGTH:
        raise Exception("Incorrect datetime length:'%s'" % tmp)


#
#
#
def testDateStringLength(tmp):
    if len(tmp) != FIXED_DATE_STRING_LENGTH:
        raise Exception("Incorrect date length:'%s'" % tmp)


#
#
#
def testTimeStringLength(tmp):
    if len(tmp) != FIXED_TIME_STRING_LENGTH:
        raise Exception("Incorrect time length:'%s'" % tmp)


#
#
#
class Cryosat_info:

    def __init__(self):
        self.typecode = None
        self.instrumentShortName = None
        self.sensorMode = None
        self.sensorType = None
        self.acquisitionType = None
        self.level = None
        self.hasQr = None

    # #instrument shortname|sensor type|sensor mode|acquisition type|typecode|QR|level
    # or #instrument shortname,sensor type,sensor mode,acquisition type,typecode,QR,level
    def fromLine(self, line):
        if line[0] != '#':
            toks = line.strip().split(',')
            self.instrumentShortName = toks[0]
            self.sensorType = toks[1]
            self.sensorMode = toks[2]
            self.acquisitionType = toks[3]
            self.typecode = toks[4]
            self.hasQr = toks[5]
            self.level = toks[6]

    #
    def toString(self):
        res = "typecode:%s; instrumentShortName:%s; sensorType:%s; sensorMode:%s\n" % (
        self.typecode, self.instrumentShortName, self.sensorType, self.sensorMode)
        res = res + "  acquisitionType:%s; level:%s; hasQr=%s" % (self.acquisitionType, self.level, self.hasQr)
        return res


#
# load typecode info from 2 files, use relative path
# returns a dictionnary containing typecode ->  Cryosat_info
#
def loadCryosatInfo():
    typeCodeInfo = {}

    SIR_data_path = 'data/cryosat2/SIRAL v1.1.dat'
    DORIS_data_path = 'data/cryosat2/STR-DORIS v1.1.dat'
    sirdata = None
    path = "%s/%s" % (currentdir, SIR_data_path)
    if not os.path.exists(path):
        raise Exception("can not find SIRAL data")
    fd = open(path, 'r')
    lines = fd.readlines()
    fd.close()
    n = 0
    for line in lines:
        line = line.strip()
        if len(line) > 0:
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
        line = line.strip()
        if len(line) > 0:
            anInfo = Cryosat_info()
            anInfo.fromLine(line)
            print(" typecode info[%s]:%s" % (n, anInfo.toString()))
            typeCodeInfo[anInfo.typecode] = anInfo
            n += 1
    print(" loaded %s typecodes info from files" % len(list(typeCodeInfo.keys())))
    return typeCodeInfo


#
typeCodeInfo = loadCryosatInfo()


# os._exit(1)


class Product_Cryosat(Product_Directory):
    # the cryosat typecodes by sensor and instruments
    """SENSORMODE_LRM=['SIR1LRM_0_', 'SIR2LRM_0_', 'SIR1LRC10_', 'SIR2LRC10_', 'SIR_LRM_1B', 'SIR1LRC11B', 'SIR2LRC11B', 'SIR_GOP_1B',
                    'SIR_LRMI2_', 'SIR_LRM_2_', 'SIR_GOP_2_']
    SENSORMODE_SAR=['SIR1SAR_0_', 'SIR2SAR_0_', 'SIR1TKSA0_', 'SIR2TKSA0_', 'SIR1SAC10_', 'SIR2SAC10_', 'SIR1SAC20_', 'SIR2SAC20_',
                    'SIR_SAR_1B', 'SIR1SAC11B', 'SIR2SAC11B', 'SIR1SAC21B', 'SIR2SAC21B', 'SIR_GOP_1B', 'SIR_SAR_2A', 'SIR_SARI2_',
                    'SIR_SAR_2_']
    SENSORMODE_SARIN=['SIR1SIN_0_', 'SIR2SIN_0_', 'SIR1TKSI0_', 'SIR2TKSI0_', 'SIR1SIC10_', 'SIR2SIC10_', 'SIR1SIC20_', 'SIR2SIC20_',
                      'SIR_SIN_1B', 'SIR_SIC11B', 'SIR_SICC1B', 'SIR1SIC21B', 'SIR2SIC21B', 'SIR_SINI2_', 'SIR_SIN_2_']

    SENSORMODE_GDR=['SIR_GDR_2A', 'SIR_GDR_2_']

    SENSORMODE_STR_NA=['STR1DAT_0_', 'STR2DAT_0_', 'STR3DAT_0_', 'STR1ATT_0_', 'STR2ATT_0_', 'STR3ATT_0_', 'STR_ATTREF']
    SENSORMODE_DORIS_NA=['DOR_NAV_0P', 'DOR_DOP_0_', 'DOR_DAT_0_', 'DOR_JAM_0P', 'DOR_TST_0P']



    # new:
    SENSORMODE_GOP=['SIR_GOP_1B', 'SIR_GOP_2_']
    SENSORMODE_SYNERGY=['SIR_GDR_2_']



    # the list of instrument
    INSTRUMENT_SIRAL=[SENSORMODE_LRM, SENSORMODE_SAR, SENSORMODE_SARIN, SENSORMODE_GDR]
    INSTRUMENT_DORIS=[SENSORMODE_DORIS_NA]
    INSTRUMENT_STR=[SENSORMODE_STR_NA]
    #INSTRUMENT_ALL=[INSTRUMENT_SIRAL, INSTRUMENT_DORIS, INSTRUMENT_STR]

    # the acquisition type
    ACQUISITION_TYPE_NOMINAL=['SIR1LRM_0_', 'SIR2LRM_0_',
                              'SIR1SAR_0_', 'SIR2SAR_0_',
                              'SIR1TKSA0_', 'SIR2TKSA0_',
                              'SIR1SIN_0_', 'SIR2SIN_0_',
                              'SIR1TKSI0_', 'SIR2TKSI0_',
                              'SIR_LRM_1B',
                              'SIR_GOP_1B','SIR_SAR_1B',
                              'SIR_SIN_1B',
                              'SIR_LRMI2_', 'SIR_LRM_2_'
                              'SIR_GOP_2_', 'SIR_SAR_2A', 'SIR_SARI2_', 'SIR_SAR_2_',  'SIR_SINI2_',
                              'SIR_GDR_2_',
                              'STR1DAT_0_', 'STR2DAT_0_', 'STR3DAT_0_', 'STR1ATT_0_', 'STR2ATT_0_', 'STR3ATT_0_',
                              'DOR_NAV_0P', 'DOR_DOP_0_', 'DOR_DAT_0_',
                              ]
    ACQUISITION_TYPE_CALIBRATION=['SIR1LRC10_', 'SIR2LRC10_',
                                  'SIR1SAC10_', 'SIR2SAC10_',
                                  'SIR1SAC20_', 'SIR2SAC20_',
                                  'SIR1SIC10_', 'SIR2SIC10_',
                                  'SIR1SIC20_', 'SIR2SIC20_',
                                  'SIR1LRC11B', 'SIR2LRC11B',
                                  'SIR1SAC11B', 'SIR2SAC11B',
                                  'SIR1SAC21B', 'SIR2SAC21B',
                                  'SIR_SIC11B', 'SIR_SICC1B', 'SIR1SIC21B', 'SIR2SIC21B',
                                  ]
    ACQUISITION_TYPE_OTHER= ['DOR_JAM_0P', 'DOR_TST_0P']

    # the one that has no QR file
    NO_QR=['SIR_GOP_1B', 'SIR_LRMI2_', 'SIR_GOP_2_', 'SIR_SARI2_', 'SIR_SAR_2_', 'SIR_SIN_2_', 'SIR_GDR_2_',
            'DOR_NAV_0P', 'DOR_DOP_0_', 'DOR_DAT_0_', 'DOR_JAM_0P', 'DOR_TST_0P', 'STR_ATTREF']
            """

    # the allowed file class:
    ALLOWED_CLASS = ['OPER', 'RPRO', 'OFFL', 'NRT_', 'TEST', 'LTA_']

    #
    xmlMapping = {metadata.METADATA_TYPECODE: 'Fixed_Header/File_Type',
                  metadata.METADATA_START_DATE: 'Fixed_Header/Validity_Period/Validity_Start',
                  metadata.METADATA_STOP_DATE: 'Fixed_Header/Validity_Period/Validity_Stop',
                  # metadata.METADATA_SIP_VERSION:'Fixed_Header/File_Version',
                  metadata.METADATA_FILECLASS: 'Variable_Header/MPH/Proc_Stage_Code',
                  metadata.METADATA_PHASE: 'Variable_Header/MPH/Phase',
                  # metadata.METADATA_CYCLE:'Variable_Header/MPH/Cycle',
                  metadata.METADATA_TRACK: 'Variable_Header/MPH/Rel_Orbit',
                  metadata.METADATA_ORBIT: 'Variable_Header/MPH/Abs_Orbit',
                  metadata.METADATA_SOFTWARE_VERSION: 'Variable_Header/MPH/Software_Version',
                  metadata.METADATA_PROCESSING_TIME: 'Variable_Header/MPH/Proc_Time',
                  'Start_Lat': 'Variable_Header/SPH/Product_Location/Start_Lat',
                  'Start_Long': 'Variable_Header/SPH/Product_Location/Start_Long',
                  'Stop_Lat': 'Variable_Header/SPH/Product_Location/Stop_Lat',
                  'Stop_Long': 'Variable_Header/SPH/Product_Location/Stop_Long',
                  'Z_Velocity': 'Variable_Header/MPH/Z_Velocity'}
    # metadata.METADATA_ORBIT_DIRECTION:'Variable_Header/SPH/Orbit_Information/Ascending_Flag'}

    METADATA_SUFIX = '.HDR'
    QUALITY_SUFIX = '.EEF'
    PRODUCT_SUFFIX = '.DBL'

    # acquisition type
    ACQ_NOMINAL = 'NOMINAL'
    ACQ_CALIBRATION = 'CALIBRATION'
    ACQ_OTHER = 'OTHER'

    # quality
    Q_NOMINAL = 'NOMINAL'
    Q_DEGRADED = 'DEGRADED'

    #
    #
    #
    def __init__(self, path=None):
        global typeCodeInfo
        Product_Directory.__init__(self, path)
        self.metContentName = None
        self.metContent = None

        self.qualityName = None
        self.qualityContent = None

        self.productName = None
        self.productContent = None

        #
        self.mphSphProduct = None
        self.mphSphProductMetadata = None

        self.isSir = False
        # if self.DEBUG!=0:
        print(" init class Cryosat_Product, there are %s known typecodes info" % len(list(typeCodeInfo.keys())))
        # os._exit(1)

    #
    # has QR?
    # based on #NO_QR list above
    #
    def asQrReport(self, typecode):
        global typeCodeInfo
        '''for code in self.NO_QR:
            if typecode==code:
                return False
        return True'''
        if typeCodeInfo[typecode].hasQr == 'QR':
            return True
        else:
            return False

    #
    # get the acquisition_type.
    # based on # the acquisition type lists above
    #
    def getAcquisitionTypeFromTypeCode(self, typecode):
        global typeCodeInfo
        '''type=None
        for code in self.ACQUISITION_TYPE_NOMINAL:
            if typecode==code:
                return self.ACQ_NOMINAL
        for code in self.ACQUISITION_TYPE_CALIBRATION:
            if typecode==code:
                return self.ACQ_CALIBRATION
        for code in self.ACQUISITION_TYPE_OTHER:
            if typecode==code:
                return self.ACQ_OTHER
                '''
        return typeCodeInfo[typecode].acquisitionType

    #
    # get the instrument.
    # based on # the cryosat typecodes by sensor and instruments lists above
    #
    def getInstrumentFromTypeCode(self, typecode):
        global typeCodeInfo
        '''instrument=None
        mode=None
        for code in self.SENSORMODE_LRM:
            if typecode==code:
                instrument='SIRAL'
                mode='LRM'
                return instrument, mode

        for code in self.SENSORMODE_SAR:
            if typecode==code:
                instrument='SIRAL'
                mode='SAR'
                return instrument, mode

        for code in self.SENSORMODE_SARIN:
            if typecode==code:
                instrument='SIRAL'
                mode='SARIN'
                return instrument, mode
        
        for code in self.SENSORMODE_GDR:
            if typecode==code:
                instrument='SIRAL'
                mode='GDR'
                return instrument, mode
        #
        for code in self.SENSORMODE_STR_NA:
            if typecode==code:
                instrument='STR'
                mode='NA'
                return instrument, mode

        for code in self.SENSORMODE_DORIS_NA:
            if typecode==code:
                instrument='DORIS'
                mode='NA'
                return instrument, mode
        '''

        return typeCodeInfo[typecode].instrumentShortName

    #
    #
    def getSensorTypeFromTypeCode(self, typecode):
        global typeCodeInfo
        return typeCodeInfo[typecode].sensorType

    #
    #
    def getSensorModeFromTypeCode(self, typecode):
        global typeCodeInfo
        return typeCodeInfo[typecode].sensorMode

        #

    #
    def getLevelFromTypeCode(self, typecode):
        global typeCodeInfo
        return typeCodeInfo[typecode].level

        #

    #
    #
    def getAllTypeCodes___(self):
        result = {}
        for item in self.INSTRUMENT_SIRAL:
            for piece in item:
                if piece in result:
                    print("ERROR: %s already present (INSTRUMENT_SIRAL)" % piece)
                result[piece] = piece

        for item in self.INSTRUMENT_DORIS:
            for piece in item:
                if piece in result:
                    print("ERROR: %s already present (INSTRUMENT_DORIS)" % piece)
                result[piece] = piece

        for item in self.INSTRUMENT_STR:
            for piece in item:
                if piece in result:
                    print("ERROR: %s already present (INSTRUMENT_STR)" % piece)
                result[piece] = piece

        a = list(result.keys())
        a.sort()
        return a

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # read matadata file
    #
    def getMetadataInfo(self):
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
        # test file class:
        tmp = self.origName[3:7]
        try:
            index = self.ALLOWED_CLASS.index(tmp)
        except:
            raise Exception("unknown file class:'%s'" % tmp)

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)
        tar = tarfile.open(self.path, 'r')

        # 
        n = 0
        # TODO : implements spot5 take5 test
        self.isSpot5Take5 = True
        for tarinfo in tar:
            n = n + 1
            name = tarinfo.name
            if self.debug != 0:
                print("  extract[%d]:%s" % (n, name))

            # keep metadata data
            # don't want the .EEF file in the Eo product
            asEef = False
            if name.find(self.METADATA_SUFIX) >= 0:  # metadata
                if self.debug != 0:
                    print("   metName:%s" % name)
                fd = tar.extractfile(tarinfo)
                data = fd.read()
                fd.close()
                print("   metContent length:%s" % len(data))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.metContent = data
            elif name.find(self.QUALITY_SUFIX) >= 0:  # quality
                self.qualityName = name
                if self.debug != 0:
                    print("   qualityName:%s" % name)
                fd = tar.extractfile(tarinfo)
                data = fd.read()
                fd.close()
                print("   qualityContent length:%s" % len(data))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.qualityContent = data
                asEef = True
            elif name.find(self.PRODUCT_SUFFIX) >= 0:  # product
                self.productName = name
                if self.debug != 0:
                    print("   productName:%s" % name)
                fd = tar.extractfile(tarinfo)
                data = fd.read()
                fd.close()
                print("   productContent length:%s" % len(data))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()
                self.productContent = data

                #
                self.mphSphProduct = Product_Mph_Sph(folder + '/' + name)

            else:
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(folder + '/' + name, 'wb')
                    outfile.write(data)
                    outfile.close()

            # remove .EEF qr file from tar
            # sept 2016: don't do it anymore: keep all original content
            # if not asEef:
            self.contentList.append(name)

        tar.close()

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met == None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")

        metNum = 0
        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metContent)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

                    # if self.DEBUG!=0:
            print("  metnum[%s] -->%s=%s" % (metNum, field, aValue))

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # baseline version: last 4 digits
        baseline = self.origName[-8:-4]
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, baseline)
        met.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, baseline)

        # don't want originalName in local attribute
        # met.addLocalAttribute("originalName", self.origName)

        # get from product itself
        self.mphSphProduct.getMetadataInfo()
        self.mphSphProductMetadata = metadata.Metadata()
        self.mphSphProduct.extractMetadata(self.mphSphProductMetadata)

        self.metadata = met

        #
        self.useQualityReport()

        # refine
        self.refineMetadata(helper)

        # footprint
        self.extractFootprint(helper)

        if self.debug != 0:
            print("\n\n\nheader metadata:%s" % self.metadata.toString())

        if self.debug != 0:
            print("MphSph metadata:%s" % self.mphSphProductMetadata.toString())

    #
    # extract METADATA_QUALITY_STATUS from quality file if any
    #
    def useQualityReport(self):
        if self.qualityContent is None or len(self.qualityContent.strip()) == 0:
            # raise Exception('no data in quality report')
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_STATUS, self.Q_NOMINAL)
            print("METADATA_QUALITY_STATUS set to NOMINAL because no quality report:'%s'; type:%s" % (
            self.qualityContent, self.qualityContent))
            return

        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.qualityContent)
        helper.parseData()

        # set eop:productQualityStatus
        quality = helper.getNodeText(
            helper.getFirstNodeByPath(None, '/Earth_Explorer_Header/Variable_Header/Product_Quality', None))
        self.metadata.setMetadataPair('Product_Quality', quality)
        print("product quality:%s" % quality)
        if quality == 'VALID_PRODUCT':
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_STATUS, self.Q_NOMINAL)
        else:
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_STATUS, self.Q_DEGRADED)

    #
    # refine the metada
    #
    def refineMetadata(self, xmlHelper):
        # date and time from START_DATE
        # is like: UTC=2016-03-18T05:12:43
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        tmp = tmp.replace('UTC=', '')
        pos = tmp.find('T')
        date = tmp[0:pos]
        time = tmp[pos + 1:]
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, date)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, time)
        print("start date:%s; time:%s" % (date, time))
        # valid?: 
        testDateStringLength(date)
        testTimeStringLength(time)

        # and STOP_DATE
        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        tmp = tmp.replace('UTC=', '')
        pos = tmp.find('T')
        date = tmp[0:pos]
        time = tmp[pos + 1:]
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, date)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, time)
        print("sop date:%s; time:%s" % (date, time))
        # valid?:
        testDateStringLength(date)
        testTimeStringLength(time)

        # processing time: round it
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        # tmp='UTC=2016-03-14T05:46:12.432045'
        # tmp='UTC=2016-03-14T05:46:12.532045'
        tmp = tmp.replace('UTC=', '')
        pos = tmp.find('.')
        fraction = 0
        if pos > 0:
            fraction = float("0.%s" % tmp[pos + 1:])
            tmp = tmp[0:pos]
        # print "@@@###@@@ processing time:'%s' fraction='%s'" % (tmp, fraction)
        if fraction >= 0.5:
            tmp = formatUtils.datePlusMsec(tmp + "Z", 1000, pattern=formatUtils.DEFAULT_DATE_PATTERN)
            pos = tmp.find('.')
            tmp = tmp[0:pos]
        # print "@@@###@@@ processing time final:'%s'" % (tmp)
        # os._exit(1)

        tmp = "%sZ" % tmp
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, tmp)
        # valid?: 
        testDateTimeStringLength(tmp)

        # Z_Velocity -> ascending descending
        # tmp = self.metadata.getMetadataValue('Z_Velocity')
        # print "Z_Velocity:%s" % tmp
        # if tmp[0]=='+':
        #    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'ASCENDING')
        # else:
        #    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'DESCENDING')

        # tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        # self.metadata.setMetadataPair(metadata.METADATA_LAST_ORBIT, tmp)

        # METADATA_PLATFORM
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        # has QR as expected?
        self.shouldHaveQr = self.asQrReport(tmp)
        self.qrPresent = False
        self.qrProblem = None
        if self.qualityName != None:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Product '%s' has a QR file" % tmp)
            self.qrPresent = True
        else:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Product '%s' has a QR file" % tmp)

        # do we have the QR file as defined in the Cryosat_info? (from  LUTs files)
        if self.qrPresent != self.shouldHaveQr:
            print("WARNING: Product '%s' quality file problem: should have:%s; has QR file:%s" % (
            tmp, self.asQrReport(tmp), self.qrPresent))
            self.qrProblem = "WARNING: Product '%s' quality file problem: should have:%s; has QR file:%s" % (
            tmp, self.asQrReport(tmp), self.qrPresent)
            # 2016-09-16: not an error, but a warning
            # raise Exception("Product '%s' quality file problem: should have:%s; has QR file:%s" % (tmp, self.asQrReport(tmp), self.qrPresent))
        else:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Product '%s'; QR file presence check is: ok" % tmp)

        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, self.getInstrumentFromTypeCode(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, self.getSensorModeFromTypeCode(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, self.getSensorTypeFromTypeCode(tmp))
        is_sir_met_flag = self.metadata.getMetadataValue(IS_SIR_METADATA_FLAG_NAME)
        if tmp[0:3] == 'STR':
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ typecode is STR:%s" % tmp)
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_DEGRADATION_QUOTATION_MODE, 'AUTOMATIC')
            if is_sir_met_flag != 'False':
                raise Exception("SIR VS STR_DOR product check problem (config used is for SIR)")
        elif tmp[0:3] == 'DOR':
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ typecode is DOR:%s" % tmp)
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_DEGRADATION_QUOTATION_MODE, 'AUTOMATIC')
            if is_sir_met_flag != 'False':
                raise Exception("SIR VS STR_DOR product check problem (config used is for SIR)")
        elif tmp[0:3] == 'SIR':
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ typecode is SIR:%s" % tmp)
            if is_sir_met_flag != 'True':
                raise Exception("SIR VS STR_DOR product check problem (config used is for DOR_STR)")
            self.isSir = True
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Product is SIR?:%s" % is_sir_met_flag)
        # os._exit(1)

        '''
        if tmp[0:3]=='DOR':
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'DORIS')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'NA')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, 'other: DORIS')
        elif tmp[0:3]=='STR':
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'STR')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'NA')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, 'other: StarTracker')
            self.metadata.setMetadataPair(metadata.METADATA_QUALITY_DEGRADATION_QUOTATION_MODE, 'AUTOMATIC')

        elif tmp[0:3]=='SIR':
            self.isSir=True
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'SIRAL')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, 'ALTIMETRIC')
            # LRM SAR SARIN GDR ACQ LRC SAC SIC GOP
            # TODO: how to discriminate?
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SARIN')
        else:
            raise Exception('unknown instrument shortname:%s' % tmp)
            '''

        # proc level
        if tmp[-2:-1] == '0':
            if self.isSir:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: L0')
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: L0')
        elif tmp[-2:] == '1B':
            if self.isSir:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, '1B')
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: L0')
        elif tmp[-2:] == '2_':
            if self.isSir:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, '2')
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: L0')
        elif tmp[-2:] == '2A':
            if self.isSir:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 2a')
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: L0')
        elif tmp[-2:] == 'EF':  # STR_ATTREF
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, '1B')
        else:
            raise Exception("unknown processing level:'%s'" % tmp)

        # phase
        phase = self.metadata.getMetadataValue(metadata.METADATA_PHASE)
        self.metadata.addLocalAttribute('missionPhase', phase)

        # acquisition type
        acqType = self.getAcquisitionTypeFromTypeCode(tmp)
        print("@@@@@@@@#################@@@@@@@@@@@@@@@@@#####################@@@@@@@@@@@@@@@@@@########## acqType=%s" % acqType)
        # self.metadata.addLocalAttribute(metadata.METADATA_ACQUISITION_TYPE, acqType)
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_TYPE, acqType)

        # from MphSph:
        # orbit
        tmp = "%s" % int(self.mphSphProductMetadata.getMetadataValue(metadata.METADATA_ORBIT))
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_LAST_ORBIT, tmp)
        # processing center
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, self.mphSphProductMetadata.getMetadataValue(
            metadata.METADATA_PROCESSING_CENTER).replace('"', '').strip())
        # acquisition station: FIXED TO KS
        # tmp=self.mphSphProductMetadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER).replace('"', '').strip()
        # tmp1='__'
        # try:
        #    tmp1=LUT_acquisition_stations.getCode2FromName(tmp)
        # except:
        #    pass
        # self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, tmp1)

        # ascending
        asc = self.mphSphProduct.findInSphData('ASCENDING_FLAG')
        # TODO: ascending is not when z velocoty vector is positive??
        if asc == 'D':
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "DESCENDING")
        else:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, "ASCENDING")

        # SIRAL only
        if self.isSir:
            ascNodeDate = self.mphSphProduct.findInSphData('EQUATOR_CROSS_TIME_UTC')
            tmp = product_mph_sph.mphFormatDate(ascNodeDate, -1)
            print("@@@@@@@@@@@###@@@ ascNodeDate: %s;%s" % (ascNodeDate, tmp))
            self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_DATE, tmp)
            # valid?:
            testDateTimeStringLength(tmp)

            ascNodeLon = self.mphSphProduct.findInSphData('EQUATOR_CROSS_LONG')
            ascNodeLon = product_mph_sph.mphEeeToNumber(ascNodeLon)
            print("@@@@@@@@@@@###@@@ ascNodeLon:%s" % ascNodeLon)
            # os._exit(0)
            self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_LONGITUDE, "%s" % ascNodeLon)

            ascNodeStart = self.mphSphProduct.findInSphData('REL_TIME_ASC_NODE_START').replace('<s>', '')
            ascNodeStart = float(ascNodeStart) * 1000.0
            print("ascNodeStart:%s" % ascNodeStart)
            # os._exit(0)
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE, "%s" % ascNodeStart)

            ascNodeStop = self.mphSphProduct.findInSphData('REL_TIME_ASC_NODE_STOP').replace('<s>', '')
            ascNodeStop = float(ascNodeStop) * 1000.0
            print("ascNodeStop:%s" % ascNodeStop)
            # os._exit(0)
            self.metadata.setMetadataPair(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE, "%s" % ascNodeStop)

        # use processing time
        # self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (date, time))

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper):
        slat = self.metadata.getMetadataValue('Start_Lat')
        slat = int(slat) / 1000000.0

        slon = self.metadata.getMetadataValue('Start_Long')
        slon = int(slon) / 1000000.0

        elat = self.metadata.getMetadataValue('Stop_Lat')
        elat = int(elat) / 1000000.0

        elon = self.metadata.getMetadataValue('Stop_Long')
        elon = int(elon) / 1000000.0

        footprint = "%s %s %s %s" % (slat, slon, elat, elon)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

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
