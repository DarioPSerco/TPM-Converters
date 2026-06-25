"""This class represent a metadata population product"""
import os
import shutil
import sys
import traceback
import zipfile

import eoSip_converter.esaProducts.definitions_EoSip as definitions_EoSip
import eoSip_converter.esaProducts.formatUtils as formatUtils
import eoSip_converter.esaProducts.product_EOSIP as product_EOSIP
import eoSip_converter.xmlHelper as xmlHelper
#
import xml_nodes.eop_browse as eop_browse
from eoSip_converter.esaProducts import metadata as metadata, browse_metadata as browse_metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from .product_EOSIP_stripline import Product_EOSIP_Stripline


#
#
#
class Product_Mdp(Product_EOSIP_Stripline):
    xmlMapping = {}

    #
    #
    #
    def __init__(self, path=None):
        Product_EOSIP_Stripline.__init__(self, path)
        #
        self.mdXmlReplacementMap = {}
        #
        self.ssmXmlReplacementMap = {}
        #
        self.imageWidth = -1
        self.imageHeight = -1
        #
        # self.DEBUG=0
        print(" init class Product_Mdp")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # read matadata file
    #
    def getMetadataInfo(self):
        pass

    #
    # extract the MDP content into workfolder
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

    #
    # build package and peoductname
    # namingConvention is the class instance used
    # ext is the extension of the eoProduct (what is inside the eoSip package),if not specified, use default EoSip extension: .ZIP
    #
    # def buildEoNames(self, namingConvention=None): #, ext=None, eoExt=None ):
    #    EOSIP_Stripline_Product.buildEoNames(self, namingConvention, )

    #
    # build the product SSM report: get it from src product
    # make it a piece
    #
    # called by the ingester.afterReportsDone()
    #
    def buildSsmReportFile(self):
        # copy SSM.XML EoPieces into dest EoSip
        found = False
        for pieceName in self.processInfo.srcProduct.getPieceNames():
            if pieceName.find(definitions_EoSip.getDefinition('SSM_EXT')) > 0:
                self.ssmFullPath = "%s/%s" % (self.folder, pieceName)
                # rename report from envisat filename convention to eosip filename convention
                self.ssmFullPath = "%s/%s.%s" % (
                    self.folder, self.eoProductName, definitions_EoSip.getDefinition('SSM_EXT'))
                self.processInfo.addLog("  buildSsmReportFile name:%s at dest:%s" % (pieceName, self.ssmFullPath))
                if self.debug != 0:
                    print("  buildSsmReportFile name:%s at dest:%s" % (pieceName, self.ssmFullPath))
                found = True

                # create piece
                piece = product_EOSIP.EoPiece(pieceName)
                piece.compressed = True
                piece.alias = "%s.%s" % (self.eoProductName, definitions_EoSip.getDefinition('SSM_EXT'))
                piece.type = definitions_EoSip.getDefinition('SSM_EXT')
                self.eoPieces.append(piece)
                self.contentList.append(pieceName)

                # get content from src EoSip
                self.ssmReport = self.processInfo.srcProduct.getPieceContent(pieceName)
                piece.content = self.ssmReport
                # write it
                fd = open(self.ssmFullPath, "wb")
                fd.write(self.ssmReport)
                fd.flush()
                fd.close()

                break
        if not found:
            raise Exception("SSM product report file not found in src product")

        return self.reportFullPath

    #
    # add the reference of strip frame browse into MD report
    #
    def addBrowseInMd(self):
        # get MD piece
        piece = None
        for pieceName in self.getPieceNames():
            piece = self.getPiece(pieceName)
            if self.debug != 0:
                print(" addBrowseInMd: test piece[%s]=%s" % (pieceName, piece))
            if piece.type == definitions_EoSip.getDefinition('MD_EXT'):
                if self.debug != 0:
                    print(" addBrowseInMd: piece[%s] is MD" % pieceName)  # , content=\n%s" % (pieceName, piece.content)
                break

        if piece is None:
            raise Exception("can not find MD piece")
        helper = xmlHelper.XmlHelper()
        helper.setData(piece.content)
        helper.parseData()
        self.processInfo.addLog(" addBrowseInMd: md report parsed")
        if self.debug != 0:
            print((" addBrowseInMd: md report parsed:%s" % piece.content))

        # if there is some browse
        doc = helper.getDomDoc()
        if len(self.sourceBrowsesPath) > 0:
            browsePath = self.sourceBrowsesPath[0]
            if self.debug != 0:
                print((" addBrowseInMd: browsePath=%s" % browsePath))

            earthObservationResultNodes = doc.getElementsByTagName('eop:EarthObservationResult')

            filename = os.path.split(browsePath)[1]

            met = metadata.Metadata()
            # set typology
            met.setOtherInfo("TYPOLOGY_SUFFIX", self.metadata.getOtherInfo("TYPOLOGY_SUFFIX"))
            # set xml node used map
            met.xmlNodeUsedMapping = self.xmlMappingBrowse

            met.setMetadataPair(metadata.METADATA_BROWSES_TYPE, 'QUICKLOOK')
            met.setMetadataPair(browse_metadata.BROWSE_METADATA_FILENAME, filename)
            met.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, '')
            met.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, '')

            productReportBuilder = eop_browse.eop_browse()
            replacement = productReportBuilder.buildMessage(met,
                                                            "sar:EarthObservation/om:result/eop:EarthObservationResult")
            if self.debug != 0:
                print("\n addBrowseInMd: replacement:%s" % replacement)
            # add in replacement map
            self.mdXmlReplacementMap['<TO_BE_REPLACED_BROWSE/>'] = replacement

            entry = doc.createElement('TO_BE_REPLACED_BROWSE')
            productNode = earthObservationResultNodes[0].getElementsByTagName('eop:product')
            earthObservationResultNodes[0].insertBefore(entry, productNode[0])
            if self.debug != 0:
                print("\n addBrowseInMd: after:%s" % helper.prettyPrint(earthObservationResultNodes[0]))
        else:
            if self.debug != 0:
                print(" addBrowseInMd: sourceBrowsesPath is empty, no strip browse")

        #
        colRowList = self.buildBrowseColRowList()
        if colRowList is not None:
            earthObservationMetaDataNodes = doc.getElementsByTagName('eop:EarthObservationMetaData')
            vendorSpecificNodes = earthObservationMetaDataNodes[0].getElementsByTagName('eop:vendorSpecific')
            if self.debug != 0:
                print(" number of vendorSpecific nodes:%s" % len(vendorSpecificNodes))
            # add a new one
            cloned = vendorSpecificNodes[-1].cloneNode(True)
            ntnode = cloned.getElementsByTagName('eop:localAttribute')
            nvnode = cloned.getElementsByTagName('eop:localValue')
            helper.setNodeText(ntnode[0], 'browseColRowList')
            helper.setNodeText(nvnode[0], colRowList)
            earthObservationMetaDataNodes[0].appendChild(cloned)

        productReportBuilder = eop_browse.eop_browse()

        # build the final xml
        self.correctMdXml = '<?xml version="1.0" encoding="UTF-8"?>\n%s' % self.buildCorrectMdXml(helper)
        if self.debug != 0:
            print("\n addBrowseInMd: correctMdXml:\n%s" % self.correctMdXml)

        fd = open('%s/modified_md.xml' % self.processInfo.workFolder, 'w')
        fd.write(self.correctMdXml)
        fd.flush()
        fd.close()

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
    # build the browseColRowList
    # we don't consider the shifted vertex, to not having a path going forward then backward
    #
    def buildBrowseColRowList(self):
        if self.imageWidth <= 0 or self.imageHeight <= 0:
            self.processInfo.addLog("  buildBrowseColRowList: bon't build it: strip image not present: w=%s; h=%s" % (
                self.imageWidth, self.imageHeight))
            print("  buildBrowseColRowList: bon't build it: strip image not present: w=%s; h=%s" % (
                self.imageWidth, self.imageHeight))
            return None

        ssmNumFrames = self.processInfo.srcProduct.getNumFrames()
        print(" buildBrowseColRowList; ssmNumFrames=%s" % ssmNumFrames)
        durations = []
        totalDuration = 0
        for frameNum in range(ssmNumFrames):
            # print " buildBrowseColRowList[%s]" % frameNum
            srcFrame = self.processInfo.srcProduct.getFrame(frameNum)
            sec = float(srcFrame.getProperty(metadata.METADATA_DURATION))
            oldSec = sec
            if srcFrame.hasPropertyKey('old_duration'):
                oldSec = float(srcFrame.getProperty('old_duration'))
            if self.debug != 0:
                print(" buildBrowseColRowList; frame[%s] old duration=%s; duration=%s" % (frameNum, oldSec, sec))
            # durations.append(sec)
            durations.append(oldSec)
            # totalDuration=totalDuration+sec
            totalDuration = totalDuration + oldSec
            if self.debug != 0:
                print(" buildBrowseColRowList; frame[%s]=%s" % (frameNum, srcFrame.info()))

        #
        if self.debug != 0:
            print(" buildBrowseColRowList; durations=%s; totalDuration=%s, imageWidth=%s; imageWidth=%s" % (
                durations, totalDuration, self.imageWidth, self.imageHeight))
        browseImage = BrowseImage()
        aFootprint = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        if self.showCHANGED:
            # pos = aFootprint.find('CHANGED:')
            # if pos>=0:
            #    aFootprint=aFootprint[pos+len('CHANGED:')+1:]
            aFootprint = self.getValueFromChangedString(aFootprint)

        browseImage.debug = 1
        colRowList = browseImage.buildDefaultColRowListFromDurations(self.imageWidth, self.imageHeight, durations,
                                                                     totalDuration,
                                                                     self.processInfo.srcProduct.metadata.getMetadataValue(
                                                                         metadata.METADATA_ORBIT_DIRECTION), aFootprint)
        # colRowList = browseImage.buildDefaultColRowListFromDurations(self.imageWidth, self.imageHeight, durations, totalDuration, self.processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION), None)
        # ascending test: colRowList = browseImage.buildDefaultColRowListFromDurations(self.imageWidth, self.imageHeight, durations, totalDuration, 'ASCENDING', aFootprint)
        if self.debug != 0:
            print(" buildBrowseColRowList; buildDefaultColRowListFromDurations result:%s" % colRowList)
        self.processInfo.addLog("  buildBrowseColRowList:%s" % colRowList)

        return colRowList

    #
    # add the reference of frame browse into SSM report
    #
    # called by the ingester.afterReportsDone()
    #
    def addBrowsesInSsm(self):
        helper = xmlHelper.XmlHelper()
        helper.setData(self.ssmReport)
        helper.parseData()
        self.processInfo.addLog(" addBrowsesInSsm: ssm report parsed")  #:%s" % self.ssmReport)

        doc = helper.getDomDoc()
        earthObservationResultNodes = doc.getElementsByTagName('eop:EarthObservationResult')
        n = 0
        for node in earthObservationResultNodes:
            if self.debug != 0:
                print("node:%s" % node)
                print("\nbefore:%s" % helper.prettyPrint(node))
            productNode = node.getElementsByTagName('eop:product')
            if self.debug != 0:
                print("productNode:%s" % productNode)

            # build replacement
            # get EoSip piece corresponding to node
            goodPiece = None
            for pieceName in self.getPieceNames():
                piece = self.getPiece(pieceName)
                if self.debug != 0:
                    print(" addBrowsesInSsm: test piece[%s]=%s" % (pieceName, piece))
                if piece.type == 'BI':
                    if self.debug != 0:
                        print(" addBrowsesInSsm: piece[%s] is browse" % pieceName)
                    if piece.srcObject.num == n:
                        goodPiece = piece
                        if self.debug != 0:
                            print(" addBrowsesInSsm: piece[%s] is goodPiece=%s" % (pieceName, goodPiece))
                        break

            if self.debug != 0:
                print(" addBrowsesInSsm: goodPiece:%s, type:%s" % (goodPiece, type(goodPiece)))
            filename = 'the_filename'
            if goodPiece is not None:
                filename = piece.name

                met = metadata.Metadata()
                # set typology
                met.setOtherInfo("TYPOLOGY_SUFFIX", self.metadata.getOtherInfo("TYPOLOGY_SUFFIX"))
                # set xml node used map
                met.xmlNodeUsedMapping = self.xmlMappingBrowse

                met.setMetadataPair(metadata.METADATA_BROWSES_TYPE, 'QUICKLOOK')
                met.setMetadataPair(browse_metadata.BROWSE_METADATA_FILENAME, filename)
                met.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, '')
                met.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, '')

                productReportBuilder = eop_browse.eop_browse()
                replacement = productReportBuilder.buildMessage(met,
                                                                "sar:EarthObservation/om:result/eop:EarthObservationResult")
                if self.debug != 0:
                    print("\n addBrowsesInSsm: replacement:%s" % replacement)
                # add in replacement map
                self.ssmXmlReplacementMap['<TO_BE_REPLACED_BROWSE_%s/>' % n] = replacement

                entry = doc.createElement('TO_BE_REPLACED_BROWSE_%s' % n)
                node.insertBefore(entry, productNode[0])
                if self.debug != 0:
                    print("\n addBrowsesInSsm: after:%s" % helper.prettyPrint(node))

            n = n + 1

        if self.debug != 0:
            print("\n addBrowsesInSsm: RESULT:%s" % helper.prettyPrint(None))

        self.CorrectFirstLastTimeInSsm(helper)
        self.CorrectFirstLastFrameInSsm(helper)
        self.CorrectFirstLastCompletionTimeInSsm(helper)
        self.CorrectFirstLastStartTimeFromAscendingInSsm(helper)
        self.CorrectFirstLastFootprintInSsm(helper)
        self.CorrectFirstLastSceneCenterInSsm(helper)
        self.CorrectIdentifierInSsm(helper)
        self.CorrectGmlIdInSsm(helper)

        # build the final xml
        self.correctSsmXml = '<?xml version="1.0" encoding="UTF-8"?>\n%s' % self.buildCorrectSsmXml(helper)
        if self.debug != 0:
            print("\n addBrowsesInSsm: correctSsmXml:\n%s" % self.correctSsmXml)

        fd = open('%s/modified_ssm.xml' % self.processInfo.workFolder, 'w')
        fd.write(self.correctSsmXml)
        fd.flush()
        fd.close()

    #
    #
    #
    def buildCorrectSsmXml(self, helper):
        rawXml = helper.prettyPrint(None)
        for key in list(self.ssmXmlReplacementMap.keys()):
            value = self.ssmXmlReplacementMap[key]
            if self.debug != 0:
                print("buildCorrectSsmXml: key=%s; value=%s" % (key, value))
            rawXml = rawXml.replace(key, "%s\n" % value)

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(rawXml)
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()

        return formattedXml

    #
    #
    #
    def buildCorrectMdXml(self, helper):
        rawXml = helper.prettyPrint(None)
        for key in list(self.mdXmlReplacementMap.keys()):
            value = self.mdXmlReplacementMap[key]
            if self.debug != 0:
                print("buildCorrectMdXml: key=%s; value=%s" % (key, value))
            rawXml = rawXml.replace(key, "%s\n" % value)

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(rawXml)
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()

        return formattedXml

    #
    # correct the gmlId into SSM report
    #
    # called from self.addBrowsesInSsm()
    #
    #
    def CorrectGmlIdInSsm(self, helper):
        doc = helper.getDomDoc()
        frameNodes = doc.getElementsByTagName('sar:EarthObservation')

        if frameNodes is None or len(frameNodes) == 0 or len(frameNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            startNodes = doc.getElementsByTagName('gml:beginPosition')
            raise Exception("Error getting frame sar:EarthObservation: %s" % startNodes)

        numFrame = 0
        for node in frameNodes:
            if numFrame == 0 or numFrame == len(frameNodes) - 1:
                if self.debug != 0:
                    print(" frame node[%s] type=%s (text); localname=%s" % (numFrame, node.nodeType, node.localName))

                aFrame = self.processInfo.srcProduct.frames[numFrame]
                identifier = aFrame.getProperty(metadata.METADATA_IDENTIFIER)
                if self.debug != 0:
                    self.processInfo.addLog(" CorrectGmlIdInSsm: frame[%s] identifier:%s" % (numFrame, identifier))
                    self.processInfo.addLog(" CorrectGmlIdInSsm: frame[%s] dump:%s" % (numFrame, aFrame.info()))
                # change in sar:EarthObservation
                numGmlId = 1
                attrValue = node.getAttribute('gml:id')
                if self.debug != 0:
                    self.processInfo.addLog(" CorrectGmlIdInSsm: frame[%s] node attrValue:%s" % (numFrame, attrValue))
                if self.showCHANGED:
                    pos = identifier.find("CHANGED: ")
                    if pos >= 0:
                        identifier = identifier[pos + len("CHANGED: "):]
                    node.setAttribute('gml:id', "%s CHANGED: %s_%s" % (attrValue, identifier, numGmlId))
                    self.processInfo.addLog(" CorrectGmlIdInSsm: frame[%s] node new attrValue (show changed):%s_%s" % (
                        numFrame, identifier, numGmlId))
                else:
                    node.setAttribute('gml:id', "%s_%s" % (identifier, numGmlId))
                    self.processInfo.addLog(
                        " CorrectGmlIdInSsm: frame[%s] node new attrValue:%s_%s" % (numFrame, identifier, numGmlId))

                # and in every children
                resultChlds = []
                helper.getNodeDescendant(node, None, resultChlds)
                n = 0
                for children in resultChlds:
                    if self.debug != 0:
                        print(" chidren node[%s] type=%s (text); localname=%s" % (
                            n, children.nodeType, children.localName))
                    if children.nodeType != children.TEXT_NODE:
                        try:
                            attrValue = children.getAttribute('gml:id')
                            if self.debug != 0:
                                self.processInfo.addLog(
                                    " CorrectGmlIdInSsm: frame[%s].child[%s] attrValue:%s" % (numFrame, n, attrValue))
                            if attrValue is not None and len(attrValue) > 0:
                                if self.debug != 0:
                                    print(" change gml id: '%s'; counter:%s" % (attrValue, numGmlId))
                                numGmlId = numGmlId + 1
                                if self.showCHANGED:
                                    pos = identifier.find("CHANGED: ")
                                    if pos >= 0:
                                        identifier = identifier[pos + len("CHANGED: "):]
                                    children.setAttribute('gml:id',
                                                          "%s CHANGED: %s_%s" % (attrValue, identifier, numGmlId))
                                    self.processInfo.addLog(
                                        " CorrectGmlIdInSsm: frame[%s].child[%s] node new attrValue (show changed):%s_%s" % (
                                            numFrame, n, identifier, numGmlId))
                                else:
                                    children.setAttribute('gml:id', "%s_%s" % (identifier, numGmlId))
                                    self.processInfo.addLog(
                                        " CorrectGmlIdInSsm: frame[%s].child[%s] node new attrValue:%s_%s" % (
                                            numFrame, n, identifier, numGmlId))

                        except:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            print("Error getting node attribute: %s   %s\n%s\n" % (
                                exc_type, exc_obj, traceback.format_exc()))
                    n += 1

            numFrame += 1

        print("CorrectGmlIdInSsm frame node length:%s" % len(frameNodes))

    #
    # correct the first and last frame start/stop time into SSM report
    #
    #
    def CorrectFirstLastTimeInSsm(self, helper):
        doc = helper.getDomDoc()
        startNodes = doc.getElementsByTagName('gml:beginPosition')
        stopNodes = doc.getElementsByTagName('gml:endPosition')
        timeNodes = doc.getElementsByTagName('gml:timePosition')

        if startNodes is None or len(startNodes) == 0 or len(startNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame gml:beginPosition: %s" % startNodes)

        if stopNodes == None or len(stopNodes) == 0 or len(stopNodes) != len(list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame gml:endPositionn:%s" % stopNodes)

        if timeNodes == None or len(timeNodes) == 0 or len(timeNodes) != len(list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame gml:timePosition:%s" % timeNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        self.processInfo.addLog(
            "  CorrectFirstLastTimeInSsm: first frame dump:%s" % self.processInfo.srcProduct.frames[0].info())

        stopFirst = self.processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_STOP_DATE_TIME)
        startLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(metadata.METADATA_START_DATE_TIME)

        helper.setNodeText(stopNodes[0], stopFirst)
        helper.setNodeText(timeNodes[0], stopFirst)
        helper.setNodeText(startNodes[lastFrame], startLast)

        self.processInfo.addLog("  CorrectFirstLastTimeInSsm stopFirst=%s; startLast=%s" % (stopFirst, startLast))
        print("  CorrectFirstLastTimeInSsm stopFirst=%s; startLast=%s" % (stopFirst, startLast))

    #
    # correct the first and last frame number into SSM report
    #
    #
    def CorrectFirstLastFrameInSsm(self, helper):
        doc = helper.getDomDoc()
        frameNodes = doc.getElementsByTagName('eop:wrsLatitudeGrid')

        if frameNodes is None or len(frameNodes) == 0 or len(frameNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame eop:wrsLatitudeGrid: %s" % frameNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        frameFirst = self.processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        frameLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(
            metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        helper.setNodeText(frameNodes[0], frameFirst)
        helper.setNodeText(frameNodes[lastFrame], frameLast)
        self.processInfo.addLog("  CorrectFirstLastFrameInSsm frameFirst=%s; frameLast=%s" % (frameFirst, frameLast))
        if self.debug != 0:
            print("  CorrectFirstLastFrameInSsm frameFirst=%s; frameLast=%s" % (frameFirst, frameLast))

    #
    # correct the first and last completion time from ascending node into SSM report
    #
    #
    def CorrectFirstLastCompletionTimeInSsm(self, helper):
        doc = helper.getDomDoc()
        compNodes = doc.getElementsByTagName('eop:completionTimeFromAscendingNode')

        if compNodes == None or len(compNodes) == 0 or len(compNodes) != len(list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame eop:completionTimeFromAscendingNode :%s" % compNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        compFirst = self.processInfo.srcProduct.frames[0].getProperty(
            metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE)
        # compLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(metadata.METADATA_COMPLETION_TIME_FROM_ASCENDING_NODE)
        helper.setNodeText(compNodes[0], compFirst)
        # helper.setNodeText(compNodes[lastFrame], compLast)
        # self.processInfo.addLog("  CorrectFirstLastCompletionTimeInSsm compFirst=%s; compLast=%s" % (compFirst, compLast))
        # print "  CorrectFirstLastCompletionTimeInSsm compFirst=%s; compLast=%s" % (compFirst, compLast)
        self.processInfo.addLog("  CorrectFirstLastCompletionTimeInSsm compFirst=%s" % compFirst)
        if self.debug != 0:
            print("  CorrectFirstLastCompletionTimeInSsm compFirst=%s" % compFirst)

    #
    # correct the first and last start time from ascending node into SSM report
    #
    #
    def CorrectFirstLastStartTimeFromAscendingInSsm(self, helper):
        doc = helper.getDomDoc()
        ascTimeNodes = doc.getElementsByTagName('eop:startTimeFromAscendingNode')

        if ascTimeNodes == None or len(ascTimeNodes) == 0 or len(ascTimeNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            compNodes = doc.getElementsByTagName('eop:completionTimeFromAscendingNode')
            raise Exception("Error getting frame eop:startTimeFromAscendingNode :%s" % compNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        # ascTimeFirst = self.processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_START_TIME_FROM_ASCENDING_NODE)
        ascTimeLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(
            metadata.METADATA_START_TIME_FROM_ASCENDING_NODE)
        # helper.setNodeText(ascTimeNodes[0], ascTimeFirst)
        helper.setNodeText(ascTimeNodes[lastFrame], ascTimeLast)
        # self.processInfo.addLog("  CorrectFirstLastStartTimeFromAscendingInSsm ascTimeFirst=%s; ascTimeLast=%s" % (ascTimeFirst, ascTimeLast))
        # print "  CorrectFirstLastStartTimeFromAscendingInSsm ascTimeFirst=%s; ascTimeLast=%s" % (ascTimeFirst, ascTimeLast)
        self.processInfo.addLog("  CorrectFirstLastStartTimeFromAscendingInSsm ascTimeLast=%s" % ascTimeLast)
        if self.debug != 0:
            print("  CorrectFirstLastStartTimeFromAscendingInSsm ascTimeLast=%s" % ascTimeLast)

    #
    # correct the first and last footprint into SSM report
    #
    #
    def CorrectFirstLastFootprintInSsm(self, helper):
        doc = helper.getDomDoc()
        footprintNodes = doc.getElementsByTagName('gml:posList')

        if footprintNodes == None or len(footprintNodes) == 0 or len(footprintNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame gml:posList:%s" % footprintNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        footprintFirst = self.processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_FOOTPRINT)
        footprintLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(metadata.METADATA_FOOTPRINT)

        self.processInfo.addLog("  CorrectFirstLastFootprintInSsm not rounded footprintFirst=%s; footprintLast=%s" % (
            footprintFirst, footprintLast))

        # round to 2 digit float
        footprintFirstRounded = ''
        for coord in footprintFirst.split(' '):
            if coord != 'CHANGED:':
                if len(footprintFirstRounded) > 0:
                    footprintFirstRounded = "%s " % footprintFirstRounded
                v = float(coord)
                footprintFirstRounded = "%s%.2f" % (footprintFirstRounded, v)
            else:
                footprintFirstRounded = "%s %s" % (footprintFirstRounded, 'CHANGED:')

        footprintLastRounded = ''
        for coord in footprintLast.split(' '):
            if coord != 'CHANGED:':
                if len(footprintLastRounded) > 0:
                    footprintLastRounded = "%s " % footprintLastRounded
                v = float(coord)
                footprintLastRounded = "%s%.2f" % (footprintLastRounded, v)
            else:
                footprintLastRounded = "%s %s" % (footprintLastRounded, 'CHANGED:')

        helper.setNodeText(footprintNodes[0], footprintFirstRounded)
        helper.setNodeText(footprintNodes[lastFrame], footprintLastRounded)
        self.processInfo.addLog("  CorrectFirstLastFootprintInSsm footprintFirst=%s; footprintLast=%s" % (
            footprintFirstRounded, footprintLastRounded))
        if self.debug != 0:
            print("  CorrectFirstLastFootprintInSsm ascTimeFirst=%s; footprintFirst=%s" % (
                footprintFirstRounded, footprintLastRounded))

    #
    # correct the first and last sceneCenter into SSM report
    #
    #
    def CorrectFirstLastSceneCenterInSsm(self, helper):
        doc = helper.getDomDoc()
        sceneCenterNodes = doc.getElementsByTagName('gml:pos')

        if sceneCenterNodes == None or len(sceneCenterNodes) == 0 or len(sceneCenterNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame gml:pos :%s" % sceneCenterNodes)

        lastFrame = len(list(self.processInfo.srcProduct.frames.keys())) - 1

        sceneCenterFirst = self.processInfo.srcProduct.frames[0].getProperty(metadata.METADATA_SCENE_CENTER)
        sceneCenterLast = self.processInfo.srcProduct.frames[lastFrame].getProperty(metadata.METADATA_SCENE_CENTER)

        sceneCenterFirstRounded = ''
        for coord in sceneCenterFirst.split(' '):
            if coord != 'CHANGED:':
                if len(sceneCenterFirstRounded) > 0:
                    sceneCenterFirstRounded = "%s " % sceneCenterFirstRounded
                v = float(coord)
                sceneCenterFirstRounded = "%s%.2f" % (sceneCenterFirstRounded, v)
            else:
                sceneCenterFirstRounded = "%s %s" % (sceneCenterFirstRounded, 'CHANGED:')

        sceneCenterLastRounded = ''
        for coord in sceneCenterLast.split(' '):
            if coord != 'CHANGED:':
                if len(sceneCenterLastRounded) > 0:
                    sceneCenterLastRounded = "%s " % sceneCenterLastRounded
                v = float(coord)
                sceneCenterLastRounded = "%s%.2f" % (sceneCenterLastRounded, v)
            else:
                sceneCenterLastRounded = "%s %s" % (sceneCenterLastRounded, 'CHANGED:')

        helper.setNodeText(sceneCenterNodes[0], sceneCenterFirstRounded)
        helper.setNodeText(sceneCenterNodes[lastFrame], sceneCenterLastRounded)
        self.processInfo.addLog("  CorrectFirstLastSceneCenterInSsm sceneCenterFirst=%s; sceneCenterLast=%s" % (
            sceneCenterFirstRounded, sceneCenterLastRounded))
        if self.debug != 0:
            print("  CorrectFirstLastSceneCenterInSsm sceneCenterFirst=%s; sceneCenterLast=%s" % (
                sceneCenterFirstRounded, sceneCenterLastRounded))

    #
    #
    #
    def CorrectIdentifierInSsm(self, helper):
        doc = helper.getDomDoc()
        identifierNodes = doc.getElementsByTagName('eop:identifier')

        if identifierNodes == None or len(identifierNodes) == 0 or len(identifierNodes) != len(
                list(self.processInfo.srcProduct.frames.keys())):
            raise Exception("Error getting frame eop:identifier :%s" % identifierNodes)

        numFrame = 0
        for node in identifierNodes:
            identifier = self.processInfo.srcProduct.frames[numFrame].getProperty(metadata.METADATA_IDENTIFIER)
            helper.setNodeText(node, identifier)
            self.processInfo.addLog(" CorrectIdentifierInSsm numFrame=%s; identifier=%s" % (numFrame, identifier))
            if self.debug != 0:
                print(" CorrectIdentifierInSsm numFrame=%s; identifier=%s" % (numFrame, identifier))
            numFrame = numFrame + 1

    #
    # turn the browse image into pieces, to have them writen automaticaly
    #
    # called by the ingester.afterReportsDone()
    #
    def makeFramebrowseIntoPieces(self):
        pass

    #
    # build the product metadata report: get it from src product
    # make it a piece
    #
    def buildProductReportFile(self):
        # copy MD.XML EoPieces into dest EoSip
        found = False
        for pieceName in self.processInfo.srcProduct.getPieceNames():
            if pieceName.find(definitions_EoSip.getDefinition('MD_EXT')) > 0:
                # self.reportFullPath = "%s/%s"% (self.folder, pieceName)
                # rename report from envisat filename convention to eosip filename convention
                self.reportFullPath = "%s/%s.%s" % (
                    self.folder, self.eoProductName, definitions_EoSip.getDefinition('MD_EXT'))
                self.processInfo.addLog(
                    "  buildProductReportFile name:%s at dest:%s" % (pieceName, self.reportFullPath))
                if self.debug != 0:
                    print("  buildProductReportFile name:%s at dest:%s" % (pieceName, self.reportFullPath))
                found = True

                # create piece
                piece = product_EOSIP.EoPiece(pieceName)
                piece.compressed = True
                piece.alias = "%s.%s" % (self.eoProductName, definitions_EoSip.getDefinition('MD_EXT'))
                piece.type = definitions_EoSip.getDefinition('MD_EXT')
                self.eoPieces.append(piece)
                self.contentList.append(pieceName)

                self.productReport = self.processInfo.srcProduct.getPieceContent(pieceName)
                piece.content = self.productReport
                # write it
                fd = open(self.reportFullPath, "wb")
                fd.write(self.productReport)
                fd.flush()
                fd.close()
                break
        if not found:
            raise Exception("MD product report file not found in src product")

        return self.reportFullPath

    #
    # build the browse metadata reports: do nothing
    #
    def buildBrowsesReportFile(self):
        pass

    #
    # build the sip report: get it from src product
    # make it a piece
    #
    def buildSipReportFile(self):
        # copy SI.XML EoPieces into dest EoSip
        found = False
        for pieceName in self.processInfo.srcProduct.getPieceNames():
            if pieceName.find(definitions_EoSip.getDefinition('SI_EXT')) > 0:
                # self.sipFullPath = "%s/%s"% (self.folder, pieceName)
                # rename report from envisat filename convention to eosip filename convention
                self.sipFullPath = "%s/%s.%s" % (
                    self.folder, self.eoProductName, definitions_EoSip.getDefinition('SI_EXT'))
                self.processInfo.addLog("  buildSipReportFile name:%s at dest:%s" % (pieceName, self.sipFullPath))
                if self.debug != 0:
                    print("  buildSipReportFile name:%s at dest:%s" % (pieceName, self.sipFullPath))
                found = True

                # create piece
                piece = product_EOSIP.EoPiece(pieceName)
                piece.compressed = True
                piece.alias = "%s.%s" % (self.eoProductName, definitions_EoSip.getDefinition('SI_EXT'))
                piece.type = definitions_EoSip.getDefinition('SI_EXT')
                self.eoPieces.append(piece)
                self.contentList.append(pieceName)

                # get content from src EoSip
                self.sipReport = self.processInfo.srcProduct.getPieceContent(pieceName)
                piece.content = self.sipReport
                # write it
                fd = open(self.sipFullPath, "wb")
                fd.write(self.sipReport)
                fd.flush()
                fd.close()
                break
        if not found:
            raise Exception("SIP report file not found in src product")

        return self.sipReport

    #
    # write the Eo-Sip package in a folder.
    # p: path of the output folder
    # as in product_EOSIP classe
    #
    def writeToFolder(self, p=None, overwrite=None):
        if self.eoProductName == None:
            raise Exception("Eo-Sip product has no productName")
        if self.debug == 0:
            print("\n will write EoSip product at folder path:%s" % p)
        if p[-1] != '/':
            p = p + '/'

        # create destination path
        self.path = "%s%s.MDP.ZIP" % (p, self.sipProductName)
        if self.debug == 0:
            print(" full eoSip path:%s" % self.path)

        # already exists?
        if os.path.exists(self.path) and (overwrite == None or overwrite == False):
            raise Exception("refuse to overwite existing product:%s" % self.path)

        # create folder needed
        if not os.path.exists(p):
            os.makedirs(p)

        # remove precedent zip if any
        if os.path.exists(self.path):
            os.remove(self.path)

        if self.debug >= 0:
            self.processInfo.addLog("  write EoSip src:%s  as dest:%s" % (self.sourceProductPath, self.path))
            print("  write EoSip src:%s  as dest:%s" % (self.sourceProductPath, self.path))

        # implements build in temporary folder them move when built. Atomic creation in output folder.
        finalPath = "%s.part" % self.path
        tmpPath = "%s/%s.part" % (os.path.dirname(self.folder), self.sipProductName)
        zipf = None
        if self.test_build_in_tmpspace:
            # raise Exception("built in TMPSPACE not implemented")
            print(" will build product in TMPSPACE, .part file path:%s" % tmpPath)
            # create zip, use temporary .part suffix
            zipf = zipfile.ZipFile(tmpPath, 'w', allowZip64=True)
        else:
            # create zip, use temporary .part suffix
            zipf = zipfile.ZipFile("%s.part" % self.path, 'w', allowZip64=True)

        # copy all EoPieces into dest EoSip
        n = 0
        for pieceName in self.getPieceNames():
            piece = self.getPiece(pieceName)
            data = None
            # replace MD and SSM with corrected content
            if piece.type == definitions_EoSip.getDefinition('MD_EXT'):
                self.processInfo.addLog("  write EoSip piece[%s]: substitute MD content with corrected one" % n)
                data = self.correctMdXml
            elif piece.type == definitions_EoSip.getDefinition('SSM_EXT'):
                self.processInfo.addLog("  write EoSip piece[%s]: substitute SSM content with corrected one" % n)
                data = self.correctSsmXml
            else:
                if piece.content is not None:  # has already the content
                    self.processInfo.addLog("  write EoSip piece[%s]: has content" % n)
                    data = piece.content
                else:  # get it from file: piece.localPathhas to be filled
                    self.processInfo.addLog(
                        "  write EoSip piece[%s]: dont has content: get from file:%s" % (n, piece.localPath))
                    fd = open(piece.localPath, 'r')
                    data = fd.read()
                    fd.close()
            # piece use alias?
            if piece.alias is not None:
                self.processInfo.addLog("  write EoSip piece[%s]: use alias:%s" % (n, piece.alias))
                pieceName = piece.alias
            self.writeStrInZip(zipf, pieceName, data, True)
            if self.debug >= 0:
                self.processInfo.addLog("  write EoSip piece[%s]:%s" % (n, pieceName))
                print("  write EoSip piece[%s]:%s" % (n, pieceName))
            n = n + 1

        # write strip browses images into dest EoSip
        for browsePath in self.sourceBrowsesPath:
            folder = os.path.split(browsePath)[0]
            bmet = self.browse_metadata_dict[browsePath]
            #
            extension = formatUtils.getFileExtension(browsePath)
            name = "%s.%s" % (self.eoProductName, extension)
            if self.processInfo.test_dont_do_browse != True:
                if self.debug == 0:
                    print("   write EoSip browse[n]:%s  as:%s" % (browsePath, name))
                if self.src_product_stored_compression == True:
                    zipf.write(browsePath, name, zipfile.ZIP_DEFLATED)
                    self.processInfo.addLog("deflated: %s" % name)
                else:
                    zipf.write(browsePath, name, zipfile.ZIP_STORED)
                    self.processInfo.addLog("stored: %s" % name)
            else:
                print("   dont' do browse flag is set, so don't write EoSip browse[n]:%s  as:%s" % (browsePath, name))

        zipf.close()
        # 
        if self.test_build_in_tmpspace:
            # self.processInfo.ingester.safeCopy(tmpPath, self.path)
            shutil.move(tmpPath, self.path)
        else:
            # remove temporary part extension
            os.rename("%s.part" % self.path, self.path)

        return self.path

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    #
    #
    def extractMetadata(self, met=None):
        pass

    #
    # refine the metada
    #
    def refineMetadata(self):
        pass

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
        pass

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)
