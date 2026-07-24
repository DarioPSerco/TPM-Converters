#!/usr/bin/env python
#
# 
# Lavaux Gilles 2013
#
#
import os
# import time
import sys


# import re
# from os import walk


#
#
#
#
class SectionDocument:
    debug = 0

    #
    #
    #
    def __init__(self):
        #
        # DEBUG=0
        # section:lineNumber
        self.sectionMap = {}
        #
        self.lines = None
        if self.debug != 0:
            print(" SectionDocument created")

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
    # set content: has to be lines
    #
    def setContentLines(self, lns):
        self.lines = lns
        print(" SectionDocument setContentLines, %s lines" % len(self.lines))

    #
    # set content: has to be lines
    #
    def setContent(self, txt):
        self.lines = txt.split('\n')
        print(" SectionDocument setContent, %s lines" % len(self.lines))

    #
    # section can end with * pattern:
    # 'sectionName blablabla...' or 'sectionName*'
    #
    # also section can start with * pattern:
    # '   sectionName'
    #
    def getSectionLine(self, section):
        if self.debug != 0:
            print(" getSectionLine for section:'%s'" % section)
        posLine = -1
        if section[-1] == '*':  # Wildcard at end
            n = 0
            for line in self.lines:
                if self.debug != 0:
                    print(" test line[%s]:%s" % (n, line))
                if line[0:len(section[0:-1])] == section[0:-1]:
                    if self.debug != 0:
                        print(" getSectionLine wildcard at end; section:%s found at line:%d" % (section, n))
                    posLine = n
                    break
                n = n + 1
        elif section[0] == '*':  # Wildcard at start
            n = 0
            for line in self.lines:
                if self.debug != 0:
                    print(" test line[%s]:%s" % (n, line))
                if line[1:].endswith(section[1:]):
                    if self.debug != 0:
                        print(" getSectionLine  wildcard at start; section:%s found at line:%d" % (section, n))
                    posLine = n
                    break
                n = n + 1
        else:
            if section in self.sectionMap:
                posLine = self.sectionMap[section]
                if self.debug != 0:
                    print(" getSectionLine for section:%s  already known at line:%d" % (section, posLine))
            else:
                n = 0
                for line in self.lines:
                    if line.strip() == section:
                        if self.debug != 0:
                            print(" getSectionLine section:%s found at line:%d" % (section, n))
                        self.sectionMap[section] = n
                        posLine = n
                        break
                    n = n + 1
            if posLine == -1:
                raise Exception("section not found:'%s'" % section)

        if posLine == -1:
            raise Exception("section '%s' not found" % section)
        return posLine

    #
    #
    #
    def getLineValue(self, posLine, name=None, separator=':'):
        pos = self.lines[posLine].find(separator)
        if pos > 0:
            name = self.lines[posLine][0:pos].strip()
            if self.debug != 0:
                print("  getValue: name:'%s'" % name)
            value = self.lines[posLine][pos + 1:]
            if self.debug != 0:
                print("  getValue 00: found:'%s'" % value)
            value = value.replace('\n', '')
            value = value.replace('\r', '')
            if self.debug != 0:
                print("  getValue 11: found:'%s'" % value)
            return value
        else:
            raise Exception("no '%s' in line:%s" % (separator, self.lines[posLine]))

    #
    #
    #
    def getValue(self, section, key, lineNum=0, separator=':'):
        if self.debug != 0:
            print(" getValue for section:'%s' key:'%s'" % (section, key))
        posLine = -1
        if section in self.sectionMap:
            posLine = self.sectionMap[section]
            if self.debug != 0:
                print(" getValue for section:%s  already known at line:%d" % (section, posLine))
        else:
            n = 0
            for line in self.lines:
                if line.strip() == section:
                    if self.debug != 0:
                        print(" getValue for section:%s found at line:%d" % (section, n))
                    self.sectionMap[key] = n
                    posLine = n
                    break
                n = n + 1
        endSection = 0
        if posLine == -1:
            raise Exception("section not found:'%s'" % section)
        posLine = posLine + 1
        value = None
        inBlock = False  # block are inside {} on several lines
        while not endSection == 1 and posLine < len(self.lines):
            line = self.lines[posLine]
            if ord(line[-1]) == 10:
                line = line[0:-1]
            if self.debug != 0:
                print("  getValue: test line[%d]:%s" % (posLine, line))
                print("end of line:%s %d" % (line[-1], ord(line[-1])))
            skip = False
            if line[0] != ' ' and line[0] != '\t':
                endSection = 1
                if self.debug != 0:
                    print("  getValue: end section:'%d'" % ord(line[0]))
            else:
                if line[-1] == '(':
                    if self.debug != 0:
                        print("  getValue: inBlock is True")
                    inBlock = True
                elif line[-2:] == ');':
                    if self.debug != 0:
                        print("  getValue: inBlock is False")
                    inBlock = False
                    skip = True

                if not inBlock and not skip:
                    pos = line.find(separator)
                    if pos > 0:
                        name = line[0:pos].strip()
                        if self.debug != 0:
                            print("  getValue: name:'%s'" % name)
                        if key == name:
                            value = line[pos + 1:]
                            if self.debug != 0:
                                print("  getValue 0: found:'%s'" % value)
                            value = value.replace('\n', '')
                            value = value.replace('\r', '')
                            if self.debug != 0:
                                print("  getValue 1: found:'%s'" % value)
                            break

                    else:
                        raise Exception("no '%s' in line:%s" % (separator, line))

            posLine = posLine + 1
        if value == None:
            raise Exception("Key '%s' not found" % key)
        return value


def test2(sectionDoc):
    mapping_MTL = {'METADATA_CLOUD_COVERAGE': 'CLOUD_COVER*|0',
                   'model': 'DATA_TYPE*|0'}

    for field in mapping_MTL:
        rule = mapping_MTL[field]
        aValue = None
        print(" ##### Handle MTL matadata:%s" % field)

        toks = rule.split('|')
        if len(toks) != 2:
            raise Exception("Malformed MTL matadata rule:%s" % field)
        # wildcard used?
        if toks[0][-1] == '*':
            line = sectionDoc.getSectionLine(toks[0])
            # line offset(s) list are in second token
            offsets = toks[1].split(',')
            aValue = ''
            for offset in offsets:
                nLine = line + int(offset)
                if len(aValue) > 0:
                    aValue = "%s " % aValue
                aValue = "%s%s" % (aValue, sectionDoc.getLineValue(nLine, None, separator='=').replace('"', ''))
            print(" => MTL matadata:%s='%s'" % (field, aValue))
        else:
            aValue = sectionDoc.getValue(toks[0], toks[1])
        # supress initial space is any
        if aValue[0] == ' ':
            aValue = aValue[1:]
        print(" ==>> MTL matadata added:%s='%s'" % (field, aValue))


def main():
    """Main funcion"""

    sectionDoc = SectionDocument()
    if len(sys.argv) > 1:
        print("use SectionDocument on path:%s" % sys.argv[1])
        sectionDoc.loadDocument(sys.argv[1])
    else:
        # sectionDoc.loadDocument('C:/Users/glavaux/Shared/LITE/Ikonos/20090721222747_po_2627437_0000000/po_2627437_metadata.txt')
        sectionDoc.loadDocument(
            '/home/gilles/shared/converter_workspace/tmpspace/landsat_eosip/batch_landsat-eosip_001_workfolder_0/eosip_product/LS02_RMTI_MSS_GTC_1P_19780525T083756_19780525T083825_016997_0204_0021_0001.TIFF/LM22040211978145MTI00_MTL.txt')

    test2(sectionDoc)
    v = sectionDoc.getValue('BEGIN_GROUP = MAP_PROJECTED_PRODUCT', 'mapProjName', 0, '=')
    print("value='%s'" % v)
    os._exit(0)
    mapProjName = v.replace(' ', '').replace(';', '').replace('"', '')

    n = sectionDoc.getSectionLine('numTiles*')
    v = sectionDoc.getLineValue(n, None, '=')
    print("value='%s'" % v)

    n = sectionDoc.getSectionLine('BEGIN_GROUP = TILE_1')
    print("   BEGIN_GROUP = TILE_1 line:%s" % n)

    filename = sectionDoc.getLineValue(n + 1, 'filename', '=').replace('"', '').replace(';', '')
    print("   filename:%s" % filename)
    ULLon = sectionDoc.getLineValue(n + 10, 'ULLon', '=').replace('"', '').replace(';', '')
    print("   ULLon:%s" % ULLon)

    # sectionDoc.getValue('Product Order Area (Geographic Coordinates)', "Number of Coordinates")

    # sectionDoc.getSectionLine('Map Projection:*')


if __name__ == "__main__":
    main()
