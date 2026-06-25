#
# For Esa/lite dissemination project
#
# Serco 02/2015 Lavaux Gilles
#
# 03/03/2015: V: 0.1
#
#
#
#
import sys
import traceback
from io import StringIO

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP, product_spot5_take5
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes
from eoSip_converter.serviceClients import countryResolverClient
from eoSip_converter.serviceClients import townResolverClient
from eoSip_converter.serviceClients import luzResolverClient
import eoSip_converter.gisHelper as gisHelper
import eoSip_converter.xmlHelper as xmlHelper

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = "Spot4-5_take5 converter V:1.0.0"

#
REF_SIP_NAME = "SP5_OPER_NAO_P_S_3__20100720T103912_N46-874_E007-498_0000_v0100.SIP.ZIP"
REF_EO_NAME = "SP5_OPER_NAO_P_S_3__20100720T103912_N46-874_E007-498_0000"

# test: run without the WFS service, LUZ, country etc. will not be resolved
ALLOW_NO_SERVOICE = True

# some constants
NO_LUZ_MESSAGE = "Error resolving LUZ: got no data."
NO_LUZ_FOUND_MESSAGE = "Error resolving LUZ: no result found."

# WANT THE luz ONLY, NO TOWN
WANT_SITE_LUZ = True


#
#
#
class ingester_spot5_take5(ingester.Ingester):

    #
    #
    #
    def getVersionImpl(self):
        return VERSION

    #
    #
    #
    def afterStarting(self, **kargs):
        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")

    #
    # config version is like: name_floatVersion
    #
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    #
    # prepare metadata from a browse report generation
    #
    def prepareBrowseMetadata(self, processInfo):
        pass

    #
    # called before doing the various reports
    #
    #  change the mapping of href from METADATA_PACKAGENAME to METADATA_FULL_PRODUCTNAME
    #
    def beforeReportsDone(self, processInfo):
        #
        processInfo.destProduct.metadata.alterMetadataMaping(
            "href", metadata.METADATA_FULL_PACKAGENAME
        )

        isDimap = processInfo.srcProduct.isDimap
        processInfo.srcProduct.metadata.setMetadataPair("IS_DIMAP", isDimap)
        self.keepInfo("isDimap:%s" % isDimap, processInfo.srcProduct.path)
        processInfo.addLog(" Is source product DIMAP?:%s" % isDimap)

        isN1c = processInfo.srcProduct.isN1c
        if isN1c is not None:
            self.keepInfo("isN1c:%s" % isN1c, processInfo.srcProduct.path)

        isL2 = processInfo.srcProduct.isL2
        if isL2 is not None:
            self.keepInfo("isL2:%s" % isL2, processInfo.srcProduct.path)

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        # alter MD.XML
        self.alterReportXml(processInfo)

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    # add namespace in: <eop:operationalMode
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog("- alterReportXml: product report parsed")
        if self.debug != 0:
            print(" alterReportXml: product report parsed")

        # add namespace:
        codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE
        )
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
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            "alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

    #
    # request is like:
    #
    #  http://localhost:7003/
    #
    #  reply is: site, country
    #
    #
    def getSpot4Take5LuzInfo(self, processInfo):
        #
        footprint = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT
        )
        if self.debug != 0:
            print(" getSpot4Take5LuzInfo; footprint=%s" % footprint)
        # use client
        client = None
        tmp = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_PLATFORM_ID
        )
        if tmp == "4":
            client = luzResolverClient.LuzResolverClient(processInfo)
            client.setDebug(self.debug)
        elif tmp == "5":
            client = luzResolverClient.LuzResolverClient(processInfo, "luzResolver2")
            client.setDebug(self.debug)

        params = []
        params.append(footprint)
        data = client.callWfsService(processInfo, params)
        if self.debug != 0:
            print(" getSpot4Take5LuzInfo; data=%s; type:%s" % (data, type(data)))
        if data is None:
            raise Exception(NO_LUZ_MESSAGE)

        lines = data.split("\n")
        res, n = self.findDataLine(lines, "## items:1")
        if res == None:
            raise Exception(NO_LUZ_FOUND_MESSAGE)

        res, n = self.findDataLine(lines, "# wfsInfo[0]")
        tokens = lines[n + 1].split("|")

        print(" getSpot4Take5LuzInfo; LUX zone=%s; country=%s" % (tokens[0], tokens[2]))
        # os._exit(1)
        return tokens[0], tokens[2]

    #
    # request is like:
    #
    #  http://localhost:7001/polygonToCountry?FOOTPRINT=52.23165364%208.76142652%2052.05466425%208.76142652%2052.05466425%209.01463051%2052.23165364%209.01463051%2052.23165364%208.76142652
    #
    #  reply is like:
    # ## class:lite.PolygonToCountryWfsMatcher
    # ## shapefile:serviceServer/data/gis/TM_WORLD_BORDERS-0.3.shp
    # ## footprint:36.098037266252511 9.086975669616571 35.825717613163953 10.56600354554495 34.873960952777672 10.226078662747391 35.141711859481518 8.764936568236594 36.098037266252511 9.086975669616571
    # ## class:server.httpHandler.PolygonToCountryWfsRequestHandler
    # ## Class:lite.PolygonToCountryWfsMatcher
    # ## shapefile:serviceServer/data/gis/TM_WORLD_BORDERS-0.3.shp
    # ## wantedFieldMap:{0=FIELD_ID, 4=FIELD_DESCRIPTION}
    # ## footprint:36.098037266252511 9.086975669616571 35.825717613163953 10.56600354554495 34.873960952777672 10.226078662747391 35.141711859481518 8.764936568236594 36.098037266252511 9.086975669616571
    # ## items:1
    # wfsInfo[0]
    # TS | key__TS_Tunisia | Tunisia | null | null | null
    #
    #
    def getCountryInfo__NOT_USED(self, processInfo):
        #
        footprint = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT
        )
        if self.debug != 0:
            print(" getCountryInfo; footprint=%s" % footprint)
        # use client
        client = countryResolverClient.CountryResolverClient(processInfo)
        client.setDebug(self.debug)

        params = []
        params.append(footprint)
        data = client.callWfsService(processInfo, params)
        if self.debug != 0:
            print(" getCountryInfo; data=%s; type:%s" % (data, type(data)))
        if data is None:
            raise Exception("Error resolving country info")

        lines = data.split("\n")
        res, n = self.findDataLine(lines, "## items:1")
        if res == None:
            raise Exception("getCountryInfo: no item found")

        res, n = self.findDataLine(lines, "# wfsInfo[0]")
        tokens = lines[n + 1].split("|")

        print(" getCountryInfo; country ISO=%s; name=%s" % (tokens[0], tokens[2]))
        return tokens[0], tokens[2]

    #
    # request is like:
    #
    #  http://localhost:7000/polygonToTown?FOOTPRINT=52.23165364%208.76142652%2052.05466425%208.76142652%2052.05466425%209.01463051%2052.23165364%209.01463051%2052.23165364%208.76142652
    #
    #  reply is like:
    # ## class:server.httpHandler.PolygonToTownWfsRequestHandler
    # ## class:gl.gis.ClosestTown
    # ## shapefile:serviceServer/data/gis/ne_10m_admin_0_countries.shp
    # ## min population:50000
    # ## footprint:36.098037266252511 9.086975669616571 35.825717613163953 10.56600354554495 34.873960952777672 10.226078662747391 35.141711859481518 8.764936568236594 36.098037266252511 9.086975669616571
    # wfsInfo[0]
    # WmsInfo - name:Kairouan
    # WmsInfo - Id:null
    # Description:null
    # WmsInfo - city:null
    # WmsInfo - city_ascii:null
    # WmsInfo - country:Tunisia
    # WmsInfo - country_code:TN
    # WmsInfo - lat - lon[0]:lat = 35.48599910951509 lon = 9.65652716618198
    #
    #
    def getTownInfo__NOT_USED(self, processInfo):
        #
        footprint = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT
        )
        if self.debug != 0:
            print(" getTownInfo; footprint=%s" % footprint)
        # use client
        client = townResolverClient.TownResolverClient(processInfo)
        client.setDebug(self.debug)

        params = []
        params.append(footprint)
        data = client.callWfsService(processInfo, params)
        if self.debug != 0:
            print(" getTownInfo; data=%s; type:%s" % (data, type(data)))
        if data is None:
            raise Exception("Error resolving towm")

        lines = data.split("\n")
        # get town name
        res, n = self.findDataLine(lines, "# wfsInfo[0]")
        tokens = lines[n + 1].split(":")
        townName = tokens[1]
        # get country ISO
        res, n = self.findDataLine(lines, "WmsInfo-country_code:")
        tokens = lines[n].split(":")
        countryIso = tokens[1]
        print(" getTownInfo; country ISO=%s; townName=%s" % (countryIso, townName))
        return countryIso, townName

    #
    #
    #
    def findDataLine(self, lines, pattern):
        res = None
        n = 0
        for line in lines:
            if line.find(pattern) >= 0:
                if self.debug != 0:
                    print(
                        "  !!!!!!!!!!!!!!! findDataLine: pattern '%s' found in line:%s"
                        % (pattern, line)
                    )
                res = line
                break
            n += 1
        return res, n

    #
    #
    #
    def testServiceAvailable(self, processInfo):
        testFootprint = "36.098037266252511 9.086975669616571 35.825717613163953 10.56600354554495 34.873960952777672 10.226078662747391 35.141711859481518 8.764936568236594 36.098037266252511 9.086975669616571"
        #
        if self.debug != 0:
            print("testServiceAvailable; testFootprint=%s" % testFootprint)
        # use client
        client = countryResolverClient.CountryResolverClient(processInfo)
        client.setDebug(self.debug)

        params = []
        params.append(testFootprint)
        data = client.callWfsService(processInfo, params)
        print(" testServiceAvailable; data=%s" % data)

        lines = data.split("\n")
        res, n = self.findDataLine(lines, "## items:1")
        if res == None:
            raise Exception("getLuzInfo: no item found")

        res, n = self.findDataLine(lines, "# wfsInfo[0]")
        tokens = lines[n + 1].split("|")

        print(" testServiceAvailable; country ISO=%s; name=%s" % (tokens[0], tokens[2]))
        return tokens[0], tokens[2]

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # test default in ingester
        self.buildEoNamesDefault(processInfo, namingConvention)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(REF_SIP_NAME):
            print("ref name:%s" % REF_SIP_NAME)
            print("EoSip name:%s" % aName)
            raise Exception(
                "EoSip name has incorrect length:%s VS %s"
                % (len(aName), len(REF_SIP_NAME))
            )
        if aName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

        anEoName = processInfo.destProduct.getEoProductName()
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
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        #
        processInfo.srcPath = processInfo.srcPath.replace("\\", "/")
        product = product_spot5_take5.Product_Spot5_Take5(processInfo.srcPath)
        product.stretcherAppExe = self.stretcherAppExe

        # product.setDebug(1)
        processInfo.srcProduct = product

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.sourceProductPath = processInfo.srcPath
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE)
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        # namingConventionSip.setDebug(1)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        namingConventionEo = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        # namingConventionEo.setDebug(1)
        eosipP.setNamingConventionEoInstance(namingConventionEo)

        self.logger.info(" Eo-Sip product created")
        processInfo.addLog("- Eo-Sip product created")

    #
    # Override
    #
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" verifying product:%s" % (processInfo.srcPath))
        self.logger.info(" verifying product")

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog("- prepare product in:%s" % (processInfo.workFolder))
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(
            processInfo.workFolder, processInfo.test_dont_extract
        )

        processInfo.addLog(" extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")
        processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met, processInfo)

        # met.setMetadataPair(metadata.METADATA_GENERATION_TIME, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        # use method in base converter
        self.getGenerationTime(met)

        # keep some info
        mode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_SENSOR_OPERATIONAL_MODE
        )
        self.keepInfo("sensor mode", mode)
        instrument = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_INSTRUMENT
        )
        self.keepInfo("instrument", instrument)
        typecode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_TYPECODE
        )
        self.keepInfo("typecode", typecode)
        versionOK = processInfo.srcProduct.metadata.getMetadataValue("VERSION_OK")
        self.keepInfo("VERSION_OK", versionOK)

        aFootprint = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT
        )

        # 2020-04-27: get all from shapefiles
        """
            #
            # get country ISO and name
            #
            iso="N/A"
            country="N/A"
            try:
                iso, country = self.getCountryInfo(processInfo)
            except Exception as e:
                #exc_type, exc_obj, exc_tb = sys.exc_info()
                #print "getCountryInfo error: %s; %s" % (exc_type, exc_obj)
                print "getCountryInfo error: %s" % (e)
                traceback.print_exc(file=sys.stdout)
                self.keepInfo("COUNTRY_FAIL", "%s|%s" % (processInfo.srcProduct.path, aFootprint))
                # no country is fatal
                raise e
            self.keepInfo("ISO", iso)
            self.keepInfo("COUNTRY", country)
            #os._exit(1)"""

        #
        # get LUZ zone
        #
        site = None
        country = None
        try:
            site, country = self.getSpot4Take5LuzInfo(processInfo)
            self.keepInfo("LUZ SITE", site)
            self.keepInfo("LUZ COUNTRY", country)
            processInfo.srcProduct.metadata.setMetadataPair("LUZ SITE", site)
            processInfo.srcProduct.metadata.setMetadataPair("LUZ COUNTRY", country)
        except Exception as e:
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # print "getSpot4Take5LuzInfo error: %s; %s" % (exc_type, exc_obj)
            print("getSpot4Take5LuzInfo problem: %s" % (e.message))
            if e.message == NO_LUZ_MESSAGE:  # service return nothing, may be down
                self.keepInfo(
                    "NO_DATA:%s" % processInfo.srcProduct.path,
                    "%s|%s" % (e.message, processInfo.srcProduct.path),
                )
                raise e
            elif e.message == NO_LUZ_FOUND_MESSAGE:  # service return no match
                self.keepInfo(
                    "NO_MATCH:%s" % processInfo.srcProduct.path,
                    "%s|%s|%s" % (e.message, processInfo.srcProduct.path, aFootprint),
                )
                if WANT_SITE_LUZ:
                    res = gisHelper.footprintToJson(
                        processInfo.srcProduct.metadata.getMetadataValue(
                            metadata.METADATA_FOOTPRINT
                        ),
                        "name:%s" % processInfo.srcProduct.origName,
                    )
                    aPath = "%s/take5_site_not_resolved.json" % (processInfo.workFolder)
                    fd = open(aPath, "w")
                    fd.write(res)
                    fd.flush()
                    fd.close()
                    raise Exception("OUT_OF_SITE and town acceptance disabled")
            else:  # other error
                self.keepInfo(
                    "UNEXPECTED ERROR:%s" % processInfo.srcProduct.path,
                    "%s|%s|%s" % (e.message, processInfo.srcProduct.path, aFootprint),
                )
                raise Exception("UNEXPECTED ERROR:%s" % e.message)

        # 2020-04-27: get all from shapefiles
        """
            #
            # get town iso and name if site not found
            #
            iso = None
            town = None
            if site is None:
                try:
                    iso, town = self.getTownInfo(processInfo)
                except Exception as e:
                    #exc_type, exc_obj, exc_tb = sys.exc_info()
                    #print "getTownInfo error: %s; %s" % (exc_type, exc_obj)
                    print "getTownInfo error: %s" % (e)
                    traceback.print_exc(file=sys.stdout)
                    self.keepInfo("TOWN_FAIL",  "%s|%s" % (processInfo.srcProduct.path, aFootprint))
                self.keepInfo("TOWN", town)
                self.keepInfo("ISO", iso)"""

        processInfo.srcProduct.metadata.addLocalAttribute("country", country)
        processInfo.srcProduct.metadata.addLocalAttribute("site", site)

        """else:
                processInfo.srcProduct.metadata.addLocalAttribute("site", town)
                # write footprint as json
                res = gisHelper.footprintToJson(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT), 'Town:%s' % town)
                aPath="%s/take5_site_not_resolved.json" % (processInfo.workFolder)
                fd = open(aPath, 'w')
                fd.write(res)
                fd.flush()
                fd.close()"""
        # processInfo.srcProduct.metadata.addLocalAttribute("ISO", iso)
        # processInfo.srcProduct.metadata.addLocalAttribute("ZONE", zoneName)

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
        processInfo.srcProduct.makeBrowses(processInfo)

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip: basePath=%s" % (basePath))

        #
        productPath = None
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            self.logger.info("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addIngesterLog(
                "  write done:%s" % processInfo.destProduct.path, "PROGRESS"
            )

            # output link in other path
            i = 0
            for item in self.outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % (item)
                    self.logger.info("  eoSip product tree path[%d] is:%s" % (i, item))
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


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_spot5_take5()

            commandLineInfo = ingester.getCommandLineInfo()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Spot4-5 take5 conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Spot4-5_take5_conversion_report.txt"
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
