# -*- coding: cp1252 -*-
#
# this class is a base class for Esa products
#
#
import logging
import os
import sys
import traceback
from abc import abstractmethod


class Product(object):
    debug = 0
    type = None
    TYPE_UNKNOWN = 0
    TYPE_MPH_SPH = 1
    TYPE_DIR = 2
    TYPE_EOSIP = 3
    TYPE_NETCDF = 4

    #
    #
    #
    def __init__(self, p=None):
        if self.debug:
            print(" init class Product, path=%s" % p)
        self.path = p
        self.metadata = None
        self.size = 0
        self.type = self.TYPE_UNKNOWN
        self.contentList = []
        if p == None:
            return
        # the product original name
        self.origName = os.path.split(self.path)[1]
        self.folder = os.path.split(self.path)[0]
        self.parentFolder = os.path.dirname(self.folder)
        if self.debug:
            print(" folder=%s" % self.folder)
            print(" origName=%s" % self.origName)

    #
    #
    #
    def getPath(self):
        return self.path

    #
    #
    #
    def getSize(self):
        self.size = os.stat(self.path).st_size
        return self.size

    #
    #
    #
    def read(self, size=0, seek=0):
        if self.debug:
            print(" will read product: offset=%d; size=%d" % (seek, size))
        if not os.path.exists(self.path):
            raise Exception("no product at path:%s" % self.path)
        fd = open(self.path, "r")
        if seek > 0:
            fd.seek(seek)
        data = fd.read(size)
        fd.close()
        if self.debug:
            print(" product readed")
        return data

    #
    #
    #
    def writeToPath(self, path=None):
        if self.debug:
            print(" will write product at path:%s" % path)
        return None

    #
    #
    #
    def parseFileName(self):
        if self.debug:
            print(" will parse filename")
        pass

    #
    #
    #
    @abstractmethod
    def getMetadataInfo(self):
        if self.debug:
            print(" will get metadata info")
        return None

    #
    #
    #
    @abstractmethod
    def extractMetadata(self, processInfo):
        if self.debug:
            print(" will extract metadata")
        return None

    #
    # set product metadata
    #
    def setMetadata(self, m=None):
        if self.debug:
            print(" product set metadata to:%s" % m)
            print(" product set metadata to values:%s" % m.toString())
            if self.metadata == None:
                print(" product current metadata :None")
            else:
                print(" product current metadata :%s" % self.metadata)

        if self.metadata is None:
            self.metadata = m
        else:
            # add to existing one
            # dict name/values
            for key in m.getMetadataNames():
                if self.debug:
                    print(" product set metadata name:%s" % key)

                self.metadata.setMetadataPair(key, m.getMetadataValue(key))
                if self.debug:
                    print(" product values:%s" % m.getMetadataValue(key))

                # other info
                self.metadata.otherInfo = m.otherInfo

                # local attributes
                self.metadata.localAttributes = m.localAttributes
            # xml mapping


    @abstractmethod
    def buildTypeCode(self):
        return None

    #
    # set DEBUG flag
    #
    def setDebug(self, b):
        if not isinstance(b, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = b

    #
    # get DEBUG flag
    #
    def getDebug(self):
        return self.debug


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        p = Product("d:\gilles\dev\M01_abcdefgfhj_20020920T100345.txt")
        p.read(1000)
    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
