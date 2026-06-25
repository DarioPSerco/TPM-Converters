# -*- coding: cp1252 -*-
#
# this class represent a proba product, which is composed of several files
#
#
import os
import sys
import tarfile
import time
import traceback
from datetime import datetime
from datetime import timedelta

from lxml import etree

import eoSip_converter.osPlatform as osPlatform
from . import formatUtils
from . import metadata
#
from eoSip_converter.esaProducts.browseImage import BrowseImage
from .product import Product

# phase limits
DATE_COMMISSIONNING_LIMIT = "2009-11-01T00:00:00Z"
DATE_ROUTINE_LIMIT = "2013-10-20T00:00:00Z"

# eosip spec REF_DATETIME
REF_DATETIME = "2009-11-01T00:01:00.000Z"
REF_DATETIME_MICROSEC = "2009-11-01T00:01:00.000000Z"

####
#### references
####

# products with footprint:
FOOTPRINT_PRODUCTS = ['EGG_NOM_1b', 'STR_VC2_1b', 'STR_VC3_1b', 'SST_NOM_1b', 'SST_RIN_1b']

# products without footprint:
NO_FOOTPRINT_PRODUCTS = ['EGG_NOM_2_', 'EGG_TRF_2_', 'GRC_SPW_2_', 'GRD_SPW_2_', 'EGM_GCF_2_', 'EGM_GOC_2_',
                         'EGM_GVC_2_', 'EGM_QLK_2I', 'GGC_GRF_2_', 'GGC_TRF_2_', 'GGG_225_2_', 'GGG_255_2_',
                         'TGG_225_2_', 'TGG_255_2_', 'GRF_GOC_2_', 'TRF_GOC_2_', 'MGG_NTC_2_', 'MGG_WTC_2_',
                         'MTR_GOC_1B', 'TDC_GOC_2_', 'SLA_GOC_2_', 'ACC_DF1_1B', 'ACC_DF2_1B', 'ACC_DF3_1B',
                         'ACC_DF4_1B', 'ACC_DF5_1B', 'ACC_DF6_1B', 'SST_PSO_2_', 'SST_AUX_2_', 'TEC_TMS_2_',
                         'VTGOCE_DS_', 'HKT_GOC_0_', 'MGM_GO1_1B', 'MGM_GO2_1B', 'MGM_GO3_1B']

# 2.3: all typecodes
REF_TYPECODE = ['EGG_NOM_1b', 'STR_VC2_1b', 'STR_VC3_1b', 'SST_NOM_1b', 'SST_RIN_1b',
                'EGG_NOM_2_', 'EGG_TRF_2_', 'GRC_SPW_2_', 'GRD_SPW_2_', 'EGM_GCF_2_', 'EGM_GOC_2_', 'EGM_GVC_2_',
                'EGM_QLK_2I', 'GGC_GRF_2_', 'GGC_TRF_2_', 'GGG_225_2_', 'GGG_255_2_', 'TGG_225_2_', 'TGG_255_2_',
                'MGG_NTC_2_', 'MGG_WTC_2_', 'MTR_GOC_1B', 'TDC_GOC_2_', 'SLA_GOC_2_', 'ACC_DF1_1B', 'ACC_DF2_1B',
                'ACC_DF3_1B', 'ACC_DF4_1B', 'ACC_DF5_1B', 'ACC_DF6_1B', 'SST_PSO_2_', 'SST_AUX_2_', 'TEC_TMS_2_',
                'VTGOCE_DS_', 'HKT_GOC_0_', 'MGM_GO1_1B', 'MGM_GO2_1B', 'MGM_GO3_1B']

# + L0 typecodes
REF_TYPECODE += ['AUX_NOM_0_', 'STR_VC2_0_', 'STR_VC3_0_', 'SST_TOT_0_', 'SST_NOM_0_', 'GRF_LOR_0_', 'EGG_AUX_0_',
                 'EGG_NOM_0_', 'EGG_TOT_0_',
                 'DFC_F01_0_', 'DFC_F10_0_', 'EGG_ICM_0_', 'SST_ICB_0_']

# instrument short name
INSTRUMENT_SHORT_NAME_EGG = 'EGG'
INSTRUMENT_SHORT_NAME_SSTI = 'SSTI'
INSTRUMENT_SHORT_NAME_STR = 'STR'
INSTRUMENT_SHORT_NAME_TLM = 'TLM'
REF_INSTRUMENT_SHORT_NAME = [INSTRUMENT_SHORT_NAME_EGG, INSTRUMENT_SHORT_NAME_SSTI, INSTRUMENT_SHORT_NAME_STR,
                             INSTRUMENT_SHORT_NAME_TLM]

# sensor type
SENSOR_TYPE_GRADIOMETER = 'other: GRADIOMETER'
SENSOR_TYPE_GPS = 'other: GPS'
SENSOR_TYPE_STARTRACKER = 'other: STARTRACKER'
SENSOR_TYPE_TELEMETRY = 'other: TELEMETRY'
REF_SENSOR_TYPE = [SENSOR_TYPE_GRADIOMETER, SENSOR_TYPE_GPS, SENSOR_TYPE_STARTRACKER, SENSOR_TYPE_TELEMETRY]

# the sensor operational mode codespace
REF_CODESPACE_SENSOR_OPERATIONAL_MODE = [INSTRUMENT_SHORT_NAME_EGG, INSTRUMENT_SHORT_NAME_SSTI,
                                         INSTRUMENT_SHORT_NAME_STR, INSTRUMENT_SHORT_NAME_TLM]

# QA report
HAS_NOMINAL_QR_REPORT_FILE_TYPE = ['EGG_NOM_1B', 'SST_NOM_1B', 'SST_RIN_1B']
HAS_DEORBITING_QR_REPORT_FILE_TYPE = ['EGG_NOM_1B', 'SST_NOM_1B', 'SST_RIN_1B', 'STR_VC2_1B', 'STR_VC3_1B',
                                      'ACC_DF1_1B', 'ACC_DF2_1B', 'ACC_DF3_1B', 'ACC_DF4_1B', 'ACC_DF5_1B',
                                      'ACC_DF6_1B', 'MGM_GO1_1B', 'MGM_GO2_1B', 'MGM_GO3_1B', 'MTR_GOC_1B',
                                      'EGG_NOM_2_', 'SST_PSO_2_', 'SST_AUX_2_']

#
PHASE_DE_ORBITING = 'De-orbiting'
PHASE_ROUTINE = 'Routine'
PHASE_COMMISIONNING = 'Commissioning'

#
# for L) products
#
L0_DEFAULT_PROCESSING_CENTER = 'KIRUNA'
L0_DEFAULT_PROCESSOR_NAME = 'N/A'
L0_DEFAULT_SOFTWARE_VERSION = 'N/A'

#
SENSOR_SHORTNAME_SOURCE = {
    #
    # with footprint
    'EGG_NOM_1b': INSTRUMENT_SHORT_NAME_EGG,
    # L0
    # 'DFC_Anw_0_': INSTRUMENT_SHORT_NAME_EGG,
    'DFC_F01_0_': INSTRUMENT_SHORT_NAME_EGG,
    'DFC_F10_0_': INSTRUMENT_SHORT_NAME_EGG,
    'EGG_AUX_0_': INSTRUMENT_SHORT_NAME_EGG,
    'EGG_ICM_0_': INSTRUMENT_SHORT_NAME_EGG,
    'EGG_NOM_0_': INSTRUMENT_SHORT_NAME_EGG,
    'EGG_TOT_0_': INSTRUMENT_SHORT_NAME_EGG,

    #
    'STR_VC2_1b': INSTRUMENT_SHORT_NAME_STR,
    'STR_VC3_1b': INSTRUMENT_SHORT_NAME_STR,
    # L0
    'STR_VC2_0_': INSTRUMENT_SHORT_NAME_STR,
    'STR_VC3_0_': INSTRUMENT_SHORT_NAME_STR,

    #
    'SST_NOM_1b': INSTRUMENT_SHORT_NAME_SSTI,
    'SST_RIN_1b': INSTRUMENT_SHORT_NAME_SSTI,
    # L0
    'SST_ICB_0_': INSTRUMENT_SHORT_NAME_SSTI,
    'SST_NOM_0_': INSTRUMENT_SHORT_NAME_SSTI,
    'SST_TOT_0_': INSTRUMENT_SHORT_NAME_SSTI,

    #
    # without footprint
    'EGG_NOM_2_': INSTRUMENT_SHORT_NAME_EGG,
    #
    'EGG_TRF_2_': INSTRUMENT_SHORT_NAME_EGG,
    'GRC_SPW_2_': INSTRUMENT_SHORT_NAME_EGG,
    'GRD_SPW_2_': INSTRUMENT_SHORT_NAME_EGG,
    'EGM_GCF_2_': INSTRUMENT_SHORT_NAME_EGG,
    'EGM_GOC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'EGM_GVC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'EGM_QLK_2I': INSTRUMENT_SHORT_NAME_EGG,

    'GGC_GRF_2_': INSTRUMENT_SHORT_NAME_EGG,
    'GGC_TRF_2_': INSTRUMENT_SHORT_NAME_EGG,

    'GGG_225_2_': INSTRUMENT_SHORT_NAME_EGG,
    'GGG_255_2_': INSTRUMENT_SHORT_NAME_EGG,
    'TGG_225_2_': INSTRUMENT_SHORT_NAME_EGG,
    'TGG_255_2_': INSTRUMENT_SHORT_NAME_EGG,
    # 'GRF_GOC_2_': INSTRUMENT_SHORT_NAME_EGG,
    # 'TRF_GOC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'MGG_NTC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'MGG_WTC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'MTR_GOC_1B': INSTRUMENT_SHORT_NAME_EGG,
    'TDC_GOC_2_': INSTRUMENT_SHORT_NAME_EGG,
    'SLA_GOC_2_': INSTRUMENT_SHORT_NAME_EGG,
    #
    'ACC_DF1_1B': INSTRUMENT_SHORT_NAME_EGG,
    'ACC_DF2_1B': INSTRUMENT_SHORT_NAME_EGG,
    'ACC_DF3_1B': INSTRUMENT_SHORT_NAME_EGG,
    'ACC_DF4_1B': INSTRUMENT_SHORT_NAME_EGG,
    'ACC_DF5_1B': INSTRUMENT_SHORT_NAME_EGG,
    'ACC_DF6_1B': INSTRUMENT_SHORT_NAME_EGG,
    #
    'SST_PSO_2_': INSTRUMENT_SHORT_NAME_SSTI,
    'SST_AUX_2_': INSTRUMENT_SHORT_NAME_SSTI,
    'TEC_TMS_2_': INSTRUMENT_SHORT_NAME_SSTI,
    #
    'VTGOCE_DS_': 'N/A',
    #
    'HKT_GOC_0_': INSTRUMENT_SHORT_NAME_TLM,
    'MGM_GO1_1B': INSTRUMENT_SHORT_NAME_TLM,
    'MGM_GO2_1B': INSTRUMENT_SHORT_NAME_TLM,
    'MGM_GO3_1B': INSTRUMENT_SHORT_NAME_TLM,
    # L0
    'GRF_LOR_0_': INSTRUMENT_SHORT_NAME_TLM,
    'AUX_NOM_0_': INSTRUMENT_SHORT_NAME_TLM
}

#
SENSOR_TYPE = {
    #
    # with footprint
    'EGG_NOM_1b': SENSOR_TYPE_GRADIOMETER,
    # L0
    # 'DFC_Anw_0_': SENSOR_TYPE_GRADIOMETER,
    'DFC_F01_0_': SENSOR_TYPE_GRADIOMETER,
    'DFC_F10_0_': SENSOR_TYPE_GRADIOMETER,
    'EGG_AUX_0_': SENSOR_TYPE_GRADIOMETER,
    'EGG_ICM_0_': SENSOR_TYPE_GRADIOMETER,
    'EGG_NOM_0_': SENSOR_TYPE_GRADIOMETER,
    'EGG_TOT_0_': SENSOR_TYPE_GRADIOMETER,

    #
    'STR_VC2_1b': SENSOR_TYPE_STARTRACKER,
    'STR_VC3_1b': SENSOR_TYPE_STARTRACKER,
    # L0
    'STR_VC2_0_': SENSOR_TYPE_STARTRACKER,
    'STR_VC3_0_': SENSOR_TYPE_STARTRACKER,

    #
    'SST_NOM_1b': SENSOR_TYPE_GPS,
    'SST_RIN_1b': SENSOR_TYPE_GPS,
    # L0
    'SST_ICB_0_': SENSOR_TYPE_GPS,
    'SST_NOM_0_': SENSOR_TYPE_GPS,
    'SST_TOT_0_': SENSOR_TYPE_GPS,

    #
    # without footprint
    'EGG_NOM_2_': SENSOR_TYPE_GRADIOMETER,
    #
    'EGG_TRF_2_': SENSOR_TYPE_GRADIOMETER,
    'GRC_SPW_2_': SENSOR_TYPE_GRADIOMETER,
    'GRD_SPW_2_': SENSOR_TYPE_GRADIOMETER,
    'EGM_GCF_2_': SENSOR_TYPE_GRADIOMETER,
    'EGM_GOC_2_': SENSOR_TYPE_GRADIOMETER,
    'EGM_GVC_2_': SENSOR_TYPE_GRADIOMETER,
    'EGM_QLK_2I': SENSOR_TYPE_GRADIOMETER,

    'GGC_GRF_2_': SENSOR_TYPE_GRADIOMETER,
    'GGC_TRF_2_': SENSOR_TYPE_GRADIOMETER,

    'GGG_225_2_': SENSOR_TYPE_GRADIOMETER,
    'GGG_255_2_': SENSOR_TYPE_GRADIOMETER,
    'TGG_225_2_': SENSOR_TYPE_GRADIOMETER,
    'TGG_255_2_': SENSOR_TYPE_GRADIOMETER,
    # 'GRF_GOC_2_': SENSOR_TYPE_GRADIOMETER,
    # 'TRF_GOC_2_': SENSOR_TYPE_GRADIOMETER,
    'MGG_NTC_2_': SENSOR_TYPE_GRADIOMETER,
    'MGG_WTC_2_': SENSOR_TYPE_GRADIOMETER,
    'MTR_GOC_1B': SENSOR_TYPE_GRADIOMETER,
    'TDC_GOC_2_': SENSOR_TYPE_GRADIOMETER,
    'SLA_GOC_2_': SENSOR_TYPE_GRADIOMETER,
    #
    'ACC_DF1_1B': SENSOR_TYPE_GRADIOMETER,
    'ACC_DF2_1B': SENSOR_TYPE_GRADIOMETER,
    'ACC_DF3_1B': SENSOR_TYPE_GRADIOMETER,
    'ACC_DF4_1B': SENSOR_TYPE_GRADIOMETER,
    'ACC_DF5_1B': SENSOR_TYPE_GRADIOMETER,
    'ACC_DF6_1B': SENSOR_TYPE_GRADIOMETER,
    #
    'SST_PSO_2_': SENSOR_TYPE_GPS,
    'SST_AUX_2_': SENSOR_TYPE_GPS,
    'TEC_TMS_2_': SENSOR_TYPE_GPS,
    #
    'VTGOCE_DS_': 'other: N/A',
    #
    'HKT_GOC_0_': SENSOR_TYPE_TELEMETRY,
    'MGM_GO1_1B': SENSOR_TYPE_TELEMETRY,
    'MGM_GO2_1B': SENSOR_TYPE_TELEMETRY,
    'MGM_GO3_1B': SENSOR_TYPE_TELEMETRY,
    # L0
    'GRF_LOR_0_': SENSOR_TYPE_TELEMETRY,
    'AUX_NOM_0_': SENSOR_TYPE_TELEMETRY
}

#
HDR_SUFFIX = '.HDR'
EEF_SUFFIX = '.EEF'

#
DUMMY_DATE = '1970-01-01T00:00:00.000Z'
DUMMY_DATE_PROCESSING = '1970-01-01T01:01:01.000Z'
REFERENCE_DATE = '1999-10-28T07:18:41.000Z'

DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%S.000Z"
#
DATE_1 = 'UTC=20091101T000000'
DATE_PATTERN_1 = "UTC=%Y%m%dT%H%M%S"
DATE_2 = 'UTC=2009-11-01T00:00:00'
DATE_PATTERN_2 = "UTC=%Y-%m-%dT%H:%M:%S"
DATE_3 = 'UTC=09-Jun-2015 08:32:51'
DATE_PATTERN_3 = 'UTC=%d-%b-%Y %H:%M:%S'
DATE_4 = 'UTC=2012-03-30T15:21:14.822005'
DATE_PATTERN_4 = 'UTC=%Y-%m-%dT%H:%M:%S'
DATE_5 = 'UTC=0000-00-00T00:00:00'
DATE_PATTERN_5 = 'UTC=%Y-%m-%dT%H:%M:%S'
DATE_6 = 'UTC=9999-99-99T99:99:99'
DATE_PATTERN_6 = 'UTC=%Y-%m-%dT%H:%M:%S'
#
DATE_10 = '1999-10-28T07:18:41'
DATE_PATTERN_10 = '%Y-%m-%dT%H:%M:%S'

DEBUG = False


#
#
#
def verifyDateTime(aDateTime):
    if len(aDateTime) != len(REF_DATETIME):
        raise Exception("Invalid datetime, not as specified in spec:'%s'" % aDateTime)
    # T position
    pos = REF_DATETIME.find("T")
    if pos < 0:
        raise Exception("Invalid datetime, T not present:'%s'" % aDateTime)
    if aDateTime.find("T") != pos:
        raise Exception("Invalid datetime, T not at good place'%s'" % aDateTime)

    # . position
    pos = REF_DATETIME.find(".")
    if pos < 0:
        raise Exception("Invalid datetime, . not present:'%s'" % aDateTime)
    if aDateTime.find(".") != pos:
        raise Exception("Invalid datetime, . not at good place'%s'" % aDateTime)


#
#
#
def verifyDateTimeMicrosec(aDateTime):
    if len(aDateTime) != len(REF_DATETIME_MICROSEC):
        raise Exception("Invalid datetime with microsec:'%s'" % aDateTime)
    # T position
    pos = REF_DATETIME.find("T")
    if pos < 0:
        raise Exception("Invalid datetime, T not present:'%s'" % aDateTime)
    if aDateTime.find("T") != pos:
        raise Exception("Invalid datetime, T not at good place'%s'" % aDateTime)

    # . position
    pos = REF_DATETIME.find(".")
    if pos < 0:
        raise Exception("Invalid datetime, . not present:'%s'" % aDateTime)
    if aDateTime.find(".") != pos:
        raise Exception("Invalid datetime, . not at good place'%s'" % aDateTime)


#
#
#
def normalizeDateTimeValue(dts):
    strDateTime = None
    if dts.startswith('UTC='):
        if len(dts) == len(DATE_1):
            dt = datetime.strptime(dts, DATE_PATTERN_1)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)

        elif dts == DATE_5:  # 'UTC=0000-00-00T00:00:00'
            strDateTime = DATE_5.replace('UTC=', '') + 'Z'
        elif dts == DATE_6:  # 'UTC=9999-99-99T99:99:99'
            strDateTime = DATE_6.replace('UTC=', '') + 'Z'

        elif len(dts) == len(DATE_2):  # UTC=%Y-%m-%dT%H:%M:%S
            dt = datetime.strptime(dts, DATE_PATTERN_2)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)
        elif len(dts) == len(DATE_3):
            dt = datetime.strptime(dts, DATE_PATTERN_3)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)
        elif len(dts) == len(DATE_4):
            dt = datetime.strptime(dts.split('.')[0], DATE_PATTERN_4)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)
        elif len(dts) == len(DATE_4):
            dt = datetime.strptime(dts.split('.')[0], DATE_PATTERN_4)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)

        else:
            raise Exception("unknown datetime pattern:'%s'" % dts)
    else:
        if len(dts) == len(DATE_10):
            dt = datetime.strptime(dts, DATE_PATTERN_10)
            strDateTime = dt.strftime(DEFAULT_DATE_PATTERN)

    if DEBUG:
        print((" ######################### normalizeDateTimeValue from:'%s' to:'%s'" % (dts, strDateTime)))
    return strDateTime


class Product_Goce(Product):
    # for products with HDR file
    xmlMapping_XPATH_HDR_1 = {
        # like: UTC=2009-11-01T00:00:00
        metadata.METADATA_START_DATE: '//Fixed_Header/Validity_Period/Validity_Start',
        metadata.METADATA_STOP_DATE: '//Fixed_Header/Validity_Period/Validity_Stop',
        metadata.METADATA_TYPECODE: '//Fixed_Header/File_Type',
        metadata.METADATA_ACQUISITION_CENTER: '//Variable_Header/MPH/Acquisition_Station',

        metadata.METADATA_PROCESSING_CENTER: '//Variable_Header/MPH/Processor/Proc_Center',
        metadata.METADATA_PROCESSING_TIME: '//Variable_Header/MPH/Processor/Proc_Time',
        metadata.METADATA_SOFTWARE_VERSION: '//Variable_Header/MPH/Processor/Software_Ver',
        metadata.METADATA_NATIVE_PRODUCT_FORMAT: '//Variable_Header/MPH/Ref_Doc',

        metadata.METADATA_ORBIT: '//Variable_Header/SPH/Time_Information/Abs_Orbit/Start',
        metadata.METADATA_LAST_ORBIT: '//Variable_Header/SPH/Time_Information/Abs_Orbit/Stop',

        'State_Vector_Time': '//Variable_Header/MPH/State_Vector_Time',
        'X_Position': '//Variable_Header/MPH/X_Position',
        'Y_Position': '//Variable_Header/MPH/Y_Position',
        'Z_Position': '//Variable_Header/MPH/Z_Position',
        'X_Velocity': '//Variable_Header/MPH/X_Velocity',
        'Y_Velocity': '//Variable_Header/MPH/Y_Velocity',
        'Z_Velocity': '//Variable_Header/MPH/Z_Velocity',

        'Equator_Cross_Long': '//Variable_Header/SPH/Equator_Cross_Long',
        'Equator_Cross_Time_Start': '//Variable_Header/SPH/Equator_Cross_Time_Start',
        'Start_GPS_Time': '//Variable_Header/SPH/Start_GPS_Time',
        'Stop_GPS_Time': '//Variable_Header/SPH/Stop_GPS_Time',
    }

    # for products with EEF file
    xmlMapping_EEF = {
        metadata.METADATA_START_DATE: 'Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Start',
        metadata.METADATA_STOP_DATE: 'Earth_Explorer_Header/Fixed_Header/Validity_Period/Validity_Stop',
        metadata.METADATA_TYPECODE: 'Earth_Explorer_Header/Fixed_Header/File_Type',
        metadata.METADATA_ACQUISITION_CENTER: 'Earth_Explorer_Header/Variable_Header/MPH/Acquisition_Station',
        metadata.METADATA_PROCESSING_CENTER: 'Earth_Explorer_Header/Variable_Header/MPH/Proc_Center',
        metadata.METADATA_PROCESSING_TIME: 'Earth_Explorer_Header/Variable_Header/MPH/Proc_Time',
        metadata.METADATA_SOFTWARE_VERSION: 'Earth_Explorer_Header/Variable_Header/MPH/Software_Ver',
        # metadata.METADATA_PHASE: 'Earth_Explorer_Header/Variable_Header/MPH/Phase',
        metadata.METADATA_ORBIT: 'Earth_Explorer_Header/Variable_Header/MPH/Abs_Orbit',
        metadata.METADATA_RELATIVE_ORBIT: 'Earth_Explorer_Header/Variable_Header/MPH/Rel_Orbit',

        metadata.METADATA_NATIVE_PRODUCT_FORMAT: 'Earth_Explorer_Header/Variable_Header/MPH/Ref_Doc',

        'State_Vector_Time': 'Earth_Explorer_Header/Variable_Header/MPH/State_Vector_Time',
        'X_Position': 'Earth_Explorer_Header/Variable_Header/MPH/X_Position',
        'Y_Position': 'Earth_Explorer_Header/Variable_Header/MPH/Y_Position',
        'Z_Position': 'Earth_Explorer_Header/Variable_Header/MPH/Z_Position',
        'X_Velocity': 'Earth_Explorer_Header/Variable_Header/MPH/X_Velocity',
        'Y_Velocity': 'Earth_Explorer_Header/Variable_Header/MPH/Y_Velocity',
        'Z_Velocity': 'Earth_Explorer_Header/Variable_Header/MPH/Z_Velocity',

        'Equator_Cross_Long': 'Earth_Explorer_Header/Variable_Header/SPH/Equator_Cross_Long',
        'Equator_Cross_Time_Start': 'Earth_Explorer_Header/Variable_Header/SPH/Equator_Cross_Time_Start',
        'Start_GPS_Time': 'Earth_Explorer_Header/Variable_Header/SPH/Start_GPS_Time',
        'Stop_GPS_Time': 'Earth_Explorer_Header/Variable_Header/SPH/Stop_GPS_Time',
    }

    #
    # goce product are made of one TGZ file, which contains 2 files: one header + one xxx
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        #
        self.hdrContent = None
        self.eefContent = None
        # alternate metadata file
        self.alternateMatadata = None

        #
        self.hasFootprint = None
        self.isLevel0 = False
        # self.level0HasFootprint = None

        if self.debug != 0:
            print(" init class Product_Goce")

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
    # handle the input product files:
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract directory product '%s' to path:%s" % (self.path, folder))

        self.tmpSize = os.stat(self.path).st_size

        self.contentList = []
        # src will be added as a piece in the ingester, make it known in the contentList
        self.contentList.append(self.origName)

        self.EXTRACTED_PATH = "%s/EO_PRODUCT" % folder

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)

        tar = tarfile.open(self.path, 'r')
        # new: don't extract all product, just keep the xml files
        n = 0
        for tarinfo in tar:
            n = n + 1
            name = tarinfo.name
            if self.debug != 0:
                print("  test tar content[%d]:'%s'" % (n, name))

            if name.find(HDR_SUFFIX) >= 0:
                fd = tar.extractfile(tarinfo)
                self.hdrContent = fd.read()
                fd.close()
                print("   HDR length:%s" % len(self.hdrContent))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    self.eefSrcPath = folder + '/' + name
                    outfile = open(self.eefSrcPath, 'wb')
                    outfile.write(self.hdrContent)
                    outfile.close()

            elif name.find(EEF_SUFFIX) >= 0:
                fd = tar.extractfile(tarinfo)
                self.eefContent = fd.read()
                fd.close()
                if self.debug != 0:
                    print("   EEF length:%s" % len(self.eefContent))
                if dont_extract != True:
                    parent = os.path.dirname(folder + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    self.eefSrcPath = folder + '/' + name
                    outfile = open(self.eefSrcPath, 'wb')
                    outfile.write(self.eefContent)
                    outfile.close()

        tar.close()
        # os._exit(1)

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    #
    #
    def getXmlNodeValueAtPath(self, aXpath):
        aNodeList = self.rootXmlNode.xpath(aXpath)
        if len(aNodeList) == 1:
            if not aNodeList[0].text:
                if self.debug != 0:
                    print((" #### NOT FOUND:%s; not text element:%s" % (aNodeList, aNodeList[0])))
                return None
            else:
                if self.debug != 0:
                    print((" #### FOUND:%s; text=%s" % (aNodeList, aNodeList[0].text)))
                return aNodeList[0].text
        else:
            if self.debug != 0:
                print((" #### NOT FOUND:%s; list empty" % aNodeList))
            return None

    #
    #
    #
    def extractMetadata(self, met=None):
        if met is None:
            raise Exception("metadate is None")

        self.metadata = met
        if self.hdrContent is None and self.eefContent is None:
            raise Exception("no metadata to be parsed")

        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.tmpSize)

        start = time.time()
        num_added = 0
        self.rootXmlNode = etree.parse(self.eefSrcPath)
        for key in self.xmlMapping_XPATH_HDR_1:
            if self.debug != 0:
                print(" ###################### will use xml XPATH mapping:%s using path:%s" % (
                key, self.xmlMapping_XPATH_HDR_1[key]))
            met.setMetadataPair(key, self.getXmlNodeValueAtPath(self.xmlMapping_XPATH_HDR_1[key]))
            num_added += 1

        duration = time.time() - start
        if self.debug != 0:
            print(" ########################################  METADATA EXTACT DURATION:%s; found:%s" % (
            duration, num_added))
        return num_added

    #
    # done inside metadata refine, when we know we have a L0 with groundtrack
    #
    def sanityCheckL0(self, processInfo):
        # some L0 AUX_NOM_0_ have empty State_Vector_Time, look in DBL file
        otime = self.metadata.getMetadataValue('State_Vector_Time')
        if otime is None:
            otime = self.getStateVectorTimeFromAlternateFile()
        if otime is None:
            raise Exception("cannot use goceTool propagator because State_Vector_Time is not present in source product")
        self.metadata.setMetadataPair('State_Vector_Time', otime)

        # L0 have Equator_Cross_Time and not Equator_Cross_Time_Start
        # NEW: use goce tool in any case
        # ectStart = self.metadata.getMetadataValue('Equator_Cross_Time_Start')
        # if ectStart is None:
        #    ectStart = self.getEquatorCrossingTimeFromAlternateFile()
        # if ectStart is None:
        # raise Exception("cannot use goceTool propagator because State_Vector_Time is not present in source product")
        # use gocetool with start time
        ectStart, anxLong = self.runGoceToolAnx(processInfo)
        self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_DATE, ectStart)
        # self.metadata.setMetadataPair('Equator_Cross_Long', anxLong) this shoulf be 1^-6 deg from src product. not good
        self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_LONGITUDE, anxLong)

    #
    # done at end of metadata refine
    #
    def sanityCheck(self, processInfo):

        tmp = self.metadata.getMetadataValue(metadata.METADATA_NATIVE_PRODUCT_FORMAT)
        if not self.metadata.valueExists(tmp):
            raise Exception("no METADATA_NATIVE_PRODUCT_FORMAT")

        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if not self.metadata.valueExists(tmp):
            raise Exception("no METADATA_PROCESSING_TIME")

        tmp = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        if not self.metadata.valueExists(tmp):
            raise Exception("no METADATA_SOFTWARE_VERSION")

        if self.hasFootprint:
            # format Equator_Cross_Time_Start GPS time for non L0 products
            if not self.isLevel0:
                tmp = self.metadata.getMetadataValue('Equator_Cross_Time_Start')
                if self.debug != 0:
                    print((" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Equator_Cross_Time_Start:%s" % tmp))
                if not self.metadata.valueExists(tmp):
                    raise Exception("no Equator_Cross_Time_Start")
                # format it
                tmp = self.gpsTimeToUtc(tmp)
                self.metadata.setMetadataPair('Equator_Cross_Time_Start', tmp)
                self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_DATE, tmp)
                if self.debug != 0:
                    print((" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Equator_Cross_Time_Start HUMAN:%s" % tmp))
            else:  # L0 products have run the goce tool for ANX date + long
                pass

    #
    # refine the metada
    #
    def refineMetadata(self, processInfo, COLLECTION_DOI_LUT, TYPECODE_COLLECTION_LUT):

        typecode = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        #
        # patch for faulty EGM_GOC_2
        #
        if typecode == 'EGM_GOC_2':
            typecode = 'EGM_GOC_2_'
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

            # no Ref_Doc for metadata.METADATA_NATIVE_PRODUCT_FORMAT
            self.metadata.setMetadataPair(metadata.METADATA_NATIVE_PRODUCT_FORMAT, 'N/A')

        #
        # patch for faulty EGG_NOM_2_ that have typecode: EGG_NOM_2i
        #
        if typecode == 'EGG_NOM_2i':
            typecode = 'EGG_NOM_2_'
            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

            # no Ref_Doc for metadata.METADATA_NATIVE_PRODUCT_FORMAT
            # self.metadata.setMetadataPair(metadata.METADATA_NATIVE_PRODUCT_FORMAT, 'N/A')

        # print("TYPECODE:%s" % typecode)
        # set FILE_TYPE, because of _1b _1B mess
        self.metadata.setMetadataPair(metadata.METADATA_FILE_TYPE, typecode.upper())
        #
        l0Case = False
        if typecode not in REF_TYPECODE:
            # telemetry typecode for non L0 products
            if typecode[0:2] != 'T_':
                if typecode[-2:] != '0_':  # not L0
                    raise Exception("unknown typecode:%s" % typecode)
                else:  # shall be like DFC_Anw_0_ , n 0-6 w X,Y,Z
                    l0Case = True
                    if not typecode.startswith("DFC_A"):
                        raise Exception("unknown L0 typecode:%s" % typecode)
                    else:
                        n = typecode[5]
                        w = typecode[6]
                        if w != 'X' and w != 'Y' and w != 'Z':
                            raise Exception("unknown L0 typecode %s; w is wrong:%s" % (typecode, w))
                        if int(n) < 1 and int(n) > 6:
                            raise Exception("unknown L0 typecode %s; n is wrong:%s" % (typecode, n))

        collectionName = None
        if l0Case:
            collectionName = 'GOCE Level 0'
            self.metadata.setMetadataPair(metadata.METADATA_COLLECTION_NAME, collectionName)
            self.metadata.setMetadataPair(metadata.METADATA_DOI, None)
        else:
            if typecode not in TYPECODE_COLLECTION_LUT:
                if typecode[0:2] != 'T_':
                    raise Exception("typecode '%s' is not present in TYPECODE_COLLECTION_LUT look up table" % typecode)
                else:
                    collectionName = 'GOCE Telemetry'
                    # self.metadata.setMetadataPair(metadata.METADATA_DOI, 'GOCE Telemetry-DOI')
            else:
                collectionName = TYPECODE_COLLECTION_LUT[typecode]
            self.metadata.setMetadataPair(metadata.METADATA_COLLECTION_NAME, collectionName)

            if collectionName not in COLLECTION_DOI_LUT:
                raise Exception("collection '%s' is not present in COLLECTION_DOI_LUT look up table; typecode is:%s" % (
                collectionName, typecode))
            self.metadata.setMetadataPair(metadata.METADATA_DOI, COLLECTION_DOI_LUT[collectionName])

        #
        # differences in TDS file, so do additional check that we have all needed fields
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)
        if not self.metadata.valueExists(tmp):
            found = []
            n = 0
            #
            aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Proc_Center')
            if not aValue is None:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, aValue)
                found.append('Proc_Center')
                n += 1
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, L0_DEFAULT_PROCESSING_CENTER)
                found.append("DEFAULT processing center:%s" % L0_DEFAULT_PROCESSING_CENTER)
                n += 1

            #
            aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Proc_Time')
            if not aValue is None:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, aValue)
                found.append('Proc_Time')
                n += 1
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, "1970-01-011T00:00:00.000Z")
                found.append("DEFAULT processing time:1970-01-011T00:00:00.000Z")
                n += 1

            #
            aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Software_Ver')
            if not aValue is None:
                self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, aValue)
                found.append('Software_Ver')
                n += 1
            else:  # L0 products
                aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Software_Version')
                if not aValue is None:
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, aValue)
                    found.append('Software_Version')
                    n += 1
                else:
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, L0_DEFAULT_SOFTWARE_VERSION)
                    found.append("DEFAULT software version:%s" % L0_DEFAULT_SOFTWARE_VERSION)
                    n += 1

            if n != 3:
                raise Exception("can not recover 3 processor info but:%s; found:%s" % (n, found))

        # is version like aaaa/number, separate it and set software name + software version
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        if tmp is not None:
            if tmp.strip() == 'N/A':
                self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, tmp)
                self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, tmp)
            else:
                if tmp.find('/') > 0:
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, tmp.split('/')[0])
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, tmp.split('/')[1])
                else:
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_VERSION, 'N/A')
                    self.metadata.setMetadataPair('MISSING_SOFTWARE_VERSION', tmp)
                    self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, 'N/A')

        # get version from SRC filename
        toks1 = self.origName.split('_')
        tmp = toks1[-1].split('.')[0]
        if len(tmp) != 4:
            raise Exception("incorrect src version field length:'%s'" % tmp)
        print(("  -> version from source file:'%s'" % tmp))
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, tmp)

        # UTC=2009-11-01T00:00:00. new: not only!!!
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        print(("metadata.METADATA_START_DATE 0:%s" % tmp))
        tmp = normalizeDateTimeValue(tmp)
        print(("metadata.METADATA_START_DATE 1:%s" % tmp))
        # print(tmp)
        # os._exit(1)
        # tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE).replace('UTC=', '')
        toks = tmp.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, toks[1][0:-1])
        startDateTime = "%sT%s" % (toks[0], toks[1])
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME_MICROSEC, startDateTime.replace('Z', '000Z'))
        #
        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        print(("metadata.METADATA_STOP_DATE 0:%s" % tmp))
        tmp = normalizeDateTimeValue(tmp)
        print(("metadata.METADATA_STOP_DATE 1:%s" % tmp))
        # tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE).replace('UTC=', '')
        toks = tmp.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, toks[1][0:-1])
        stopDateTime = "%sT%s" % (toks[0], toks[1])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME_MICROSEC, stopDateTime.replace('Z', '000Z'))
        #

        verifyDateTime(self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME))
        verifyDateTime(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME))

        verifyDateTimeMicrosec(self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME_MICROSEC))
        verifyDateTimeMicrosec(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME_MICROSEC))
        print(("metadata.METADATA_START_DATE_TIME_MICROSEC:%s; metadata.METADATA_STOP_DATE_TIME_MICROSEC:%s" % (
        self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME_MICROSEC),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME_MICROSEC))))
        # os._exit(1)

        # METADATA_PROCESSING_TIME is a mess, it can be like:
        # 'XXXX'
        # 'UTC=10-Dec-2014 14:21:43'
        # '09-Jun-2015 08:32:51'
        #

        # SST_RIN_1b have another processing time. NOT USED BECAUSE WE HAVE DIFFERENT MAPPING NOW
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if not self.metadata.valueExists(tmp):
            print((" -> METADATA_PROCESSING_TIME value non exists, set it to %s" % DUMMY_DATE_PROCESSING))
            processInfo.addLog("METADATA_PROCESSING_TIME value non exists, set it to %s" % DUMMY_DATE_PROCESSING)
            tmp = DUMMY_DATE_PROCESSING
            self.metadata.setMetadataPair('NO_METADATA_PROCESSING_TIME', self.origName)
        else:
            if tmp == 'XXXX':  # TODO : REMOVE
                tmp = DUMMY_DATE_PROCESSING
                self.metadata.setMetadataPair('NO_METADATA_PROCESSING_TIME', self.origName)
            else:
                # tmp = tmp.replace('UTC=', '')
                tmp = normalizeDateTimeValue(tmp)

        if len(tmp) == len(REFERENCE_DATE):
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)
        else:
            raise Exception("invalid METADATA_PROCESSING_TIME:'%s'" % tmp)

        # final check: look for T
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        if tmp[10] != 'T':
            raise Exception("No T in datetime:%s" % tmp)

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        #
        print((" -> METADATA_START_DATE:%s" % startDateTime))
        print((" -> METADATA_STOP_DATE:%s" % stopDateTime))

        # '0000-00-00T00:00:00'
        strangeDate_0 = '0000-00-00T00:00:00'
        strangeDate_1 = '9999-99-99T99:99:99'
        duration = None
        durationSecs = None

        # datetime can be:
        # 2009-11-01T00:00:00
        # or:
        # 2009-11-01T00:00:00Z
        # or:
        # 20091101T000000

        # special date case
        # calculate duration
        if self.debug != 0:
            print((" ###### duration #######      'UTC=%s'" % startDateTime))
            print((" #######################  VS :'%sZ'" % DATE_5))
        if "UTC=%s" % startDateTime == "%sZ" % DATE_5:  # UTC=0000-00-00T00:00:00
            self.metadata.setMetadataPair(metadata.METADATA_DURATION, 'infinite')
            # set schema acceptable values
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, DUMMY_DATE)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, DUMMY_DATE[0:10])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, DUMMY_DATE[11:19])

            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, DUMMY_DATE)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, DUMMY_DATE[0:10])
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, DUMMY_DATE[11:19])

            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, DUMMY_DATE)

        else:
            if len(startDateTime) == len(REFERENCE_DATE):
                if startDateTime != strangeDate_0 and stopDateTime != strangeDate_1:
                    d1 = datetime.strptime(startDateTime, formatUtils.DEFAULT_DATE_PATTERN_MSEC)
                    d2 = datetime.strptime(stopDateTime, formatUtils.DEFAULT_DATE_PATTERN_MSEC)
                    duration = d2 - d1
                    durationSecs = duration.seconds
                    self.metadata.setMetadataPair(metadata.METADATA_DURATION, "%s" % durationSecs)
            else:
                if len(startDateTime) == len('20091101T000000'):
                    d1 = datetime.strptime(startDateTime, "%Y%m%dT%H%M%S")
                    d2 = datetime.strptime(stopDateTime, "%Y%m%dT%H%M%S")
                    duration = d2 - d1
                    durationSecs = duration.seconds
                    self.metadata.setMetadataPair(metadata.METADATA_DURATION, "%s" % durationSecs)
                else:
                    if len(startDateTime) == len('2009-11-01T00:00:00'):
                        if startDateTime != strangeDate_0 and stopDateTime != strangeDate_1:
                            d1 = datetime.strptime(startDateTime, "%Y-%m-%dT%H:%M:%S")
                            d2 = datetime.strptime(stopDateTime, "%Y-%m-%dT%H:%M:%S")
                            duration = d2 - d1
                            durationSecs = duration.seconds
                            self.metadata.setMetadataPair(metadata.METADATA_DURATION, "%s" % durationSecs)
                    else:
                        raise Exception("unknown dateTime format:'%s'" % startDateTime)
        # os._exit(1)

        # processing level/sensor type
        sensorOK = False
        level0HasFootprint = False
        if self.debug != 0:
            print((" TYPECODE:'%s'; 1: '%s'" % (typecode, typecode[0:1])))
            print((" TYPECODE:'%s'; 2: '%s'" % (typecode, typecode[0:2])))
            print((" TYPECODE:'%s'; -2: '%s'" % (typecode, typecode[-2:])))
            print((" TYPECODE:'%s'; -3: '%s'" % (typecode, typecode[-3:])))
        #
        if typecode[-2:] == '1B':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, typecode[-2:])
            print(" CASE 0")
        elif typecode[-2:] == '1A':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, typecode[-2:])
            print(" CASE 1")
        elif typecode[-2:] == '1b':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, typecode[-2:].upper())
            print(" CASE 2")
        elif typecode[-2:] == '1_':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, typecode[-2:])
            print(" CASE 3")
        elif typecode[-2:] == '2_':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, typecode[-2:-1])
            print(" CASE 4")
        elif typecode[-3:] == 'DS_':  # the simplified EoSip
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 00')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, 'other: None')
            print(" CASE 5")
            sensorOK = True
        elif typecode[0:2] == 'T_':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 00')
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, SENSOR_TYPE_TELEMETRY)
            print(" CASE 6")
            sensorOK = True
        # L0
        elif typecode[-2:] == '0_':
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: 00')
            # disable doi
            self.metadata.deleteMetadata(metadata.METADATA_DOI)
            # and last orbit number
            self.metadata.deleteMetadata(metadata.METADATA_LAST_ORBIT)
            print(" CASE 7")
            # if typecode != 'AUX_NOM_0_':
            self.isLevel0 = True
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, 'other: %s' % typecode[-2:])
            print(" CASE 8")

        if 1 == 1 or self.debug != 0:
            print(("processing level:'%s'" % (self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL))))

        # os._exit(1)

        #
        # NEW: footprint has been changed in groundTrack local attribute
        #
        if typecode in FOOTPRINT_PRODUCTS:
            self.hasFootprint = True
        else:
            self.hasFootprint = False

        ## L0: have footprint
        if self.isLevel0:
            # L0 acquisition center
            self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, L0_DEFAULT_PROCESSING_CENTER)
            # GoceTool is ok: footprint for everybody
            self.hasFootprint = True
            print("### L0 product has footprint")
            processInfo.addLog(" ### L0 product has footprint")
            self.sanityCheckL0(processInfo)

        # os._exit(0)

        # instrument and source mapping
        # t_xxxxx are telemetry products, the famous 1200 types
        if typecode.startswith('T_'):
            self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, INSTRUMENT_SHORT_NAME_TLM)
            if not sensorOK:
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, SENSOR_TYPE_TELEMETRY)
            self.hasFootprint = False
        else:
            if l0Case:
                self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, SENSOR_TYPE_GRADIOMETER)
                self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, INSTRUMENT_SHORT_NAME_EGG)
            else:
                if not typecode in SENSOR_TYPE:
                    raise Exception('no instrument mapping for typecode:%s' % typecode)
                self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, SENSOR_SHORTNAME_SOURCE[typecode])
                if not sensorOK:
                    self.metadata.setMetadataPair(metadata.METADATA_SENSOR_TYPE, SENSOR_TYPE[typecode])

        # NEED ORBIT IN ANY CASE; for the filename
        # TEST ORBIT:
        # set orbit to 000000 if not present
        # print("######################### ORBIT:%s; type:%s" % (self.metadata.getMetadataValue(metadata.METADATA_ORBIT), type(self.metadata.getMetadataValue(metadata.METADATA_ORBIT))))
        if not self.metadata.valueExists(self.metadata.getMetadataValue(metadata.METADATA_ORBIT)):
            # raise Exception("NO ORBIT")
            aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Abs_Orbit')
            if not aValue is None:
                self.metadata.setMetadataPair(metadata.METADATA_ORBIT, aValue)
            else:
                # L0 products
                aValue = self.getXmlNodeValueAtPath('//Variable_Header/MPH/Abs_Orbit_Start')
                if not aValue is None:
                    self.metadata.setMetadataPair(metadata.METADATA_ORBIT, aValue)
                else:
                    raise Exception("NO ORBIT FOUND")

            # print("######################### ORBIT value non exists, set it to 000000")
            # processInfo.addLog("ORBIT value non exists, set it to 000000")
            # self.metadata.setMetadataPair(metadata.METADATA_ORBIT, '000000')

        if self.hasFootprint:
            # TEST LAST ORBIT:
            # set last orbit to orbit if not present
            # print("######################### LAST ORBIT:%s; type:%s" % (self.metadata.getMetadataValue(metadata.METADATA_LAST_ORBIT), type(self.metadata.getMetadataValue(metadata.METADATA_LAST_ORBIT))))
            if not self.metadata.valueExists(self.metadata.getMetadataValue(metadata.METADATA_LAST_ORBIT)):
                print("######################### LAST ORBIT value non exists, set it to ORBIT")
                processInfo.addLog("LAST ORBIT value non exists, set it to ORBIT")
                self.metadata.setMetadataPair(metadata.METADATA_LAST_ORBIT,
                                              self.metadata.getMetadataValue(metadata.METADATA_ORBIT))

            self.metadata.setMetadataPair("HAS_FOOTPRINT", 'YES')

            # equator longitude
            if not self.isLevel0:
                tmp = self.metadata.getMetadataValue('Equator_Cross_Long')
                if not self.metadata.valueExists(tmp):
                    raise Exception("'Equator_Cross_Long' node not found in src product")
                self.metadata.setMetadataPair(metadata.METADATA_ASCENDING_NODE_LONGITUDE, float(tmp) / 1000000)

            #
            pstart = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
            pstop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME)
            otime = self.metadata.getMetadataValue('State_Vector_Time')

            oorbit = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
            #
            X_Position = self.metadata.getMetadataValue('X_Position')
            Y_Position = self.metadata.getMetadataValue('Y_Position')
            Z_Position = self.metadata.getMetadataValue('Z_Position')
            X_Velocity = self.metadata.getMetadataValue('X_Velocity')
            Y_Velocity = self.metadata.getMetadataValue('Y_Velocity')
            Z_Velocity = self.metadata.getMetadataValue('Z_Velocity')

            # command = '%s UTC=%s UTC=%s %s %s ' \
            #                '%s %s %s ' \
            #                '%s %s %s ' \
            #                '%s' % (self.goceToolAppExe, pstart, pstop, otime, oorbit ,
            #                                X_Position, Y_Position, Z_Position,
            #                                X_Velocity, Y_Velocity, Z_Velocity,
            #                                durationSecs/60)

            command = '%s UTC=%s UTC=%s %s' % (self.goceToolAppExe, pstart, pstop, durationSecs / 60)

            self.metadata.setMetadataPair("COMMAND_goceTool_normal", command)
            processInfo.addLog("COMMAND_goceTool_normal=%s" % command)

            commandFile = "%s/command_goceTool_normal.sh" % processInfo.workFolder
            fd = open(commandFile, 'w')
            fd.write(command)
            fd.close()

            # launch the goceTool script:
            command = "/bin/bash -f %s 2>&1 | tee %s/goceTool_normal.stdout" % (commandFile, processInfo.workFolder)

            try:
                if self.debug != 0:
                    print("COMAND_goceTool_normal=%s" % command)
                retval, out = osPlatform.runCommand(command, useShell=True)
                if retval != 0:
                    raise Exception("Error goceTool, exit code:%s; %s" % (retval, out))
                footprint = out.strip().split('\n')[-1]
                # wrap longitude
                bim = BrowseImage()
                bim.setFootprint(footprint)
                footprint = bim.footprint
                if self.debug != 0:
                    print("FOOTPRINT=%s" % footprint)
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
                processInfo.addLog(' #### FOOPRINT=%s' % footprint)

            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" ERROR running goceTool normal:%s %s" % (exc_type, exc_obj))
                traceback.print_exc(file=sys.stdout)
                raise Exception(" ERROR running goceTool normal:%s %s" % (exc_type, exc_obj))

            # os._exit(1)
        else:
            self.metadata.setMetadataPair("HAS_FOOTPRINT", 'NO')
            processInfo.addLog(' #### FOOPRINT= has no footprint !!')

        # local attributes
        # phase
        # start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        # special datetime case
        if self.debug != 0:
            print((" ###################### 2 #      'UTC=%s'" % startDateTime))
            print((" ###################### 2 #  VS :'%s'" % DATE_5))
        if "UTC=%s" % startDateTime != "%s" % DATE_5:
            # secs = formatUtils.timeFromDatePatterm(start+"Z")
            secs = formatUtils.timeFromDatePatterm(startDateTime, DEFAULT_DATE_PATTERN)
            # self.metadata.addLocalAttribute("missionPhase", self.metadata.getMetadataValue(metadata.METADATA_PHASE))
            secsLimit1 = formatUtils.timeFromDatePatterm(DATE_COMMISSIONNING_LIMIT)
            secsLimit2 = formatUtils.timeFromDatePatterm(DATE_ROUTINE_LIMIT)
            if secs < secsLimit1:
                self.metadata.setMetadataPair(metadata.METADATA_PHASE, PHASE_COMMISIONNING)
            elif secs < secsLimit2:
                self.metadata.setMetadataPair(metadata.METADATA_PHASE, PHASE_ROUTINE)
            else:
                self.metadata.setMetadataPair(metadata.METADATA_PHASE, PHASE_DE_ORBITING)
        else:
            self.metadata.setMetadataPair(metadata.METADATA_PHASE, PHASE_ROUTINE)

        # use collection name as parentIdentifier
        self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, collectionName)

        self.sanityCheck(processInfo)

    #
    # run the goce tool with start time
    # get ANX time + ANX longitude from goce tool
    # for level 0
    #
    def runGoceToolAnx(self, processInfo):
        pstartMicrosec = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME_MICROSEC)
        command = '%s UTC=%s\n' % (self.goceToolAppExe, pstartMicrosec)

        self.metadata.setMetadataPair("COMMAND_goceTool_ANX_time", command)
        processInfo.addLog("COMMAND_goceTool_ANX_time=%s" % command)

        commandFile = "%s/command_goceTool_ANX_time.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(command)
        fd.close()

        # launch the goceTool script:
        command = "/bin/bash -f %s | tee %s/goceTool_ANX_time.stdout" % (commandFile, processInfo.workFolder)

        anx_time = None
        try:
            if self.debug != 0:
                print("COMMAND_goceTool_ANX_time=%s" % command)
            retval, out = osPlatform.runCommand(command, useShell=True)
            if retval != 0:
                raise Exception("Error goceTool, exit code:%s; %s" % (retval, out))
            lines = out.strip().split('\n')
            if not lines[-2].startswith("ANX Time: "):
                raise Exception("GoceTool return unexpected ANX Time line:%s" % lines[-2])
            if not lines[-1].startswith("ANX Longitude: "):
                raise Exception("GoceTool return unexpected ANX Longitude line:%s" % lines[-1])
            anx_time = lines[-2].split(': ')[1]
            anx_long = lines[-1].split(': ')[1]

            # lon > 180 wrap
            if float(anx_long) > 180.0:
                old = anx_long
                anx_long = "%s" % (float(anx_long) - 360.0)
                if self.debug != 0:
                    print((" ### wrap longitude from %s to %s" % (old, anx_long)))

            # 3 digit for msec
            pos = anx_time.find('.')
            if pos > 0:
                anx_time = anx_time[0:pos + 4]

            if self.debug != 0:
                print(" ######################################## out:%s" % out)
                print(" ######################################## anx_time:%s" % anx_time)
                print(" ######################################## anx_long:%s" % anx_long)
                # os._exit(1)
            return "%sZ" % anx_time, anx_long

        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" ERROR running goceTool ANX time:%s %s" % (exc_type, exc_obj))
            traceback.print_exc(file=sys.stdout)
            raise Exception(" ERROR running goceTool ANX time:%s %s" % (exc_type, exc_obj))

    #
    # get alternate metadata file, to extract other info
    # Ex: .DBL file from .HDR filename
    #
    def getAlternateMetadata(self):
        tar = tarfile.open(self.path, 'r')
        n = 0
        for tarinfo in tar:
            n = n + 1
            name = tarinfo.name
            if self.debug:
                print("  getAlternateMetadata: test tar content[%d]:'%s'" % (n, name))

            if name.find(HDR_SUFFIX) >= 0:
                fd = tar.extractfile(tarinfo.name.replace(".HDR", ".DBL"))
                self.alternateMatadata = fd.read()
                fd.close()
                print("   alternateMatadata length:%s" % len(self.alternateMatadata))

        if self.alternateMatadata is None:
            raise Exception("cannot find alternate metadata file from:%s/%s" % (self.path, ".HDR -> .DBL"))

        tar.close()

    #
    #
    #
    def getEquatorCrossingLonFromAlternateFile(self):
        if self.alternateMatadata is None:
            self.getAlternateMetadata()

        equatorCrossingLon = None
        # like EQUATOR_CROSS_LONG=+0165023241<10-6degE>
        toks = self.alternateMatadata.split('\n')
        num = 0
        for line in toks:
            if line.startswith('DS_NAME='):
                break
            line = line.strip()
            if self.debug != 0:
                print((" test line[%s]:'%s'" % (num, line)))
            if line.startswith('EQUATOR_CROSS_LONG'):
                if self.debug != 0:
                    print((" #### getEquatorCrossingLonFromAlternateFile found STATE_VECTOR_TIME:%s" % line))
                line = line.replace('EQUATOR_CROSS_LONG=', '')
                equatorCrossingLon = line
                if self.debug != 0:
                    print(("#### equatorCrossingLon:%s" % equatorCrossingLon))
                break

        if equatorCrossingLon is None:
            raise Exception("getEquatorCrossingLonFromAlternateFile didn't find equator crossing lon info")

        # os._exit(1)
        return equatorCrossingLon

    #
    #
    #
    def getEquatorCrossingTimeFromAlternateFile(self):
        if self.alternateMatadata is None:
            self.getAlternateMetadata()

        equatorCrossingTime = None
        # like EQUATOR_CROSS_TIME_UTC="04-NOV-2013 08:35:57.030739"
        toks = self.alternateMatadata.split('\n')
        num = 0
        for line in toks:
            line = line.strip()
            if line.startswith('DS_NAME='):
                break
            if self.debug != 0:
                print((" test line[%s]:'%s'" % (num, line)))
            if line.startswith('EQUATOR_CROSS_TIME_UTC'):
                if self.debug != 0:
                    print((" #### getEquatorCrossingTimeFromAlternateFile found EQUATOR_CROSS_TIME_UTC:%s" % line))
                line = line.replace('EQUATOR_CROSS_TIME_UTC=', '').replace('"', '')
                toks = line.split(' ')
                month = formatUtils.getMonth2DigitFromMonthString(toks[0].split('-')[1])
                if self.debug != 0:
                    "month:%s" % month
                year = toks[0].split('-')[2]
                if self.debug != 0:
                    print("year:%s" % year)
                day = toks[0].split('-')[0]
                time = toks[1]
                pos = time.find('.')
                if pos > 0:
                    time = time[0:pos + 4]

                equatorCrossingTime = "%s-%s-%sT%sZ" % (year, month, day, time)
                if self.debug != 0:
                    print(("#### equatorCrossingTime:%s" % equatorCrossingTime))
                break
            num += 1

        if equatorCrossingTime is None:
            # raise Exception("getEquatorCrossingTimeFromAlternateFile didn't find equator crossing time info")
            return None

        # os._exit(1)
        return equatorCrossingTime

    #
    #
    #
    def getStateVectorTimeFromAlternateFile(self):
        if self.alternateMatadata is None:
            self.getAlternateMetadata()

        stateVectorTime = None
        # like STATE_VECTOR_TIME="18-MAR-2009 05:10:50.993935"
        toks = self.alternateMatadata.split('\n')
        num = 0
        for line in toks:
            line = line.strip()
            if line.startswith('DS_NAME='):
                break
            if self.debug != 0:
                print((" test line[%s]:'%s'" % (num, line)))
            if line.startswith('STATE_VECTOR_TIME'):
                if self.debug != 0:
                    print((" #### getStateVectorTimeFromAlternateFile found STATE_VECTOR_TIME:%s" % line))
                line = line.replace('STATE_VECTOR_TIME=', '').replace('"', '')
                toks = line.split(' ')
                month = formatUtils.getMonth2DigitFromMonthString(toks[0].split('-')[1])
                if self.debug != 0:
                    print("month:%s" % month)
                year = toks[0].split('-')[2]
                if self.debug != 0:
                    print("year:%s" % year)
                day = toks[0].split('-')[0]
                time = toks[1]

                stateVectorTime = "%s-%s-%sT%sZ" % (year, month, day, time)
                if self.debug != 0:
                    print(("#### stateVectorTime:%s" % stateVectorTime))
                break
            num += 1

        if stateVectorTime is None:
            raise Exception("getStateVectorTimeFromAlternateFile didn't find state vector time info")

        # os._exit(1)
        return stateVectorTime

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
        pass

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

    #
    # GPS is from 1960-06-01
    # format like: 1005000553.299677000
    #
    def gpsTimeToUtc(self, gpsEpochStr):
        gpsMicro = gpsEpochStr.split('.')[1][0:6]
        gpsMicro = int(gpsMicro)
        gpsSec = gpsEpochStr.split('.')[0]
        gpsSec = int(gpsSec)
        print((" gpsTimeToUtc: sec=%s; msec=%s" % (gpsSec, gpsMicro)))
        sec = int(gpsSec) - 15
        if sec >= 1025132400:
            sec -= 1

        initTime = formatUtils.timeFromDatePatterm('1980-01-06T00:00:00Z')
        d2 = initTime + timedelta(seconds=sec, microseconds=gpsMicro)
        timeStr = "%sZ" % d2.strftime('%Y-%m-%dT%H:%M:%S.%f')[0:-3]
        print((" gpsTimeToUtc: %s -> %s" % (gpsEpochStr, timeStr)))
        return timeStr
