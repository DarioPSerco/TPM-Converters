# -*- coding: cp1252 -*-
#
# this is an helper for EoSip product
#
#
import logging
import os
import sys
import traceback
import zipfile

from xml_nodes import sipBuilder


class Eosip_product_helper:

    #
    #
    #
    def __init__(self, sipProduct):
        self.eoSipProduct = sipProduct
        # if the metadata is not named 'MD.XML'
        self.mdXmlAlias = None
        # and the 'adapter' used to make standrd MD.XML from other source
        self.mdXmlAdapter = None
        print(" init class Eosip_product_helper")

    #
    # NEW for LANDSAT1-7
    # set an an alias for the MD.XML file, to be used instead of the normal MD.XML
    #
    def setMdXmlAlias(self, s):
        print(" setMdXmlAlias to:%s" % s)
        self.mdXmlAlias = s

    #
    # NEW for LANDSAT1-7
    # set an an alias for the MD.XML file, to be used instead of the normal MD.XML
    #
    def setMdXmlAlias(self, s):
        print(" setMdXmlAlias to:%s" % s)
        self.mdXmlAlias = s

    #
    #
    #
    def getMdXmlAlias(self):
        return self.getMdXmlAlias

    #
    #
    #
    def setXmlAdapter(self, a):
        print(" setXmlAdapter to:%s" % a)
        self.mdXmlAdapter = a

    #
    #
    #
    def getXmlAdapter(self):
        return self.mdXmlAdapter

    #
    #
    #
    def getFileContent(self, path):
        if not os.path.exists(path):
            raise Exception("file does not exists:%s" % path)
        fd = open(path, 'r')
        data = fd.read()
        fd.close()
        return data

    #
    # return an item content of a zipFile item
    #
    # param path: path of zip file
    # param entry: name of the entry we want 
    #
    def getZipFileItem(self, path, entry):
        if entry is None:
            raise Exception("getZipFileItem: cannot get None entry!")
        # example: get MD file in zip
        fh = open(path, 'rb')
        z = zipfile.ZipFile(fh)
        data = z.read(entry)
        z.close()
        fh.close()
        return data

    #
    # test if an zip item is compressed 
    #
    # param path: path of zip file
    # param entry: name of the entry we want 
    #
    def isZipFileItemCompressed(self, path, entry):
        if entry is None:
            raise Exception("isZipFileItemCompressed: cannot get None entry!")
        # get MD file in zip
        fh = open(path, 'rb')
        z = zipfile.ZipFile(fh)
        zipInfo = z.getinfo(entry)
        z.close()
        fh.close()
        print(" ## zip entry %s. Size:%s; compressed size:%s" % (entry, zipInfo.file_size, zipInfo.compress_size))
        return zipInfo.file_size != zipInfo.compress_size

    #
    # return the path and content of MD report
    #
    def getMdPart(self):
        if self.eoSipProduct.created:
            # get MD file in work folder
            return self.eoSipProduct.reportFullPath, self.getFileContent(self.eoSipProduct.reportFullPath)
        else:
            print(" ##@@##@@## getMdPart, self.mdXmlAlias=%s" % self.mdXmlAlias)
            # get MD file in zip
            if self.mdXmlAlias is None:
                if self.eoSipProduct.reportFullPath is None:
                    raise Exception("Problem: don't know what is the metadata file name (MD.XML alias) in the product")
                print(" ##@@##@@## getMdPart, from reportFullPath=%s" % self.eoSipProduct.reportFullPath)
                return self.eoSipProduct.reportFullPath, self.getZipFileItem(self.eoSipProduct.path,
                                                                             self.eoSipProduct.reportFullPath)
            else:
                print(" ##@@##@@## getMdPart, from self.mdXmlAlias=%s" % self.mdXmlAlias)
                return self.eoSipProduct.reportFullPath, self.getZipFileItem(self.eoSipProduct.path, self.mdXmlAlias)

    #
    #
    #
    def getQrPart(self):
        if self.eoSipProduct.created:
            # get QR file in work folder
            return self.eoSipProduct.qualityReportFullPath, self.getFileContent(self.eoSipProduct.qualityReportFullPath)
        else:
            # get QR file in zip
            return self.eoSipProduct.qualityReportFullPath, self.getZipFileItem(self.eoSipProduct.path,
                                                                                self.eoSipProduct.qualityReportFullPath)

    #
    #
    #
    def getSiPart(self):
        if self.eoSipProduct.created:
            # get SI file in work folder
            return self.eoSipProduct.sipFullPath, self.getFileContent(self.eoSipProduct.sipFullPath)
        else:
            # get SI file in zip
            return self.eoSipProduct.sipFullPath, self.getZipFileItem(self.eoSipProduct.path,
                                                                      self.eoSipProduct.sipFullPath)

    #
    #
    #
    def getBrowsePart(self, browseIndex=0):
        if len(self.sourceBrowsesPath) == 0:
            raise Exception("no browse")

        if self.eoSipProduct.created:
            # get browse[n] file in work folder
            return self.eoSipProduct.sipFullPath, self.getFileContent(self.eoSipProduct.sipFullPath)
        else:
            # get browse[n] file in zip
            return self.eoSipProduct.sipFullPath, self.getZipFileItem(self.eoSipProduct.path,
                                                                      self.eoSipProduct.sipFullPath)

    #
    #
    #
    def getEoProductPart(self):
        pass

    #
    # get typology from MD.XML
    #
    def getTypologyFromMdContent(self, data):
        pos = data.find(':EarthObservation')
        if pos > 0:
            tmp = data[pos - 3:pos]
            if tmp in sipBuilder.TYPOLOGY_REPRESENTATION:
                return tmp
            else:
                raise Exception("Wrong typology retrieved: '%s'" % tmp)
        else:
            if 1 == 2:
                if len(data) > 50:
                    tmp = data[0:50]
                else:
                    tmp = data
            raise Exception("can not extract typology")


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        helper = Eosip_product_helper()
    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
