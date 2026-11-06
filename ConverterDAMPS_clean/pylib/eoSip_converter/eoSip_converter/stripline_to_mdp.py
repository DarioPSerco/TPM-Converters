"""This will generate MDP packages from ASAR stripline L0 products

Serco 10/2015
Lavaux Gilles
"""
from datetime import datetime, timedelta
import io
import sys
import traceback

from . import imageUtil
from .esaProducts import formatUtils
from .base import ingester
from .esaProducts.ipfIcd import ipfLogger
from .esaProducts import product_EOSIP, product_EOSIP_stripline, product_mdp
from .esaProducts import metadata, browse_metadata
from .esaProducts.namingConvention_AsSource import NamingConvention_AsSource
from .esaProducts.namingConvention_envisat import NamingConvention_Envisat
from .serviceClients import m2bsClient
from .esaProducts.frameStrip import FrameStrip

# minumum config version that can be use
MIN_CONFIG_VERSION = 1.0

# the ASAR reference duration 
PRODUCT_DURATION_LIMIT = 15.09
LONG_PRODUCT_DURATION_LIMIT = 60.0

#
JOBORDER_VERSION_PARAM_NAME = 'MDP_version'

#s
# start test DEBUG stuff, set it False in production!!
#
DONT_RETRIEVE_BROWSE = False
USE_NO_PREVIEW_BROWSE = False
#
# end test DEBUG stuff
#

REF_NAME = 'SSS_PCCC_TTTTTTTTTT_yyyymmddThhmmss_YYYYMMDDTHHMMSS_oooooo_tttt_yYyYmMdDThHmMsS_vvvv.MDP.ZIP'


class StriplineToMdp(ingester.Ingester):

    #
    # config version is like: name_floatVersion
    # if on test mode: set showCHANGED to True
    #
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)
        if self.test_mode:
            # self.logger.info("[PROGRESS] starting converter stripline_to_mdg in TEST_MODE")
            self.showCHANGED = True
        else:
            self.showCHANGED = False

        # self.logger.info("[PROGRESS] starting converter stripline_to_mdg '%s' ..." % self.VERSION_INFO)

    #
    # called ny ingester 'if it exists'
    # set the joborder MDP_version value into METADATA_SIP_VERSION
    # check his length, ensure it is 4 digits long
    #
    def useJobOrder(self):
        self.logger.info(" useJobOrder:%s" % self.jobOrder)
        self.mdpVersion = self.jobOrder.getProcessingParameter(JOBORDER_VERSION_PARAM_NAME)
        if len(self.mdpVersion) > 4:
            nVersion = self.mdpVersion[0:4]
            self.logger.info(" useJobOrder: mdpVersion is too long:%s; cut it to:%s" % (self.mdpVersion, nVersion))
            self.mdpVersion = nVersion
        elif len(self.mdpVersion) < 4:
            nVersion = formatUtils.leftPadString(self.mdpVersion[0:4], 4, '0')
            self.logger.info(" useJobOrder: mdpVersion is too short:%s; change it to:%s" % (self.mdpVersion, nVersion))
            self.mdpVersion = nVersion
        self.logger.info(" useJobOrder: mdpVersion=%s" % self.mdpVersion)

    #
    # all products are 15 sec long, expect WS which are 60 sec
    #
    def getProductLength(self, product):
        typecode = product.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        sensor = typecode.split('_')[1]
        if self.debug != 0:
            print("getProductLength; sensor='%s'" % sensor)
        if sensor == 'WS':
            return LONG_PRODUCT_DURATION_LIMIT
        else:
            return PRODUCT_DURATION_LIMIT

    #
    # verify test mode -> show changed
    #
    def afterStarting(self, **kargs):
        self.logger.info("[PROGRESS] afterStarting")
        if self.test_mode:
            print("StriplineToMdp; is in test mode, will show changes in xmls?: %s" % self.showCHANGED)

    #
    # prepare metadata from a browse report generation
    #
    def prepareBrowseMetadata(self, processInfo):
        pass

    #
    # called before doing the various reports
    #
    def beforeReportsDone(self, processInfo):
        pass

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        processInfo.addIngesterLog(" will build metadata reports ...", 'PROGRESS')
        processInfo.destProduct.buildSsmReportFile()
        processInfo.destProduct.addBrowsesInSsm()
        processInfo.destProduct.addBrowseInMd()
        processInfo.destProduct.makeFramebrowseIntoPieces()
        processInfo.addIngesterLog("  metadata reports builded", 'PROGRESS')

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    # build eoPackgageName and eoProductName
    # add version because not present in source product and namingConvention was decided: as_source
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        #
        ok = False
        loopNum = 0
        while not ok and loopNum < 10:
            print("@@@@@@@@@@@@@@@@@@ buildEoNames loop:%s" % loopNum)
            processInfo.addLog(" buildEoNames loop:%s" % loopNum)
            # processInfo.destProduct.setDebug(1)
            processInfo.destProduct.buildEoNames(namingConvention)
            # processInfo.destProduct.setDebug(0)
            if not self.product_overwrite:
                # test for duplicate
                exists, newFileCounter = self.checkDestinationAlreadyExists(processInfo)
                if exists:
                    processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_FILECOUNTER,
                                                                     "%s" % newFileCounter)
                else:
                    ok = True
            else:
                ok = True
            loopNum += 1
        if not ok:
            raise Exception("error creating product filename: duplicate test reach loop limit of 10")

        aName = processInfo.destProduct.getSipPackageName()
        processInfo.addIngesterLog(" eo 'as source' package name is:%s" % aName, 'PINFO')
        # normaly there is no version, check and add it
        # CHANGE: the EOSIP filename has new the creation date: yYyYmMdDThHmMsS
        # REFNAME         = 'SSS_PCCC_TTTTTTTTTT_yyyymmddThhmmss_YYYYMMDDTHHMMSS_oooooo_tttt_yYyYmMdDThHmMsS_vvvv.MDP.ZIP
        # NO VERSION NAME = 'SSS_PCCC_TTTTTTTTTT_yyyymmddThhmmss_YYYYMMDDTHHMMSS_oooooo_tttt_yYyYmMdDThHmMsS.MDP.ZIP
        endOfName = aName[len('SSS_PCCC_TTTTTTTTTT_yyyymmddThhmmss_YYYYMMDDTHHMMSS_oooooo_tttt_'):]
        processInfo.addIngesterLog(" eo package name version test: end of name from version is '%s'" % endOfName,
                                   'PINFO')
        print("@@@@@@@@@@@@@@@@@@ eo package name version test: end of name from version is '%s'" % endOfName)
        extension = ''
        endOfName2 = endOfName
        pos = endOfName.find('.')
        if pos > 0:
            extension = endOfName[pos:]
            endOfName2 = endOfName[:pos]
        else:
            raise Exception("eo package name has no extension: %s" % aName)
        pos = endOfName.find('_')
        if pos < 0:
            processInfo.addIngesterLog(
                " eo package name no version; endOfName2=%s; extension=%s" % (endOfName2, extension))
            print("@@@@@@@@@@@@@@@@@@ eo package name no version; endOfName2=%s; extension=%s" % (endOfName2, extension))
            # version=endOfName[0:pos]
            # if version=='MDP':
            #        if self.jobOrder!=None:
            #                newName=aName.replace('.MDP.ZIP', '_%s.MDP.ZIP' % self.mdpVersion)
            #                processInfo.addIngesterLog(" eo package name has no version; add it from joborder; new package name is:%s" % newName, 'PINFO')
            #        else:
            #                versionFromCfg = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
            #                newName=aName.replace('.MDP.ZIP', '_%s.MDP.ZIP' % versionFromCfg)
            #                processInfo.addIngesterLog(" eo package name has no version; add it fron config; new package name is:%s" % newName, 'PINFO')
            #        # set it back in dest product
            #        aName=newName
            #        processInfo.destProduct.setSipProductName(aName.replace('.MDP.ZIP', ''))
            #        processInfo.destProduct.setSipPackageName(aName)
            #        processInfo.destProduct.setEoProductName(aName.replace('.MDP.ZIP', ''))

            if self.jobOrder != None:
                newName = aName.replace('_%s' % endOfName, '_%s_%s%s' % (endOfName2, self.mdpVersion, extension))
                processInfo.addIngesterLog(
                    " eo package name has no version; add it from joborder; new package name is:%s" % newName, 'PINFO')
            else:
                versionFromCfg = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
                newName = aName.replace('_%s' % endOfName, '_%s_%s%s' % (endOfName2, versionFromCfg, extension))
                processInfo.addIngesterLog(
                    " eo package name has no version; add it fron config; new package name is:%s" % newName, 'PINFO')
            # set back new package names in dest product
            aName = newName
            eoName = aName.replace(extension, '')
            processInfo.addIngesterLog("@@@@@@@@@@@@@@@@@@@@@@@@ eoName=%s" % eoName)
            print("@@@@@@@@@@@@@@@@@@@@@@@@ eoName=%s" % eoName)
            processInfo.destProduct.setSipProductName(eoName)
            processInfo.destProduct.setSipPackageName(aName)
            processInfo.destProduct.setEoProductName(eoName)
        else:
            processInfo.addIngesterLog(
                " eo package name has version; endOfName2=%s; extension=%s" % (endOfName2, extension))
            print("@@@@@@@@@@@@@@@@@@ eo package name has version; endOfName2=%s; extension=%s" % (
            endOfName2, extension))

        # else:
        #        raise Exception("invalid eo package name: has no '.'")
        # print "\n\n@@@@@@@@@@@@@@@@@@\nnames info:%s" % processInfo.destProduct.getNamesInfo()

        if len(aName) != len(REF_NAME):
            print("ref name:%s" % REF_NAME)
            print("mdp name:%s" % aName)
            raise Exception("MDP name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME)))
        if aName.find('@') >= 0 or aName.find('#') > 0:
            raise Exception("MDP name incomplet:%s" % aName)

    #
    # Override
    # this is the first function called by the base ingester
    #
    # the source product is the EoSip stripline file
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = product_EOSIP_stripline.Product_EOSIP_Stripline(processInfo.srcPath)
        if self.test_mode:
            product.setDebug(1)
        product.loadProduct()
        processInfo.srcProduct = product
        if self.debug != 0:
            print("\n\n\nSOURCE PRODUCT:%s" % product.info())

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        product = product_mdp.Product_Mdp()
        if self.test_mode:
            product.setDebug(1)
        # set dest product showChanged flasg if in test mode
        product.showCHANGED = self.showCHANGED
        product.sourceProductPath = processInfo.srcPath
        product.setSipExtension("MDP.ZIP")
        processInfo.destProduct = product

        # set naming convention instance
        namingConventionSip = NamingConvention_AsSource(self.OUTPUT_SIP_PATTERN)
        namingConventionSip.debug = 1
        processInfo.destProduct.setNamingConventionSipInstance(namingConventionSip)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionSip)
        if self.debug != 0:
            print("\n\n\DEST PRODUCT:%s" % processInfo.destProduct.info())

        self.logger.info(" mdp product created")
        processInfo.addLog(" mdp product created")

    #
    # Override
    #
    #
    def verifySourceProduct(self, processInfo):
        pass

    #
    # check that product is at least 15 SEC (or 60 sec for typecode ??)
    #
    def verifyDuration(self, processInfo):
        processInfo.addLog(" verifying product:%s" % processInfo.srcPath)
        self.logger.info(" verifying product")

        startDate = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        startTime = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_START_TIME)
        startMs = 0
        pos = startTime.find('.')
        if pos > 0:
            startMs = startTime[pos + 1:]
            start = "%sT%sZ" % (startDate, startTime[0:pos])

        stopDate = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        stopTime = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)
        stopMs = 0
        pos = stopTime.find('.')
        if pos > 0:
            stopMs = stopTime[pos + 1:]
            stop = "%sT%sZ" % (stopDate, stopTime[0:pos])
        if self.debug != 0:
            print(" source product: start:%s ms:%s;  stop:%s ms:%s" % (start, startMs, stop, stopMs))

        # duration in sec
        duration = formatUtils.dateDiffmsec(start, int(startMs), stop, int(stopMs))
        processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_DURATION, "%s" % duration)

        d1 = datetime.strptime(start, formatUtils.DEFAULT_DATE_PATTERN)
        startMsF = float(startMs)
        processInfo.addLog("  source date start:%s; msec:%s" % (d1, startMsF))
        d1 = d1 + timedelta(milliseconds=startMsF)

        d2 = datetime.strptime(stop, formatUtils.DEFAULT_DATE_PATTERN)
        stopMsF = float(stopMs)
        processInfo.addLog("  source date stop:%s; msec:%s" % (d2, stopMsF))
        d2 = d2 + timedelta(milliseconds=stopMsF)

        # duration in HH:MN:SS.msec
        duration_Hms = d2 - d1
        processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_DURATION_HMS, "%s" % duration_Hms)
        processInfo.addLog("  source product duration:%s; duration_Hms=%s" % (duration, duration_Hms))
        self.logger.info("  source product duration:%s; duration_Hms=%s" % (duration, duration_Hms))
        if self.debug != 0:
            print("  source product duration:%s; duration_Hms=%s" % (duration, duration_Hms))

        typecode = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        sensor = typecode.split('_')[1]
        print("getProductLength; sensor='%s'" % sensor)
        refDuration = -1
        if sensor == 'WS':
            refDuration = LONG_PRODUCT_DURATION_LIMIT
        else:
            refDuration = PRODUCT_DURATION_LIMIT
        if duration < refDuration:
            raise Exception("Product too short; duration:%s (%s sec); min=%s" % (duration_Hms, duration, refDuration))

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog(" prepare product in:%s" % processInfo.workFolder)
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)

        self.noBrowseData = None

        processInfo.addLog("  extracted inside:%s" % processInfo.workFolder)
        self.logger.info("  extracted inside:%s" % processInfo.workFolder)

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        processInfo.addIngesterLog(" will extract metadata ...", 'PROGRESS')

        # we don't want to use the processing center from the product, but the one given in configuration
        configProcessingCenter = met.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)

        numAdded = processInfo.srcProduct.extractMetadata(met)
        if self.debug != 0:
            print(" extractMetadata METADATA dump:\n%s" % met.toString())
        processInfo.addIngesterLog("  metadata extracted", 'PROGRESS')

        # change MDP_version value into METADATA_SIP_VERSION if joborder
        if self.jobOrder is not None:
            versionFromCfg = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
            processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION, self.mdpVersion)
            processInfo.addIngesterLog(
                "  metadata METADATA_SIP_VERSION changed from:%s to %s" % (versionFromCfg, self.mdpVersion), 'PROGRESS')

        #
        processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, configProcessingCenter)

        #
        self.verifyDuration(processInfo)

        #
        self.checkFirstLastFrame(processInfo)

        #
        self.adjustFramesIdentifierInFrames(processInfo)

    #
    # build the strip footprint from the SSM frames
    #
    def getStripFootprintFromSsm(self, processInfo):
        processInfo.addIngesterLog(" getting stripline info from SSM ...", 'PROGRESS')
        side0 = ''
        side1 = ''
        vertex0 = None
        vertex1 = None
        first = None
        for frameId in processInfo.srcProduct.getFramesKeys():
            frame = processInfo.srcProduct.getFrame(frameId)
            print("   getStripFootprintFromSsm n=%s; frame:%s;" % (frameId, frame.info()))
            # afootprint = frame.getFootprint()
            afootprint = frame.getProperty(metadata.METADATA_FOOTPRINT)
            print("   getStripFootprintFromSsm n=%s; afootprint=%s;" % (frameId, afootprint))
            toks = afootprint.split(' ')
            if first == None:
                first = "%s %s" % (toks[0], toks[1])
            if len(side0) > 0:
                side0 = "%s " % side0
            side0 = "%s%s %s" % (side0, toks[0], toks[1])
            vertex0 = "%s %s" % (toks[2], toks[3])

            if len(side1) > 0:
                side1 = " %s" % side1
            side1 = "%s %s%s" % (toks[6], toks[7], side1)
            vertex1 = "%s %s" % (toks[4], toks[5])
            print("   getStripFootprintFromSsm n=%s; side0=%s; side1=%s;" % (frameId, side0, side1))
        # add lest side vertex
        side0 = "%s %s" % (side0, vertex0)
        side1 = "%s %s" % (vertex1, side1)
        print(" getStripFootprintFromSsm side0=%s; side1=%s; first=%s;" % (side0, side1, first))
        print(" getStripFootprintFromSsm result:%s %s %s" % (side0, side1, first))
        processInfo.addIngesterLog(" got stripline info", 'PROGRESS')
        return "%s %s %s" % (side0, side1, first)

    #
    # expand the first and last frame
    # called from self.extractMetadata()
    #
    # to to this: create a FrameStrip, fill it with frame info from src product
    #
    #
    #
    def checkFirstLastFrame(self, processInfo):
        processInfo.addIngesterLog("check and adjust stripline first and last frame ...", 'PROGRESS')
        # use footprint (the MD one)
        footprint = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        print("  refineMetadata footprint:%s" % footprint)
        # create framestrip
        frameStrip = FrameStrip()
        frameStrip.showCHANGED = processInfo.ingester.showCHANGED
        # this will create the frames in the FrameStrip:
        frameStrip.setFootprintString(footprint)

        print(" MD footprint:%s" % frameStrip.getFootprintString())
        print(" SSM footprint:%s" % self.getStripFootprintFromSsm(processInfo))

        # set times and other values we want to modify in framestrip, taken from striplineEoSip.Frames
        # also verify that MD has same number of frame than SSM
        ssmNumFrames = processInfo.srcProduct.getNumFrames()
        if ssmNumFrames != frameStrip.getNumFootprintFrames():
            # correct the MD footprint: build it starting from SSM footprints
            correctedMdFootprint = self.getStripFootprintFromSsm(processInfo)
            print("########### footprint:%s CHANGED correctedMdFootprint:'%s'" % (footprint, correctedMdFootprint))
            processInfo.addLog(
                "########### footprint:%s CHANGED correctedMdFootprint:'%s'" % (footprint, correctedMdFootprint))
            self.keepInfo('correctedFootprint', "%s (SSM:%s vs MD:%s): %s CHANGED %s" % (
            processInfo.srcProduct.origName, ssmNumFrames, frameStrip.getNumFootprintFrames(), footprint,
            correctedMdFootprint))
            # raise Exception("number of frame mismatch: MD has %s; SSM has %s" % (frameStrip.getNumFootprintFrames(), ssmNumFrames))
            processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, correctedMdFootprint)
            # recreate frameStrinp
            frameStrip = FrameStrip()
            frameStrip.showCHANGED = processInfo.ingester.showCHANGED
            frameStrip.setFootprintString(correctedMdFootprint)

        processInfo.addLog(
            "number of frame: MD has %s; SSM has %s" % (frameStrip.getNumFootprintFrames(), ssmNumFrames))
        for frameNum in range(ssmNumFrames):
            srcFrame = processInfo.srcProduct.getFrame(frameNum)
            processInfo.addLog("frameStrip.frame[%s]: get info from srcProduct.Frame:%s" % (frameNum, srcFrame.info()))
            stripFrame = frameStrip.getFrameFromFootprint(frameNum)
            startDateTime = srcFrame.getProperty(metadata.METADATA_START_DATE_TIME)
            stopDateTime = srcFrame.getProperty(metadata.METADATA_STOP_DATE_TIME)
            processInfo.addLog(
                "frameStrip.frame[%s]: startDateTime:%s; stopDateTime:%s" % (frameNum, startDateTime, stopDateTime))
            #
            startTimeFromAscending = srcFrame.getProperty(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE)
            completionTimeFromAscending = srcFrame.getProperty(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE)
            #
            processInfo.addLog("frameStrip.frame[%s]: startTimeFromAscending:%s; completionTimeFromAscending:%s" % (
            frameNum, startTimeFromAscending, completionTimeFromAscending))
            #
            wrsLatitudeGrid = srcFrame.getProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
            wrsLongitudeGrid = srcFrame.getProperty(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED)
            processInfo.addLog("frameStrip.frame[%s]: wrsLatitudeGrid:%s; wrsLongitudeGrid:%s" % (
            frameNum, wrsLatitudeGrid, wrsLongitudeGrid))
            #
            ascending = srcFrame.getProperty(metadata.METADATA_ORBIT_DIRECTION)
            processInfo.addLog("frameStrip.frame[%s]: ascending:%s" % (frameNum, ascending))
            #
            stripFrame.setProperty(metadata.METADATA_START_DATE_TIME, startDateTime)
            stripFrame.setProperty(metadata.METADATA_STOP_DATE_TIME, stopDateTime)
            stripFrame.setProperty(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE, startTimeFromAscending)
            stripFrame.setProperty(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE, completionTimeFromAscending)
            stripFrame.setProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, wrsLatitudeGrid)
            stripFrame.setProperty(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, wrsLongitudeGrid)
            stripFrame.setProperty(metadata.METADATA_ORBIT_DIRECTION, ascending)
            startms = formatUtils.dateTimeMsecsStringToMsecs(startDateTime)
            stopms = formatUtils.dateTimeMsecsStringToMsecs(stopDateTime)
            stripFrame.setStartTimeMsec(startms)
            stripFrame.setStopTimeMsec(stopms)

        # print frames info
        processInfo.addLog("!!!!!!!!!!! all source footprint:")
        allFootprint = ''
        allDistances = ''
        allDurations = ''
        for frameNum in range(ssmNumFrames):
            frame = frameStrip.getFrameFromFootprint(frameNum)
            if len(allFootprint) > 0:
                allFootprint = allFootprint + '\n'
            allFootprint = "%s%s" % (allFootprint, frame.getFootprint())
            if len(allDistances) > 0:
                allDistances = allDistances + '\n'
            allDistances = "%s%s" % (allDistances, frameStrip.getFrameDistance(frameNum))
            if len(allDurations) > 0:
                allDurations = allDurations + '\n'
            allDurations = "%s%s" % (allDurations, frame.getDurationMsec())
        processInfo.addLog(
            "original footprints info:\n%s\nall footprints distance:\n%s\nall footprints duration:\n%s" % (
            allFootprint, allDistances, allDurations))

        # expand first and  last strip
        length = self.getProductLength(processInfo.srcProduct)
        expanded, log = frameStrip.expandFirstFrameFootprint(length)
        if self.debug != 0:
            print(" checkFirstLastFrame: first frame expanded by: %s percent\nlog:%s\n" % (expanded, log))
        processInfo.addLog("first frame expanded; log:\n%s\n" % log)
        if expanded > 0:
            tmp = processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_FOOTPRINT)
            frameInStrip = frameStrip.getFrameFromFootprint(0)
            processInfo.addLog("frameInStrip[%s]: %s" % (0, frameInStrip.info()))
            processInfo.addLog("first frame footprint changed from: %s to: %s" % (tmp, frameInStrip.getFootprint()))
            processInfo.srcProduct.frames[0].setProperty(metadata.METADATA_FOOTPRINT, frameInStrip.getFootprint())

        expanded, log = frameStrip.expandLastFrameFootprint(length)
        if self.debug != 0:
            print(" checkFirstLastFrame: last frame expanded by: %s percent\nlog:%s\n" % (expanded, log))
        processInfo.addLog("last frame expanded; log:\n%s\n" % log)
        lastFrame = len(list(processInfo.srcProduct.frames.keys())) - 1
        if expanded > 0:
            tmp = processInfo.srcProduct.frames[lastFrame].getProperty(metadata.METADATA_FOOTPRINT)
            frameInStrip = frameStrip.getFrameFromFootprint(lastFrame)
            processInfo.addLog("frameInStrip[%s]: %s" % (lastFrame, frameInStrip.info()))
            processInfo.addLog("last frame footprint changed from: %s to: %s" % (tmp, frameInStrip.getFootprint()))
            processInfo.srcProduct.frames[lastFrame].setProperty(metadata.METADATA_FOOTPRINT,
                                                                 frameInStrip.getFootprint())

        # get back corrected values from framestrip frame 0 and last, set them in striplineEoSip.Frames
        # FIRST
        firstStripFrame = frameStrip.getFrameFromFootprint(0)
        firstSrcFrame = processInfo.srcProduct.getFrame(0)
        #
        print("PB: %s" % firstStripFrame.info())
        footprint = firstStripFrame.getProperty(metadata.METADATA_FOOTPRINT)
        firstSrcFrame.setProperty(metadata.METADATA_FOOTPRINT, footprint)
        #
        sceneCenter = firstStripFrame.getProperty(metadata.METADATA_SCENE_CENTER)
        firstSrcFrame.setProperty(metadata.METADATA_SCENE_CENTER, sceneCenter)
        #
        stopdateTime = firstStripFrame.getProperty(metadata.METADATA_STOP_DATE_TIME)
        firstSrcFrame.setProperty(metadata.METADATA_STOP_DATE_TIME, stopdateTime)
        stopdate = firstStripFrame.getProperty(metadata.METADATA_STOP_DATE)
        firstSrcFrame.setProperty(metadata.METADATA_STOP_DATE, stopdate)
        stopTime = firstStripFrame.getProperty(metadata.METADATA_STOP_TIME)
        firstSrcFrame.setProperty(metadata.METADATA_STOP_TIME, stopTime)
        # keep old duration to make the colrowlist
        duration = firstStripFrame.durationMsec
        oldDuration = firstSrcFrame.getProperty(metadata.METADATA_DURATION)
        firstSrcFrame.setProperty('old_duration', oldDuration)
        firstSrcFrame.setProperty(metadata.METADATA_DURATION, duration)
        #
        completionFromAscending = firstStripFrame.getProperty(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE)
        firstSrcFrame.setProperty(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE, completionFromAscending)
        #
        frame = firstStripFrame.getProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        firstSrcFrame.setProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, frame)

        firstFrameIdentifier = self.buildFrameIdentifier(processInfo, 0)
        processInfo.addLog(" firstFrameIdentifier:%s" % firstFrameIdentifier)

        # LAST
        lastStripFrame = frameStrip.getFrameFromFootprint(lastFrame)
        lastSrcFrame = processInfo.srcProduct.getFrame(lastFrame)
        #
        footprint = lastStripFrame.getProperty(metadata.METADATA_FOOTPRINT)
        lastSrcFrame.setProperty(metadata.METADATA_FOOTPRINT, footprint)
        #
        sceneCenter = lastStripFrame.getProperty(metadata.METADATA_SCENE_CENTER)
        lastSrcFrame.setProperty(metadata.METADATA_SCENE_CENTER, sceneCenter)
        #
        startdateTime = lastStripFrame.getProperty(metadata.METADATA_START_DATE_TIME)
        lastSrcFrame.setProperty(metadata.METADATA_START_DATE_TIME, startdateTime)
        startdate = lastStripFrame.getProperty(metadata.METADATA_START_DATE)
        lastSrcFrame.setProperty(metadata.METADATA_START_DATE, startdate)
        startTime = lastStripFrame.getProperty(metadata.METADATA_START_TIME)
        lastSrcFrame.setProperty(metadata.METADATA_START_TIME, startTime)
        # keep old duration to make the colrowlist
        duration = lastStripFrame.durationMsec
        oldDuration = lastSrcFrame.getProperty(metadata.METADATA_DURATION)
        lastSrcFrame.setProperty('old_duration', oldDuration)
        lastSrcFrame.setProperty(metadata.METADATA_DURATION, duration)
        #
        startFromAscending = lastStripFrame.getProperty(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE)
        lastSrcFrame.setProperty(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE, startFromAscending)
        #
        frame = lastStripFrame.getProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        lastSrcFrame.setProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, frame)

        lastFrameIdentifier = self.buildFrameIdentifier(processInfo, lastFrame)
        processInfo.addLog(" lastFrameIdentifier:%s" % lastFrameIdentifier)

        processInfo.addLog("!!!!!!!!!!! all final footprint:")
        allFootprint = ''
        for frameNum in range(ssmNumFrames):
            frame = frameStrip.getFrameFromFootprint(frameNum)
            if len(allFootprint) > 0:
                allFootprint = allFootprint + '\n'
            allFootprint = "%s%s" % (allFootprint, frame.getFootprint())
        processInfo.addLog("final footprints info:\n%s\n" % allFootprint)
        processInfo.addIngesterLog("  first and last frame checked", 'PROGRESS')

    #
    # adjust the frame identifier of all frames
    # build the browse name
    #
    def adjustFramesIdentifierInFrames(self, processInfo):
        ssmNumFrames = processInfo.srcProduct.getNumFrames()
        for frameNum in range(ssmNumFrames):
            frame = processInfo.srcProduct.getFrame(frameNum)
            oldIdentifier = frame.getProperty(metadata.METADATA_IDENTIFIER)
            newIdentifier = self.buildFrameIdentifier(processInfo, frameNum)
            processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; \noldIdentifier:%s\nnewIdentifierr:%s" % (
            frameNum, oldIdentifier, newIdentifier))
            print("adjustFramesIdentifierInFrames frame[%s]; \noldIdentifier:%s\nnewIdentifierr:%s" % (
            frameNum, oldIdentifier, newIdentifier))

            # keep source <P><ccc>: 2054 bellow
            # keep also version: 0000 bellow
            # ASA_IM__0PNESA20070101_051054_000000112054_00191_25295_0000_5
            # toks = oldIdentifier.split('_')
            # tmp=toks[4][-4:]
            # processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; keep phase+cycle 4digits=:%s" % (frameNum, tmp))
            # if self.DEBUG!=0:
            #        print "adjustFramesIdentifierInFrames frame[%s]; keep phase+cycle: 4digits=%s\noldIdentifier:%s" % (frameNum, tmp, oldIdentifier)

            # can rely on _ delimiter only after having passed the typecode than can contains various number of _

            toks = oldIdentifier[10:].split('_')
            tmp = toks[2][-4:]
            counter = toks[5]

            toks2 = newIdentifier[10:].split('_')
            newIdentifier2 = newIdentifier[0:10]
            n = 0
            for item in toks2:
                # if len(newIdentifier2)>0:
                if n > 0:
                    newIdentifier2 = '%s_' % newIdentifier2
                # newIdentifier2='%s%s' % (newIdentifier2, item)
                # processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; newIdentifier2[%s]:%s" % (frameNum, n, newIdentifier2))
                if n == 5:
                    newIdentifier2 = '%s%s' % (newIdentifier2, counter)
                    processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; n==2 newIdentifier2[%s]:%s" % (
                    frameNum, n, newIdentifier2))
                elif n == 2:
                    newIdentifier2 = '%s%s' % (newIdentifier2, item)
                    newIdentifier2 = "%s%s" % (newIdentifier2[0:len(newIdentifier2) - 4], tmp)
                    processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; n==4 newIdentifier2[%s]:%s" % (
                    frameNum, n, newIdentifier2))
                else:
                    newIdentifier2 = '%s%s' % (newIdentifier2, item)
                    processInfo.addLog("adjustFramesIdentifierInFrames frame[%s]; newIdentifier2[%s]:%s" % (
                    frameNum, n, newIdentifier2))
                n += 1
            processInfo.addLog(
                "adjustFramesIdentifierInFrames frame[%s]; newIdentifier2:%s" % (frameNum, newIdentifier2))
            if self.debug != 0:
                print("newIdentifier:%s" % newIdentifier2)

            # test no # in names
            if newIdentifier2.find('#') >= 0:
                raise Exception("frame identifier naming convention build is incomplet:%s" % newIdentifier2)

            # test length ok
            if len(oldIdentifier) != len(newIdentifier2):
                raise Exception("frame identifier length mismatch:%s VS %s" % (oldIdentifier, newIdentifier2))

            if self.showCHANGED:
                frame.setProperty(metadata.METADATA_IDENTIFIER, "%s CHANGED: %s" % (oldIdentifier, newIdentifier2))
            else:
                frame.setProperty(metadata.METADATA_IDENTIFIER, "%s" % newIdentifier2)
            vf = frame.getProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
            try:
                pos = vf.rindex(' ')
                vf = vf[pos + 1:]
            except:
                pass
            vf = formatUtils.leftPadString(vf, 4, '0')
            vt = formatUtils.leftPadString(frame.getProperty(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED), 4, '0')
            # changed from SIP_PRODUCT_NAM_track_frame.BI.JPG to:SIP_PRODUCT_NAM.BI_track_frame.JPG
            # browseIdentifier = "@SIP_PRODUCT_NAME@_%s_%s" % (vt, vf)
            # frame.setProperty(browse_metadata.BROWSE_METADATA_FILENAME, "%s.BI.JPG" % browseIdentifier)
            browseIdentifier = "@SIP_PRODUCT_NAME@.BI_%s_%s.JPG" % (vt, vf)
            frame.setProperty(browse_metadata.BROWSE_METADATA_FILENAME, browseIdentifier)
            processInfo.addLog(
                "adjustFramesIdentifierInFrames frame[%s]; browseIdentifier:%s" % (frameNum, browseIdentifier))
            if self.debug != 0:
                print("adjustFramesIdentifierInFrames frame[%s]; browseIdentifier:%s" % (frameNum, browseIdentifier))

    #
    # return the eop:identifier
    #
    # CHANGE: to build the identifier we need to have in block 5: <dddddddd><P><ccc> the phase Id + the cycle number. Get them from source identifier
    #
    #
    def buildFrameIdentifier(self, processInfo, frameId):
        neededMetadata = [metadata.METADATA_TYPECODE, metadata.METADATA_PROCESSING_STAGE_FLAG,
                          metadata.METADATA_PROCESSING_CENTER,
                          metadata.METADATA_START_DATE, metadata.METADATA_START_TIME, metadata.METADATA_DURATION,
                          metadata.METADATA_TRACK,
                          metadata.METADATA_ORBIT, metadata.METADATA_SIP_VERSION]
        # note: we don't have the phaseId + cycle, so the builded identifier will have #### inside
        # but it will be filled above in adjustFramesIdentifierInFrames()
        namingConvention = NamingConvention_Envisat()
        srcFrame = processInfo.srcProduct.getFrame(frameId)

        met = metadata.Metadata()
        for item in neededMetadata:
            tmp = None
            processInfo.addLog("#### buildFrameIdentifier[%s]: frame info:\n%s" % (frameId, srcFrame.info()))
            if srcFrame.hasPropertyKey(item):
                tmp = srcFrame.getProperty(item)
                if self.debug == 0:
                    processInfo.addLog(
                        "#### buildFrameIdentifier[%s]:  got metadata:%s from frame:%s" % (frameId, item, tmp))
            else:
                if processInfo.srcProduct.metadata.hasMetadataName(item):
                    tmp = processInfo.srcProduct.metadata.getMetadataValue(item)
                    if self.debug == 0:
                        processInfo.addLog(
                            "#### buildFrameIdentifier[%s]:  got metadata:%s from src product metadata:%s" % (
                            frameId, item, tmp))
            met.setMetadataPair(item, tmp)

        namingConvention.setDebug(self.debug)
        namingConvention.setDebug(1)
        identifier = namingConvention.buildProductName(met)
        # test no # in names
        # if identifier.find('#')>=0:
        #        raise Exception("frame identifier naming convention build is incomplet:%s" % identifier)
        if self.debug == 0:
            processInfo.addLog("#### buildFrameIdentifier[%s]:  identifier:%s" % (frameId, identifier))
        return identifier

    #
    #
    #
    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    #
    # retrieve the no preview browse name + image data
    #
    # to be called once
    #
    def getNoPreviewImage(self, processInfo):
        if self.noBrowseData == None:
            self.noBrowsePath = self.ressourcesProvider.getRessourcePath('noPreviewImage')
            if self.debug != 0:
                print(" get no browse data from:%s" % self.noBrowsePath)
            processInfo.addLog(" get no browse data from:%s" % self.noBrowsePath)
            fd = open(self.noBrowsePath, 'r')
            self.noBrowseData = fd.read()
            fd.close()
            if self.debug != 0:
                print(" got no browse data length:%s" % len(self.noBrowseData))
            processInfo.addLog(" got no browse data length:%s" % len(self.noBrowseData))

    #
    #
    #
    def getValueFromChangedString(self, mess):
        pos = mess.find('CHANGED:')
        if pos >= 0:
            return mess[pos + len('CHANGED:') + 1:]
        else:
            return mess

    #
    # Override
    # make the Jpeg (or Png) browse image. Retrieve them from m2bs
    #
    # strip browse filename like: EN1_NPDE_ASA_APH_0P_20021122T023858_20021122T024002_003808_0247_1234.BI.JPG
    # frame browse filename like: EN1_OPDE_ASA_APC_0P_20090315T002138_20090315T002153_036801_0174_<version>.BI_<track>_<frame>.JPG
    #                             actual: EN1_NPDE_ASA_APH_0P_20021122T023858_20021122T024002_003808_0247_1234_0247_0909.BI.JPG
    #
    def makeBrowses(self, processInfo, ratio=50):
        self.logger.info("  makeBrowses: frames:%s" % list(processInfo.srcProduct.frames.keys()))
        processInfo.addIngesterLog(" will make browses: frames:%s ..." % list(processInfo.srcProduct.frames.keys()),
                                   'PROGRESS')
        if self.debug != 0:
            print("  makeBrowses: frames:%s" % list(processInfo.srcProduct.frames.keys()))

        # use m2bs service
        client = m2bsClient.M2bsClient(processInfo)
        client.setDebug(self.debug)

        #
        processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'not-done')
        numFrameBrowseRetrived = 0
        mainBrowseRetrived = False

        # get browse for full strip
        print("  makeBrowses: get full strip browse")
        processInfo.addLog("  makeBrowses: get full strip browse")
        try:
            params = []
            params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM))
            platform_id = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
            if self.debug != 0:
                print(" makeBrowses: platform_id:'%s'" % platform_id)
            if platform_id is not None:
                params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID))
            else:
                params.append("1")

            start = "%sT%sZ" % (processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_START_DATE),
                                processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_START_TIME))
            stop = "%sT%sZ" % (processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
                               processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_STOP_TIME))

            params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_TYPECODE))
            params.append(start)
            params.append(stop)
            params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION))

            if self.debug != 0:
                print("  makeBrowses: strip footprint:%s" % processInfo.srcProduct.metadata.getMetadataValue(
                    metadata.METADATA_FOOTPRINT))
            processInfo.addLog("  makeBrowses: strip footprint:%s" % processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_FOOTPRINT))

            if self.debug != 0:
                print("  makeBrowses: strip duration:%s" % processInfo.srcProduct.metadata.getMetadataValue(
                    metadata.METADATA_DURATION))
            processInfo.addLog("  makeBrowses: strip duration:%s" % processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_DURATION))

            data = None
            try:
                if DONT_RETRIEVE_BROWSE:
                    raise Exception("TEST: get browse disabled")
                # client.setDebug(1)
                data = client.callWfsService(processInfo, params)
                mainBrowseRetrived = True
                if self.debug != 0:
                    if data is not None:
                        print("  makeBrowses: received MAIN BROWSE DATA length:%s" % (len(data)))
                    else:
                        print("  makeBrowses: received MAIN BROWSE DATA is None")
            except:
                print(" make main browse Error:")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                # print "HAHAHA %s %s" % (exc_type, exc_obj)
                traceback.print_exc(file=sys.stdout)
                print("  makeBrowses: NO MAIN BROWSE")
                if USE_NO_PREVIEW_BROWSE:
                    self.getNoPreviewImage(processInfo)
                    data = self.noBrowseData
                # else:
                #        data='no preview'

            print("  makeBrowses: Url:%s" % client.lastCalledUrl)
            processInfo.addLog("  makeBrowses: Url:%s" % client.lastCalledUrl)
            if len(data) > 0:
                # create browse file with name:  EN1_OESR_ASA_IM__0P_20100204T002608_20100204T002623_041467_0331_0001.BI.JPG
                # BI_TRACK_FRAME
                browseName = processInfo.destProduct.getSipProductName()
                browseDestPath = "%s/%s.BI.JPG" % (processInfo.destProduct.folder, browseName)
                fd = open(browseDestPath, 'w')
                fd.write(data)
                fd.flush()
                fd.close()

                # get image size
                width, height = imageUtil.get_image_size(browseDestPath)
                if self.debug != 0:
                    print("  makeBrowses: strip browse width:%s, height=%s" % (width, height))
                processInfo.addLog("  makeBrowses: strip browse width:%s, height=%s" % (width, height))

                processInfo.destProduct.addSourceBrowse(browseDestPath, [])
                processInfo.destProduct.imageWidth = width
                processInfo.destProduct.imageHeight = height

                if self.debug != 0:
                    print("  makeBrowses: strip browse saved at path:%s" % browseDestPath)
                processInfo.addLog("  makeBrowses: strip browse saved at path:%s" % browseDestPath)
                processInfo.addIngesterLog("  makeBrowses: got strip browse:'%s'" % browseDestPath, 'PROGRESS')
            else:
                print("#####  makeBrowses: no strip data retrieved")
                processInfo.addLog("  makeBrowses: no strip data retrieved")
                processInfo.addIngesterLog("  makeBrowses: no strip data retrieved", 'PROGRESS')
        except:
            print(" make strip browse Error:")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)

            # get browse for every frame, add them in dest product as piece
        #
        # ER1_OPDE_SAR_IM__0P_19990522T101026_19990522T101041_041049_0480_0001.BI_0480_0256.JPG : .BI_tttt_ffff.JPG
        #
        for key in processInfo.srcProduct.getFramesKeys():
            if self.debug != 0:
                print("\n  makeBrowses: doing frame:%s" % key)
            processInfo.addLog("\n  makeBrowses: doing frame:%s" % key)
            try:
                frame = processInfo.srcProduct.getFrame(key)
                if self.debug != 0:
                    print("  makeBrowses: frame:%s; dump:\n%s" % (frame, frame.info()))
                params = []
                #
                params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM))
                platform_id = processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)
                if self.debug != 0:
                    print(" makeBrowses: platform_id:'%s'" % platform_id)
                if platform_id is not None:
                    params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID))
                else:
                    params.append("1")

                #
                params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_TYPECODE))

                #
                astart = frame.getProperty(metadata.METADATA_START_DATE_TIME)
                if self.showCHANGED:
                    astart = self.getValueFromChangedString(astart)
                params.append(astart)

                astop = frame.getProperty(metadata.METADATA_STOP_DATE_TIME)
                if self.showCHANGED:
                    astop = self.getValueFromChangedString(astop)
                params.append(astop)

                if self.debug != 0:
                    print(" makeBrowses: start date time:'%s'" % astart)
                    print(" makeBrowses: stop date time:'%s'" % astop)
                processInfo.addLog(" makeBrowses: start date time:'%s'" % astart)
                processInfo.addLog(" makeBrowses: stop date time:'%s'" % astop)

                #
                params.append(processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION))

                #
                processInfo.addLog("  makeBrowses: frame footprint:%s" % frame.getProperty(metadata.METADATA_FOOTPRINT))
                processInfo.addLog("  makeBrowses: frame duration:%s" % frame.getProperty(metadata.METADATA_DURATION))
                if self.debug != 0:
                    print("  makeBrowses: frame footprint:%s" % frame.getProperty(metadata.METADATA_FOOTPRINT))
                    print("  makeBrowses: frame duration:%s" % frame.getProperty(metadata.METADATA_DURATION))

                data = None
                try:
                    if DONT_RETRIEVE_BROWSE:
                        raise Exception("TEST: get browse disabled")
                    data = client.callWfsService(processInfo, params)
                    if self.debug != 0:
                        if data is not None:
                            processInfo.addLog(
                                "  makeBrowses: ==> received BROWSE[%s] DATA length:%s" % (key, len(data)))
                        else:
                            processInfo.addLog("  makeBrowses: ==> received BROWSE[%s] DATA is None" % key)
                except:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    traceback.print_exc(file=sys.stdout)
                    # print "HAHAHA %s %s" % (exc_type, exc_obj)
                    print("  makeBrowses: NO BROWSE[%s]" % key)
                    processInfo.addLog("  makeBrowses: ==> NO BROWSE[%s]" % key)
                    if USE_NO_PREVIEW_BROWSE:
                        self.getNoPreviewImage(processInfo)
                        data = self.noBrowseData
                    # else:
                    #        data='no preview'

                print("  makeBrowses[%s]: Url:%s" % (key, client.lastCalledUrl))
                processInfo.addLog("  makeBrowses[%s]: Url:%s" % (key, client.lastCalledUrl))
                if data != None and len(data) > 0:
                    # create browse file with name:  frame identifier +track+frame.BI.JPB
                    # NO: BI_TRACK_FRAME
                    browseName = frame.getProperty(browse_metadata.BROWSE_METADATA_FILENAME).replace(
                        '@SIP_PRODUCT_NAME@', processInfo.destProduct.getSipProductName())
                    if self.debug != 0:
                        print("  browseName:%s" % browseName)
                    processInfo.addLog("  browseName:%s" % browseName)
                    browseDestPath = "%s/%s" % (processInfo.destProduct.folder, browseName)
                    fd = open(browseDestPath, 'w')
                    fd.write(data)
                    fd.flush()
                    fd.close()
                    if self.debug != 0:
                        print("  makeBrowses: frame browse saved at path:%s" % browseDestPath)
                    processInfo.addLog("  makeBrowses: frame browse saved at path:%s" % browseDestPath)

                    #
                    piece = product_EOSIP.EoPiece(browseName)
                    piece.compressed = True
                    piece.type = 'BI'
                    piece.content = data
                    piece.srcObject = frame
                    processInfo.destProduct.eoPieces.append(piece)
                    processInfo.destProduct.contentList.append(browseName)

                    numFrameBrowseRetrived = numFrameBrowseRetrived + 1
                    processInfo.addIngesterLog("  makeBrowses[%s]:got strip browse:'%s'" % (key, browseDestPath),
                                               'PROGRESS')
                else:
                    print("#####  makeBrowses[%s]: no browse data retrieved" % key)
                    processInfo.addIngesterLog("  makeBrowses[%s]: no browse data retrieved" % key, 'PROGRESS')

            except:
                print(" make frame browse[%s] Error:" % key)
                exc_type, exc_obj, exc_tb = sys.exc_info()
                traceback.print_exc(file=sys.stdout)
                raise Exception(" make frame browse[%s] Error: %s %s" % (key, exc_type, exc_obj))

        #
        numFrames = len(list(processInfo.srcProduct.frames.keys()))
        if self.debug != 0:
            print("numFrameBrowseRetrived=%s; num frames:%s" % (numFrameBrowseRetrived, numFrames))
        if numFrameBrowseRetrived == len(list(processInfo.srcProduct.frames.keys())):
            processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'all-browses')
            processInfo.addLog("  makeBrowses: got all browses")
            self.logger.info("  makeBrowses: got all browses")
            if self.debug != 0:
                print("  makeBrowses: got all browses")
            self.keepInfo('all-browses', processInfo.srcProduct.origName)
        else:
            if numFrameBrowseRetrived > 0:
                processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'some-browses')
                processInfo.addLog("  makeBrowses: got some browses: %s on %s" % (numFrameBrowseRetrived, numFrames))
                self.logger.info("  makeBrowses: got some browses: %s on %s" % (numFrameBrowseRetrived, numFrames))
                if self.debug != 0:
                    print("  makeBrowses: got some browses: %s on %s" % (numFrameBrowseRetrived, numFrames))
                self.keepInfo('some-browses', processInfo.srcProduct.origName)
            else:
                processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'no-browses')
                self.logger.info("  makeBrowses: got no browse!")
                if self.debug != 0:
                    print("  makeBrowses: got no browse!")
                self.keepInfo('no-browses', processInfo.srcProduct.origName)
                # raise Exception("  makeBrowses: got no browse!")

        # if not mainBrowseRetrived:
        # processInfo.destProduct.metadata.setMetadataPair("mainBrowseRetrieved", 'no-main-browse')
        # processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'no-main-browse')
        # else:
        # processInfo.destProduct.metadata.setMetadataPair("mainBrowseRetrieved", 'main-browse')
        # processInfo.destProduct.metadata.setMetadataPair("frameBowsesRetrieved", 'main-browse')

        processInfo.addIngesterLog(
            "  make browses done, got %s" % processInfo.destProduct.metadata.getMetadataValue("frameBowsesRetrieved"),
            'PROGRESS')

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info(" will output eoSip: basePath='%s' ..." % basePath)
        # return
        # copy eoSip in first path; make links in other paths:

        # now done before in base_ingester.doOneProduct
        # self.outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)

        #
        # productPath=None
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            self.logger.info("  MDP product writen in folder:'%s'\n" % firstPath)
            processInfo.addLog("  MDP product writen in folder:'%s'\n" % firstPath)
            processInfo.addIngesterLog(" will write MDP at path:'%s'" % firstPath, 'PROGRESS')
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addIngesterLog("  write done:%s" % processInfo.destProduct.path, 'PROGRESS')

            # output link in other path
            i = 0
            for item in self.outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % item
                    self.logger.info("  MDP product tree path[%d] is:%s" % (i, item))
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog("  MDP product link writen in folder[%d]:%s\n" % (i, otherPath))
                    self.logger.info("  MDP product link writen in folder[%d]:%s\n" % (i, otherPath))
                i = i + 1
        self.logger.info("  done")
        return productPath


#
# catpute test
#
import contextlib


@contextlib.contextmanager
def capture(out=None):
    oldout, olderr = sys.stdout, sys.stderr
    try:
        print(" define out")
        if out == None:
            out = [io.StringIO(), io.StringIO()]
        sys.stdout, sys.stderr = out
        print(" got out")
        yield out

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)

    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


#
# class that capture/filter stdout or stderr
#
class Capture(io.StringIO):
    callback = None
    silent = False
    matchingString = []
    matchingLines = None
    mesg = None
    allStd = None

    def __init__(self, stdout, cb=None, silent=False):
        self.__stdout = stdout
        self.callback = cb
        self.silent = silent
        io.StringIO.__init__(self)
        self.matchingLines = []
        self.mesg = ''
        self.allStd = io.StringIO()

    def getRealStd(self):
        return self.__stdout

    def write(self, s):
        io.StringIO.write(self, s)
        self.allStd.write(s)
        #
        match = self.matchFilter(s)
        #
        if match:
            if self.callback is not None:
                self.callback.write(s)
            else:
                if not self.silent:
                    self.__stdout.write(s)

    def setFilter(self, f):
        try:
            self.matchingString.index(f)
        except:
            self.matchingString.append(f)
            self.mesg = "%sadded filter:%s\n" % (self.mesg, f)

    def matchFilter(self, mess):
        for item in self.matchingString:
            if mess.find(item) >= 0:
                return True
                # self.matchingLines.append(mess)
                # self.__stdout.write(mess)

    def getMatchingLines(self):
        res = ''
        for item in self.matchingLines:
            res = "%s%s\n" % (res, item)
        return res

    def read(self):
        self.seek(0)
        self.__stdout.write(io.StringIO.read(self))

    def getMesg(self):
        return self.mesg

    def getStdAll(self):
        return self.allStd.getvalue()


#
#
#
if __name__ == '__main__':
    exitCode = -1

    try:

        #
        # in joborder mode the stdout/stderr have to be formatted
        # so we need to do:
        # - swap the stds for some Capture class that can capture/filter/reformat them
        # - the 'PROGRESS' keyword will be used as match by the Capture that will display only these lines
        #

        # keep old stds
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        # will test if we are in joborder mode or not
        jobOrderMode = False
        ipfLopper = None
        # test for --joborder options
        # if present, want to change stdoutstd/err + use log reformater
        for item in sys.argv:
            if item == '--joborder':
                jobOrderMode = True
                # print " is in joborder mode"

        #
        # change stds, use std reformater to comply to IPF spec
        #
        captureStderr = None
        captureStdout = None
        ipfLopper = None
        if jobOrderMode:
            #
            # ingester logger is formatted, is on stderr
            #
            # don't want to examine stdout, but want to capture it
            captureStdout = Capture(sys.stdout, None, True)
            # logger1 = ipfLogger.IpfLogger(captureStdout.getRealStd())
            # captureStdout.callback=logger1
            # captureStdout.setFilter('ERROR')

            # want to capture and filter the formatted stderr messages
            captureStderr = Capture(sys.stderr, None, True)
            ipfLopper = ipfLogger.IpfLogger(captureStderr.getRealStd())
            captureStderr.callback = ipfLopper
            # matches
            captureStderr.setFilter('ERROR')
            captureStderr.setFilter('PINFO')
            captureStderr.setFilter('PROGRESS')

            #
            sys.stdout = mystdout = captureStdout
            sys.stderr = mystderr = captureStderr

        rawError = None
        formattedError = None
        #
        # run the ingester, in case of error in joborder mode the except bellow will display a compliant error log line
        #
        try:
            if len(sys.argv) > 1:
                ingester = StriplineToMdp()
                ingester.setDebug(1)
                if ipfLopper is not None:
                    ingester.ipfLopper = ipfLopper
                    import socket

                    ingester.ipfLopper.nodename = socket.gethostname()
                # ingester.DEBUG=1
                # raise Exception("RAISE TEST")
                exitCode = ingester.starts(sys.argv)

            else:
                raise Exception("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
                exitCode = 1

        except Exception as e:
            if jobOrderMode:  # format the error message for IPF spec
                exc_type, exc_obj, exc_tb = sys.exc_info()
                rawError = "ERROR: %s; %s\n%s" % (exc_type, exc_obj, traceback.format_exc())
                if ipfLopper is not None:
                    formattedError = ipfLopper.formatMsg("ERROR: %s; %s" % (exc_type, exc_obj), 'E')
                    # write error in file
                    fd = open('jobOrderMode_error.log', 'w')
                    fd.write(formattedError)
                    traceback.print_exc(file=fd)
                    fd.flush()
                    fd.close()

            else:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" Error1: %s; %s" % (exc_type, exc_obj))
                #        traceback.print_exc(file=sys.stdout)

        #
        # re swap the stds
        #
        finally:
            # reset stds
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if jobOrderMode:
                if captureStdout is not None:
                    # write to file
                    fd1 = open('stdout.log', 'w')
                    fd1.write(captureStdout.getStdAll())
                    fd1.flush()
                    fd1.close()
                if captureStderr is not None:
                    #
                    fd1 = open('stderr.log', 'w')
                    fd1.write(captureStderr.getStdAll())
                    fd1.flush()
                    fd1.close()
            if rawError is not None:
                print("rawError:%s" % rawError)

            # display formatted error (i.e. in joborder mode) if any
            if formattedError is not None:
                print(formattedError)

    # if we are at this exception we can not really know if we are in joborder or not...
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error2: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
