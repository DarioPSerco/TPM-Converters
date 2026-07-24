import os, sys, inspect
import traceback
from io import StringIO

# add converter package path to sys.path 
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parrent=os.path.dirname(currentdir)
print(("##### eoSip converter package dir:%s" % parrent))
sys.path.insert(0, parrent)

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import definitions_EoSip, metadata, product_EOSIP
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

from geoeye1_json import __version__, product_geoeye1, json_emitter

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION=f"Geoeye1 converter V:{__version__}"

SIP_REF_NAME='GE1_OPER_GIS_PAN_MP_20100527T231608_N13-756_W100-000_0001_v0100.SIP.ZIP'
EO_REF_NAME='GE1_OPER_GIS_PAN_MP_20100527T231608_N13-756_W100-000_0001'


class ingester_geoeye1(ingester.Ingester):

        # JSON converter: disable all eoSIP/XML output at the base-ingester level.
        # The cfg also sets TEST_JUST_EXTRACT_METADATA=True; this is the defensive default.
        test_just_extract_metadata = True

        def getVersionImpl(self):
            return VERSION

        def afterStarting(self, **kargs):
            self.test_just_extract_metadata = True

        #
        # Build and write the JSON metadata manifest (replaces XML/eoSIP output).
        #
        def _emit_json(self, processInfo):
            eoName = processInfo.destProduct.getEoProductName()
            outDir = self.outputProductResolvedPaths[0] if self.outputProductResolvedPaths else processInfo.workFolder
            os.makedirs(outDir, exist_ok=True)
            jsonPath = json_emitter.emit(
                processInfo.destProduct.metadata,
                processInfo.srcProduct,
                eoName,
                outDir,
                native_product_name=processInfo.srcProduct.origName,
            )
            processInfo.addLog("  JSON metadata manifest written: %s" % jsonPath)
            self.logger.info("  JSON metadata manifest written: %s" % jsonPath)
            return jsonPath

        # config version is like: name_floatVersion
        def checkConfigurationVersion(self):
                global MIN_CONFIG_VERSION
                self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)
                

        # prepare metadata from a browse report generation
        def prepareBrowseMetadata(self, processInfo):
                pass

        # called before doing the various reports
        # JSON-only mode: report/output stages downstream are disabled, so emit
        # the JSON manifest here (this hook still runs in extract-metadata mode).
        def beforeReportsDone(self, processInfo):
            self._emit_json(processInfo)

        # called after having done the various reports
        # JSON-only mode: no XML reports and no eoSIP piece list are produced.
        def afterReportsDone(self, processInfo):
            pass


        #
        # called at the end of the doOneProduct, before the index/shopcart creation
        #
        def afterProductDone(self, processInfo):
            pass


        #
        #
        #
        def buildEoNames(self, processInfo, namingConvention=None):

            # force setEoExtension to ZIP. Because we use SRC_PRODUCT_AS_DIR to use several files as input, and we want a .SIP.ZIP package.
            processInfo.destProduct.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))
            # test default in ingester
            self.buildEoNamesDefault(processInfo, namingConvention)

            # test EoSip package name
            aName = processInfo.destProduct.getSipPackageName()
            if len(aName) != len(SIP_REF_NAME):
                print(("Ref name  :%s" % SIP_REF_NAME))
                print(("EoSip name:%s" % aName))
                raise Exception("EoSip name has incorrect length:%s VS %s" % (len(aName), len(SIP_REF_NAME)))

            if aName.find('@') >= 0 or aName.find('#') > 0:
                raise Exception("SipProductName incomplet:%s" % aName)

            anEoName = processInfo.destProduct.getEoProductName()
            if len(anEoName) != len(EO_REF_NAME):
                print(("Ref EO name:%s" % EO_REF_NAME))
                print(("EO name    :%s" % anEoName))
                raise Exception("EO name has incorrect length:%s VS %s" % (len(anEoName), len(EO_REF_NAME)))


            if anEoName.find('@') >= 0 or aName.find('#') > 0:
                raise Exception("EoProductName incomplet:%s" % aName)

            #som = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
            #opm = product_radarsat.operationalMode[som]
            #print(" -> sensor operational mode string:%s" % opm)
            #processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, opm)
            
                
        #
        # Override
        # this is the first function called by the base ingester
        #
        # as input we have the manifest path. Need to use his parent for the product path
        #
        def createSourceProduct(self, processInfo):
            global debug,logger
            #
            processInfo.srcPath=processInfo.srcPath.replace('\\','/')
            product = product_geoeye1.Product_Geoeye1(processInfo.srcPath)
            product.setDebug(1)
            processInfo.srcProduct = product


        #
        # Override
        #
        def createDestinationProduct(self, processInfo):
            global debug,logger
            eosipP=product_EOSIP.Product_EOSIP()
            eosipP.setDebug(1)
            eosipP.sourceProductPath = processInfo.srcPath
            eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE)
            processInfo.destProduct = eosipP

            # set naming convention instance
            namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
            eosipP.setNamingConventionSipInstance(namingConventionSip)

            namingConventionEo = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
            eosipP.setNamingConventionEoInstance(namingConventionEo)
            
            self.logger.info(" Eo-Sip product created")
            processInfo.addLog(" Eo-Sip product created")

                    
        #
        # Override
        #
        def verifySourceProduct(self, processInfo):
                processInfo.addLog(" verifying product:%s" % (processInfo.srcPath))
                self.logger.info(" verifying product");
                

        #
        # Override
        #
        def prepareProducts(self, processInfo):
                processInfo.addLog(" prepare product in:%s" % (processInfo.workFolder))
                self.logger.info(" prepare product");
                processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)
                
                processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
                self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

                self.stretcherAppExe = self.ressourcesProvider.getRessourcePath('stretchAppExe')
                processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

        #
        # Override
        #
        def extractMetadata(self, met, processInfo):
            # fill metadata object
            numAdded=processInfo.srcProduct.extractMetadata(met, processInfo)

            # use method in base converter
            self.getGenerationTime(met)

            # the one using bbox or not
            if processInfo.srcProduct.useBbox:
                self.keepInfo('useBbox', processInfo.srcProduct.path)
            else:
                self.keepInfo('dontUseBbox', processInfo.srcProduct.path)

            # orbit direction
            tmp=processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)
            self.keepInfo(metadata.METADATA_PROCESSING_LEVEL, tmp)

            # satId
            tmp=processInfo.srcProduct.metadata.getMetadataValue('satId')
            self.keepInfo('satId', tmp)


            tmp=processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_RESOLUTION)
            self.keepInfo(metadata.METADATA_RESOLUTION, tmp)
            if float(tmp) != 0.3 and float(tmp) != 0.4 and float(tmp) != 0.5 and float(tmp) != 0.6:
                self.keepInfo("resolution:%s" % tmp, processInfo.srcProduct.path)

            self.keepInfo('imageDescriptor', processInfo.srcProduct.metadata.getMetadataValue('imageDescriptor'))

            self.keepInfo('numberOfBands', processInfo.srcProduct.metadata.getMetadataValue('numberOfBands'))

            self.keepInfo(metadata.METADATA_TYPECODE, processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_TYPECODE))
            self.keepInfo(metadata.METADATA_CLOUD_COVERAGE, processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE))
	    

                
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
            # JSON-only mode: no browse image is produced.
            pass


        #
        # Override
        #
        # JSON-only mode: emit the JSON metadata manifest instead of an eoSIP
        # .SIP.ZIP package. No XML and no ZIP packaging is written. (Not reached
        # in normal JSON mode - output is gated off by TEST_JUST_EXTRACT_METADATA
        # and emission happens in beforeReportsDone. Kept JSON-only so no eoSIP
        # packaging code remains.)
        #
        def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
                self.logger.info("  output_eoSip (JSON): basePath=%s" % (basePath))
                return self._emit_json(processInfo)



if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_geoeye1()

            #ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            ingester.makeConversionReport("Geoeye1 conversion report")

            sys.exit(exitCode)
        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)
            
    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)