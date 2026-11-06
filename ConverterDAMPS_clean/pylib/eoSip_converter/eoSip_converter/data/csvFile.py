"""Contains csvData class which is used to get a row values from CSV files,
using a column as primary key so it returns a single value

Lavaux Gilles 2014
"""
import csv
import sys
import traceback


class csvData:
    headers = None
    key = None
    lut = None
    reader = None

    debug = 0
    numLines = -1

    def __init__(self):
        print(" init csvData")

    def openFile(self, path, key=None, name=None):
        """Open a csv file"""
        with open(path, 'rt') as fd:
            self.reader = csv.DictReader(fd, delimiter=',')

            doLut = True
            line_idx = None
            for line_idx, row in enumerate(self.reader):
                if line_idx == 0:
                    self.headers = list(row.keys())
                    if self.debug != 0:
                        print("headers:%s" % self.headers)
                    if key is not None and name is not None:
                        try:
                            i1 = self.headers.index(key)
                            i2 = self.headers.index(name)
                            if self.debug != 0:
                                print("can create lut: i1=%d; i2=%d" % (i1, i2))
                            self.lut = {}
                        except ValueError:
                            print("can not create lut: csv file has no column '%s' or '%s'" % (key, name))
                            doLut = False
                    else:
                        doLut = False

                if doLut:
                    a = row[key]
                    b = row[name]
                    if self.debug != 0:
                        print(" lut entry[%d]:%s==>%s" % (line_idx, a, b))
                    self.lut[a] = b

            self.numLines = 0 if line_idx is None else line_idx + 1

            print("csv file %s opened, num lines:%s" % (path, self.numLines))
            if self.debug != 0:
                print("dir:%s" % dir(self.reader))
            if not doLut:
                raise Exception("cvsFile '%s' error: has no column:'%s' or '%s' needed to build LUT" % (path, key, name))

    def getRowValue(self, k):
        """Get a value"""
        if k in self.lut:
            return self.lut[k]
        else:
            return None

    def getValues(self):
        """Get values"""
        return list(self.lut.values())


if __name__ == '__main__':
    try:
        csvd = csvData()
        csvd.openFile("e:/shared/soft/data/AUX_Parent.csv", 'ProductName_child', 'ServerName_child')
        csvd.openFile("e:/shared/soft/data/AUX_Parent.csv", 'ProductName_parent', 'ProductName_child')
        print(
            "get MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1: %s" %
            csvd.getRowValue('MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1')
        )

        values = csvd.getValues()
        values.sort()
        typecode = {}
        for item in values:
            pos = item.find('.')
            if pos > 0:
                typecode[item[pos + 1:]] = item

        for item in list(typecode.keys()):
            print(item)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
