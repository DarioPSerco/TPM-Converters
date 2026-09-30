# -*- coding: cp1252 -*-
"""This class represent a worldview directory product"""
import os

from eoSip_converter.esaProducts.product import Product


class Product_TEMPLATE(Product):
    xmlMapping = {}

    def __init__(self, path=None):
        Product.__init__(self, path)
        if self.debug != 0:
            print(" init class Product_TEMPLATE")

    def afterProductDone(self):
        """
        Called at the end of the doOneProduct, before the index/shopcart
        creation
        """
        pass

    def getMetadataInfo(self):
        """Read metadata file"""
        pass

    def makeBrowses(self, processInfo):
        pass

    def extractToPath(self, folder=None, dont_extract=False):
        """Extract the product"""
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder

    def buildTypeCode(self):
        pass

    def extractMetadata(self, met=None):
        pass

    def refineMetadata(self):
        """refine the metada"""
        pass

    def extractQuality(self, helper, met):
        """Extract quality"""
        pass

    def extractFootprint(self, helper, met):
        """Extract the footprint posList point, ccw, lat lon"""
        pass

    def toString(self):
        res = "path:%s" % self.path
        return res

    def dump(self):
        res = "path:%s" % self.path
        print(res)
