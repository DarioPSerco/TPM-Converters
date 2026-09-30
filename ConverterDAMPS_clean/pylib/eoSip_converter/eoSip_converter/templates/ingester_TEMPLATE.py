"""For Esa/lite dissemination project

Serco 02/2015 Lavaux Gilles

03/03/2015: V: 0.1
"""
import os
import sys
import traceback
from io import StringIO

from ..base import ingester, reportMaker
from ..esaProducts import product_EOSIP

# minumunm config version that can be use
MIN_CONFIG_VERSION = 1.0


class ingester_TEMPLATE(ingester.Ingester):
    def afterStarting(self, **kwargs):
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
        pass

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        pass

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    #
    def alterReportXml(self, processInfo):
        pass

    def buildEoNames(self, processInfo, namingConvention=None):
        pass

    # Override
    # this is the first function called by the base ingester
    # as input we have the manifest path. Need to use his parent for the product path
    def createSourceProduct(self, processInfo):
        from eoSip_converter.esaProducts.product import Product

        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = Product(processInfo.srcPath)
        product.setDebug(1)
        processInfo.srcProduct = product

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        from eoSip_converter.esaProducts.namingConvention import NamingConvention

        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention(self.OUTPUT_SIP_PATTERN)
        processInfo.destProduct.setNamingConventionSipInstance(namingConventionSip)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionSip)

        self.logger.info(" Eo-Sip product created")
        processInfo.addLog(" Eo-Sip product created")

    #
    # Override
    #
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" verifying product:%s" % processInfo.srcPath)
        self.logger.info(" verifying product")

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog(" prepare product in:%s" % processInfo.workFolder)
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)

        processInfo.addLog("  extracted inside:%s" % processInfo.workFolder)
        self.logger.info("  extracted inside:%s" % processInfo.workFolder)

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        self.getGenerationTime(met)

        # refine
        processInfo.srcProduct.refineMetadata()

    #
    #
    #
    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    #
    # Override
    # make the Jpeg (or Png) browse image from the TIFF image. We want Jpeg
    # construct the browse_metadatareport footprint block: it is the rectifedBrowse for tropforest
    #
    def makeBrowses(self, processInfo, ratio=50):
        pass

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip: basePath=%s" % basePath)
        # return
        # copy eoSip in first path; make links in other paths:

        # now done before in base_ingester.doOneProduct
        # self.outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)

        #
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product will be writen in folder:%s" % firstPath)
            self.logger.info("  Eo-Sip product will be writen in folder:%s" % firstPath)
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addLog("  ok, writen well\n%s" % processInfo.destProduct.info())
            self.logger.info(" ok, writen well\n%s" % processInfo.destProduct.info())
            processInfo.addIngesterLog("  write done:%s" % processInfo.destProduct.path, 'PROGRESS')

            # output link in other path
            i = 0
            for item in self.outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % item
                    self.logger.info("  eoSip product tree path[%d] is:%s" % (i, item))
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                    self.logger.info("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                i = i + 1

        self.logger.info("  done")
        return productPath

    #
    # create a kmz, use the bounding box
    # created in the log folder
    #
    def makeKmz(self, processInfo):
        if not self.test_dont_write:
            from eoSip_converter import kmz

            processInfo.ingester.logger.info("WILL CREATE KMZ")
            outPath = "%s/kmz" % processInfo.ingester.LOG_FOLDER
            if not os.path.exists(outPath):
                self.logger.info("  will make kmz folder:%s" % outPath)
                os.makedirs(outPath)
            kmzPath = kmz.eosipToKmz.makeKmlFromEoSip_new(False, outPath, processInfo)
            print(" KMZ created at path:%s" % kmzPath)
            if kmzPath != None:
                processInfo.addLog("KMZ created at path:%s" % kmzPath)
            else:
                processInfo.addLog("KMZ was NOT CREATED!")
                raise Exception("KMZ was NOT CREATED!")


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_TEMPLATE()
            ingester.debug = 1
            ingester.starts(sys.argv)

            out = StringIO()
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("SPOT-ESA conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            print(out.getvalue())

        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
