# Ingester class for the Pleiades mission
import sys
import traceback
from io import StringIO

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes
import eoSip_converter.xmlHelper as xmlHelper

from pleiades import __version__, product_pleiades

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = f"Pleiades converter V:{__version__}"
REF_NAME = 'PL1_OPER_HIR_MS__1A_20001122T112233_N20-882_E095-939_0001.SIP.ZIP'


class ingester_pleiades(ingester.Ingester):
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
        #

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

        if mode == 'P_S':
            processInfo.addLog(" alterReportXml: add subType because sensor mode is %s" % mode)
            result2 = []
            helper.getNodeByPath(entryNode=None, path='result/EarthObservationResult/browse/BrowseInformation', attr=None, result=result2)
            if len(result2) == 0:
                raise Exception("can not find node 'result/EarthObservationResult/browse/BrowseInformation' in MD report")
            for item in result2:
                aNodeReferenceSystemIdentifier = helper.getFirstNodeByPath(item, 'referenceSystemIdentifier', None)
                aNodeServiceReference = helper.getFirstNodeByPath(item, 'fileName/ServiceReference', None)
                href = helper.getNodeAttributeText(aNodeServiceReference, 'xlink:href')
                print(" serviceReference href: %s " % href)
                isMs = False
                if processInfo.srcProduct.previewIsMs[href] == True:
                    print(" alterReportXml href is MS")
                    isMs = True
                else:
                    print(" alterReportXml href is not MS")
                if isMs:
                    nodeSubType = helper.getDomDoc().createElement('eop:subType')
                    helper.setNodeAttributeText(nodeSubType, 'codeSpace', 'urn:esa:eop:HiRI:Bundle:browsesubType')
                    helper.setNodeText(nodeSubType, 'MS')
                    item.insertBefore(nodeSubType, aNodeReferenceSystemIdentifier)
                else:
                    nodeSubType = helper.getDomDoc().createElement('eop:subType')
                    helper.setNodeAttributeText(nodeSubType, 'codeSpace', 'urn:esa:eop:HiRI:Bundle:browsesubType')
                    helper.setNodeText(nodeSubType, 'P')
                    item.insertBefore(nodeSubType, aNodeReferenceSystemIdentifier)
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

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(helper.prettyPrint())
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
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = product_pleiades.Product_Pleiades(processInfo.srcPath)
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
        # d'ont want an Eosip > 2gb done using python zip lib
        if aSize > 1900 * 1024 * 1024:
            processInfo.addLog(" ## zip: will use wrapped library because size >=1.9 gb: %s" % (aSize))
            eosipP.setUsePythonZipLib(False)
        else:
            processInfo.addLog(" ## zip: will use python library because size <1.9 gb: %s" % (aSize))
        #
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionEoInstance(namingConventionSip)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionSip)

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
        if processInfo.srcProduct.isPleiades:
            # if processInfo.srcProduct.isSpot6:
            #    processInfo.addInfo("SPOT6", processInfo.srcProduct.origName)
            # elif processInfo.srcProduct.isSpot7:
            #    processInfo.addInfo("SPOT7", processInfo.srcProduct.origName)
            pass
        else:
            raise Exception("is not a pleiades product")

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
            ingester = ingester_pleiades()

            commandLineInfo = ingester.getCommandLineInfo()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Pleiades conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Pleaides_conversion_report.txt"
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