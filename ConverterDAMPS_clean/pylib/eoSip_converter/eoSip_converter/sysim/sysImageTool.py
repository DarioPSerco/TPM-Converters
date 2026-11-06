#
# a tool that make operation on image files:
# - concatenate them
#
#
#
# Lavaux Gilles
#
# 25/05/2018: V: 0.5
#
#
# -*- coding: cp1252 -*-


from datetime import datetime
from optparse import OptionParser

from .sysItem import *

debug = False

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
def syntax():
    print("syntax: python sysImageTool -a action -o output  a b c d e ...")


#
#
#
def concat(aList, outfilename):
    print((" -> will create %s with files:%s" % (outfilename, aList)))

    fd = open("%s_part" % outfilename, 'w')

    n = 0
    error = 0
    doneFile = 0
    numItems = 0
    totalSize = 0
    for aFile in aList:
        print((" doing file[%s]:%s" % (doneFile, aFile)))
        if not os.path.exists(aFile):
            raise Exception("File not found:%s" % aFile)

        numDoneItems = 0
        numFileItems = 0
        with open(aFile) as infile:
            nLine = 0
            numFileItems = 0
            numDoneItems = 0
            for line in infile:
                line = line.strip()
                if len(line) > 0:
                    if nLine == 0:
                        numFileItems = int(line[1:].split(':')[1])
                    else:
                        if line[0] != '#':
                            print((" T:%s; a file[%s].item[%s]:%s" % (numItems, doneFile, numDoneItems, line)))
                            try:
                                size = int(line.split('|')[2])
                                totalSize += size
                            except:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                traceback.print_exc(file=sys.stdout)
                                raise Exception(
                                    "Error getting size from:%s; %s %s" % (line.split('|')[2], exc_type, exc_obj))
                            fd.write(line)
                            fd.write('\n')
                            numDoneItems += 1
                            numItems += 1
                    nLine += 1
            if numFileItems != numDoneItems:
                print((" Error on file:%s; numItems:%s; doneItems=%s" % (numFileItems, numDoneItems)))

        doneFile += 1

    fd.flush()
    fd.close()
    print("\n\n\n temporary file created")
    fd = open("%s" % outfilename, 'w')
    fd.write("#items:%s\n" % numItems)
    fd.write("#path:/\n")
    fd.write("#date:%s\n" % dateFromSec(time.time()))
    fd.write("# headers:path|type|size|perm|hash|ctime\n")
    with open("%s_part" % outfilename, 'r') as infile:
        for line in infile:
            fd.write(line)
    fd.flush()
    fd.close()
    print(("\n\n\n final file created:%s" % outfilename))

    print((" done files:%s; num items:%s; size=%s" % (doneFile, numItems, totalSize)))
    print((" human size=%s" % (humansize(totalSize))))


suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


def humansize(nbytes):
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


#
#
#
def main():
    try:
        parser = OptionParser()
        parser.add_option("-a", "--action", dest="action", help="action")
        parser.add_option("-o", "--output", dest="output", help="output filename")
        parser.add_option("-d", "--directory", dest="directory", help="directory containing source files")
        options, args = parser.parse_args(sys.argv)

        # concat
        if options.action is not None:
            if options.action == 'concat':
                if options.output is None:
                    print(" missing -o parameter")
                    syntax()
                aList = []
                ok = False
                n = 0
                m = 0

                if options.directory is not None:
                    # get from directory
                    aListtmp = os.listdir(options.directory)
                    for item in aListtmp:
                        aList.append("%s/%s" % (options.directory, item))
                else:
                    for item in sys.argv:
                        if debug:
                            print((" test param[%s]=%s; m=%s" % (n, item, m)))

                        if n > 0 and not item.startswith('-'):
                            ok = True
                            if m == 0:
                                m = 1
                                if debug:
                                    print(" m armed!")
                            else:
                                m += 1
                                if debug:
                                    print((" increase m to:%s" % m))

                        if 1 == 2:  # else:
                            if m > 0:
                                m += 1
                                if debug:
                                    print((" increase m to:%s" % m))
                            else:
                                if debug:
                                    print((" no increase for m at:%s" % m))

                        if m > 2:
                            if debug:
                                print((" a list element:%s" % item))
                            aList.append(item)
                        n += 1

                concat(aList, options.output)

            else:
                print(" only concat action supported at this time")

        else:
            print(" missing -a action parameter")

        # else:
        #   print(" invalid syntax: try sysImageTool.py -h")
        #   sys.exit(1)

    except Exception as e:
        print(" Error:")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
