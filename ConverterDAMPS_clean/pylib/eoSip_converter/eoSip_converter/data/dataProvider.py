"""DataProvider class is used to get product metadata from various sources

Lavaux Gilles 2014
"""


class DataProvider:
    initString = None
    dataReader = None
    debug = 0

    def __init__(self, init):
        """
        init (str) is like: METADATA_ORBIT@Kompsat|csvData@csvFile@filePath|Orbit@New_Filename
        - METADATA_ORBIT@Kompsat: name of the metadata we look at, for Product Kompsat
        - class@module@properties that will be used to retrieve the value
        - key|name pair that will be used to build the query
        """
        print("init DataProvider with init string:'%s'" % init)
        self.initString = init
        toks = init.split("|")
        if len(toks[1].split("@")) != 3:
            raise Exception("token 1 of provider source has not 3 '@' separated fields:'%s'" % toks[1])

        aClass, aPackage, aPath = toks[1].split("@")
        if self.debug != 0:
            print("  will instantiate class:'%s' in package:'%s' with init:'%s'" % (aClass, aPackage, aPath))

        name, key = toks[2].split("@")
        if self.debug != 0:
            print(" key;'%s' name;'%s'" % (key, name))

        module = __import__(aPackage, fromlist=['*'])
        if self.debug != 0:
            print(" module loaded:%s" % module)
        class_ = getattr(module, aClass)
        self.dataReader = class_()
        if self.debug != 0:
            print(" got class")
        self.dataReader.openFile(aPath, key, name)
        if self.debug != 0:
            print(" dataReader ready")

    def getRowValue(self, k):
        """Get a value"""
        if self.debug >= 1:
            print(" DataProvider.getRowValue for:%s" % k)
        return self.dataReader.getRowValue(k)

    def getRowValues(self, k):
        """Get values"""
        if self.debug >= 1:
            print(" DataProvider.getRowValues for:%s" % k)
        return self.dataReader.getRowValues(k)


if __name__ == '__main__':
    dp = DataProvider(
        "METADATA_ORBIT@Kompsat|csvData@csvFile@filePath|Orbit@New_Filename"
    )
