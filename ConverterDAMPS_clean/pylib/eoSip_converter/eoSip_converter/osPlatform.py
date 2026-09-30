import os
import subprocess as sp
import sys
import traceback
from collections import namedtuple

debug = 0
_ntuple_diskusage = namedtuple('diskusage', 'total used free freePercent')


#
# test the disk usage on a certain path.
# return: float total, used, free +  percentFree as string
#  
#
def testDiskSpace(path):
    try:
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        percentFree = float(free) / float(total) * 100.0
        percentFreeS = "%.2f" % percentFree
        print(" testDiskSpace on path %s: total:%s, used:%s, free:%s, percentFree=%s" % (
        path, total, used, free, percentFree))
        return _ntuple_diskusage(total, used, free, percentFree)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" ERROR checking disk space:%s %s" % (exc_type, exc_obj))
        if debug != 0:
            traceback.print_exc(file=sys.stdout)

        #


# test if the os support disk usage (windows: no; linux: yes)
#
def canDoDiskUsage():
    try:
        st = os.statvfs('.')
        return True
    except:
        return False


#
# test if a object has a method
# UNTESTED
#
def testHasMethodName(anObject, aMethodName):
    if hasattr(anObject, aMethodName):
        meth = getattr(anObject, aMethodName, None)
        if callable(meth):
            return True
    return False


def test():
    COMMAND = '/home/gilles/shared/WEB_TOOLS/MISSIONS/Goce/GOCETool/GOCE_Orb.sh UTC=2009-11-01T05:18:27 UTC=2009-11-01T05:18:27 UTC=2009-11-01T06:03:18.644753 003661 +6630247.000 +6630247.000 +6630247.000 +0004.538735 -1381.434937 -7701.927734 40'
    args = COMMAND.split(' ')
    # retval, out = runCommand(args, useShell=True)
    retval, out = runCommand(COMMAND, useShell=True)
    if retval != 0:
        raise Exception("Error, exit code:%s; %s" % (retval, out))
    footprint = out.strip().split('\n')[-1]
    print("FOOTPRINT=%s" % footprint)

    print(canDoDiskUsage())
    testDiskSpace('.')


#
#
#
def runCommand(args, useShell=False):
    print("  will run command:%s" % args)

    if useShell:
        sub = sp.Popen(args, stdout=sp.PIPE, stdin=sp.PIPE, shell=True)
        print("   subprocess done")
    else:
        sub = sp.Popen(args, stdout=sp.PIPE, stdin=sp.PIPE)
        print("   subprocess done")

    stdout = sub.communicate()[0]
    print("   got stdout:%s" % stdout)

    res = sub.returncode
    print("   returncode:%s" % res)

    return res, stdout


if __name__ == '__main__':
    try:
        test()

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
