#!/usr/bin/env python
#
# 
# Lavaux Gilles 2014
#
# This class is used to get rows values from CSV files, using a column as  key
# so it returns is a list
#
#
import csv
import sys
import traceback

#
from .csvFile import csvData
from eoSip_converter.base import infoKeeper


class csvMultData(csvData):

    #
    #
    #
    def __init__(self):
        csvData.__init__(self)
        self.multLut = None
        print(" init csvMultData")

    #
    # open a csv file
    #
    def openFile(self, path, key=None, name=None):
        self.debug = 1
        fd = open(path, 'r')
        self.reader = csv.DictReader(fd, delimiter=',')
        n = 0
        doLut = True
        for row in self.reader:
            if n == 0:
                self.headers = list(row.keys())
                if self.debug != 0:
                    print("headers:%s" % self.headers)
                if key is not None and name is not None:
                    try:
                        i1 = self.headers.index(key)
                        i2 = self.headers.index(name)
                        if self.debug != 0:
                            print("can create lut: i1=%d; i2=%d" % (i1, i2))
                        self.multLut = infoKeeper.InfoKeeper()
                    except:
                        print("can not create lut: csv file has no column '%s' or '%s'" % (key, name))
                        doLut = False
                else:
                    doLut = False
            else:
                if doLut:
                    a = row[key]
                    b = row[name]
                    if self.debug != 0:
                        print(" multLut entry[%d]:%s==>%s" % (n, a, b))
                    self.multLut.addInfo(a, b)

            n = n + 1

        self.numLines = n
        print("csv file %s opened, num lines:%s" % (path, self.numLines))
        if self.debug != 0:
            print("dir:%s" % dir(self.reader))
        if doLut == False:
            raise Exception("cvsFile '%s' error: has no column:'%s' or '%s' needed to build LUT" % (path, key, name))

    #
    # get values
    #
    def getRowValues(self, k):
        if k in self.multLut:
            return self.multLut.getKeyValues(k)
        else:
            return None


if __name__ == '__main__':
    try:
        csvd = csvMultData()
        # csvd.openFile("e:/shared/soft/data/AUX_Parent.csv", 'ProductName_child', 'ServerName_child')
        # print "get MIP_PS2_AXVCNR20150320_120000_20050603_000000_20101028_020000:%s" % csvd.getRowValue('MIP_PS2_AXVCNR20150320_120000_20050603_000000_20101028_020000')

        csvd.debug = 1
        # csvd.openFile("e:/shared/soft/data/AUX_Parent.csv", 'ProductName_parent', 'ProductName_child')
        csvd.openFile("e:/shared/soft/data/Product_Parent.csv", 'ProductName_parent', 'ProductName_child')
        # print "get MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1: %s" % csvd.getRowValues('MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1')
        print("get MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1: %s" % csvd.getRowValues(
            'MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1'))

        sys.exit(0)


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
