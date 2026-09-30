#!/usr/bin/env python
#
# file helper
# Lavaux Gilles 2013
#
#
import os
import re
import subprocess
import sys
import time
import traceback
from os import walk
from os.path import splitext, join


#
#
#
def df1(filename):
    df = subprocess.Popen(["df", "filename"], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    device, size, used, available, percent, mountpoint = output.split("\n")[1].split()


#
#
#
def df2_NOT_USED(filename):
    statvfs = os.statvfs(filename)
    statvfs.f_frsize * statvfs.f_blocks  # Size of filesystem in bytes
    statvfs.f_frsize * statvfs.f_bfree  # Actual number of free bytes
    statvfs.f_frsize * statvfs.f_bavail  # Number of free bytes that ordinary users
    # are allowed to use (excl. reserved space)


class FileHelper:
    scanned = 0
    debug = 0

    #
    #
    #
    def __init__(self):
        if self.debug != 0:
            print("fileHelper created")

    #
    # params:
    #  root: root path
    #  files: list of files (string)
    #  nameFilter: regex (re) compiled filter for name 
    #  extFilter: regex (re) compiled filter for extension
    #
    def select_files(self, root, files, nameFilter=None, extFilter=None):

        # sys.stdout.write(" current path:%s                                                 \r" % root)
        selected_filesPath = []

        for file in files:
            self.scanned += 1
            # do concatenation here to get full path
            full_path = join(root, file)
            ext = splitext(file)[1]
            name = splitext(file)[0]
            if self.debug != 0:
                print("  full_path:%s; name=%s; ext=%s" % (full_path, name, ext))
            ok = 1
            if nameFilter is not None:
                rs = nameFilter.match(name)
                # print "  name re result:%s" % rs
                if rs == None:
                    ok = 0
                    continue

            if extFilter is not None:
                rs = extFilter.match(ext)
                # print "  ext re result:%s" % rs
                if rs == None:
                    ok = 0
                    continue

            if ok:
                selected_filesPath.append(full_path)

        return selected_filesPath

    #
    # params:
    #  root: root path
    #  dirs: list of dirs (string)
    #  dirFilter: regex (re) compiled filter
    #  isLeaf: is the folder terminal
    #  isEmpty: 
    #
    def select_dirs(self, root, dirs, dirFilter=None, isLeaf=None, isEmpty=None):

        if self.debug != 0:
            print(" select_dirs root:%s" % root)
            print("             dirs:%s" % dirs)
            print("             dirFilter:%s" % dirFilter)
            print("             isLeaf:%s" % isLeaf)
            print("             isEmpty:%s" % isEmpty)

        selected_dirPath = []

        for dir in dirs:
            self.scanned += 1
            # do concatenation here to get full path
            full_path = join(root, dir)
            if self.debug != 0:
                print("  full_path:%s" % full_path)

            ok = 1
            if dirFilter != None:
                rs = dirFilter.match(dir)
                # print "  re result:%s" % rs
                if rs == None:
                    ok = 0
                    if self.debug != 0:
                        print("   --> not ok because of name re")
                    continue

            # test on isLeaf: test if there is subdir
            childs = os.listdir(full_path)
            if isLeaf is not None and isLeaf == 1:
                for item in childs:
                    empty = 0
                    if os.path.isdir(os.path.join(full_path, item)):
                        ok = 0
                        if self.debug != 0:
                            print("   --> not ok because of isleaf")
                        continue

            # test on isEmpty
            if isEmpty is not None and isEmpty == 1 and len(childs) != 0:
                ok = 0
                if self.debug != 0:
                    print("   --> not ok because of isEmpty has to be 1")
                continue

            if isEmpty is not None and isEmpty == 0 and len(childs) == 0:
                ok = 0
                if self.debug != 0:
                    print("   --> not ok because of isEmpty has to be 0")
                continue

            if ok:
                selected_dirPath.append(full_path)

        return selected_dirPath

    #
    # get recursive list of files
    #
    def list_files(self, path, nameFilter=None, extFilter=None):
        self.scanned = 0
        if self.debug != 0:
            print("")
            print(" list_files: path=%s;  nameFilter=%s;  extFilter=%s" % (path, nameFilter.pattern, extFilter.pattern))
        selected_files = []

        if os.path.exists(path):
            for root, dirs, files in walk(path):
                selected_files += self.select_files(root, files, nameFilter, extFilter)
        else:
            raise Exception("path does not exists:%s" % path)

        return selected_files

    #
    # get recursive list of dir
    #
    def list_dirs(self, path, dirFilter=None, isLeaf=None, isEmpty=None):
        self.scanned = 0
        if self.debug != 0:
            print("")
            print(" list_dirs: path=%s;  dirFilter=%s;  isLeaf=%s;  inEmpty=%s" % (path, dirFilter, isLeaf, isEmpty))
        selected_dir = []

        if os.path.exists(path):
            for root, dirs, files in walk(path):
                selected_dir += self.select_dirs(root, dirs, dirFilter, isLeaf, isEmpty)
        else:
            raise Exception("path does not exists:%s" % path)

        return selected_dir

    #
    # return the basename of a file (remove the path)
    #
    def basename(self, path):
        return os.path.basename(path)
        # pos = path.rfind('/')
        # if pos > 0:
        #    return path[pos+1:]
        # else:
        #    return path

    #
    # return the dirname of a file (the path)
    #
    def dirname(self, path):
        return os.path.dirname(path)
        # pos = path.rfind('/')
        # if pos > 0:
        #    return path[0:pos]
        # else:
        #    return None

    #
    # return the extension for a filename/fullPath
    #
    def getFileExtension(self, path):
        pos = path.rfind('.')
        if pos > 0:
            return path[(pos + 1):]
        else:
            return None

    #
    # remove the extension for a filename/fullPath
    #
    def removeFileExtension(self, path):
        pos = path.rfind('.')
        if pos > 0:
            return path[0:pos]
        else:
            return path

    #
    # erase a folder content
    #
    def eraseFolder(self, path, itself=False):
        try:
            # if self.DEBUG!=0:
            print(" will erase folder at path:%s" % path)
            files = self.list_files(path, None, None)
            # if self.DEBUG!=0:
            print("  number of files to erase:%s" % len(files))
            for item in files:
                if self.debug != 0:
                    print("eraseFolder: will erase file:%s" % item)
                self.safeRemoveFile(item, path)

            dirs = self.list_dirs(path, None, None)
            if len(dirs) > 0:
                dirs.reverse()
                for item in dirs:
                    if self.debug != 0:
                        print("eraseFolder: will erase dir:%s" % item)
                    os.rmdir(item)

            if itself is not None and itself == True:
                os.rmdir(path)

        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("eraseFolder error:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))

    #
    # remove a file, test that is is inside a base folder
    #
    def safeRemoveFile(self, path, base):
        realBase = os.path.realpath(base)
        if self.debug != 0:
            print(" safeRemoveFile: path:%s; base:%s" % (path, realBase))
        realPath = os.path.realpath(path)
        if self.debug != 0:
            print("\n safeRemoveFile: realPath:%s" % realPath)
            print(" safeRemoveFile:     base:%s" % realBase)
        # os._exit(1)

        if realPath.startswith(realBase):
            if self.debug != 0:
                print(" in base path, can remove")
            os.remove(path)
        else:
            print(" safeRemoveFile problem: not in base path %s, can not remove file %s" % (realBase, realPath))

    #
    # set access and modification time
    #
    def setAMtime(self, path, accessed, modified):
        if self.debug != 0:
            print(" setAMtime on %s to:%s and %s" % (path, accessed, modified))
        os.utime(path, (accessed, modified))

    #
    # set DEBUG flag
    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        print(" fileHelper setDebug:%s" % d)
        self.debug = d

    #
    def getDebug(self):
        return self.debug


def main():
    """Main funcion"""

    helper = FileHelper()

    if len(sys.argv) > 1:
        print("use fileHelper on path:%s" % sys.argv[1])
    #
    # reProg = re.compile("^LS__PROD_RPT___.*")
    re1Prog = re.compile("^.*Analytic_metadata$")
    re2Prog = re.compile("^.xml$")
    #
    # reProg=None
    # re1Prog=None
    # re2Prog=None
    start = time.time()
    list = helper.list_files(sys.argv[1], re1Prog, re2Prog)
    # list=helper.list_dirs(sys.argv[1], reProg, 1, 0)
    stop = time.time()
    for item in list:
        print(item)

    print("")
    print("num of result:%d" % len(list))
    print("done in %f sec, scanned:%d" % ((stop - start), helper.scanned))
    # print "result:%s" % list

    a = 'C:/Users/glavaux/Shared/LITE/testData/Aeolus/ADM/1B/AE_TEST_ALD_U_N_1B_20101002T000000059_000936000_017071_0001.DBL'
    print("basename of:%s" % a)
    print(" ==>%s" % helper.basename(a))
    print("dirname of:%s" % a)
    print(" ==>%s" % helper.dirname(a))


if __name__ == "__main__":
    main()
