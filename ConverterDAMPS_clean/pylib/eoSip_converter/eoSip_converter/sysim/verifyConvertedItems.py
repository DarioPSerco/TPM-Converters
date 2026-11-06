#
# a tool that can verify that converted EoSip files are ok
# using the conversion image files
#
# Lavaux Gilles
#
# 31/03/2016: V: 0.5
#
#
# -*- coding: cp1252 -*-


from optparse import OptionParser

from . import sysItem
from .sysItem import *

debug = False


#
# An conversion image is at leat 6 lines:
# they may be several output for one input, so the items: entry has to be used
#
# items:2
# path:mixed
# date:2016-03-31T11:38:44Z
# headers:path|size|perm|hash|ctime
#  /home/gilles/shared/Datasets/Cryosat/L0/CS_OPER_DOR_DAT_0__20160318T051243_20160318T065142_0001.TAR|471040|0777|5592608eb6a11502d6af5f4229164fe9|1458295750.0
#  /home/gilles/shared/converter_workspace/outspace/cryosat/2016/03/18/CR2_OPER_DOR_DAT_0__201603T051243_201603T065142_0001.ZIP|26011|0777|936a1f2d604ee0f63bbf2b2f4e5d0d04|1459417124.9
#
#
#
#
def verifyOneConversion(imgFile, options):
    print("  verify image file:%s" % imgFile)
    verifyEoSip = options.verifyEoSip
    verifySrc = options.verifySrc
    eoSipPath = options.eoSipPath
    srcPath = options.srcPath
    fd = open(imgFile, 'r')
    lines = fd.readlines()
    fd.close()
    if len(lines) < 6:
        raise Exception("image file has too few lines:%s" % len(lines))
    # print "line0:%s" % lines[0]
    numItems = lines[0].strip()[len('items:') + 1:]
    numItems = int(numItems)
    path = lines[1].strip()[len('path:') + 1:]
    date = lines[2].strip()[len('date:') + 1:]
    headers = lines[3].strip()[len('headers:') + 1:]
    if debug:
        print("   numItems:%s; path:%s" % (numItems, path))

    totalSrcOk = 0
    totalSrcNotOk = 0
    if verifySrc is not None and verifySrc:
        # print "    verify source"
        sItem = SysItem()
        sItem.fromString(lines[4].strip())
        print("    verify source:%s" % sItem.path)
        ok = sItem.verify()
        if ok != sysItem.FILE_OK:
            print("    -> NOT OK")
            totalSrcNotOk += 1
        else:
            print("    -> OK")
            totalSrcOk += 1

    totalOk = 0
    totalNotOk = 0
    if verifyEoSip is not None and verifyEoSip:
        print("    verify EoSip(s)")
        for n in range(numItems - 1):
            # print "    verify EoSip[%s]" % n
            sItem = SysItem()
            sItem.fromString(lines[5 + n].strip())
            print("    verify EoSip[%s]:%s" % (n, sItem.path))
            ok = sItem.verify()
            if ok != sysItem.FILE_OK:
                print("    -> NOT OK")
                totalNotOk += 1
            else:
                print("    -> OK")

    ok = True
    if verifySrc is not None and verifySrc:
        if totalSrcNotOk != 0:
            ok = False
            print("    -not all ok because some source failled.")
    if verifyEoSip is not None and verifyEoSip:
        if totalNotOk != 0:
            ok = False
            print("    -not all ok because some EoSip failled.")

    return ok


#
#
#
def main():
    try:

        imagesPath = None
        imagesPathIsFolder = False
        #
        parser = OptionParser()
        parser.add_option("-i", "--images", dest="imagesPath", help="path of the image(s) file(s)")
        parser.add_option("--eoSipPath", dest="eoSipPath", help="new path of the EoSip")
        parser.add_option("--verifyEoSip", dest="verifyEoSip", help="verify the EoSip")
        parser.add_option("--srcPath", dest="srcPath", help="new path of the source(s)")
        parser.add_option("--verifySrc", dest="verifySrc", help="verify the source(s)")
        options, args = parser.parse_args(sys.argv)

        if options.imagesPath is not None:
            imagesPath = options.imagesPath
            print(" imagesPath:%s" % imagesPath)
            if os.path.isdir(imagesPath):
                imagesPathIsFolder = True
                if debug:
                    print("  imagesPath is a folder")
                total = 0
                totalOk = 0
                totalNotOk = 0
                for afile in os.listdir(imagesPath):
                    if debug:
                        print("  doing image file:%s" % afile)
                    total += 1
                    ok = verifyOneConversion("%s/%s" % (imagesPath, afile),
                                             options)  # options.verifyEoSip, options.verifySrc, options.eoSipPath, options.srcPath)
                    if ok:
                        totalOk += 1
                    else:
                        totalNotOk += 1
                print("\n  Result: ok:%s; not ok:%s\n" % (totalOk, totalNotOk))

            else:
                if debug:
                    print("  imagesPath is a file")
                print("  doing image file:%s" % imagesPath)
                ok = verifyOneConversion("%s" % imagesPath, options)
                if ok:
                    print("\n  ok\n")
                else:
                    print("\n  ok\n")


        else:
            print(" invalid syntax: try verifyConvertedItems.py -h")
            print("   need at least an image(s) path")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
