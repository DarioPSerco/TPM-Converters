"""Methods used to build the eoSip xml message
used by sipMessageBuilder class

Contains also the metadata_name to xml node mapping
"""
import sys
import traceback
from abc import ABCMeta, abstractmethod

import eoSip_converter.esaProducts.base_metadata as base_metadata
import eoSip_converter.esaProducts.browse_metadata as browse_metadata
import eoSip_converter.esaProducts.metadata as metadata

VALUE_OPTIONAL = base_metadata.VALUE_OPTIONAL
VALUE_CONDITIONS = base_metadata.VALUE_CONDITIONS
VALUE_UNKNOWN = base_metadata.VALUE_UNKNOWN
VALUE_NONE = base_metadata.VALUE_NONE
VALUE_NOT_PRESENT = base_metadata.VALUE_NOT_PRESENT

# mapping as used to construct the xml node representation
EOSIP_METADATA_MAPPING = {
    'acquisitionStation': metadata.METADATA_ACQUISITION_CENTER,
    'acquisitionDate': metadata.METADATA_ACQUISITION_DATE,
    'responsible': metadata.METADATA_RESPONSIBLE,
    'SIPCreator': metadata.METADATA_CREATOR,
    'SIPVersion': metadata.METADATA_SIP_VERSION,
    'SIPChangeLog': metadata.METADATA_SIP_CHANGE_LOG,
    'SIPSpecNameVersion': metadata.METADATA_SIP_SPEC_NAME_VERSION,
    'reportType': metadata.METADATA_REPORT_TYPE,
    'generationTime': metadata.METADATA_GENERATION_TIME,
    'gmlId': metadata.METADATA_IDENTIFIER,
    'identifier': metadata.METADATA_IDENTIFIER,
    'productType': metadata.METADATA_TYPECODE,
    'beginPositionDate': metadata.METADATA_START_DATE,
    'beginPositionTime': metadata.METADATA_START_TIME,
    'endPositionDate': metadata.METADATA_STOP_DATE,
    'endPositionTime': metadata.METADATA_STOP_TIME,
    'platformShortName': metadata.METADATA_PLATFORM,
    'platformSerialIdentifier': metadata.METADATA_PLATFORM_ID,
    'instrumentShortName': metadata.METADATA_INSTRUMENT,
    'instrumentDescription': metadata.METADATA_INSTRUMENT_DESCRIPTION,
    'sensorType': metadata.METADATA_SENSOR_TYPE,
    'operationalMode': metadata.METADATA_SENSOR_OPERATIONAL_MODE,
    'codeSpace_operationalMode': metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE,
    'resolution': metadata.METADATA_RESOLUTION,
    'resolutionUomAttr': metadata.METADATA_RESOLUTION_UNIT,
    'nativeProductFormat': metadata.METADATA_NATIVE_PRODUCT_FORMAT,
    'orbitNumber': metadata.METADATA_ORBIT,
    'lastOrbitNumber': metadata.METADATA_LAST_ORBIT,
    'orbitDirection': metadata.METADATA_ORBIT_DIRECTION,
    'wrsLongitudeGrid': metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED,
    'codeSpace_wrsLongitudeGrid': metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED,
    'wrsLatitudeGrid': metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED,
    'codeSpace_wrsLatitudeGrid': metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED,
    'ascendingNodedate': metadata.METADATA_ASCENDING_NODE_DATE,
    'ascendingNodeLongitude': metadata.METADATA_ASCENDING_NODE_LONGITUDE,
    'startTimeFromAscendingNode': metadata.METADATA_START_TIME_FROM_ASCENDING_NODE,
    'completionTimeFromAscendingNode': metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE,
    'illuminationElevationAngle': metadata.METADATA_SUN_ELEVATION,
    'illuminationAzimuthAngle': metadata.METADATA_SUN_AZIMUTH,
    'illuminationZenithAngle': metadata.METADATA_SUN_ZENITH,
    'instrumentElevationAngle': metadata.METADATA_INSTRUMENT_ELEVATION_ANGLE,
    'instrumentZenithAngle': metadata.METADATA_INSTRUMENT_ZENITH_ANGLE,
    'instrumentAzimuthAngle': metadata.METADATA_INSTRUMENT_AZIMUTH_ANGLE,
    'pitch': metadata.METADATA_PITCH,
    'yaw': metadata.METADATA_YAW,
    'roll': metadata.METADATA_ROLL,
    'incidenceAngle': metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE,
    'alongTrackIncidenceAngle': metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE,
    'acrossTrackIncidenceAngle': metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE,
    'productQualityStatus': metadata.METADATA_QUALITY_STATUS,
    'productQualityReportURL': metadata.METADATA_QUALITY_REPORT_URL,
    'productQualityDegradationTag': metadata.METADATA_QUALITY_DEGRADATION_TAG,
    'productSize': metadata.METADATA_PRODUCT_SIZE,
    'productSizeUomAttr': metadata.METADATA_PRODUCT_SIZE_UOM,
    'referenceSystemIdentifier': metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER,
    'href': metadata.METADATA_PRODUCTNAME,
    'timePosition': metadata.METADATA_TIME_POSITION,
    'cloudCoverPercentage': metadata.METADATA_CLOUD_COVERAGE,
    'status': metadata.METADATA_STATUS,
    'acquisitionType': metadata.METADATA_ACQUISITION_TYPE,
    'coordList': metadata.METADATA_FOOTPRINT,
    'numberOfNodes': 'BROWSE_METADATA_FOOTPRINT_NUMBER_NODES',
    'browseType': browse_metadata.BROWSE_METADATA_BROWSE_TYPE,
    'browsesType': metadata.METADATA_BROWSES_TYPE,
    'codeSpace_referenceSystemIdentifier': metadata.METADATA_CODESPACE_REFERENCE_SYSTEM,
    'browseImageType': browse_metadata.BROWSE_METADATA_IMAGE_TYPE,
    'browseIdentifier': browse_metadata.BROWSE_METADATA_FILENAME,
    'browseFileName': browse_metadata.BROWSE_METADATA_NAME,
    'BrowseRectCoordList': browse_metadata.BROWSE_METADATA_RECT_COORDLIST,
    'colRowList': metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL,
    'parentIdentifier': metadata.METADATA_PARENT_IDENTIFIER,
    'processingMode': metadata.METADATA_PROCESSING_MODE,
    'processingDate': metadata.METADATA_PROCESSING_TIME,
    'processingCenter': metadata.METADATA_PROCESSING_CENTER,
    'processorName': metadata.METADATA_SOFTWARE_NAME,
    'processorVersion': metadata.METADATA_SOFTWARE_VERSION,
    'processingLevel': metadata.METADATA_PROCESSING_LEVEL,
    'cycleNumber': metadata.METADATA_CYCLE,
    'relativePassNumber': metadata.METADATA_RELATIVE_ORBIT,
    'snowCoverPercentage': metadata.METADATA_SNOW_COVERAGE,
    'sceneCenter': metadata.METADATA_SCENE_CENTER,
    'productVersion': metadata.METADATA_PRODUCT_VERSION,
    'polarisationMode': metadata.METADATA_POLARISATION_MODE,
    'polarisationChannels': metadata.METADATA_POLARISATION_CHANNELS,
    'antennaLookDirection': metadata.METADATA_ANTENNA_LOOK_DIRECTION,
    'minimumIncidenceAngle': metadata.METADATA_ANTENNA_LOOK_DIRECTION,
    # v101 specific (cf v100)
    'SIPSoftwareName': metadata.METADATA_SIP_SOFTWARE_NAME,
    'SIPSoftwareVersion': metadata.METADATA_SIP_SOFTWARE_VERSION,
    'timeliness': metadata.METADATA_TIMELINESS,
    'codeSpace_timeliness': metadata.METADATA_CODESPACE_TIMELINESS,
    'doi': metadata.METADATA_DOI,
    # v200 specific (cf v100/v101)
    'codeSpace_processingCenter': metadata.METADATA_CODESPACE_PROCESSING_CENTER,
    'productQualityDegradationQuotationMode': metadata.METADATA_QUALITY_DEGRADATION_QUOTATION_MODE,
    'missionphase': metadata.METADATA_PHASE,
}

# the various eo typology supported. i.e. the namespace used in xml report files
TYPOLOGY_EOP = 0
TYPOLOGY_SAR = 1
TYPOLOGY_OPT = 2
TYPOLOGY_LMB = 3
TYPOLOGY_ALT = 4
TYPOLOGY_ATM = 5
TYPOLOGY_GIN = 6  # v200 specific
TYPOLOGY_LIST = [TYPOLOGY_EOP, TYPOLOGY_SAR, TYPOLOGY_OPT, TYPOLOGY_LMB, TYPOLOGY_ALT, TYPOLOGY_ATM, TYPOLOGY_GIN]
TYPOLOGY_REPRESENTATION_SUFFIX = ['EOP', 'SAR', 'OPT', 'LMB', 'ALT', 'ATM', 'GIN']
TYPOLOGY_REPRESENTATION = ['eop', 'sar', 'opt', 'lmb', 'alt', 'atm', 'gin']
TYPOLOGY_DEFAULT_REPRESENTATION = 'REPRESENTATION'


class SipBuilder(metaclass=ABCMeta):
    debug = 0
    debugUnused = False
    debugCondition = False

    def __init__(self):
        # the matadata to xml node mapping in use
        self.USED_METADATA_MAPPING = EOSIP_METADATA_MAPPING

    @abstractmethod
    def buildMessage(self, representation, metadata, currentTreePath):
        raise Exception("abstractmethod")

    # condition value is like:"FILLED__acquisitionStation"
    # where FILLED is the OPERATOR
    # and acquisitionStation is the mappiing name (present in the EOSIP_METADATA_MAPPING)
    #
    # TODO: change EOSIP_METADATA_MAPPING to self.USED_METADATA_MAPPING ??
    def checkConditions(self, metadata=None, condition=None):
        try:
            result = False
            pos = condition.find('__')
            operator = condition[0:pos]
            aliasName = condition[pos + 2:]
            if aliasName not in EOSIP_METADATA_MAPPING:
                raise Exception("condition has unknown mapping key:%s" % aliasName)
            metaName = EOSIP_METADATA_MAPPING[aliasName]
            if self.debug != 0 or self.debugCondition:
                print("################################## checkConditions: operator:'%s'  varname='%s'" % (
                operator, metaName))
            if metaName in metadata.dict:
                resolved = metadata.getMetadataValue(metaName)
                if self.debug != 0 or self.debugCondition:
                    print("################################## checkConditions: resolved==None: '%s'" % (
                                resolved == None))
                    print("################################## checkConditions: resolved='%s'" % resolved)
                if operator == "FILLED":
                    if resolved is not None and resolved != VALUE_NONE and resolved != VALUE_UNKNOWN and resolved != VALUE_NOT_PRESENT:
                        result = True
                else:
                    raise Exception("unknown condition operator:'%s'" % operator)
            else:
                if self.debug != 0 or self.debugCondition:
                    print("################################## checkConditions: metaName not in metadata:'%s'" % metaName)
            if self.debug != 0 or self.debugCondition:
                print("################################## checkConditions: returns:%s" % result)
            return result
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("################################## checkConditions: ERROR:%s  %s\n%s\n" % (
            exc_type, exc_obj, traceback.format_exc()))
            raise e

    # return a field name, from:
    # - field xml representation like: "<gml:orbitNumber>@orbitNumber@</gml:orbitNumber>" ==> gml:orbitNumber
    # - field xml representation like: "<opt:cloudCoverPercentage uom='%'>@cloudCoverPercentage@</opt:cloudCoverPercentage>" ==> opt:cloudCoverPercentage
    # - class name like: "eop_earthObservation" ==> eop:earthObservation
    def getFieldName(self, rep=None):
        if rep.strip()[0] == '<':
            pos = rep.find('>')
            if pos < 0:
                raise Exception("field is malformed: no end >:%s" % rep)
            rep = rep[1:pos]
            pos = rep.find(" ")
            if pos > 0:
                rep = rep[0:pos]
            return rep
        else:
            pos = rep.find('_')
            if pos < 0:
                raise Exception("field is malformed: no _ in class name:%s" % rep)
            return rep.replace('_', ':')

    # check if a field is in the xml used map
    # based on field path like: /rep:browseReport/rep_browse/rep:referenceSystemIdentifier=UNUSED
    def isFieldUsed(self, rep=None, metadata=None, path=None):
        if self.debug != 0 or self.debugUnused:
            print("### isFieldUsed: test rep:'%s' at path:'%s'" % (rep, path))
        if path[0] != '/':
            path = "/%s" % path

        # normalise path
        # replace path blocks like '/eop_Sensor@eop_sensor/...' with eop_Sensor
        # this is because of windows filename case problem, so workarround
        pos = path.find('@')
        pathOk = ''
        while pos > 0:
            # raise Exception("TEST @ in path")
            pathOk = pathOk + path[0:pos]
            if self.debug != 0 or self.debugUnused:
                print("### isFieldUsed: pathOk:'%s'" % pathOk)
            endPos = path.find('/')
            if endPos > 0:
                pos = path.find('@', endPos + 1)
                if self.debug != 0 or self.debugUnused:
                    print("### isFieldUsed: pathOk remain from pos:'%d'" % pos)
            else:
                pos = -1
                if self.debug != 0 or self.debugUnused != 0:
                    print("### isFieldUsed: pathOk end")

        if len(pathOk) == 0:
            pathOk = path

        if self.debug != 0 or self.debugUnused:
            print("### isFieldUsed: pathOk:'%s'" % pathOk)
        name = self.getFieldName(rep)
        # metDebug=metadata.DEBUG
        if self.debug != 0 or self.debugUnused:
            print("### isFieldUsed: name:'%s'" % name)
        res = metadata.isFieldUsed("%s/%s" % (pathOk, name), self.debugUnused)
        if self.debug != 0 or self.debugUnused:
            print("### isFieldUsed: returns:'%s'" % res)
        return res

    # resolve a field string, may contains varName or/and eval patterns
    def resolveField(self, name, metadata=None):
        # get normal mapping or altered one if any
        metaName = metadata.getMetadataMaping(name, self.USED_METADATA_MAPPING)
        # if self.USED_METADATA_MAPPING.has_key(name):
        if metaName != None:
            # metaName=self.USED_METADATA_MAPPING[name]
            if self.debug != 0:
                print(" resolveField: '%s' in metadata name:%s" % (name, metaName))
            try:
                resolved = metadata.getMetadataValue(metaName)
            except Exception as e:
                print(" Error:")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exc(file=sys.stdout)
                resolved = 'ERROR! %s; %s' % (exc_type, exc_obj)
            return resolved
        else:
            print("resolveField: no mapping for name:%s" % name)
            return VALUE_UNKNOWN

    # evaluate things like: $$self.getNextCounter()$$
    # in the context of the Metadata object
    def resolveEval(self, segment, met=None):
        pos = segment.find('$$')
        if pos >= 0:
            pos2 = pos
            n = 0
            result = ''
            while pos >= 0 and pos2 >= 0:
                if self.debug != 0:
                    print("### resolveEval: actual eval segment[%d]:'%s'" % (n, segment))
                pos2 = segment.find('$$', pos + 2)
                varName = segment[pos + 2:pos2]
                if self.debug != 0:
                    print("### resolveEval: eval[%d]:'%s'" % (n, varName))
                value = met.eval(varName)
                if self.debug != 0:
                    print("### resolveEval: eval:'%s'->'%s'" % (varName, value))
                result = "%s%s%s" % (result, segment[0:pos], value)
                segment = segment[pos2 + 2:]
                pos = segment.find('$$')
            result = "%s%s" % (result, segment)
            if self.debug != 0:
                print("### resolveEval: resolved eval:'%s'" % result)
            return result
        else:
            return segment

    # resolve variable inside @varName@
    # in the context of the Metadata object
    def resolveVarname(self, segment, met=None):
        pos = segment.find('@')
        if self.debug != 0:
            print("### resolveVarname: to be varName resolved:'%s'" % segment)
        pos2 = pos
        n = 0
        result = ''
        while pos >= 0 and pos2 >= 0:
            if self.debug != 0:
                print("### resolveVarname: actual varName segment[%d]:'%s'" % (n, segment))
            pos2 = segment.find('@', pos + 1)
            varName = segment[pos + 1:pos2]
            if self.debug != 0:
                print("### resolveVarname: resolve varname[%d]:'%s'" % (n, varName))
            value = self.resolveField(varName, met)
            if self.debug != 0:
                print("### resolveVarname: resolve varname:'%s'->'%s'" % (varName, value))
            result = "%s%s%s" % (result, segment[0:pos], value)
            segment = segment[pos2 + 1:]
            pos = segment.find('@')
        result = "%s%s" % (result, segment)
        if self.debug != 0:
            print("### resolveVarname: varName resolved:'%s'" % result)
        return result
