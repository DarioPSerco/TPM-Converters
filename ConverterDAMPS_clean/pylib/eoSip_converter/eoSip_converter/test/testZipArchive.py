# -*- coding: cp1252 -*-
#
# 
#
#
import sys
import traceback
import zipfile


def listZipContent(path):
    fh = open(path, 'rb')
    z = zipfile.ZipFile(fh)

    #
    n = 0
    numCompress = 0
    numNonCompress = 0
    for entry in z.namelist():
        print("entry[%d] name:%s" % (n, entry))
        zipInfo = z.getinfo(entry)
        # print "  entry[%d] zipInfo:%s" % (n, zipInfo)
        compressed = zipInfo.file_size != zipInfo.compress_size
        if compressed:
            numCompress += 1
        else:
            numNonCompress += 1
        print(" size:%s; compressed size:%s;   compressed:%s" % (zipInfo.file_size, zipInfo.compress_size, compressed))
        n = n + 1

    print("\n\nTotal:%s\n compressed:%s\n non compressed:%s" % (n, numCompress, numNonCompress))


if __name__ == '__main__':

    aZip = 'E:/Shared/converter_workspace/outspace/pleiades/2012/02/25/PH1_OPER_HIR_P_S_1A_201202T002500_S37-818_E144-955_3081.SIP.ZIP'

    try:
        if len(sys.argv) > 1:
            aZip = sys.argv[1]
        print("looking at zip file:%s\n" % aZip)

        listZipContent(aZip)

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
