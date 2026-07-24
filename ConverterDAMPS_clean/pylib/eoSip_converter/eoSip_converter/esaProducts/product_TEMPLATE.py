# -*- coding: cp1252 -*-
#
# this class represent a worldview directory product
#
#  - 
#  - 
#
#
import os

from .product import Product


class Product_TEMPLATE(Product):
    xmlMapping = {}

    def __init__(self, path=None):
        Product.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_TEMPLATE")

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
    #
    #
    def makeBrowses(self, processInfo):
        pass

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

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
