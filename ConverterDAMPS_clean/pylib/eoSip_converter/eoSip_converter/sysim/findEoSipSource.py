#
# a tool that can find the source of an EoSip (-e option)
#  or from a list (-el option)
# or the eoSip from a source ( -s option)
#  also list of source ( -sl option)
#
# using the conversion image files
#
# Lavaux Gilles
#
# 31/03/2016: V: 0.5
#
#
# -*- coding: cp1252 -*-


from datetime import datetime
from optparse import OptionParser

from .sysItem import *

debug = True

DEFAULT_DATE_PATTERN = "%Y-%m-%d %H:%M:%S"


#
# return a dateTime string
#
def dateFromSec(t, pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(t)
    return d.strftime(pattern)


#
#
#
def doImageFile(imPath, lookedEoSip=None, lookedSrc=None):
    result = []
    print("  doing image file:%s" % imPath)
    with open(imPath, 'r') as fd:
        lines = fd.readlines()

    if len(lines) < 6:
        raise Exception("image file has too few lines:%s" % len(lines))

    numItems = int(lines[0].strip()[len('items:') + 1:])
    path = lines[1].strip()[len('path:') + 1:]
    # date = lines[2].strip()[len('date:') + 1:]
    # headers = lines[3].strip()[len('headers:') + 1:]

    srcPath = lines[4].strip()
    pos = srcPath.find('|')
    srcPath = srcPath[0:pos]

    if debug:
        print("   numItems:%s; path:%s" % (numItems, path))

    # look EoSip from  src
    if lookedSrc != None:
        srcPath = os.path.basename(srcPath)
        if debug:
            print("   test lookedSrc==srcPath: %s == %s " % (lookedSrc, srcPath))
        if lookedSrc == srcPath:
            if debug:
                print("found src:%s" % srcPath)
            for n in range(numItems - 1):
                aPath = lines[5 + n].strip()
                pos = aPath.find('|')
                aPath = aPath[0:pos]
                aBasename = os.path.basename(aPath)
                if debug:
                    print("    an eoSip path[%s]:%s" % (n, aPath))
                result.append(aPath)

    # look SRC from EoSip
    elif lookedEoSip != None:
        for n in range(numItems - 1):
            aPath = lines[5 + n].strip()
            pos = aPath.find('|')
            aPath = aPath[0:pos]
            aBasename = os.path.basename(aPath)
            if debug:
                print("    a path[%s]:%s" % (n, aPath))
            if aBasename == lookedEoSip:
                if debug:
                    print("\n found:%s\n src:%s" % (aBasename, srcPath))
                result.append(srcPath)
                break
    else:
        print("ERROR: botheoSip and src params are None")

    return result


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
def main():
    try:

        imagesPath = None
        imagesPathIsFolder = False
        #
        parser = OptionParser()
        parser.add_option("-i", "--images", dest="imagesPath", help="path of the image(s) file(s)")
        parser.add_option("-e", dest="eoSipPath", help="path of the EoSip")
        parser.add_option("--el", dest="eoSipFileList", help="path of the EoSips list file")
        parser.add_option("-s", dest="srcPath", help="path of the source file")
        parser.add_option("--sl", dest="srcFileList", help="path of the sources list file")
        options, args = parser.parse_args(sys.argv)

        allResult = []
        if options.imagesPath is not None:

            # look for an eosip source
            imagesPath = options.imagesPath
            print(" imagesPath:%s" % imagesPath)
            if options.eoSipPath is not None:
                eoSipPath = options.eoSipPath
                eoSipBasename = os.path.basename(eoSipPath)
                print(" eoSipPath:%s; eoSipBasename:%s" % (eoSipPath, eoSipBasename))
                if os.path.isdir(imagesPath):
                    if debug:
                        print("  imagesPath is a folder")
                    for afile in os.listdir(imagesPath):
                        print("  doing image file:%s" % afile)
                        result = doImageFile("%s/%s" % (imagesPath, afile), eoSipBasename, None)
                        if len(result) > 0:
                            for item in result:
                                if debug:
                                    print("src:%s" % item)
                                allResult.append(item)
                        else:
                            if debug:
                                print('notfound')

                else:
                    print("  imagesPath is a file")
                    print("  doing image file:%s" % imagesPath)
                    result = doImageFile(imagesPath, eoSipBasename, None)
                    if len(result) > 0:
                        for item in result:
                            if debug:
                                print("src:%s" % item)
                            allResult.append(item)
                    else:
                        if debug:
                            print('notfound')

                            # display resutls
                if len(allResult) == 0:
                    print('\nNOTFOUND')
                else:
                    print("")
                    for item in allResult:
                        print("SRC:%s" % item)

            # look for an source EoSip(s)
            elif options.srcPath is not None:
                srcPath = options.srcPath
                srcBasename = os.path.basename(srcPath)
                print(" srcPath:%s; srcBasename:%s" % (srcPath, srcBasename))
                if os.path.isdir(imagesPath):
                    if debug:
                        print("  imagesPath is a folder")
                    for afile in os.listdir(imagesPath):
                        print("  doing image file:%s" % afile)
                        result = doImageFile("%s/%s" % (imagesPath, afile), None, srcBasename)
                        if len(result) > 0:
                            for item in result:
                                if debug:
                                    print("eosip:%s" % item)
                                allResult.append(item)
                        else:
                            if debug:
                                print('notfound')

                else:
                    print("  imagesPath is a file")
                    print("  doing image file:%s" % imagesPath)
                    result = doImageFile(imagesPath, None, srcBasename)
                    if len(result) > 0:
                        for item in result:
                            if debug:
                                print("eosip:%s" % item)
                            allResult.append(item)
                    else:
                        if debug:
                            print('notfound')

                # display resutls
                if len(allResult) == 0:
                    print('\nNOTFOUND')
                else:
                    print("")
                    for item in allResult:
                        print("EOSIP:%s" % item)

            # look sources from a list ofEoSip(s)
            elif options.eoSipFileList is not None:
                eoSipFileList = options.eoSipFileList

                fd = open(eoSipFileList, 'r')
                lines = fd.readlines()
                fd.close()
                for eoSipPath in lines:
                    eoSipPath = eoSipPath.strip()
                    eoSipBasename = os.path.basename(eoSipPath)
                    print(" eoSipPath:%s; eoSipBasename:%s" % (eoSipPath, eoSipBasename))
                    if os.path.isdir(imagesPath):
                        if debug:
                            print("  imagesPath is a folder")
                        for afile in os.listdir(imagesPath):
                            print("  doing image file:%s" % afile)
                            result = doImageFile("%s/%s" % (imagesPath, afile), eoSipBasename, None)
                            if len(result) > 0:
                                for item in result:
                                    if debug:
                                        print("eosip:%s" % item)
                                    allResult.append(item)
                            else:
                                if debug:
                                    print('notfound')

                    else:
                        srcBasename = None
                        print("  imagesPath is a file")
                        print("  doing image file:%s" % imagesPath)
                        result = doImageFile(imagesPath, None, srcBasename)
                        if len(result) > 0:
                            for item in result:
                                if debug:
                                    print("src:%s" % item)
                                allResult.append(item)
                        else:
                            if debug:
                                print('notfound')

                # display resutls
                if len(allResult) == 0:
                    print('\nNOTFOUND')
                else:
                    print("")
                    for item in allResult:
                        print("SRC:%s" % item)

            # look EoSips from a list of source(s)
            elif options.srcFileList is not None:
                srcFileList = options.srcFileList

                fd = open(srcFileList, 'r')
                lines = fd.readlines()
                fd.close()
                for srcPath in lines:
                    srcPath = srcPath.strip()
                    srcBasename = os.path.basename(srcPath)
                    print(" srcPath:%s; srcBasename:%s" % (srcPath, srcBasename))
                    if os.path.isdir(imagesPath):
                        if debug:
                            print("  imagesPath is a folder")
                        for afile in os.listdir(imagesPath):
                            print("  doing image file:%s" % afile)
                            result = doImageFile("%s/%s" % (imagesPath, afile), None, srcBasename)
                            if len(result) > 0:
                                for item in result:
                                    if debug:
                                        print("eosip:%s" % item)
                                    allResult.append(item)
                            else:
                                if debug:
                                    print('notfound')

                    else:
                        print("  imagesPath is a file")
                        print("  doing image file:%s" % imagesPath)
                        result = doImageFile(imagesPath, None, srcBasename)
                        if len(result) > 0:
                            for item in result:
                                if debug:
                                    print("eosip:%s" % item)
                                allResult.append(item)
                        else:
                            if debug:
                                print('notfound')

                # display resutls
                if len(allResult) == 0:
                    print('\nNOTFOUND')
                else:
                    print("")
                    for item in allResult:
                        print("EOSIP:%s" % item)

            #
            else:
                print(" invalid syntax: try findEoSipSource.py -h")
                sys.exit(1)

        else:
            print(" invalid syntax: try findEoSipSource.py -h")
            print("   missing imagesPath parameter")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
