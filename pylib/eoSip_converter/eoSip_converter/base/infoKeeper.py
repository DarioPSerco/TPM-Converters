#
# classe used to keep conversion information, for examplelist of typecode encountered
#
import sys
import traceback
from io import StringIO

debug = 0


#
#
#
class InfoKeeper(object):

    #
    #
    #
    def __init__(self):
        # data will be stored in a dictionary. key=info, values is a list
        self.dictionary = {}
        self.debug = debug
        if self.debug != 0:
            print(" init infoKeeper")  # id:%s" % id(self)

    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    #
    def getDebug(self):
        return self.debug

    #
    # add info pair: name=value
    #
    def addInfo(self, info, value):
        if self.debug != 0:
            print("####     infoKeeper.addInfo(): info=%s; value=%s" % (info, value))
        # info already there?
        valueList = None
        if info in self.dictionary:
            valueList = self.dictionary[info]
            if self.debug != 0:
                print("####     infoKeeper.addInfo(): key already present")
        else:
            # create new list
            valueList = []
            self.dictionary[info] = valueList
            if self.debug != 0:
                print("####     infoKeeper.addInfo(): key created")
        # add if not already in list:
        try:
            valueList.index(value)
            if self.debug != 0:
                print("####     infoKeeper.addInfo(): value already in list")
        except:
            # print " Error"
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # traceback.print_exc(file=sys.stdout)
            # print "####     infoKeeper.addInfo(): error: %s %s\n%s" % (exc_type, exc_obj, exc_tb)
            if self.debug != 0:
                print("####     infoKeeper.addInfo(): value not already in list, added")
            valueList.append(value)

        # print "\n\n\nACTUAL INFOKEEPER DUMP:\n%s" % self.toString()

    #
    # clear content
    #
    def clear(self):
        self.dictionary = {}

    #
    # return the key number
    #
    def size(self):
        return len(list(self.dictionary.keys()))

    #
    # return list of keys
    #
    def getKeys(self):
        keys = list(self.dictionary.keys())
        keys.sort()
        return keys

    #
    #
    #
    def has_key(self, key):
        return key in self.dictionary

    #
    # return list of values for a given key
    #
    def getKeyValues(self, key):
        if key not in self.dictionary:
            raise Exception("unknown key:%s" % key)
        return self.dictionary[key]

    #
    #
    #
    def toString(self):
        out = StringIO()
        print('infoKeeper dump:', file=out)
        keys = list(self.dictionary.keys())
        keys.sort()
        for info in keys:
            print("  info:'%s'" % info, file=out)
            n = 0
            values = self.dictionary[info]
            values.sort()
            for value in values:
                print("    value[%d]:'%s'" % (n, value), file=out)
                n = n + 1

        return out.getvalue()


if __name__ == '__main__':
    try:
        keeper = InfoKeeper()
        keeper.addInfo('typeCode', 'a')
        keeper.addInfo('typeCode', 'b')
        keeper.addInfo('typeCode', 'c')
        keeper.addInfo('sensor', 'sa')

        print("%s" % keeper.toString())


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
