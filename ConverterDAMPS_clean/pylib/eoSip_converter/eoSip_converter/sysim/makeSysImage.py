#
# a tool that make a image of files/directories at a given path
# - build an image file:
#   store file path, size, hash, modified time, perm
#
# - can verify if the filesystem at path X correspond with the image:
#   keeping the relative path OR just looking for file name (in this case it will not consider duplicated filenames)
#   
# basic usage:
# - make an image of path xxx; produce an sysImage.dat file:
#   > makeSysImage -p xxx
#
# - verify this sysImage.dat image:
#   > makeSysImage -v  sysImage.dat
#
#
#
#
#
#
# Lavaux Gilles
#
# 27/08/2015: V: 0.5
#
#
# -*- coding: cp1252 -*-


from datetime import datetime
from optparse import OptionParser

from . import sysItem
from .sysItem import *

DEFAULT_DATE_PATTERN = "%Y-%m-%d %H:%M:%S"


#
# return a dateTime string
#
def dateFromSec(t, pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(t)
    return d.strftime(pattern)


class SysImage:
    debug = False

    #
    #
    #
    def __init__(self):
        self.newPath = None
        self.sysItems = []
        self.doHash = True
        self.justShortName = False
        if self.debug:
            print("init SysImage")

    #
    #
    #
    def setDoHash(self, b):
        print("setDoHash to:%s; type:%s" % (b, type(b)))
        self.doHash = b

    #
    #
    #
    def setDoJustShortName(self, b):
        print("setDoJustShortName to:%s; type:%s" % (b, type(b)))
        self.justShortName = b

    #
    # make the system files image
    #
    def makeImage(self, p, re1=None, re2=None, includeDir=True, excludeFile=False, aListFile=None):
        self.path = p

        if aListFile is None:
            if not os.path.exists(self.path):
                raise Exception("path does not exists:%s" % self.path)

            print(" will make sys image of path:%s; doHash:%s; includeDir=%s" % (self.path, self.doHash, includeDir))

            total = 0
            done = 0
            error = 0
            errorMessage = {}
            # do dirs
            if includeDir == True:
                print("# DO DIRS")
                helper = fileHelper()
                alist = helper.list_dirs(self.path, None, None)
                print(" found %s items" % len(alist))
                total += len(alist)
                n = 0
                for item in alist:
                    try:
                        print(" item[%s]:%s" % (n, item))
                        sItem = SysItem()
                        sItem.setPath(item.replace('\\', '/'))
                        sItem.stat(self.doHash)
                        if self.debug:
                            print("   dir item:%s" % sItem)
                        self.sysItems.append(sItem)
                        n = n + 1
                        done += 1
                    except:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        errorMesg = "%s %s" % (exc_type, exc_obj)
                        traceback.print_exc(file=sys.stdout)
                        error += 1
                        errorMessage[sItem.path] = errorMesg

            if not excludeFile:
                # do files
                helper = fileHelper()
                res1 = re1
                res2 = re2
                if res1 == None:
                    res1 = ".*"
                if res2 == None:
                    res2 = ".*"
                print("# DO FILES\n use regex:%s and %s" % (res1, res2))
                reName = re.compile(res1)
                reExt = re.compile(res2)
                helper.DEBUG = 1
                alist = helper.list_files(self.path, reName, reExt)
                print(" found %s items" % len(alist))
                total += len(alist)
                n = 0
                for item in alist:

                    try:
                        print(" item[%s]:%s" % (n, item))
                        if os.path.isfile(item):
                            #
                            itemRelPath = item.replace(self.path, '')
                            itemRelPath = itemRelPath.replace('\\', '/')
                            #
                            sItem = SysItem()
                            sItem.setPath(item.replace('\\', '/'))
                            sItem.stat(self.doHash)
                            # if self.doHash==True:
                            #    oldHash = sItem.hash
                            #    aHash = sysItem.hashfile(sItem.getPath())
                            #    sItem.setHash(aHash)
                            # if self.DEBUG:
                            #    print "  file %s; oldHash=%s; hash:%s" % (itemRelPath, oldHash, aHash)

                            #    os._exit(1)
                            self.sysItems.append(sItem)
                            n = n + 1
                        else:
                            if self.debug:
                                print("  directory")
                            sItem = SysItem()
                            sItem.setPath(item.replace('\\', '/'))
                            sItem.stat(self.doHash)
                            self.sysItems.append(sItem)
                            n = n + 1
                        done += 1
                    except:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        errorMesg = "%s %s" % (exc_type, exc_obj)
                        traceback.print_exc(file=sys.stdout)
                        error += 1
                        errorMessage[sItem.path] = errorMesg

        else:
            if not os.path.exists(aListFile):
                raise Exception("list file does not exists:%s" % aListFile)

            print(" will make sys image of item in list file:%s; doHash:%s; includeDir=%s" % (
            aListFile, self.doHash, includeDir))
            fd = open(aListFile, 'r')
            data = fd.read()
            fd.close()
            lines = data.split('\n')
            print(" found %s items" % len(lines))
            total = 0
            done = 0
            error = 0
            errorMessage = {}

            n = 0
            for item in lines:
                if len(item.strip()) > 0:
                    total += 1
                    try:
                        print(" item[%s]:%s" % (n, item))
                        sItem = SysItem()
                        sItem.setPath(item.replace('\\', '/'))
                        sItem.stat(self.doHash)
                        if self.debug:
                            print("  item:%s" % item)
                        self.sysItems.append(sItem)
                        n = n + 1
                        done += 1
                    except:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        errorMesg = "%s %s" % (exc_type, exc_obj)
                        traceback.print_exc(file=sys.stdout)
                        error += 1
                        errorMessage[sItem.path] = errorMesg

        print("finished, total=%s; done=%s, error=%s" % (total, done, error))
        if len(list(errorMessage.keys())) > 0:
            print("\nerrors:")
            n = 0
            for item in list(errorMessage.keys()):
                print("  %s[%s]:%s" % (n, item, errorMessage[item]))
                n += 1

        return 0

    #
    #
    #
    def makeSingleFileImage(self, aPath):
        try:
            sItem = SysItem()
            sItem.setPath(aPath)
            sItem.stat(self.doHash)
            return sItem.path, sItem.type, sItem.size, sItem.perm, sItem.hash, sItem.ctime
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMesg = "%s %s" % (exc_type, exc_obj)
            traceback.print_exc(file=sys.stdout)

    #
    # verify the system files image
    #
    def verifyImage(self, imagePath, destPath, newPath=None):
        print(" will verify sys image at path:%s" % imagePath)
        print(" original system path:%s" % destPath)
        self.newPath = newPath
        if newPath is not None:
            print(" image content is at new path:%s" % self.newPath)
            if not os.path.exists(self.newPath):
                raise Exception("ERROR: new path doesn't exists:%s" % self.newPath)
        self.readImageFile(imagePath)
        print("  image file readed\n")
        if self.justShortName:
            self.verifyItemsShortName()
        else:
            self.verifyItems()

    #
    # verify the sysItems, using shortFileName only
    #
    def verifyItemsShortName(self):
        if self.debug:
            print(" will verify %s items using shortname" % len(self.sysItems))

        aPath = self.path
        if self.newPath is not None:
            aPath = self.newPath

        # build list of files present
        aDict = {}
        helper = fileHelper()
        alist = helper.list_files(aPath, None, None)
        print(" number of files at path %s: %s" % (aPath, len(alist)))

        # look for duplicate
        duplicated = {}
        unique = {}
        for item in alist:
            if os.path.basename(item) in unique:
                duplicated[os.path.basename(item)] = item
                print(" a duplicate[%s]:%s" % (len(list(duplicated.keys())), item))
            else:
                unique[os.path.basename(item)] = item
        print("\n\n number of unique shortName:%s" % len(list(unique.keys())))
        print(" number of duplicated shortName:%s" % len(list(duplicated.keys())))

        found = 0
        numError = 0
        listError = {}
        numOk = 0
        total = 0
        duplicate = 0
        for item in self.sysItems:
            if os.path.basename(item.path) not in duplicated:
                # find file based on shortname
                short = os.path.basename(item.path)
                if short in unique:
                    found += 1
                    aPath = unique[short]
                    print("  will check file[%s] at path:%s" % (total, aPath))
                    sItem = SysItem()
                    sItem.setPath(aPath.replace('\\', '/'))
                    sItem.stat(self.doHash)

                    ok, msg = item.verifyAgains(sItem)
                    if ok:
                        numOk += 1
                    else:
                        numError += 1
                        listError[item] = msg
                else:
                    numError += 1
                    listError[item] = "NOT_FOUND"
            # else:
            # numError+=1
            # duplicate+=1
            # listError[item]="DUPLICATE"

            total += 1

        print("\n\n%s done; %s ok; number of error:%s" % (total, numOk, numError))
        for key in list(listError.keys()):
            print(" %s: %s" % (listError[key], key.path))

    #
    # verify the sysItems
    #
    def verifyItems(self):
        if self.debug:
            print(" will verify %s items" % len(self.sysItems))
        numError = 0
        listError = {}
        numOk = 0
        total = 0
        for item in self.sysItems:
            code, msg = item.verify(self.path, self.newPath, self.doHash)
            if code != sysItem.FILE_OK:
                print("  ERROR: not ok: %s; %s" % (code, msg))
                print("  ERROR: not ok: %s; %s" % (item.getErrorMessage(code), msg))
                listError[item] = "%s; %s" % (item.getErrorMessage(code), msg)
                numError = numError + 1
            else:
                numOk += 1
            total += 1

        print("\n\n%s done; %s ok; number of error:%s" % (total, numOk, numError))
        for key in list(listError.keys()):
            print(" %s: %s" % (key.path, listError[key]))

    #
    #
    #
    def writeImageFile(self, p):
        print(" will write sys image at path:%s" % p)
        if len(self.sysItems) == 0:
            raise Exception("there is no item!")

        fd = open(p, 'w')
        fd.write("#items:%s\n" % len(self.sysItems))
        fd.write("#path:%s\n" % self.path.replace('\\', '/'))
        fd.write("#date:%s\n" % dateFromSec(time.time()))
        fd.write("#headers:%s\n" % self.sysItems[0].getHeader())
        n = 0
        for item in self.sysItems:
            fd.write(item.toString())
            fd.write("\n")
            n = n + 1
        fd.flush()
        fd.close()
        print(" sysImage file written at:%s; contains:%s items" % (p, n))

    #
    #
    #
    def readImageFile(self, p):
        print(" will read sys image at path:%s" % p)
        fd = open(p, 'r')
        n = 0
        self.sysItems = []
        line = 'a'
        total = 0
        while line != None and len(line.strip()) > 0:
            line = fd.readline().strip()
            if self.debug:
                print(" line[%s]:%s" % (n, line))

            if len(line) == 0:
                break

            #
            if line[0] == '#':
                if line.find('#items:') >= 0:
                    total = int(line[len('#items:'):])
                    print("  should have %s items" % total)

                if line.find('#path:') >= 0:
                    self.path = line[len('#path:'):]
                    print("  should be at path:%s" % self.path)
            else:
                sItem = SysItem()
                sItem.fromString(line)
                self.sysItems.append(sItem)
                n = n + 1
        fd.close()
        if total != n:
            raise Exception("total: %s different than readed: %s" % (total, n))
        print("  readed all items")
        print(" sys image readed")


def main():
    try:
        parser = OptionParser()
        parser.add_option("-a", "--reName", dest="reName", help="filename regex")
        parser.add_option("-b", "--reExt", dest="reExt", help="extension regex")
        parser.add_option("-p", "--path", dest="buildPath", help="path that will be imaged")
        parser.add_option("-i", "--image", dest="imagePath", help="path of the image")
        parser.add_option("-v", "--verify", dest="verifyPath", help="path that will be checked agains image")
        parser.add_option("-n", "--newPath", dest="newPath", help="new path of the image content")
        parser.add_option("-s", "--shortName", dest="shortName",
                          help="verify but just use the file shortName (not the path)")
        parser.add_option("-d", "--doHash", dest="doHash", default=True, help="set False to disable hash (faster)")
        parser.add_option("--doDir", dest="doDir", default=True, help="set False to not consider directories")
        parser.add_option("--excludeFiles", dest="excludeFile", default=False, help="set True to not consider files")
        parser.add_option("-l", dest="listFile", help="file listing products path")
        options, args = parser.parse_args(sys.argv)

        # build image file
        if options.buildPath is not None or options.listFile is not None:
            sysImage = SysImage()

            # du hash by default
            doHash = True
            print(" options.doDir=%s" % options.doDir)
            print(" options.doHash=%s" % options.doHash)
            if options.doHash is not None and options.doHash == 'False':
                print("########### do hash:%s" % options.doHash)
                doHash = False
                sysImage.setDoHash(doHash)

            # do dir by default
            doDir = True
            if options.doDir is not None and options.doDir == 'False':
                doDir = False
            print("########### doDir:%s; doHash:%s" % (doDir, doHash))

            # use a list?
            aListFile = None
            if options.listFile is not None:
                aListFile = options.listFile
                print("########### useListFile:%s" % aListFile)
                aPath = '/'
            else:
                aPath = options.buildPath

            # exclude files
            exclude = False
            if options.excludeFile is not None and options.excludeFile == 'True':
                exclude = True
            print("########### doDir:%s; doHash:%s; exclude file:%s" % (doDir, doHash, exclude))
            # os._exit(1)
            sysImage.makeImage(aPath, options.reName, options.reExt, doDir, exclude, aListFile)
            if options.imagePath is not None:
                sysImage.writeImageFile(options.imagePath)
            else:
                sysImage.writeImageFile('sysImage.dat')

        # verify an  image file
        elif options.imagePath is not None:  # options.verifyPath is not None:
            sysImage = SysImage()
            #
            if options.verifyPath is None:
                print(" no verifyPath given")

            #
            if options.shortName is not None and options.shortName == 'True':
                print(" will verify using file shortName only (not path)")
                sysImage.setDoJustShortName(True)

            # du hash by default
            print(" options.doDir=%s" % options.doDir)
            print(" options.doHash=%s" % options.doHash)
            if options.doHash is not None and options.doHash == 'False':
                print("########### do hash:%s" % options.doHash)
                sysImage.setDoHash(False)

            sysImage.verifyImage(options.imagePath, options.verifyPath, options.newPath)

        else:
            print(" invalid syntax: try makeSysImage.py -h")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
