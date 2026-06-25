#
# This is a specialized class that converter landsat1-7 MSS/ETM/TM
#
# For Esa/ lite dissemination project
#
# Serco 04/2018
# Lavaux Gilles
#
# 30/08/2018: V: 0.1
#
#
# Changes:
# -
#
import inspect
import os
import shutil
import sys
import traceback
import zipfile
from io import StringIO

# add converter package path to sys.path
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parrent = os.path.dirname(currentdir)
print("##### eoSip converter package dir:%s" % parrent)
sys.path.insert(0, parrent)

#
from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_landsat1_7_zip, product_EOSIP
from eoSip_converter.esaProducts import metadata, browse_metadata, base_metadata
from eoSip_converter.esaProducts import definitions_EoSip

from xml_nodes import rep_footprint
from eoSip_converter.esaProducts.namingConvention_DDOT import NamingConvention_DDOT

import eoSip_converter.imageUtil as imageUtil
import eoSip_converter.xmlHelper as xmlHelper

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = "Landsat1-7 converter V:0.1.0"
SIP_REF_NAME = 'L01_RKSE_MSS_GTC_1P_19990522T101026_19990522T101041_041049_0480_1914_0SLA_v0100.SIP.ZIP'
EO_REF_NAME = 'LS01_RKSE_MSS_GTC_1P_19990522T101026_19990522T101041_041049_0480_1914_0SLA'
SRC_REF_NAME = 'LS07_RNSG_ETM_GTC_1P_19991102T094600_19991102T094629_002924_0191_0031_CC72.ZIP'


class ingester_landsat_zip(ingester.Ingester):

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
    #
    #
    def afterStarting(self, **kargs):
        pass

    #
    # called before doing the various reports
    # change the mapping of product href from METADATA_PACKAGENAME to value of METADATA_FULL_PACKAGENAME, BUT set 4 digit at first section
    #   METADATA_FULL_PACKAGENAME=L02_RFUI_MSS_GTC_1P_19760218T091448_19760218T091517_005465_0205_0047_0SLA_v0100.SIP.ZIP
    #   set it as: LS02_RFUI_MSS_GTC_1P_19760218T091448_19760218T091517_005465_0205_0047_0SLA_v0100.SIP.ZIP
    #   so is like METADATA_IDENTIFIER + METADATA_SIP_VERSION + SIP.ZIP
    #   What a mess they have done in this spec.
    #
    #   UPDATE: NO the spec example is wrong, simply use METADATA_FULL_PACKAGENAME
    #
    #
    def beforeReportsDone(self, processInfo):
        #
        processInfo.destProduct.metadata.alterMetadataMaping('href', metadata.METADATA_FULL_PACKAGENAME)
        if 1 == 2:  # disabled: spec war wrong
            eoSipPackageName = "%s_v%s.SIP.ZIP" % (
            processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_IDENTIFIER),
            processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION))
            processInfo.destProduct.metadata.setMetadataPair('CUSTOM_EOSIP_PACKAGE_NAME', eoSipPackageName)
            print("@@@@@@@@@@@@@@@@@@@@@@@@@ EoSip CUSTOM_EOSIP_PACKAGE_NAME for product href:%s" % eoSipPackageName)
            if len(eoSipPackageName) != len(SIP_REF_NAME):
                print("ref EoSip package name:%s" % SIP_REF_NAME)
                print("CUSTOM_EOSIP_PACKAGE_NAME:%s" % eoSipPackageName)
                raise Exception("CUSTOM_EOSIP_PACKAGE_NAME has incorrect length:%s VS %s" % (
                len(eoSipPackageName), len(SIP_REF_NAME)))
            if eoSipPackageName.find('@') >= 0 or eoSipPackageName.find('#') > 0:
                raise Exception("CUSTOM_EOSIP_PACKAGE_NAME incomplet:%s" % eoSipPackageName)
            processInfo.destProduct.metadata.alterMetadataMaping('href', 'CUSTOM_EOSIP_PACKAGE_NAME')

        # set cloud coverage to -1 if not present
        tmp = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE)
        # print "METADATA_CLOUD_COVERAGE:%s" % tmp
        if tmp == base_metadata.VALUE_NOT_PRESENT:
            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, -1)
        # os._exit(1)

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        #
        # build the EO zip package. content is in srcProduct.contentList
        #
        # NEW REQ 2019-03-20: change also filename inside EO part. to be confirmed
        #
        #
        newContentList = []
        n = 0
        zipFilePath = "%s/%s.%s" % (
        processInfo.workFolder, processInfo.destProduct.eoProductName, processInfo.destProduct.sipPackageExtension)
        zipFilePathWithPart = "%s.part" % zipFilePath
        zipf = zipfile.ZipFile(zipFilePathWithPart, mode='w', allowZip64=True)
        print("\n\n @@@@@ EO tmp zip file is:%s" % (zipFilePath))
        processInfo.addLog("EO tmp zip file is:%s" % (zipFilePath))

        if 1 == 1:  # original: keep source EO filenames
            # was extracted in EO_product folder
            for name in processInfo.srcProduct.contentList:
                eoPiecePath = "%s/%s" % (processInfo.srcProduct.EXTRACTED_PATH, name)
                print(" @@@@@ add to EO contentList[%s]:%s at path %s" % (n, name, eoPiecePath))
                processInfo.addLog(" add to EO contentList[%s]:%s at path %s" % (n, name, eoPiecePath))
                zipf.write(eoPiecePath, name, zipfile.ZIP_DEFLATED)
                n += 1
        else:  # change: alter filenames
            pass

        #
        zipf.close()
        # remove temporary part extension
        try:
            os.rename(zipFilePathWithPart, zipFilePath)
        except:
            processInfo.addLog(".part rename error: %s" % os.listdir(os.path.dirname(zipFilePathWithPart)))
            raise Exception(".part rename error: %s" % os.listdir(os.path.dirname(zipFilePathWithPart)))

        #
        processInfo.destProduct.setTmpZipFile(os.stat(zipFilePath).st_size)

        # add EO zip as a piece
        piece = product_EOSIP.EoPiece(os.path.basename(zipFilePath))
        piece.alias = os.path.basename(zipFilePath)
        piece.localPath = zipFilePath
        newContentList.append(piece.alias)
        processInfo.destProduct.addPiece(piece)
        processInfo.srcProduct.contentList = newContentList

        #
        self.alterReportXml(processInfo)

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    #
    def afterProductDone(self, processInfo):
        pass

    #
    # add namespace in: <eop:operationalMode ??
    #
    def alterReportXml(self, processInfo):
        # add productQualityDegradation before <eop:vendorSpecific>
        xmlData = processInfo.destProduct.productReport
        if 1 == 1:
            fd = open('orig_md.xml', 'w')
            fd.write(xmlData)
            fd.flush()
            fd.close()

        pos = xmlData.find('<eop:vendorSpecific>')
        xmlData2 = "%s\n      %s\n      %s" % (
        xmlData[0:pos], '<eop:productQualityDegradation uom="lost_lines">01230</eop:productQualityDegradation>',
        xmlData[pos:])
        xmlData2 = xmlData2.replace('CONVERTER_NOT-PRESENT', 'Not applicable')
        xmlData2 = xmlData2.replace('CONVERTER_UNKNOWN', 'Not applicable')
        if 1 == 1:
            fd = open('mod1_md.xml', 'w')
            fd.write(xmlData2)
            fd.flush()
            fd.close()

        # add after first <eop:type>QUICKLOOK</eop:type>
        platformId = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
        instrument = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        pos = xmlData2.find('<eop:type>QUICKLOOK</eop:type>')
        nchar1 = len('<eop:type>QUICKLOOK</eop:type>')
        nchar2 = len('<eop:subType codeSpace="urn:esa:eop:Landsat%s:%s:browsesubType">Low Resolution</eop:subType>' % (
        platformId, instrument))
        xmlData3 = "%s\n      %s\n      %s" % (xmlData2[0:pos + nchar1],
                                               '<eop:subType codeSpace="urn:esa:eop:Landsat%s:%s:browsesubType">Low Resolution</eop:subType>' % (
                                               platformId, instrument), xmlData2[pos + nchar1:])
        if 1 == 1:
            fd = open('mod2_md.xml', 'w')
            fd.write(xmlData3)
            fd.flush()
            fd.close()

        # add after last <eop:type>QUICKLOOK</eop:type>
        pos1 = xmlData3.find('<eop:type>QUICKLOOK</eop:type>', pos + nchar1 + nchar2 + 1)
        xmlData4 = "%s\n      %s\n      %s" % (xmlData3[0:pos1 + nchar1],
                                               '<eop:subType codeSpace="urn:esa:eop:Landsat%s:%s:browsesubType">Full Resolution</eop:subType>' % (
                                               platformId, instrument), xmlData3[pos1 + nchar1:])
        print(("\n\n\nxmlData4:%s\n\n\n" % xmlData4))

        if 1 == 1:
            fd = open('mod2_md.xml', 'w')
            fd.write(xmlData4)
            fd.flush()
            fd.close()

        # set real EO part size:
        origSize = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)
        tmpZipSize = processInfo.destProduct.getTmpZipFile()
        ratio = (float(tmpZipSize) * 100) / float(origSize)
        if ratio > 110 or ratio < 90:
            raise Exception(" EO size ratio out of range: EO product source file size:%s; tmpZipSize:%s. ratio=%s" % (
            origSize, tmpZipSize, ratio))
        processInfo.addLog(" ########################### EO product source file size:%s; tmpZipSize:%s. ratio=%s" % (
        origSize, tmpZipSize, ratio))
        print((" ########################### EO product source file size:%s; tmpZipSize:%s. ratio=%s" % (
        origSize, tmpZipSize, ratio)))

        aa = '%s</eop:size>' % origSize
        pos = xmlData4.find(aa)
        if pos < 0:
            raise Exception("cannot find product size in xml")
        xmlData4.replace(aa, '%s</eop:size>' % processInfo.destProduct.getTmpZipFile())
        processInfo.addLog(
            " EO product size set to tmp zir file. From %s to %s" % (origSize, processInfo.destProduct.getTmpZipFile()))

        # replace MD.XML content
        helper2 = xmlHelper.XmlHelper()
        helper2.setData(xmlData4)
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print(" new XML: %s " % formattedXml)
        shutil.copy(processInfo.destProduct.reportFullPath, processInfo.destProduct.reportFullPath + "_orig")
        fd = open(processInfo.destProduct.reportFullPath, 'w')
        fd.write(formattedXml)
        fd.flush()
        fd.close()
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'" % processInfo.destProduct.reportFullPath)
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):

        # force setEoExtension to ZIP. Because we use SRC_PRODUCT_AS_DIR to use several files as input, and we want a .SIP.ZIP package.
        processInfo.destProduct.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))
        self.buildEoNamesDefault(processInfo, namingConvention)

        # test EoSip package name
        anEoSipPackageName = processInfo.destProduct.getSipPackageName()
        print("@@@@@@@@@@@@@@@@@@@@@@@@@ EoSip package name:%s" % anEoSipPackageName)
        if len(anEoSipPackageName) != len(SIP_REF_NAME):
            print("ref EoSip package name:%s" % SIP_REF_NAME)
            print("EoSip package name    :%s" % anEoSipPackageName)
            raise Exception(
                "EoSip package name has incorrect length:%s VS %s" % (len(anEoSipPackageName), len(SIP_REF_NAME)))

        if anEoSipPackageName.find('@') >= 0 or anEoSipPackageName.find('#') > 0:
            raise Exception("EoSip package name incomplet:%s" % anEoSipPackageName)

        #
        # convert eo package name (that is currently == sip package name) into desired version
        #
        anEoName = processInfo.destProduct.getEoProductName()
        print("@@@@@@@@@@@@@@@@@@@@@@@@@ will update EO name:%s" % anEoName)

        modifiedName = "LS%s%s" % (anEoName[1:2], anEoName[2:-6])
        if len(modifiedName) != len(EO_REF_NAME):
            print("ref EO name:%s" % EO_REF_NAME)
            print("EO name    :%s" % modifiedName)
            raise Exception("EO name has incorrect length:%s VS %s" % (len(modifiedName), len(EO_REF_NAME)))

        if anEoName.find('@') >= 0 or anEoName.find('#') > 0:
            raise Exception("Eo package name incomplet:%s" % anEoName)

        # change EO name and identifier
        processInfo.destProduct.setEoProductName(modifiedName)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, modifiedName)
        processInfo.addLog("@@@@@@@@@@@@@@@@@@@@@@@@@  modifiedName:%s" % modifiedName)

    #
    # Override
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        dimapP = product_landsat1_7_zip.Product_landsat1_7_zip(processInfo.srcPath)
        processInfo.srcProduct = dimapP

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        # eosipP.sourceProductPath = processInfo.srcPath
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE)
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_DDOT(self.OUTPUT_SIP_PATTERN)
        namingConventionSip.setDebug(1)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEo = NamingConvention_DDOT(self.OUTPUT_EO_PATTERN)
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
        fh = open(processInfo.srcPath, 'rb')
        zf = zipfile.ZipFile(fh)
        ok = zf.testzip()
        fh.close()
        if ok is not None:
            self.logger.error("  Zip file is corrupt:%s" % processInfo.srcPath)
            self.logger.error("  First bad file in zip: %s" % ok)
            processInfo.addLog("  => Zip file is corrupt:%s" % processInfo.srcPath)
            raise Exception("Zip file is corrupt:%s" % processInfo.srcPath)
        else:
            self.logger.info("  Zip file is ok")
            processInfo.addLog("  => Zip file is ok")

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog("\n - prepare product, will extract inside working folder:%s" % (processInfo.workFolder))
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)
        processInfo.addLog("  => extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

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
        processInfo.srcProduct.refineMetadata()

        # keep some info
        tmp = met.getMetadataValue(metadata.METADATA_TYPECODE)
        self.keepInfo(metadata.METADATA_TYPECODE, tmp)
        #
        tmp = met.getMetadataValue(metadata.METADATA_PROCESSING_TYPE)
        self.keepInfo(metadata.METADATA_PROCESSING_TYPE, tmp)

        tmp = met.getMetadataValue(metadata.METADATA_INSTRUMENT)
        self.keepInfo(metadata.METADATA_INSTRUMENT, tmp)
        #
        tmp = met.getMetadataValue('MODEL_FIT_TYPE')
        self.keepInfo('MODEL_FIT_TYPE', tmp)
        if tmp != base_metadata.VALUE_NOT_PRESENT:
            self.keepInfo('HAS__MODEL_FIT_TYPE', processInfo.srcProduct.path)
        #
        tmp = met.getMetadataValue('GEOMETRIC_MAX_ERR')
        self.keepInfo('GEOMETRIC_MAX_ERR', tmp)
        if tmp != base_metadata.VALUE_NOT_PRESENT:
            self.keepInfo('HAS__GEOMETRIC_MAX_ERR', processInfo.srcProduct.path)
        #
        tmp = met.getMetadataValue('CLOUD_COVER_AUTOMATED_L1')
        tmp1 = met.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE)
        self.keepInfo('CLOUD_COVER_AUTOMATED_L1', tmp)
        self.keepInfo(metadata.METADATA_CLOUD_COVERAGE, tmp1)
        #
        if tmp != base_metadata.VALUE_NOT_PRESENT:  # some CLOUD_COVER_AUTOMATED_L1
            self.keepInfo('HAS__CLOUD_COVER_AUTOMATED_L1', processInfo.srcProduct.path)
            if tmp1 != base_metadata.VALUE_NOT_PRESENT:  # some CLOUD_COVERAGE
                self.keepInfo('HAS__CLOUD_COVER', processInfo.srcProduct.path)
            else:  # use CLOUD_COVER_AUTOMATED_L1 as cloud_cover
                met.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, tmp)
        else:  # no CLOUD_COVER_AUTOMATED_L1
            if tmp1 != base_metadata.VALUE_NOT_PRESENT:
                met.setMetadataPair('CLOUD_COVER_AUTOMATED_L1', tmp1)
        # set it as 'cloud_cover_automated'
        met.setMetadataPair('cloud_cover_automated', met.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE))

        # set the per platformId/sensor local attributes
        processInfo.srcProduct.setLocalAttr(met)

    #
    # Override
    # copy the source browse image into work folder, or for better quality generate the browse from the TIF image
    # construct the browse_metadatareport footprint block(BROWSE_CHOICE): it is the rep:footprint for spot
    #
    def makeBrowses(self, processInfo):
        processInfo.addLog("\n - will make browse")
        self.logger.info(" will make browse")
        try:
            #
            # make default PNG browse
            #
            browseSrcPath = processInfo.srcProduct.browse_path  # src is a 'BI.PNG' file
            browseExtension = definitions_EoSip.getBrowseExtension(0, definitions_EoSip.getDefinition('BROWSE_PNG_EXT'),
                                                                   default=True)  # want a .BID.PNG ext
            processInfo.addLog("  ###browse image browseExtension:%s" % browseExtension)
            browseDestPath = "%s/%s.%s" % (
            processInfo.destProduct.folder, processInfo.destProduct.eoProductName, browseExtension)

            processInfo.destProduct.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  ### PNG browse image added: name=%s; path=%s" % (
            processInfo.destProduct.eoProductName, browseDestPath))

            # copy in place
            shutil.copyfile(browseSrcPath, browseDestPath)

            # set AM timne if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)

            # create browse choice for browse metadata report
            bmet = processInfo.destProduct.browse_metadata_dict[browseDestPath]

            footprintBuilder = rep_footprint.rep_footprint()
            #
            print("###\n###\n### BUILD PNG BROWSE CHOICE FROM METADATA:%s" % (
                processInfo.destProduct.metadata.toString()))
            browseChoiceBlock = footprintBuilder.buildMessage(processInfo.destProduct.metadata,
                                                              "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != -1:
                print("browseChoiceBlock:%s" % (browseChoiceBlock))
            bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

            # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
            # if specified in configuration
            tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

            #
            # idem for additionnal JPG
            #
            browseExtensionJpg = definitions_EoSip.getBrowseExtension(0, definitions_EoSip.getDefinition(
                'BROWSE_JPG_EXT'), default=False, numerated=False)  # want a .BI.JPG ext
            browseExtensionJpg = browseExtensionJpg.replace('BI', 'BI_F')
            browseDestPathJpg = "%s/%s.%s" % (
            processInfo.destProduct.folder, processInfo.destProduct.eoProductName, browseExtensionJpg)
            print("browseDestPathJpg:%s" % browseDestPathJpg)
            #
            # source jpg is too low resolution, use ??
            #
            ok = imageUtil.makeBrowse("JPG", browseDestPath, browseDestPathJpg, -1, transparent=False)

            processInfo.destProduct.addSourceBrowse(browseDestPathJpg, [])
            processInfo.addLog("  ### JPG browse image added: name=%s; path=%s" % (
            processInfo.destProduct.eoProductName, browseDestPathJpg))

            # set AM timne if needed
            processInfo.destProduct.setFileAMtime(browseDestPath)

            # create browse choice for browse metadata report
            bmet2 = processInfo.destProduct.browse_metadata_dict[browseDestPathJpg]

            #
            print("###\n###\n### BUILD JPG BROWSE CHOICE FROM METADATA:%s" % (
                processInfo.destProduct.metadata.toString()))
            browseChoiceBlock2 = footprintBuilder.buildMessage(processInfo.destProduct.metadata,
                                                               "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != -1:
                print("browseChoiceBlock2:%s" % (browseChoiceBlock2))
                bmet2.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock2)

            # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
            # if specified in configuration
            tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
            if tmp != None:
                bmet2.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
            if tmp != None:
                bmet2.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

            # os._exit(1)



        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "Error generating browse:%s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc())
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
        outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)
        if len(outputProductResolvedPaths) == 0:
            processInfo.addLog("   ERROR: no product resolved path")
            self.logger.info(" ERROR: no product resolved path")
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product will be writen in folder:%s" % (firstPath))
            self.logger.info("  Eo-Sip product will be writen in folder:%s" % (firstPath))
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addLog("  ok, writen well\n%s" % processInfo.destProduct.info())
            self.logger.info(" ok, writen well\n%s" % processInfo.destProduct.info())
            processInfo.addIngesterLog("  write done:%s" % processInfo.destProduct.path, 'PROGRESS')

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
                    self.logger.info("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                    processInfo.addLog("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                    self.logger.info("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
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
                res = shutil.copyfile(processInfo.destProduct.sourceBrowsesPath[0],
                                      "%s/%s" % (destPath, tmp.split("/")[-1]))
                print("copy browse file into:%s/%s: res=%s" % (destPath, tmp.split("/")[-1], res))

        except Exception as e:
            print(" browse move Error")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_landsat_zip()

            commandLineInfo = ingester.getCommandLineInfo()

            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("landsat1-7 EoSip conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Landsat1-7_eosip_conversion_report.txt"
            fd = open(reportName, 'w')
            fd.write(out.getvalue())
            fd.flush()
            fd.close()
            print("conversion report written well:%s" % reportName)

            sys.exit(exitCode)
        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
