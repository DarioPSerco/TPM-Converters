# -*- coding: cp1252 -*-
#
# This class represents a worldview directory product
#
import os
import tarfile
from pathlib import Path
from subprocess import call
from typing import Dict

from eoSip_converter.esaProducts import browse_metadata
import eoSip_converter.imageUtil as imageUtil
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.esaProducts import formatUtils
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.sectionIndentedDocument import SectionDocument
from eoSip_converter.esaProducts.product_directory import Product_Directory
from xml_nodes import rep_footprint


__version__ = '1.0.4'


class Product_Terrasar_x(Product_Directory):

    # XML mapping for metadata extraction
    xmlMapping: Dict[str, str] = {
        metadata.METADATA_START_DATE: 'temporalCoverage/startTime',
        metadata.METADATA_STOP_DATE: 'temporalCoverage/stopTime',
        metadata.METADATA_PROCESSING_TIME: 'creation/time',
        'productVariant': 'keys/feature*@key==productVariant',
        metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'feature/feature*@key==imagingMode',
        metadata.METADATA_ANTENNA_LOOK_DIRECTION: 'feature/feature*@key==antennaLookDirection',
        metadata.METADATA_POLARISATION_MODE: 'feature/feature*@key==polarisationMode',
        metadata.METADATA_POLARISATION_CHANNELS: 'feature/feature*@key==polarisationChannels',
    }

    # Additional XML mapping
    xmlMapping_bis: Dict[str, str] = {
        metadata.METADATA_ORBIT: 'productInfo/missionInfo/absOrbit',
        metadata.METADATA_ORBIT_DIRECTION: 'productInfo/missionInfo/orbitDirection',
        metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: 'productInfo/sceneInfo/sceneCenterCoord/incidenceAngle',  # Added mapping
    }

    # Mapping for secondary metadata extraction
    mapping2: Dict[str, str] = {
        metadata.METADATA_FOOTPRINT: '*<boundingPolygon>|2,3,7,8,12,13,17,18,2,3',
        'delta_lat': '*<boundingPolygon>|2,7',
        'delta_utc': '*<boundingPolygon>|4,9',
    }

    # Constants for metadata processing
    METADATA_SUFIX = 'iif.xml'
    PREVIEW_NAME = 'BROWSE.tif'
    REF_TYPECODES = ['SAR_HS_EEC', 'SAR_HS_GEC', 'SAR_HS_MGD', 'SAR_HS_SSC', 'SAR_SC_EEC', 'SAR_SC_GEC',
                     'SAR_SC_MGD', 'SAR_SC_SSC', 'SAR_SL_EEC', 'SAR_SL_GEC', 'SAR_SL_MGD', 'SAR_SL_SSC',
                     'SAR_SM_EEC', 'SAR_SM_GEC', 'SAR_SM_MGD', 'SAR_SM_SSC', 'SAR_ST_EEC', 'SAR_ST_GEC',
                     'SAR_ST_MGD', 'SAR_ST_SSC', 'SAR_WS_EEC', 'SAR_WS_GEC', 'SAR_WS_MGD', 'SAR_WS_SSC']

    # Possible reference polarization as per EoSip table 3.3
    REF_POLARIZATIONS_LUT = ['ST_S_HH', 'ST_S_VV', 'HS_S_HH', 'HS_S_VV', 'HS_D_HH, VV',
                             'SL_S_HH', 'SL_S_VV', 'SL_D_HH, VV', 'SM_S_HH', 'SM_S_VV',
                             'SM_D_HH, VV', 'SM_D_HH, HV', 'SM_D_VV, VH', 'SM_T_HH, VV',
                             'SM_Q_HH, HV, VH, VV', 'SC_S_HH', 'SC_S_VV', 'WC_S_HH',
                             'WC_S_VV', 'WC_S_HV', 'WC_S_VH']

    # Bounding box flag types
    BOUNDING_BOX_FLAG = ['SAR_HS_EEC', 'SAR_HS_GEC', 'SAR_SC_EEC', 'SAR_SC_GEC', 'SAR_SL_EEC', 'SAR_SL_GEC',
                         'SAR_SM_EEC', 'SAR_SM_GEC', 'SAR_ST_EEC', 'SAR_ST_GEC', 'SAR_WS_EEC', 'SAR_WS_GEC']

    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        self.metContentPath = None
        self.metContentName = None
        self.metContent = None
        # Secondary metadata
        self.metContentName_bis = None
        self.metContent_bis = None
        # Preview content
        self.previewContentName = None
        self.previewPath = None
        if self.debug != 0:
            print(" init class Product_Terrasar_x")

    # Called at the end of doOneProduct, before index/shopcart creation
    def afterProductDone(self):
        pass

    # Read metadata file
    def getMetadataInfo(self):
        pass

    # Generate browse images
    def makeBrowses(self, processInfo):
        if self.debug != 0:
            print(" makeBrowses")
        n = 0
        anEosip = processInfo.destProduct

        # They can be no browse
        if self.previewContentName is not None:
            browseName = processInfo.destProduct.getSipProductName()
            browseSrcPath = self.previewPath
            browseDestPath = "%s/%s.BI.JPG" % (processInfo.workFolder, browseName)

            if 1 == 2:  # Disabled: want non-transparent PNG. NO: want JPG
                browseDestPathRaw = "%s/%s.BI.PNG_raw" % (processInfo.workFolder, browseName)
                # Remove black filling area from PNG using stretcherAppExe
                imageUtil.makeBrowse('PNG', browseSrcPath, browseDestPathRaw)
                command = "%s -transparent %s %s 0xff000000" % (self.stretcherAppExe, browseDestPathRaw, browseDestPath)
                commandFile = "%s/command_browse.sh" % (processInfo.workFolder)
                fd = open(commandFile, 'w')
                fd.write(command)
                fd.close()

                # Launch the main make_browse script
                command = "/bin/sh -f %s" % (commandFile)
                retval = call(command, shell=True)
                if self.debug:
                    print("  external make browse exit code:%s" % retval)
                if retval != 0:
                    raise Exception("Error generating browse, exit coded:%s" % retval)
            else:
                imageUtil.makeBrowse('JPG', browseSrcPath, browseDestPath)

            anEosip.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  browse image[%s] added: name=%s; path=%s" % (n, browseName, browseDestPath))
            # Set AM time if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)

            # Create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[browseDestPath]
            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            if self.debug != 0:
                print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != 0:
                print("browseChoiceBlock:%s" % (browseChoiceBlock))
            bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

            # Set the browse type (if not default one) for the product metadata report BROWSES block if specified in configuration
            tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
            if tmp is not None:
                bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
            if tmp is not None:
                bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

            processInfo.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))

        else:
            raise Exception("no browse")

    # Extract the product to a specified folder
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist:%s" % folder)
        if self.debug != 0:
            print(" will extract directory product '%s' to path:%s" % (self.path, folder))

        if not os.path.exists(folder):
            raise Exception("destination folder does not exist:%s" % folder)
        if self.debug != 0:
            print(" will extract product to path:%s" % folder)

        with tarfile.open(self.path, 'r') as tar:
            # Keep list of content
            self.contentList = []
            # Extract everything
            self.EXTRACTED_PATH = folder
            tar.extractall(path=self.EXTRACTED_PATH)

        # Build content list
        n = 0
        for root, dirs, files in os.walk(self.EXTRACTED_PATH, topdown=False):
            root = Path(root)
            dirs = [Path(root / d) for d in dirs]
            files = [Path(root / f) for f in files]
            for file in files:
                if 'worlddem' in str(file).lower():
                    raise ValueError(f"WorldDEM product detected due to {'dir' if file.is_dir() else 'file'}, '{file.name}', in native")
                n += 1
                if self.debug != 0:
                    print("  test tar content[%d]:'%s'" % (n, file.name))

                # Keep metadata and preview data
                if file.name.endswith(self.PREVIEW_NAME):  # Browse image
                    self.previewContentName = file.name
                    if self.debug != 0:
                        print("   previewContentName: %s" % file.name)
                    self.previewPath = os.path.join(root, file.name)

                # Metadata
                elif file.name.lower().find(self.METADATA_SUFIX) >= 0:
                    self.metContentName = file.name
                    self.metContentPath = file

                    if self.debug != 0:
                        print("   metContentName:%s" % file.name)

                    with open(file) as fd:
                        self.metContent = fd.read()
                    print("   metContent length:%s" % len(self.metContent))

                # Secondary metadata
                elif file.suffix.lower() == '.xml' and file.stem == root.name:
                    self.metContentName_bis = file.name

                    with open(os.path.join(root, file.name)) as fd:
                        self.metContent_bis = fd.read()

                    print("   metContent_bis length:%s" % len(self.metContent_bis))

                # relPath = file[len(self.EXTRACTED_PATH) + 1:]
                relPath = file.relative_to(self.EXTRACTED_PATH)
                print("   content[%s] workfolder relative path:%s" % (n, relPath))
                self.contentList.append(relPath)

    # Updated XML metadata extraction
    def xmlExtract(self, xmlData, aMetadata, xmlMapping) -> int:
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)

        helper.setData(xmlData)
        helper.parseData()

        # Get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in xmlMapping:
            print("\n\nmetadata extract field:%s" % field)
            multiple = False
            attr = None
            aPath = None
            aValue = None
            if xmlMapping[field].find("@") >= 0:
                attr = xmlMapping[field].split('@')[1]
                aPath = xmlMapping[field].split('@')[0]
                if aPath.endswith('*'):
                    multiple = True
                    aPath = aPath[0:-1]
                    print(" -> multiple used on path:%s" % aPath)
            else:
                attr = None
                aPath = xmlMapping[field]

            if not multiple:
                aNode = helper.getFirstNodeByPath(None, aPath, None)
                if aNode is None:
                    aValue = None
                else:
                    if attr is None:  # Return NODE TEXT
                        aValue = helper.getNodeText(aNode)
                    else:  # Return attribute TEXT
                        aValue = helper.getNodeAttributeText(aNode, attr)

                if self.debug != 0:
                    print("  --> metadata[%s]: %s=%s" % (num_added, field, aValue))
                aMetadata.setMetadataPair(field, aValue)
                num_added = num_added + 1
            else:  # Will return NODE TEXT
                aList = []
                helper.getNodeByPath(None, aPath, attr, aList)
                print(" -> multiple; list of node found:%s" % len(aList))
                if len(aList) > 0:
                    for aNode in aList:
                        aValue = helper.getNodeText(aNode)
                        if self.debug != 0:
                            print("  --> metadata multiple[%s]: %s=%s" % (num_added, field, aValue))
                        aMetadata.setMetadataPair(field, aValue)
                        num_added = num_added + 1

        return num_added

    # Extract metadata
    def extractMetadata(self, met=None):
        if met is None:
            raise Exception("metadata is None")

        self.metadata = met

        # Use what contains the metadata file
        if len(self.metContent) == 0:
            raise Exception("no metadata to be parsed")

        # Source size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # First phase
        num_added = self.xmlExtract(self.metContent, met, self.xmlMapping)
        # Add bis to get orbit info
        num_added += self.xmlExtract(self.metContent_bis, met, self.xmlMapping_bis)

        # Extract the scene center incidence angle
        ##scene_center_angle = self.extractSceneCenterIncidenceAngle()
        ##met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, scene_center_angle)
        incidenceAngle = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE)
        print("Incidence angle is: ", incidenceAngle)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, format(float(incidenceAngle), '.2f'))

        # Second phase
        num_added += self.extractMetadata02()
        print("metadata extracted: %s" % num_added)

    # Extract the scene center incidence angle
    def extractSceneCenterIncidenceAngle(self):
        helper = xmlHelper.XmlHelper()
        helper.setData(self.metContent)
        helper.parseData()

        # Extract incidence angle from sceneCenterCoord
        scene_center_node = helper.getFirstNodeByPath(None, "sceneInfo/sceneCenterCoord", None)
        if scene_center_node is not None:
            incidence_angle_node = helper.getFirstNodeByPath(scene_center_node, "incidenceAngle", None)
            if incidence_angle_node is not None:
                incidence_angle = helper.getNodeText(incidence_angle_node)
                if incidence_angle:
                    try:
                        incidence_angle_value = float(incidence_angle)
                        print("Extracted incidence angle: %s" % incidence_angle_value)
                        return incidence_angle_value
                    except ValueError:
                        print("Error converting incidence angle to float: %s" % incidence_angle)
                        return "CONVERTER_UNKNOWN"

        print("Scene Center Incidence Angle: CONVERTER_UNKNOWN")
        return "CONVERTER_UNKNOWN"

    # Use a SectionDocument to extract list of XML node values
    def extractMetadata02(self):
        sectionDoc = SectionDocument()
        sectionDoc.setContent(self.metContent)
        sectionDoc.debug = 1

        num_added = 0

        for field in self.mapping2:
            rule = self.mapping2[field]
            aValue = None
            if self.debug == 0:
                print(" ##### Handle metadata2:%s" % field)

            toks = rule.split('|')
            if len(toks) != 2:
                raise Exception("Malformed report metadata rule:%s" % field)
            # Wildcard used?
            if toks[0][-1] == '*':  # Wildcard at end
                line = sectionDoc.getSectionLine(toks[0])
                # Line offset(s) list are in second token
                offsets = toks[1].split(',')
                aValue = ''
                for offset in offsets:
                    nLine = line + int(offset)
                    if len(aValue) > 0:
                        aValue = "%s " % aValue
                    aValue = "%s%s" % (aValue, sectionDoc.getLineValugetMetadataValue(nLine, None, separator='>'))
                if self.debug == 0:
                    print("  report metadata:%s='%s'" % (field, aValue))
            elif toks[0][0] == '*':  # Wildcard at start
                line = sectionDoc.getSectionLine(toks[0])
                # Line offset(s) list are in second token
                offsets = toks[1].split(',')
                aValue = ''
                for offset in offsets:
                    nLine = line + int(offset)
                    if len(aValue) > 0:
                        aValue = "%s " % aValue
                    aValue = "%s%s" % (aValue, sectionDoc.getLineValue(nLine, None, separator='>'))
                    pos = aValue.index('<')
                    aValue = aValue[0:pos]
                if self.debug == 0:
                    print("  report metadata:%s='%s'" % (field, aValue))
            else:
                aValue = sectionDoc.getValue(toks[0], toks[1])
            # Suppress initial space if any
            if aValue[0] == ' ':
                aValue = aValue[1:]
            if self.debug != 0:
                print("  --> metadata 1[%s]: %s=%s" % (num_added, field, aValue))
            self.metadata.setMetadataPair(field, aValue)
            num_added = num_added + 1

        return num_added

    # Refine the metadata
    def refineMetadata(self):

        # Defining METADATA_START_DATE, METADATA_START_TIME
        # Value is like 2017-09-12T10:45:23.117
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        start_tokens = start.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start_tokens[1].split('.')[0])

        # Defining METADATA_STOP_DATE, METADATA_STOP_TIME
        stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)
        stop_tokens = stop.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop_tokens[1].split('.')[0])

        # Build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        browseIm = BrowseImage()
        # Will wrap longitude if needed
        browseIm.setFootprint(self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        wrappedFootprint = browseIm.getFootprint()
        footprint_str = ' '.join([f"{float(c.strip()):.4f}" for c in wrappedFootprint.split()])
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint_str)
        if browseIm.footptintChanged():
            self.metadata.setMetadataPair("ORIGINAL_FOOTPRINT", browseIm.origFootprint)
        browseIm.calculateBoondingBox()
        clat, clon = browseIm.calculateCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%.4f %.4f" % (float(clat), float(clon)))
        self.boundingBox = browseIm.boondingBox

        flat = float(clat)
        flon = float(clon)
        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
        if flat < 0:
            flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)

        # Get info from folder name, use parent of iif file
        iifParent = os.path.dirname(self.metContentPath)
        print("########### iifParent=%s" % iifParent)
        # Like TDX1_SAR__SSC______ST_S_SRA_20170621T153838_20170621T153838
        produName = os.path.split(iifParent)[-1]
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SOURCE, produName)
        self.metadata.setMetadataPair(metadata.METADATA_IMAGING_MODE, produName[19:21])
        self.metadata.setMetadataPair(metadata.METADATA_POLARISATION_MODE, produName[22])
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_CLASS, produName[10:13])
        self.metadata.setMetadataPair('resolutionVariant', produName[14:18])

        # Define ascending or not
        tmp = self.metadata.getMetadataValue('delta_lat')
        dlat = float(tmp.split(' ')[1]) - float(tmp.split(' ')[0])
        print("########### dlat=%s" % dlat)
        tmp1 = self.metadata.getMetadataValue('delta_utc')
        utc1 = tmp1.split(' ')[0]
        msec1 = int(utc1[-3:])
        utc2 = tmp1.split(' ')[1]
        msec2 = int(utc2[-3:])
        print("########### utc1=%s; msec1=%s; utc2=%s; msec2=%s" % (utc1[0:-4] + 'Z', msec1, utc2[0:-4] + 'Z', msec2))
        deltaMsec = formatUtils.dateDiffmsec(utc1[0:-4] + 'Z', msec1, utc2[0:-4] + 'Z', msec2)
        print("########### deltaMsec=%s" % deltaMsec)
        self.metadata.setMetadataPair('deltaMsec', deltaMsec)
        self.metadata.setMetadataPair('dlat', dlat)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        print('############### ORBIT:%s' % tmp)

        if tmp is None:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, 0)
            if deltaMsec >= 0:
                if dlat >= 0:
                    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'ASCENDING')
                else:
                    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'DESCENDING')
            else:
                if dlat >= 0:
                    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'DESCENDING')
                else:
                    self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'ASCENDING')

        typecode = self.buildTypeCode()

        # Some typecode have no boundingBox and other fields
        if typecode in self.BOUNDING_BOX_FLAG:
            # Bounding box
            bbox_str = ' '.join([f"{float(c.strip()):.4f}" for c in self.boundingBox.split()])
            self.metadata.addLocalAttribute("boundingBox", bbox_str)
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, self.boundingBox)
            print(" ######################## typecode %s in BOUNDING_BOX_FLAG map" % typecode)
            self.useBbox = True
        else:
            print(" ######################## typecode %s NOT in BOUNDING_BOX_FLAG map" % typecode)
            self.useBbox = False

        tmp = self.metadata.getMetadataValue(metadata.METADATA_ANTENNA_LOOK_DIRECTION)
        if tmp == 'R':
            self.metadata.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, 'RIGHT')
        elif tmp == 'L':
            self.metadata.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, 'LEFT')
        else:
            self.metadata.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, 'UNDEFINED')

        # Perform some check
        IM = self.metadata.getMetadataValue(metadata.METADATA_IMAGING_MODE)
        PC = self.metadata.getMetadataValue(metadata.METADATA_POLARISATION_CHANNELS)
        if PC.find('/') > 0:
            PC = PC.replace('/', ', ')
            self.metadata.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, PC)
        PM = self.metadata.getMetadataValue(metadata.METADATA_POLARISATION_MODE)
        # Check against possible reference polarization as per EoSip table 3.3. syntax: ImagingMode_PolarizationMode_PolarizationChannel
        if "%s_%s_%s" % (IM, PM, PC) not in self.REF_POLARIZATIONS_LUT:
            raise Exception("polarization value unknown:%s" % "%s_%s_%s" % (IM, PM, PC))

    def buildTypeCode(self):
        typeCode = "SAR_%s_%s" % (
            self.metadata.getMetadataValue(metadata.METADATA_IMAGING_MODE), self.metadata.getMetadataValue(
                metadata.METADATA_PRODUCT_CLASS))
        if typeCode not in self.REF_TYPECODES:
            raise Exception("Invalid typeCode:%s" % typeCode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typeCode)
        return typeCode

    # Extract quality
    def extractQuality(self, helper):
        pass

    # Extract the footprint posList point, ccw, lat lon
    def extractFootprint(self, helper):
        pass

    def toString(self):
        res = "path:%s" % self.path
        return res

    def dump(self):
        res = "path:%s" % self.path
        print(res)

