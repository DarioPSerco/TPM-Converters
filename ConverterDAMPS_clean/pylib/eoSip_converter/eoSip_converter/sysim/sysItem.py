#
# makeSysImage tool part

# this classe represent an file system item
#
# Lavaux Gilles
#
# 27/08/2015: V: 0.5
#
#
# -*- coding: cp1252 -*-

import hashlib
import stat

from .fileHelper import *

#
FILE_UNDEFINED = 0
FILE_OK = 1
FILE_NOT_PRESENT = 2
FILE_TYPE_MISMATCH = 3
FILE_PERM_MISMATCH = 4
FILE_CTIME_MISMATCH = 5
FILE_HASH_MISMATCH = 6
FILE_SIZE_MISMATCH = 7
#
ISFILE = 1
ISDIR = 2
ISLINK = 3
ISNOTSET = -1

ERROR_CODE_MESSAGES = ["undefined", "ok", "not present", "type mismatch", "perm mismatch", "ctime mismatch",
                       "hash mismatch", "size mismatch"]

blocksize = 65536

debug = False


#
# return a hash
#
def hashfile(apath):
    # raise Exception("STOP")
    hasher = hashlib.md5()
    if debug:
        print("## hashAfile on %s" % apath)
    afile = open(apath, 'rb')
    total = 0
    buf = afile.read(blocksize)
    total += len(buf)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
        total += len(buf)
    afile.close()
    if debug:
        print("  ==> hash:%s; total=%s" % (hasher.hexdigest(), total))
    return hasher.hexdigest()


#
# represent a file system item: file, dir, link
#
class SysItem:
    debug = False

    def __init__(self):
        if self.debug:
            print("init SysItem")
        self.path = None
        self.type = -1
        self.currentPath = None
        self.size = None
        self.hash = None
        self.perm = None
        self.ctime = None
        self.mtime = None

    def getErrorMessage(self, i):
        return ERROR_CODE_MESSAGES[i]

    def stat(self, doHash=True):
        if self.debug:
            print("stat:%s; hash:%s" % (self.path, doHash))
        if os.path.isfile(self.path):
            self.type = ISFILE
        elif os.path.isdir(self.path):
            self.type = ISDIR
        elif os.path.islink(self.path):
            self.type = ISLINK
        else:
            raise Exception("file is not file not dir nor link but:%s" % self.type)
        self.size = os.path.getsize(self.path)
        self.ctime = os.path.getctime(self.path)
        self.perm = os.stat(self.path)[0]
        self.perm = oct(stat.S_IMODE(os.lstat(self.path).st_mode))
        if doHash == True:
            self.hash = hashfile(self.path)
        # self.hash2 = self.hashfile()
        # self.hash3 = self.hashfile()
        # self.hash4 = self.hashfile()
        # print "\nhash1:%s\nhash2:%s\nhash3:%s\nhash4:%s" % (self.hash1, self.hash2, self.hash3, self.hash4)
        # sys.exit(1)
        # print "perm:%s" % self.perm

    def setType(self, d):
        if d != ISFILE and d != ISDIR and d != ISLINK:
            raise Exception("setType has invalid type:" + d)
        self.type = d

    def getType(self):
        return self.type

    def setPath(self, p):
        self.path = p

    def getPath(self):
        return self.path

    def getName(self):
        return self.path.split(os.sep)[-1]

    def setSize(self, s):
        self.size = s

    def getSize(self):
        return self.size

    def setHash(self, s):
        self.hash = s

    def getHash(self):
        return self.hash

    def setPerm(self, s):
        self.perm = s

    def getPerm(self):
        return self.perm

    def getInfo(self):
        return "path:%s; size:%s; perm:%s; hash:%s" % (self.path, self.size, self.perm, self.hash)

    def getHeader(self):
        return "path|type|size|perm|hash|ctime"

    def toString(self):
        return "%s|%s|%s|%s|%s|%s" % (self.path, self.type, self.size, self.perm, self.hash, self.ctime)

    def fromString(self, line):
        toks = line.split('|')
        self.path = toks[0]
        self.type = int(toks[1])
        self.size = int(toks[2])
        self.perm = toks[3]
        self.hash = toks[4]
        self.ctime = toks[5]

    #
    # verify a sysItem
    #
    def verify(self, origPath, newPath, doHash=True):
        print("\n verify items at path:%s; orig path:%s; doHash=%s" % (self.path, origPath, doHash))
        if newPath:
            # if self.DEBUG:
            print("  items at path:%s; is now at new base path:%s" % (self.path, newPath))

            # build new path
            if len(newPath) > len(origPath):
                newFullPath = "%s/%s" % (newPath, os.path.basename(self.path))
            else:
                leaf = self.path[len(origPath):]
                if self.debug:
                    print("  leaf:%s" % leaf)
                newFullPath = "%s/%s" % (newPath, leaf)

            if self.debug:
                print("  newFullPath:%s" % newFullPath)
            return self.verifyImpl_(newFullPath, doHash)
        else:
            print("  items at path:%s" % self.path)
            return self.verifyImpl_(self.path, doHash)

    #
    # verify a sysItem S anoter one
    #
    def verifyAgains(self, anotherSysItem):
        a = os.path.basename(self.path)
        b = os.path.basename(anotherSysItem.path)
        if a != b:
            return False, 'shortName mismatch:%s VS %s' % (a, b)

        if self.type != anotherSysItem.type:
            return False, 'type mismatch:%s VS %s' % (self.type, anotherSysItem.type)

        if self.size != anotherSysItem.size:
            return False, 'size mismatch:%s VS %s' % (self.size, anotherSysItem.size)

        if self.hash != anotherSysItem.hash:
            return False, 'hash mismatch:%s VS %s' % (self.hash, anotherSysItem.hash)

        return True, 'match'

    #
    # verify implementation
    #
    def verifyImpl_(self, path, doHash):
        print("  verifyImpl items at path:%s; doHash=%s" % (path, doHash))
        # check path exist
        code = self.isPathExists(path)
        if self.debug:
            print(" verify items path:%s" % code)
        if code != FILE_OK:
            if self.debug:
                print(" verify items: return because path not ok error: %s" % code)
            return code, 'not found'

        # check type ok: file/dir/link
        code = self.isTypeOk(path)
        if self.debug:
            print(" verify current items type:%s" % code)
        if code != FILE_OK:
            if self.debug:
                print(" verify items: return because error: %s" % code)
            return code, 'wrong type'

        code, msg = self.isSizeOk(path)
        if code != FILE_OK:
            if self.debug:
                print(" verify items: return because error: %s" % code)
            return code, msg

        if doHash:
            code = self.isHashOk(path)
            if code != FILE_OK:
                if self.debug:
                    print(" verify items: return because error: %s" % code)
                return code, 'wrong hash'

        if self.debug:
            print(" verify items: return: %s" % code)
        return code, 'ok'

    #
    #
    #
    def isPathExists(self, path):
        if not os.path.exists(path):
            return FILE_NOT_PRESENT
        else:
            return FILE_OK

    #
    #
    #
    def isTypeOk(self, path):
        aType = self.getPathType(path)
        if self.debug:
            print("type test; now:%s VS ref:%s" % (aType, self.type))
        if aType != self.type:
            print("type mismatch; now:%s VS ref:%s" % (aType, self.type))
            sys._exit(1)
            return FILE_TYPE_MISMATCH
        else:
            return FILE_OK

    #
    #
    #
    def isSizeOk(self, path):
        s = os.path.getsize(path)
        if s != self.size:
            return FILE_SIZE_MISMATCH, "%s VS ref:%s" % (s, self.size)
        else:
            return FILE_OK, ''

    #
    #
    #
    def isHashOk(self, path):
        # raise Exception("STOP")
        # blocksize=65536
        # hasher=hashlib.md5()
        # afile=open(path, 'r')
        # total=0
        # buf = afile.read(blocksize)
        # total+=len(buf)
        # while len(buf) > 0:
        #    hasher.update(buf)
        #    buf = afile.read(blocksize)
        #    total+=len(buf)
        # afile.close()
        # h=hasher.hexdigest()
        h = hashfile(path)
        if self.debug:
            print("isHashOk: \nself:%s\nfile:%s" % (h, self.hash))
        print("  test original hash:%s VS actual:%s" % (self.hash, h))
        if h != self.hash:
            return FILE_HASH_MISMATCH
        else:
            return FILE_OK

    #
    # return a hash
    #
    def hashfile_not_used(self, apath):
        hasher = hashlib.md5()
        if self.debug:
            print("## hashAfile on %s" % apath)
        afile = open(apath, 'rb')
        total = 0
        buf = afile.read(blocksize)
        total += len(buf)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
            total += len(buf)
        afile.close()
        print("  ==> hash:%s; total=%s" % (hasher.hexdigest(), total))
        return hasher.hexdigest()

    #
    # return the type of the system item: file, dir, link
    #
    def getPathType(self, path):
        if os.path.isfile(path):
            return ISFILE
        elif os.path.isdir(path):
            return ISDIR
        elif os.path.islink(path):
            return ISLINK
        else:
            raise Exception("file is not file not dir nor link")
