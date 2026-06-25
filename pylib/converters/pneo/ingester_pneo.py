#
# This is a TEMPLATE ingester class. 
#
# For Esa/lite dissemination project
#
# Serco 02/2015 Lavaux Gilles
#
# 03/03/2015: V: 0.1
#
# TODO: add .SIP.ZIp in <ows:ServiceReference xlink:href="PH1_OPER_HIR_PMS_3__20130819T175900_N39-000_W105-000_0101">
# - add processing date
# - add version =   <Processing_Information> <Production_Facility> <SOFTWARE version="6">IMF</SOFTWARE>
# - remove leading _ from operational mode
#
import sys
import traceback
from io import StringIO
import os

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes
import eoSip_converter.xmlHelper as xmlHelper

from pneo import __version__, product_pneo

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = f"PNEO converter V:{__version__}"
REF_NAME = 'PLN_OPER_NEO_P_S_2__20210503T104900_N41-376_E002-153_01_v1021.SIP.ZIP'


class ingester_pneo(ingester.Ingester):
    def getVersionImpl(self):
        return VERSION

    def afterStarting(self, **kargs):
        pass

    # config version is like: name_floatVersion
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    # prepare metadata from a browse report generation
    def prepareBrowseMetadata(self, processInfo):
        pass

    # called before doing the various reports
    def beforeReportsDone(self, processInfo):
        # alter href mapping
        processInfo.destProduct.metadata.alterMetadataMaping('href', metadata.METADATA_FULL_PACKAGENAME)
        # set angle unit to deg
        processInfo.destProduct.metadata.setValidValue('UNIT_ANGLE', 'deg')
        # remove leading _ from
        sensor_mode = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        tmp = sensor_mode
        while sensor_mode.endswith('_'):
            if len(sensor_mode) == 3:
                break
            sensor_mode = sensor_mode[0:-1]
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@ sensor mode changed from '%s' to '%s'" % (tmp, sensor_mode))

        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensor_mode)

    # called after having done the various reports
    def afterReportsDone(self, processInfo):
        self.alterReportXml(processInfo)

    # called at the end of the doOneProduct, before the index/shopcart creation
    def afterProductDone(self, processInfo):
        pass

    def alterReportXml(self, processInfo):
        # add  <eop:subType codeSpace="urn:esa:eop:NAOMI:Bundle:browsesubType ">MS</eop:subType>
        # ONLY FOR P_S

        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog(" alterReportXml: product report parsed")
        print(" alterReportXml: product report parsed")

        mode = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if not processInfo.destProduct.testValueIsDefined(mode):
            raise Exception("operational mode is not defined")
        self.keepInfo("sensor mode:%s" % mode, processInfo.srcProduct.origName)
        processInfo.addLog(" alterReportXml: sensor mode:'%s'" % mode)

        result2 = []
        helper.getNodeByPath(entryNode=None, path='result/EarthObservationResult/browse/BrowseInformation', attr=None,
                             result=result2)
        if len(result2) == 0:
            raise Exception("can not find node 'result/EarthObservationResult/browse/BrowseInformation' in MD report")

        if mode == 'P_S':
            processInfo.addLog(" alterReportXml: add subType because sensor mode is %s" % mode)

            for item in result2:
                aNodeReferenceSystemIdentifier = helper.getFirstNodeByPath(item, 'referenceSystemIdentifier', None)
                aNodeServiceReference = helper.getFirstNodeByPath(item, 'fileName/ServiceReference', None)
                href = helper.getNodeAttributeText(aNodeServiceReference, 'xlink:href')
                print(" serviceReference href: %s " % href)
                isMs = False
                if processInfo.srcProduct.isBundleProduct:
                    tmp = []
                    helper.getNodeByPath(entryNode=item, path='fileName/ServiceReference', result=tmp)
                    filename_element = tmp[0]
                    filename = helper.getNodeAttributeText(filename_element, 'xlink:href')
                    nodeSubType = helper.getDomDoc().createElement('eop:subType')
                    helper.setNodeAttributeText(nodeSubType, 'codeSpace', 'urn:esa:eop:PNEO:Bundle:browsesubType')
                    helper.setNodeText(nodeSubType, 'P' if 'BID' in filename else 'MS')
                    item.insertBefore(nodeSubType, aNodeReferenceSystemIdentifier)

                # if processInfo.srcProduct.previewIsMs[href] == True:
                #     print(" alterReportXml href is MS")
                #     isMs = True
                # else:
                #     print(" alterReportXml href is not MS")
                # if isMs:
                #     nodeSubType = helper.getDomDoc().createElement('eop:subType')
                #     helper.setNodeAttributeText(nodeSubType, 'codeSpace', 'urn:esa:eop:PNEO:Bundle:browsesubType')
                #     helper.setNodeText(nodeSubType, 'MS_')
                #     item.insertBefore(nodeSubType, aNodeReferenceSystemIdentifier)
                # else:
                #     nodeSubType = helper.getDomDoc().createElement('eop:subType')
                #     helper.setNodeAttributeText(nodeSubType, 'codeSpace', 'urn:esa:eop:PNEO:Bundle:browsesubType')
                #     helper.setNodeText(nodeSubType, 'P_S')
                #     item.insertBefore(nodeSubType, aNodeReferenceSystemIdentifier)
            print(" RESULT2: %s " % result2)

        else:
            processInfo.addLog(" alterReportXml: DON'T add subType because sensor mode is %s" % mode)

            # add namespace: <eop:operationalMode codeSpace="urn:esa:eop:Pleiades:HiRI:Mode
        aNode = helper.getFirstNodeByPath(None, 'procedure/EarthObservationEquipment/sensor/Sensor/operationalMode',
                                          None)
        codeSpaceOpMode = processInfo.destProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE)
        if not processInfo.destProduct.testValueIsDefined(codeSpaceOpMode):
            raise Exception("codeSpaceOpMode is not defined")
        helper.setNodeAttributeText(aNode, 'codeSpace', codeSpaceOpMode)

        # eop:versoin set to software version here
        helper.setNodeText(
            helper.getFirstNodeByPath(
                None,
                'result/EarthObservationResult/product/ProductInformation/version',
                None),
            processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        )

        helper.setNodeText(
            helper.getFirstNodeByPath(
                None,
                'metaDataProperty/EarthObservationMetaData/identifier',
                None),
            processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PACKAGENAME)
        )

        # New requirement as of PNEO EOSIP spec v1.2
        new_xml_data = helper.prettyPrint()
        new_xml_data = new_xml_data.replace("opt:EarthObservationEquipment", "eop:EarthObservationEquipment")

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(new_xml_data)
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print(" new XML: %s " % formattedXml)
        with open(processInfo.destProduct.reportFullPath, 'wb') as fd:
            fd.write(formattedXml)
            fd.flush()

        # set AM timne if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'" % processInfo.destProduct.reportFullPath)

    def buildEoNames(self, processInfo, namingConvention=None):
        # test default in ingester
        self.buildEoNamesDefault(processInfo, namingConvention)

        # Ensure the platform ID doesn't make its way into identifiers/filenames
        # etc. which must start with 'PLN'
        if processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID) != 'N':
            sipProductName = 'PLN' + processInfo.destProduct.sipProductName[3:]
            sipPackageName = 'PLN' + processInfo.destProduct.sipPackageName[3:]
            eoProductName = 'PLN' + processInfo.destProduct.eoProductName[3:]
            eoPackageName = 'PLN' + processInfo.destProduct.eoPackageName[3:]
            identifier = 'PLN' + processInfo.destProduct.identifier[3:]

            processInfo.destProduct.identifier = identifier
            processInfo.destProduct.eoProductName = eoProductName
            processInfo.destProduct.eoPackageName = eoPackageName

            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_PRODUCTNAME, eoProductName)
            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, identifier)
            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_FULL_PRODUCTNAME, eoPackageName)

        file_counter = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        product_version = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
        product_version_and_counter = f"{product_version}{file_counter}"
        processInfo.destProduct.sipProductName = f"{processInfo.destProduct.eoProductName}_v{product_version_and_counter}"
        processInfo.destProduct.sipPackageName = f"{processInfo.destProduct.sipProductName}.SIP.ZIP"

        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_PACKAGENAME, processInfo.destProduct.sipProductName)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_FULL_PACKAGENAME, processInfo.destProduct.sipPackageName)

        processInfo.destProduct.identifier = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PACKAGENAME)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, processInfo.destProduct.identifier)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(REF_NAME):
            print("ref name:%s" % REF_NAME)
            print("EoSip name:%s" % aName)
            raise Exception("EoSip name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME)))
        if aName.find('@') >= 0 or aName.find('#') > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace('\\', os.sep)
        product = product_pneo.Product_Pneo(processInfo.srcPath)
        if self.test_mode:
            product.setDebug(1)
        processInfo.srcProduct = product
        product.processInfo = processInfo

    # Override
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        # use wrapped zip if size ~ 2gb
        aSize = processInfo.srcProduct.getSize()

        # don't want an Eosip > 2gb done using python zip lib
        if aSize > 1.9 * 1024 ** 3:
            msg = " ## zip: will use wrapped library because size >=1.9 gb: %s" % aSize
            print(msg)
            processInfo.addLog(msg)
            eosipP.setUsePythonZipLib(False)
        else:
            msg = " ## zip: will use python library because size <1.9 gb: %s" % aSize
            processInfo.addLog(msg)

        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEoInstance = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        eosipP.setNamingConventionEoInstance(namingConventionEoInstance)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionEoInstance)

        self.logger.info(" Eo-Sip product created")
        processInfo.addLog(" Eo-Sip product created")

    # Override
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" verifying product:%s" % (processInfo.srcPath))
        self.logger.info(" verifying product")

    # Override
    def prepareProducts(self, processInfo):
        processInfo.addLog(" prepare product in:%s" % (processInfo.workFolder))
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)

        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")
        processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

        processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

    # Override
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # met.setMetadataPair(metadata.METADATA_GENERATION_TIME, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        # use method in base converter
        self.getGenerationTime(met)

        # keep some info
        # pleiade or not
        if processInfo.srcProduct.isPneo:
            # if processInfo.srcProduct.isSpot6:
            #    processInfo.addInfo("SPOT6", processInfo.srcProduct.origName)
            # elif processInfo.srcProduct.isSpot7:
            #    processInfo.addInfo("SPOT7", processInfo.srcProduct.origName)
            pass
        else:
            raise Exception("is not a pleiades-neo product")

        # number of preview
        numPreview = len(processInfo.srcProduct.previewContentName)
        processInfo.addInfo(processInfo.srcProduct.origName, "number of preview:%s" % numPreview)

        if self.debug != 0:
            print("metadata dump:\n%s" % met.dump())

    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    # Override
    #
    # make the Jpeg (or Png) browse image from the TIFF image. We want Jpeg
    # construct the browse_metadatareport footprint block: it is the rectifedBrowse for tropforest
    def makeBrowses(self, processInfo, ratio=50):
        processInfo.srcProduct.makeBrowses(processInfo)

    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip: basePath=%s" % (basePath))

        productPath = None
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            self.logger.info("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addIngesterLog("  write done:%s" % processInfo.destProduct.path, 'PROGRESS')

            # output link in other path
            i = 0
            for item in self.outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % (item)
                    self.logger.info("  eoSip product tree path[%d] is:%s" % (i, item))
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                    self.logger.info("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                i = i + 1

        self.logger.info("  done")
        return productPath


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_pneo()

            commandLineInfo = ingester.getCommandLineInfo()
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Pleiades conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)

            reportName = "Pleaides_Neo_conversion_report.txt"
            with open(reportName, 'wt') as fd:
                fd.write(out.getvalue())

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