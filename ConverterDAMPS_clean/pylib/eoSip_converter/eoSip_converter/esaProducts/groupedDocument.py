#!/usr/bin/env python
#
#
# Lavaux Gilles 2018
#
#
import sys

#
# document is like:
"""
GROUP = L1_METADATA_FILE 
  GROUP = METADATA_FILE_INFO 
    ORIGIN = "Image courtesy of ESA"
    REQUEST_ID = "0007505110000_00000 "
    LANDSAT_SCENE_ID = "LM12190251975131ESA00"
    FILE_DATE = 2015-06-03T12:14:57Z
    STATION_ID = "ESA"
    PROCESSING_SOFTWARE_VERSION = "SLAP_03.04"
    DATA_CATEGORY = "NOMINAL"
  END_GROUP = METADATA_FILE_INFO
  GROUP = PRODUCT_METADATA 
    DATA_TYPE = "L1G"
    OUTPUT_FORMAT = "GEOTIFF"
"""


#
# we will access it with path like: L1_METADATA_FILE/METADATA_FILE_INFO/REQUEST_ID
#
#
class GroupedDocument:
    debug = 0

    #
    #
    #
    def __init__(self):
        #
        self.lines = None
        if self.debug != 0:
            print(" GroupedDocument created")

    #
    # load content from a file path
    #
    def loadDocument(self, path=None):
        if self.debug != 0:
            print(" loadDocument at path;%s" % path)
        fd = open(path, 'r')
        self.lines = fd.readlines()
        fd.close()

    #
    #
    #
    def getNumberOfLines(self):
        return len(self.lines)

    #
    # set content: has to be lines \n separated
    #
    def setContent(self, txt):
        self.lines = txt.split('\n')
        print(" GroupedDocument setContent, %s lines" % len(self.lines))

    #
    #
    #
    def getLine(self, n):
        return self.lines[n]

    #
    # return start and stop line of a group, between a range of lines
    #
    def getGroupBetween(self, name, start, stop):
        print((" getGroupBetween name=%s; start=%s; stop=%s" % (name, start, stop)))
        n = 0
        found = False
        start2 = -1
        stop2 = -1
        # start of group
        for line in self.lines[start:stop]:
            if line.find('GROUP = %s' % name) >= 0:
                found = True
                start2 = n
                break
            n += 1

        if found:
            found = False
            # end of group
            for line in self.lines[start2 + 1:stop]:
                if line.find('END_GROUP = %s' % name) >= 0:
                    stop2 = n
                    break
                n += 1
            print(("  group '%s' start at line:%s and stop at line:%s" % (name, start2, stop2)))
            return start2, stop2
        raise Exception("group %s not found" % name)

    #
    # return a value in a group
    #
    def getGroupValue(self, key, start, stop):
        n = 0
        v = None
        found = False
        for line in self.lines[start:stop]:
            if line.find('%s = ' % key) >= 0:
                v = line.split('=')[1].strip()
                found = True
                break
        if not found:
            raise Exception("%s not found" % key)
        return v

    #
    # return start and stop line of a group, using path like 'L1_METADATA_FILE/METADATA_FILE_INFO/REQUEST_ID'
    #
    def getGroupByPath(self, aPath):
        print((" getGroupByPath: aPath=%s" % aPath))
        toks = aPath.split('/')
        n = 0
        start = 0
        stop = len(self.lines)
        for tok in toks:
            if n < len(toks):
                print(("\n getGroupByPath: we are at level[%s]:'%s'" % (n, tok)))
                start2, stop2 = self.getGroupBetween(tok, start, stop)
                start = start2
                stop = stop2
            n += 1
        print(("  ==>> getGroupByPath: start=%s; stop=%s" % (start, stop)))
        return start, stop

    #
    #
    #
    def test(self):
        mapping = {'request_id': 'L1_METADATA_FILE/METADATA_FILE_INFO/REQUEST_ID'}

        for field in mapping:
            rule = mapping[field]
            toks = rule.split('/')
            n = 0
            start = 0
            stop = len(self.lines)
            v = None
            for tok in toks:
                if n < len(toks) - 1:
                    print(("\n we are at level[%s]:'%s'" % (n, tok)))
                    start2, stop2 = self.getGroupBetween(tok, start, stop)
                    start = start2
                    stop = stop2
                else:
                    print(("\n we are at last level[%s]:'%s'" % (n, tok)))
                    v = self.getGroupValue(tok, start, stop)
                n += 1
            print((" value=%s" % v))


if __name__ == "__main__":
    groupDoc = GroupedDocument()
    if len(sys.argv) > 1:
        print("use GroupedDocument on path:%s" % sys.argv[1])
        groupDoc.loadDocument(sys.argv[1])
    else:
        groupDoc.loadDocument(
            '/home/gilles/shared/converter_workspace/tmpspace/landsat_eosip/batch_landsat-eosip_001_workfolder_0/eosip_product/LS02_RMTI_MSS_GTC_1P_19780525T083756_19780525T083825_016997_0204_0021_0001.TIFF/LM22040211978145MTI00_MTL.txt')

    groupDoc.test()
