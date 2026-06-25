#
# This is a specialized class that ingest Goce dataset
#
# For dissemination project
#
# Lavaux Gilles
#
# 2019-05: V: 1.0.0
#
#
# Changes:
# -
#
#
import os
import shutil
import sys
import tarfile
import traceback
import zipfile
from io import StringIO
from pathlib import Path
from PIL import Image

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_goce, product_EOSIP
from eoSip_converter.esaProducts import metadata, browse_metadata
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts import data as esaProducts_data
from eoSip_converter.esaProducts.namingConvention_DDOT import NamingConvention_DDOT
from eoSip_converter.esaProducts.namingConvention_AsSource import (
    NamingConvention_AsSource,
)
import eoSip_converter.imageUtil as imageUtil
import eoSip_converter.xmlHelper as xmlHelper
from xml_nodes import rep_footprint

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = "Goce converter V:1.0.0 2019-05-21"

REF_NAME = (
    "GO1_CONS_EGG_NOM_1b_20130101T004443_20130101T021408_022231_0000_0002_v0100.SIP.ZIP"
)
REF_EO_NAME = "GO_CONS_EGG_NOM_1b_20130101T004443_20130101T021408_0002"


#
#
#
class ingester_goce(ingester.Ingester):

    #
    # load typecode<->DOI lut
    #
    def afterStarting(self, **kargs):
        # read collection name <-> type code map
        GOCE_COLLECTION_TYPECODE_LUT = None

        LUT_data_path = Path(esaProducts_data.__file__).parent / 'goce' / 'goce_collection_typecode_lut_table.dat'
        if not LUT_data_path.exists():
            raise Exception("can not find Goce DOI look up table at path: %s" % LUT_data_path)

        with open(LUT_data_path, "r") as fd:
            data = fd.read()
        exec(data)

        self.GOCE_COLLECTION_TYPECODE_LUT = GOCE_COLLECTION_TYPECODE_LUT
        self.TYPECODE_COLLECTION_LUT = {}
        for item in self.GOCE_COLLECTION_TYPECODE_LUT:
            aList = self.GOCE_COLLECTION_TYPECODE_LUT[item]
            for typecode in aList:
                self.TYPECODE_COLLECTION_LUT[typecode] = item

        # read DOI map
        GOCE_COLLECTION_DOI_LUT = None
        LUT_data_path = Path(esaProducts_data.__file__).parent / 'goce' / 'goce_collection_doi_lut_table.dat'
        if not LUT_data_path.exists():
            raise Exception("can not find Goce DOI look up table at path: %s" % LUT_data_path)

        with open(LUT_data_path, "r") as fd:
            data = fd.read()
        exec(data)

        self.GOCE_COLLECTION_DOI_LUT = GOCE_COLLECTION_DOI_LUT

    #
    #
    #
    def getVersionImpl(self):
        return VERSION

    #
    # config version is like: name_floatVersion
    #
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    #
    # called before doing the various reports
    # # change the mapping of href to METADATA_PACKAGENAME
    #
    def beforeReportsDone(self, processInfo):
        # keep some values
        self.keepInfo("hasFootprint", processInfo.srcProduct.hasFootprint)
        tmp = processInfo.destProduct.metadata.getMetadataValue(
            "NO_METADATA_PROCESSING_TIME"
        )
        if processInfo.destProduct.metadata.valueExists(tmp):
            self.keepInfo("NO_METADATA_PROCESSING_TIME", tmp)

        self.keepInfo(
            "xmlMappingNonDimap",
            processInfo.destProduct.metadata.getMetadataValue("xmlMappingNonDimap"),
        )
        self.keepInfo(
            "EarthExplorerFileVersion",
            processInfo.destProduct.metadata.getMetadataValue(
                "EarthExplorerFileVersion"
            ),
        )
        self.keepInfo(
            "groundTrack",
            processInfo.destProduct.metadata.getMetadataValue("groundTrack"),
        )
        self.keepInfo(
            metadata.METADATA_TYPECODE,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_TYPECODE
            ),
        )
        self.keepInfo(
            metadata.METADATA_FILE_TYPE,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_FILE_TYPE
            ),
        )

        self.keepInfo(
            metadata.METADATA_PROCESSING_CENTER,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_PROCESSING_CENTER
            ),
        )

        self.keepInfo(
            metadata.METADATA_PROCESSING_LEVEL,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_PROCESSING_LEVEL
            ),
        )

        self.keepInfo(
            metadata.METADATA_SOFTWARE_VERSION,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_SOFTWARE_VERSION
            ),
        )
        self.keepInfo(
            metadata.METADATA_PHASE,
            processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PHASE),
        )
        self.keepInfo(
            "EarthExplorerFileVersion",
            processInfo.destProduct.metadata.getMetadataValue(
                "EarthExplorerFileVersion"
            ),
        )

        self.keepInfo(
            metadata.METADATA_ASCENDING_NODE_LONGITUDE,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_ASCENDING_NODE_LONGITUDE
            ),
        )

        # L0 stuff:
        # self.keepInfo("level0HasFootprint", processInfo.srcProduct.level0HasFootprint)

        if not processInfo.srcProduct.hasFootprint:
            processInfo.destProduct.metadata.xmlNodeUsedMapping[
                "/gin:EarthObservation/om:featureOfInterest/gin:Footprint"
            ] = "UNUSED"
            processInfo.addLog(" ## SPEC 2.0 ## DISABLE gin_Footprint")
        else:
            processInfo.addLog(" ## SPEC 2.0 ## DONT DISABLE gin_Footprint")
            self.keepInfo(
                metadata.METADATA_FOOTPRINT,
                processInfo.destProduct.metadata.getMetadataValue(
                    metadata.METADATA_FOOTPRINT
                ),
            )

        procLevel = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_PROCESSING_LEVEL
        )
        if procLevel != "other: 00" and procLevel != "L0":
            processInfo.destProduct.metadata.xmlNodeUsedMapping[
                "/gin:EarthObservation/eop:metaDataProperty/gin:EarthObservationMetaData/eop:downlinkedTo"
            ] = "UNUSED"
            processInfo.addLog(
                " ## SPEC 2.0 ## DISABLE eop:downlinkedTo node because not level 0:'%s'"
                % procLevel
            )
        else:
            processInfo.addLog(
                " ## SPEC 2.0 ## DONT DISABLE eop:downlinkedTo node because level 0:'%s'"
                % procLevel
            )

        # upercase typecode
        processInfo.destProduct.metadata.setMetadataPair(
            metadata.METADATA_TYPECODE,
            processInfo.destProduct.metadata.getMetadataValue(
                metadata.METADATA_TYPECODE
            ).upper(),
        )

    #
    # called after having done the various reports
    #
    def beforeReportsDone_2_NOT_USED(self, processInfo):

        # build the EO zip package. content is in srcProduct.contentList
        newContentList = []
        n = 0
        zipFilePath = "%s/%s.%s" % (
            processInfo.workFolder,
            processInfo.destProduct.eoProductName,
            processInfo.destProduct.sipPackageExtension,
        )
        zipFilePathWithPart = "%s.part" % zipFilePath
        zipf = zipfile.ZipFile(zipFilePathWithPart, mode="w", allowZip64=True)
        if self.debug != 0:
            print("\n\n @@@@@ EO tmp zip file is:%s" % (zipFilePath))

        # was extracted io EO_product folder
        for name in processInfo.srcProduct.contentList:
            eoPiecePath = "%s/%s" % (processInfo.srcProduct.EXTRACTED_PATH, name)
            if self.debug != 0:
                print(
                    " @@@@@ add to EO contentList[%s]:%s at path %s"
                    % (n, name, eoPiecePath)
                )
            zipf.write(eoPiecePath, name, zipfile.ZIP_DEFLATED)
            n += 1

        #
        zipf.close()

        # set size
        processInfo.srcProduct.metadata.setMetadataPair(
            metadata.METADATA_PRODUCT_SIZE, os.stat(zipFilePathWithPart).st_size
        )

        # remove temporary part extension
        try:
            os.rename(zipFilePathWithPart, zipFilePath)
        except:
            processInfo.addLog(
                ".part rename error: %s"
                % os.listdir(os.path.dirname(zipFilePathWithPart))
            )
            raise Exception(
                ".part rename error: %s"
                % os.listdir(os.path.dirname(zipFilePathWithPart))
            )

        # add EO zip as a piece
        piece = product_EOSIP.EoPiece(os.path.basename(zipFilePath))
        piece.alias = os.path.basename(zipFilePath)
        piece.localPath = zipFilePath
        newContentList.append(piece.alias)
        processInfo.destProduct.addPiece(piece)
        processInfo.srcProduct.contentList = newContentList

    #
    # called after having done the various reports
    #
    def afterReportsDone_(self, processInfo):
        #
        self.alterReportXml(processInfo)

        # build piece list,
        n = 0
        newContentList = []
        for path in processInfo.srcProduct.contentList:
            if self.debug != 0:
                print(" @@@@@ check contentList[%s]:%s" % (n, path))
            piece = product_EOSIP.EoPiece(os.path.basename(path))
            piece.alias = os.path.basename(path)
            piece.localPath = path
            newContentList.append(piece.alias)
            processInfo.destProduct.addPiece(piece)
            n += 1
        processInfo.srcProduct.contentList = newContentList

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):

        # add src product as piece
        srcPath = processInfo.srcProduct.path
        piece = product_EOSIP.EoPiece(os.path.basename(srcPath))
        piece.alias = os.path.basename(srcPath)
        piece.localPath = srcPath
        processInfo.destProduct.addPiece(piece)

        # add quality report
        tmp = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_FILE_TYPE
        )
        phase = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_PHASE
        )
        if phase == product_goce.PHASE_DE_ORBITING:
            if tmp in product_goce.HAS_DEORBITING_QR_REPORT_FILE_TYPE:
                processInfo.addLog(" ## HAS DEORBITING REPORT")
                self.keepInfo(
                    "HAS DEORBITING REPORT: DEORBITING, in HAS_DEORBITING_QR_REPORT_FILE_TYPE:%s"
                    % tmp,
                    processInfo.destProduct.eoProductName,
                )
                self.addQrDdeorbitingReport(processInfo)
            else:
                self.keepInfo(
                    "HAS NO DEORBITING REPORT: DEORBITING, not in HAS_DEORBITING_QR_REPORT_FILE_TYPE:%s"
                    % tmp,
                    processInfo.destProduct.eoProductName,
                )
                processInfo.addLog(" ## HAS NO DEORBITING REPORT")
        else:
            if phase == product_goce.PHASE_ROUTINE:
                if tmp in product_goce.HAS_NOMINAL_QR_REPORT_FILE_TYPE:
                    processInfo.addLog(
                        " ## HAS QUALITY REPORT: not DEORBITING, in HAS_NOMINAL_QR_REPORT_FILE_TYPE:%s"
                        % tmp
                    )
                    self.keepInfo(
                        "HAS QUALITY REPORT: not DEORBITING, in HAS_NOMINAL_QR_REPORT_FILE_TYPE:%s"
                        % tmp,
                        processInfo.destProduct.eoProductName,
                    )
                    self.addQrMontlyReport(processInfo)
                else:
                    processInfo.addLog(
                        " ## HAS NO QUALITY REPORT: not DEORBITING, not in HAS_NOMINAL_QR_REPORT_FILE_TYPE:%s"
                        % tmp
                    )
                    self.keepInfo(
                        "HAS NO QUALITY REPORT: not DEORBITING, not in HAS_NOMINAL_QR_REPORT_FILE_TYPE:%s"
                        % tmp,
                        processInfo.destProduct.eoProductName,
                    )
            else:
                if phase != product_goce.PHASE_COMMISIONNING:
                    raise Exception("Invalid phase:%s" % phase)

        #
        self.alterReportXml(processInfo)

    #
    # add namespace in: <eop:operationalMode "
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog(" alterReportXml: product report parsed")
        if self.debug != 0:
            print(" alterReportXml: product report parsed")

        # add namespace:
        instrument = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_INSTRUMENT
        )
        codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE
        ).replace("{SENSOR}", instrument)
        # codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE)
        if self.debug != 0:
            print("alterReportXml: codeSpaceOpMode='%s'" % codeSpaceOpMode)
        if not processInfo.destProduct.testValueIsDefined(codeSpaceOpMode):
            raise Exception("codeSpaceOpMode is not defined")
        aNode = helper.getFirstNodeByPath(
            None,
            "procedure/EarthObservationEquipment/sensor/Sensor/operationalMode",
            None,
        )
        helper.setNodeAttributeText(aNode, "codeSpace", codeSpaceOpMode)

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(helper.prettyPrint())
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print(" new XML: %s " % formattedXml)
        fd = open(processInfo.destProduct.reportFullPath, "w")
        fd.write(formattedXml)
        fd.flush()
        fd.close()
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    #
    def afterProductDone(self, processInfo):
        pass

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):

        # forse .SIP.ZIP extension
        processInfo.destProduct.setEoExtension(
            definitions_EoSip.getDefinition("PACKAGE_EXT")
        )
        self.buildEoNamesDefault(processInfo, namingConvention)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if self.debug != 0:
            print((" ############################## EoSip package name:%s" % aName))
        if len(aName) != len(REF_NAME):
            print("ref name:%s" % REF_NAME)
            print("EoSip name:%s" % aName)
            raise Exception(
                "EoSip name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME))
            )

        if aName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

        # set correct TGZ extension
        processInfo.destProduct.setEoExtension(
            definitions_EoSip.getDefinition("TGZ_EXT")
        )
        # set correct EO package name with .TGZ
        anEoName = processInfo.destProduct.getEoProductName()
        processInfo.destProduct.setEoProductName(anEoName)  # will add extension
        anEoPackageName = processInfo.destProduct.getEoPackageName()
        if self.debug != 0:
            print(
                (" ############################## EO package name:%s" % anEoPackageName)
            )
        if len(anEoName) != len(REF_EO_NAME):
            print("ref EO name:%s" % REF_EO_NAME)
            print("EO name:%s" % anEoName)
            raise Exception(
                "EO name has incorrect length:%s VS %s"
                % (len(anEoName), len(REF_EO_NAME))
            )
        if anEoName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("EoProductName incomplet:%s" % aName)

    #
    # Override
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        goceP = product_goce.Product_Goce(processInfo.srcPath)
        # goceP.setDebug(1)
        processInfo.srcProduct = goceP

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.setDebug(1)
        eosipP.sourceProductPath = processInfo.srcPath
        eosipP.setSipInfoType(product_EOSIP.GIN_SIP_INFO_TYPE)
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_DDOT(self.OUTPUT_SIP_PATTERN)
        namingConventionSip.setDebug(1)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEo = NamingConvention_AsSource(self.OUTPUT_EO_PATTERN)
        namingConventionEo.setDebug(1)
        eosipP.setNamingConventionEoInstance(namingConventionEo)

        self.logger.info(" Eo-Sip class created")
        processInfo.addLog("\n - Eo-Sip class created")

    #
    # Override
    #
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" - verifying product: %s" % (processInfo.srcPath))
        self.logger.info(" verifying product")

        try:
            with tarfile.open(processInfo.srcPath) as tardude:
                for member in tardude.getmembers():
                    if self.debug != 0:
                        print((" verifying product member name:%s" % member.name))
                    check = tardude.extractfile(member.name)
                    if self.debug != 0:
                        print("  -> member ok")
                self.logger.info(" --> verifying product completed")
            processInfo.addLog(" --> verifying product completed")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsgShort = "Error verifying source product:%s  %s" % (
                exc_type,
                exc_obj,
            )
            errorMsg = "Error verifying source product:%s  %s\n%s" % (
                exc_type,
                exc_obj,
                traceback.format_exc(),
            )
            self.logger.error(errorMsg)
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))
            raise Exception(errorMsgShort)

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog(
            "\n - prepare product, will extract inside working folder:%s"
            % (processInfo.workFolder)
        )
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(
            processInfo.workFolder, processInfo.test_dont_extract
        )
        processInfo.addLog("  => extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

        self.goceToolAppExe = self.ressourcesProvider.getRessourcePath("goceToolAppExe")
        processInfo.srcProduct.goceToolAppExe = self.goceToolAppExe

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        processInfo.addLog("\n - will extract metadata from src product")
        self.logger.info(" will extract metadata from src product")

        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # size=processInfo.srcProduct.getSize()
        # met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, size)

        # use method in base converter
        self.getGenerationTime(met)
        self.logger.debug("number of metadata added:%d" % numAdded)

        # refine
        self.logger.info(" will refine metadata")
        processInfo.srcProduct.refineMetadata(
            processInfo, self.GOCE_COLLECTION_DOI_LUT, self.TYPECODE_COLLECTION_LUT
        )

        # will do the kmz or not?
        # self.create_kmz = processInfo.srcProduct.hasFootprint

    #
    # Override
    # copy the source browse image into work folder, or for better quality generate the browse from the TIF image
    # construct the browse_metadatareport footprint block(BROWSE_CHOICE): it is the rep:footprint for spot
    #
    def makeBrowses(self, processInfo):
        return
        processInfo.addLog("\n - will make browse")
        self.logger.info(" will make browse")
        try:
            browseSrcPath = processInfo.srcProduct.imageSrcPath
            browseExtension = definitions_EoSip.getBrowseExtension(
                0, definitions_EoSip.getDefinition("BROWSE_PNG_EXT")
            )
            browseDestPath = "%s/%s.%s" % (
                processInfo.destProduct.folder,
                processInfo.destProduct.eoProductName,
                browseExtension,
            )

            if 1 == 2:
                if (
                        processInfo.srcProduct.metadata.getMetadataValue(
                            metadata.METADATA_ORBIT_DIRECTION
                        )
                        == "ASCENDING"
                ):
                    imageUtil.makeBrowse(
                        "PNG", browseSrcPath, "%s_flipped" % browseDestPath
                    )
                    img = Image.open("%s_flipped" % browseDestPath)
                    img2 = img.transpose(Image.FLIP_TOP_BOTTOM).transpose(
                        Image.FLIP_LEFT_RIGHT
                    )
                    img2.save(browseDestPath)
                else:
                    imageUtil.makeBrowse("PNG", browseSrcPath, browseDestPath)
            else:
                imageUtil.makeBrowse("PNG", browseSrcPath, browseDestPath)

            processInfo.destProduct.addSourceBrowse(browseDestPath, [])
            processInfo.addLog(
                "  browse image added: name=%s; path=%s"
                % (processInfo.destProduct.eoProductName, browseDestPath)
            )

            # set atime and mtime to self.generationTime
            # set AM time if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)
            # aFileHelper = fileHelper.FileHelper()
            # aFileHelper.setAMtime(browseDestPath, self.generationTime, self.generationTime)

            # create browse choice for browse metadata report
            bmet = processInfo.destProduct.browse_metadata_dict[browseDestPath]

            footprintBuilder = rep_footprint.rep_footprint()
            #
            if self.debug != 0:
                print(
                    "###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s"
                    % (processInfo.destProduct.metadata.toString())
                )
            browseChoiceBlock = footprintBuilder.buildMessage(
                processInfo.destProduct.metadata,
                "rep:browseReport/rep:browse/rep:footprint",
            ).strip()
            if self.debug != 0:
                print("browseChoiceBlock:%s" % (browseChoiceBlock))
            bmet.setMetadataPair(
                browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock
            )

            # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
            # if specified in configuration
            tmp = processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_BROWSES_TYPE
            )
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_CODESPACE_REFERENCE_SYSTEM
            )
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "Error generating browse:%s  %s\n%s" % (
                exc_type,
                exc_obj,
                traceback.format_exc(),
            )
            self.logger.error(errorMsg)
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))
            raise e

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        processInfo.addLog("\n - will output eoSip; basePath=%s" % (basePath))
        self.logger.info(" will output eoSip; basePath=%s" % (basePath))
        # copy eoSip in first path
        # make links in other paths
        outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(
            basePath, pathRules
        )
        if len(outputProductResolvedPaths) == 0:
            processInfo.addLog("   ERROR: no product resolved path")
            self.logger.info(" ERROR: no product resolved path")
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = outputProductResolvedPaths[0]
            processInfo.addLog(
                "  Eo-Sip product will be writen in folder:%s" % (firstPath)
            )
            self.logger.info(
                "  Eo-Sip product will be writen in folder:%s" % (firstPath)
            )
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addLog("  ok, writen well\n%s" % processInfo.destProduct.info())
            self.logger.info(" ok, writen well\n%s" % processInfo.destProduct.info())
            processInfo.addIngesterLog(
                "  write done:%s" % processInfo.destProduct.path, "PROGRESS"
            )

            # make a thumbnail FOR TEST
            if processInfo.create_thumbnail == 1:
                self.make_thumbnail(processInfo, firstPath)
                # move also browse image
                self.move_browse(processInfo, firstPath)

            # output link in other path
            i = 0
            for item in outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % (item)
                    self.logger.info(
                        "  create also (linked?) eoSip product at tree path[%d] is:%s"
                        % (i, item)
                    )
                    processInfo.addLog(
                        "  create also (linked?) eoSip product at tree path[%d] is:%s"
                        % (i, item)
                    )
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog(
                        "  Eo-Sip product link writen in folder[%d]:%s\n"
                        % (i, otherPath)
                    )
                    self.logger.info(
                        "  Eo-Sip product link writen in folder[%d]:%s\n"
                        % (i, otherPath)
                    )
                i = i + 1

        self.logger.info("  done")
        return productPath

    #
    # move a browse in the Destination folder
    #
    def move_browse(self, processInfo, destPath):
        processInfo.addLog("\n - will move browse")
        self.logger.info("  will move browse")
        try:
            if len(processInfo.destProduct.sourceBrowsesPath) > 0:
                tmp = os.path.split(processInfo.destProduct.sourceBrowsesPath[0])[1]
                res = shutil.copyfile(
                    processInfo.destProduct.sourceBrowsesPath[0],
                    "%s/%s" % (destPath, tmp.split("/")[-1]),
                )
                print(
                    "copy browse file into:%s/%s: res=%s"
                    % (destPath, tmp.split("/")[-1], res)
                )

        except Exception as e:
            print(" browse move Error")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))

    #
    # make a thumbnail in the Destination folder
    #
    def make_thumbnail(self, processInfo, destPath):
        # make a thumbnail FOR TEST
        processInfo.addLog("\n - will make thumbnail")
        self.logger.info("  will make thumbnail")
        try:
            if len(processInfo.destProduct.sourceBrowsesPath) > 0:
                tmp = os.path.split(processInfo.destProduct.sourceBrowsesPath[0])[1]
                tmpb = tmp.split(".")[-1:]
                tmpa = tmp.split(".")[0:-1]
                thumbnail = "%s.TN.%s" % (".".join(tmpa), ".".join(tmpb))
                processInfo.destProduct.metadata.setMetadataPair(
                    metadata.METADATA_THUMBNAIL, thumbnail
                )
                thumbnail = "%s/%s" % (destPath, thumbnail)
                imageUtil.makeBrowse(
                    "JPG",
                    "%s" % (processInfo.destProduct.sourceBrowsesPath[0]),
                    thumbnail,
                    25,
                )
                print("builded thumbnail file:  destPath=%s" % destPath)
                print(
                    "builded thumbnail file:  tmp=%s ==> %s/%s_TN.%s"
                    % (tmp, destPath, tmpa, tmpb)
                )
                self.logger.info(
                    "builded thumbnail file:%s/%s_TN.%s" % (destPath, tmpa, tmpb)
                )
                processInfo.addLog(
                    "builded thumbnail file:%s/%s_TN.%s" % (destPath, tmpa, tmpb)
                )

            else:
                print("there is no browse so no thumbnail to create in final folder")
                self.logger.info(" no browse available, so no thumbnail...")
                processInfo.addLog("  => no browse available, so no thumbnail...")

        except Exception as e:
            print(" thubnail creation Error")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))
            # raise e

    #
    # get the quality report for a product, based on product start date yyyymm
    #
    def addQrMontlyReport(self, processInfo):
        yymm = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_START_DATE
        ).replace("-", "")[0:6]
        report_path = Path(esaProducts_data.__file__).parent / 'goce' / 'Reports' / f'statistics_{yymm}.pdf'

        if not report_path.exists():
            raise Exception(f"Quality report does not exists for date: {yymm}")
        else:
            qrEoName = "%s.QR.PDF" % processInfo.destProduct.eoProductName
            processInfo.addLog(" ## quality EO filename:%s" % qrEoName)
            processInfo.destProduct.addAdditionalContent(str(report_path), qrEoName)
            # for test purpose: copy it to workfolder
            shutil.copy(report_path, "%s/%s" % (processInfo.workFolder, qrEoName))

    #
    #
    #
    def addQrDdeorbitingReport(self, processInfo):
        report_path = Path(esaProducts_data.__file__).parent / "goce" / "Reports" / "GOCE_QC_RPT_Deorbiting_1.0.pdf"

        if not report_path.exists():
            raise Exception(
                f"Quality report does not exists at path: {report_path}"
            )
        else:
            qrEoName = "%s.QR.PDF" % processInfo.destProduct.eoProductName

            processInfo.addLog(" ## deorbiting quality EO filename:%s" % qrEoName)
            processInfo.destProduct.addAdditionalContent(str(report_path), qrEoName)
            # for test purpose: copy it to workfolder
            shutil.copy(report_path, "%s/%s" % (processInfo.workFolder, qrEoName))


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_goce()

            commandLineInfo = ingester.getCommandLineInfo()

            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("rapid-eye conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Goce_conversion_report.txt"
            fd = open(reportName, "w")
            fd.write(out.getvalue())
            fd.flush()
            fd.close()
            print("conversion report written well:%s" % reportName)

            sys.exit(exitCode)
        else:
            print(
                "syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]"
            )
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
