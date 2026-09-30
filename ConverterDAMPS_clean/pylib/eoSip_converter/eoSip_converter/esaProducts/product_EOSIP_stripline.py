# -*- coding: cp1252 -*-
#
# this class is an extension of the EoSip classe
#  it adds
#
# - parsing of stripline SSM file
# - frames dictionnary
#
import logging
import sys
import traceback

from eoSip_converter.esaProducts import metadata as metadata
from eoSip_converter.esaProducts.frame import Frame
#
from eoSip_converter.esaProducts.product_EOSIP import Product_EOSIP

SSM_FRAME_MAPPING = 'EarthObservation'


class Product_EOSIP_Stripline(Product_EOSIP):

    #
    # set defaults
    #
    def __init__(self, path=None):
        Product_EOSIP.__init__(self, path)
        self.frames = {}

    #
    # return information on the EoSip stipline product
    #
    def info(self):
        eoSipInfo = Product_EOSIP.info_impl(self)
        stripLineInfo = "### this is the stripline info part ###"
        return "%s\n%s" % (stripLineInfo, eoSipInfo)

    #
    # read ssm metadata content from src eoSip (zip file)
    # write a copy in workfolder
    #
    def getSsmMetadataInfo(self):
        content = None
        for item in self.eoPieces:
            if item.name.find('.SSM.') > 0:
                print("founf SSM piece:%s" % item.name)
                content = self.getPieceContent(item.name)
                break
        return content

    #
    # get frame index
    #
    def getFramesKeys(self):
        return list(self.frames.keys())

    #
    # get a frame
    #
    def getFrame(self, index):
        return self.frames[index]

    #
    # get number of frames
    #
    def getNumFrames(self):
        return len(list(self.frames.keys()))

    #
    # not needed
    #
    def extractToPath(self, folder=None, dont_extract=False):
        pass

    #
    # extract metadata, first from MD file (in parent), then from stripline SSM file
    #
    def extractMetadata(self, met=None):
        # from MD file, using parent method
        numAdded, helper = Product_EOSIP.extractMetadata(self, met)
        if self.debug != 0:
            print("  stipline_product: extractMetadata added %s metadata from parent" % numAdded)

        # get footprint from MD
        # helper=xmlHelper.XmlHelper()
        helper.setData(self.metContent)
        helper.parseData()
        doc = helper.getDomDoc()
        footprintPosListNodes = doc.getElementsByTagName('gml:posList')
        if footprintPosListNodes is not None and len(footprintPosListNodes) > 0:
            footprint = helper.getNodeText(footprintPosListNodes[0])
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            if self.debug != 0:
                print("  stipline_product: MD footprint:%s" % footprint)
        else:
            raise Exception("cannot get footprint from MD file")

        centerPosListNodes = doc.getElementsByTagName('gml:pos')
        if centerPosListNodes is not None and len(centerPosListNodes) > 0:
            center = helper.getNodeText(centerPosListNodes[0])
            met.setMetadataPair(metadata.METADATA_SCENE_CENTER, center)
            if self.debug != 0:
                print("  stipline_product: MD center:%s" % center)

        # get info from SSM file, for creating frames
        self.ssmMetContent = self.getSsmMetadataInfo()
        # print "############## ssm met content:%s" % self.ssmMetContent
        # helper=XmlHelper()
        helper.setData(self.ssmMetContent)
        helper.parseData()
        if self.debug != 0:
            print("  stipline_product: ssm metadata parsed")
        tmpNodes = []
        helper.getNodeByPath(None, SSM_FRAME_MAPPING, None, tmpNodes)
        if len(tmpNodes) == 0:
            raise Exception('can not get EarthObservation node from SSM')
        n = 0
        frame = None
        for node in tmpNodes:
            print("  parsing SSM for frame[%s]" % n)
            frame = Frame(n)
            frame.parseNode(node, helper)
            if n == 0:
                frame.first = True
            self.frames[n] = frame
            print("  frame[%s] dump:\n%s" % (n, frame.info()))
            n += 1
        if frame is not None:
            frame.last = True


if __name__ == '__main__':
    print("start")

    # print "HELLO:%s" % dir(XmlHelper)
    # sys.exit(0)

    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        # eoSipStriplineProduct=Product_EOSIP_Stripline("/home/gilles/shared2/MDPs/EN1_OESR_ASA_IM__0P_20100204T002606_20100204T002748_041467_0331_0001.MDP.ZIP")
        eoSipStriplineProduct = Product_EOSIP_Stripline(
            "/home/gilles/shared2/MDPs/fake/ASA_IM__0PNPDK20021115_131741_000001212011_00153_03714_0118.MD.ZIP")
        # eoSipStriplineProduct.setDebug(1)
        eoSipStriplineProduct.loadProduct()
        print("EoSip stipline info:\n%s" % eoSipStriplineProduct.info())

        met = metadata.Metadata()
        numAdded = eoSipStriplineProduct.extractMetadata(met)
        print(" number of metadata added:%s" % numAdded)
        print("\n###\n###\n###\nMETADATA:%s\n###\n###\n###\n" % met.toString())

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
