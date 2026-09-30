"""Provide TLE services

Lavaux Gilles 2018/05


some methods are from LiveConverter, and unfortunately have to be
removed or rewritten
"""
import math
import os
import shutil
import ssl
import sys
import time
import traceback
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta
from optparse import OptionParser
from time import mktime

from dateutil.relativedelta import relativedelta

from .service import Service
from ..sgp4.earth_gravity import wgs72
from ..sgp4.io import twoline2rv

durations_attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
human_readable = lambda delta: ['%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1]) for
                                attr in durations_attrs if getattr(delta, attr)]

# some constants
DEBUG = 1

# the local TLE file, for a satId=23456 it will be: 'tle_file_%s.dat' % satId  ==> tle_file_23456.dat
TLE_FILENAME = 'tle_file.dat'
# the delta TEL file retrieved from web
DELTA_TLE_FILE = 'delta_tle.dat'

# the date pattern used
DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"
SHORT_DATE_PATTERN = "%Y%m%d%H%M%S"

# gapSize in days
GAP_SIZE_IN_DAYS = 2


#
#
def sDateFromEpochSec(t, pattern=DEFAULT_DATE_PATTERN):
    """
    return a dateTimeString from a float sec
    (from epoch=1970-01-01 00:00:00)
    """
    d = datetime.fromtimestamp(t)
    return d.strftime(pattern)


def dateNow(pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(time.time())
    return d.strftime(pattern)


class TleService(Service):
    """Two Lines Elements service
    Provide:
    - update of local TLE file, for selected satellite id
    - propagate to a date
    """
    SETTING_dataFolder = 'dataFolder'
    SETTING_dataProviderUrl = 'dataProviderUrl'
    SETTING_satelliteId = 'satelliteId'
    SETTING_updateTimeInterval = 'updateTimeInterval'
    debug = DEBUG

    #
    # class init
    # call super class
    #
    def __init__(self, name=None):
        Service.__init__(self, name)
        # 2 path
        self.localTleFile = None
        self.deltaTleFile = None
        #
        self.dataProviderUrl = None
        self.satelliteId = None
        self.updateTimeInterval = 500
        self.tleMap = {}

    #
    # init
    # call super class
    #
    # param: p is usually the path of a property file
    #
    def init(self, p=None, ingester=None):
        super(TleService, self).init(p, ingester)
        self.my_init()

    #
    # init done after the properties are loaded
    # do:
    # - check if DEBUG option set
    # - get satelliteId used
    # - get dataProviderUrl
    # - get dataFolder where local TLE files will be keeped
    #
    def my_init(self):
        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            self.useDebugConfig(d)

        # more DEBUG: change from boolean to int > 1

        self.dataFolder = self.getProperty(self.SETTING_dataFolder)
        if self.debug != 0:
            print((" tle data folder is:%s" % self.dataFolder))
        if not os.path.exists(self.dataFolder):
            os.makedirs(self.dataFolder)
            print(("  tle data folder created:%s" % self.dataFolder))

        self.dataProviderUrl = self.getProperty(self.SETTING_dataProviderUrl)
        print(("  tle dataProviderUrl:%s" % self.dataProviderUrl))

        self.satelliteId = self.getProperty(self.SETTING_satelliteId)
        print(("  tle satelliteId:%s" % self.satelliteId))

        tmp = self.getProperty(self.SETTING_updateTimeInterval)
        try:
            self.updateTimeInterval = int(tmp)
        except:
            print(("ERROR getting updateTimeInterval from:%s" % tmp))

        # main and delta file name
        self.localTleFile = "%s/%s" % (self.dataFolder, self.getSatTleFileName())
        self.deltaTleFile = "%s/%s" % (self.dataFolder, DELTA_TLE_FILE)

        # load current sat Tle
        self.loadLocalTleFile()

    #
    # load  TLE elements from local file into a map, key is seconds since epoch
    #
    def loadLocalTleFile(self):
        self.tleMap = {}
        if not os.path.exists(self.localTleFile):
            print((" Warning: local Tle sat file %s doesn't exists" % self.localTleFile))
            return
        fd = open(self.localTleFile, 'r')
        lines = fd.read().split('\n')
        fd.close()

        # if self.DEBUG != 0:
        print(("\n\n readed %s lines from sat Tle file %s" % (len(lines), self.localTleFile)))
        self.tleList = {}
        alreadyPresent = 0
        for i in range(len(lines) // 2):
            try:
                tle = TleElement(lines[i * 2].strip(), lines[i * 2 + 1].strip())
                if not tle.getDate() in self.tleMap:
                    self.tleMap[tle.getDate()] = tle
                    # print(" @@ added to sat Tle[%s]:%s" % (i, tle.info()))
                else:
                    if self.debug > 1:
                        print((" @@ Tle[%s] record already in map:%s" % (i, tle.info())))
                    alreadyPresent += 1
            except:
                print((" tleService: error loading two line element at index: %s" % i))
        print((" tleService loadTleElements; loaded %s Tle\n\n" % len(self.tleMap)))
        if alreadyPresent > 0:
            raise Exception(" ERROR: tle record duplicated:%s" % alreadyPresent)

        # self.tleMap.keys().sort()
        firstKey = sorted(self.tleMap)[0]
        lastKey = sorted(self.tleMap)[-1]
        print(("  firstKey=%s; lastKey=%s" % (firstKey, lastKey)))
        firstSec = self.tleMap[firstKey].getDate()
        lastSec = self.tleMap[lastKey].getDate()
        print(("  first TLE record at secs:%s; human=%s; date=%s" % (
            firstSec, human_readable(relativedelta(seconds=firstSec)), sDateFromEpochSec(firstSec))))
        print(("  last TLE record at secs:%s; human=%s; date=%s" % (
            lastSec, human_readable(relativedelta(seconds=lastSec)), sDateFromEpochSec(lastSec))))

    #
    # fook for gaps in the TLE records, > n day
    #
    def lookForMissingEntry(self):
        print((" look for gap > %s day in TLE records..." % GAP_SIZE_IN_DAYS))
        oldTle = None
        oldKey = None
        n = 0
        problems = []
        for aKey in sorted(self.tleMap):
            if oldTle is not None:
                delta = self.tleMap[aKey].getDate() - oldTle.getDate()
                if delta > 86400 * GAP_SIZE_IN_DAYS:
                    problems.append("Interval > %s day at record[%s]; delta=%s; human=%s; date from %s to %s" % (
                        GAP_SIZE_IN_DAYS, n, delta, human_readable(relativedelta(seconds=delta)),
                        sDateFromEpochSec(oldTle.getDate()), sDateFromEpochSec(self.tleMap[aKey].getDate())))
                if self.debug > 1:
                    print((" delta for record[%s] is:%s; human:%s; date from %s to %s" % (
                        n, delta, human_readable(relativedelta(seconds=delta)), sDateFromEpochSec(oldTle.getDate()),
                        sDateFromEpochSec(self.tleMap[aKey].getDate()))))
                if delta < 0:
                    raise Exception("TEL file is corrupted, record %s has negative delta time" % n)
            oldKey = aKey
            oldTle = self.tleMap[aKey]
            n += 1

        if len(problems) > 0:
            print(("There are some gaps > %s day in TLE file:" % GAP_SIZE_IN_DAYS))
            n = 0
            for item in problems:
                print((" %s: %s" % (n, item)))
                n += 1
        else:
            print("There are no gap > 1 day in TLE file")

    #
    # process a request:
    # dict fields used:
    # - command: ['update', 'propagate']
    #
    def processRequest(self, aDict):
        if self.debug != 0:
            print((" processRequest; kvarg=%s" % aDict))

        if not 'command' in aDict:
            raise Exception("no command found for TLE service")

        action = aDict['command']
        #
        if action == 'update':
            # check if local time is older then updateTimeInterval
            if not os.path.exists(self.localTleFile):
                return self.updateLocalTleFileFromWeb()
            mtime = os.path.getmtime(self.localTleFile)
            age = time.time() - mtime
            print((" local TLE file age:%s" % age))
            if age > self.updateTimeInterval:
                return self.updateLocalTleFileFromWeb()
        #
        elif action == 'updateForever':
            # check if local time is older then updateTimeInterval, forever
            while True:
                if not os.path.exists(self.localTleFile):
                    self.updateLocalTleFileFromWeb()
                mtime = os.path.getmtime(self.localTleFile)
                age = time.time() - mtime
                print((" local TLE file age:%s" % age))
                if age > self.updateTimeInterval:
                    self.updateLocalTleFileFromWeb()
                print((" sleeping %s..." % (self.updateTimeInterval / 10)))
                time.sleep(self.updateTimeInterval / 10)
        #
        elif action == 'propagate':
            position, velocity = self.propagate(aDict)
            return position, velocity
        else:
            raise Exception("unknown TLE service action:%s" % action)

    #
    # propagate to a given date
    #
    def propagate(self, aDict):
        if self.debug != 0:
            print(" propagating")
        dateStr = aDict['date']
        if self.debug != 0:
            print((" propagating; use date:'%s'" % dateStr))
        d = datetime.strptime(dateStr, DEFAULT_DATE_PATTERN)
        if self.debug != 0:
            print(("  propagating; datetime:%s" % d))

        tle = self.getClosestTleElement(dateStr)
        if self.debug != 0:
            print(("  tle getdate:%s" % tle.getDate()))

        satellite = twoline2rv(tle.l1, tle.l2, wgs72)
        if self.debug != 0:
            # print "  propagating; satellite:%s" % dir(satellite)
            print(("  propagating; satellite num:%s; epoch:%s; julian date:%s" % (
                satellite.satnum, satellite.epoch, satellite.jdsatepoch)))
        position, velocity = satellite.propagate(d.year, d.month, d.day, d.hour, d.minute, d.second)
        if self.debug != 0:
            print(("  propagation error:%s" % satellite.error))  # nonzero on error
            print(("  propagation error message:%s" % satellite.error_message))
        print(("  propagation position:%s" % (position,)))
        print(("  propagation velocity:%s\n" % (velocity,)))
        return position, velocity

    #
    # update local file from web
    #
    def updateLocalTleFileFromWeb(self):
        print((" updating local TLE main file:%s from URL:%s. Delta Tle file is:%s" % (
            self.localTleFile, self.dataProviderUrl, self.deltaTleFile)))
        # disable ssl certificate check
        ssl._create_default_https_context = ssl._create_unverified_context
        print("  ssl certificate check disabled")
        #
        urllib.request.urlretrieve(self.dataProviderUrl, self.deltaTleFile)
        l1, l2 = self.getLast2LinesForSat(self.satelliteId)
        if not l1.startswith('1') and l2.startswith('2'):
            raise Exception("L1 or L2 incorrect: don't start well: L1=%s; L2=%s" % (l1, l2))

        # main TLE exists or not
        if os.path.exists(self.localTleFile):
            # self.updateSatFile(l1, l2)
            aTle = TleElement(l1, l2)
            if not self.recordPresent(aTle):
                print((" tle record not present, add it:%s" % aTle.info()))
                aList = []
                aList.append(aTle)
                self.addTle(aList)
                return True
            else:
                print((" tle record already present:%s" % aTle.info()))
                return False
        else:
            print((" main TLE sat file %s don't exists, create it" % self.localTleFile))
            fd = open(self.localTleFile, 'w')
            fd.write(l1 + '\n')
            fd.write(l2 + '\n')
            fd.flush()
            fd.close()
            self.loadLocalTleFile()
            return True

    #
    # get closest TLE element from a given date
    #
    def getClosestTleElement(self, aDateString):
        if self.debug != 0:
            print((" getClosestTleElement from %s" % aDateString))
        dt = datetime.strptime(aDateString, DEFAULT_DATE_PATTERN)
        sec_since_epoch = mktime(dt.timetuple()) + dt.microsecond / 1000000.0
        delta = 999999999999
        closest = None
        n = 0
        decrease = True
        for item in sorted(self.tleMap):
            if decrease:
                if self.debug > 1:
                    print(("  getClosestTleElement; test item[%s] '%s', line 1=%s; secs:%s" % (
                        n, item, self.tleMap[item].l1, self.tleMap[item].info())))
                diff = float(float(item) - sec_since_epoch)
                if self.debug > 1:
                    print(("  getClosestTleElement; line[%s] diff=%s" % (item, diff)))
                if abs(diff) < delta:
                    closest = self.tleMap[item]
                    if self.debug > 1:
                        print(("  MATCH: getClosestTleElement; tle:%s; %s. ## %s ##" % (
                            closest.l1, closest.l2, closest.info())))
                    delta = abs(diff)
                if diff > 0:
                    decrease = False
                    if self.debug > 1:
                        print("  MATCH: diff increase, must stop!!")
                else:
                    if self.debug > 1:
                        print("  MATCH: diff decrease, must continue")
                n += 1
            else:
                break

        if closest is None:
            raise Exception("can not find closest Tle for date:%s\n" % aDateString)
        else:
            # mesg = human_readable(relativedelta(seconds=delta))
            print(("  getClosestTleElement; closest is %s" % (closest.info())))
        return closest

    #
    # get the last 2 lines for the satellite we want from the delta TLE file we downloaded from web
    #
    #
    def getLast2LinesForSat(self, satId):
        # for test: keep all match and ave them in file
        f = open(self.deltaTleFile, 'r')
        lines = f.readlines()
        firstLine = None
        secondLine = None
        match = False
        pattern = " %s " % satId
        n = 0
        for line in lines:
            if self.debug != 0:
                print((" @@@@###  tle line[%s]:%s" % (n, line)))
            if match:
                secondLine = line
                match = False
                break
            if pattern in line:
                firstLine = line
                match = True
            n += 1
        #
        return firstLine.strip(), secondLine.strip()

    #
    # check is a TLE record is present
    #
    def recordPresent(self, aTleElement):
        found = False
        for aKey in self.tleMap:
            if aTleElement.isEqual(self.tleMap[aKey]):
                found = True
                break
        if found:
            print((" recordPresent: TLE %s is present" % aTleElement.info()))
        else:
            print((" recordPresent: TLE %s is NOT present" % aTleElement.info()))
        return found

    #
    # update the main TLE file from a delta file
    #
    def updateFromFile(self, deltaFilePath):
        if not os.path.exists(deltaFilePath):
            raise Exception("delta TLE file not present:%s" % deltaFilePath)

        with open(deltaFilePath, 'r') as fd:
            lines = fd.read().split('\n')

        print((" updateFromFile; readed %s lines from delta sat TLE file %s" % (len(lines), deltaFilePath)))
        toBeAdded = []
        for i in range(len(lines) // 2):
            tle = TleElement(lines[i * 2].strip(), lines[i * 2 + 1].strip())
            if not self.recordPresent(tle):
                print((" updateFromFile: TLE record to be added:%s" % tle.info()))
                toBeAdded.append(tle)
            else:
                print((" updateFromFile: TLE record already present:%s" % tle.info()))
        print((" updateFromFile: %s TLE record to be added; out of %s in delta TEL file" % (
            len(toBeAdded), len(lines) / 2)))

        # add Tle
        self.addTle(toBeAdded)

    # update the main TLE file with TLE records, save file
    # it is expected that the records already present check is already done
    def addTle(self, tleRecords):
        # update map
        for aTle in tleRecords:
            self.tleMap[aTle.getDate()] = aTle
        print((" addTle; %s records added" % len(tleRecords)))

        # update file
        self.saveTleMap(self.localTleFile)

    # save the current TLE map into a file
    # make a backup
    def saveTleMap(self, aFilePath):
        if os.path.exists(self.localTleFile):  # do backup
            backupFile = '%s/TLE_backup_%s.dat' % (self.dataFolder, dateNow(SHORT_DATE_PATTERN))
            shutil.copy(self.localTleFile, backupFile)
            print((" saveTleMap backup done:%s" % backupFile))

        os.remove(self.localTleFile)
        fd = open(self.localTleFile, 'w')
        for tleKey in self.tleMap:
            fd.write(self.tleMap[tleKey].l1)
            fd.write('\n')
            fd.write(self.tleMap[tleKey].l2)
            fd.write('\n')
        fd.flush()
        fd.close()
        print((" saveTleMap into:%s" % self.localTleFile))

    # return the local TLE filename for sat used
    def getSatTleFileName(self):
        return 'tle_file_%s.dat' % self.satelliteId


# 2 line element, is like:
# 1 26958U 01049B   18151.41639270 -.00000594  00000-0 -45908-4 0  9992
# 2 26958  97.6143 112.3450 0071668 241.8387 117.5586 14.95232747903558
class TleElement:

    def __init__(self, l1=None, l2=None):
        if not l1.startswith('1'):
            raise Exception("L1 ligne wrong start:'%s'" % l1)
        if not l2.startswith('2'):
            raise Exception("L2 ligne wrong start:'%s'" % l2)
        self.l1 = l1
        self.l2 = l2
        self.debug = DEBUG

    def info(self):
        secs = self.getDate()
        # return "L1:'%s'; L2:'%s'\n secs:%s; date:%s; human:%s" % (secs, self.l1, self.l2, sDateFromEpochSec(secs), human_readable(relativedelta(seconds=secs)))
        return "L1:'%s'; L2:'%s'\n secs:%s; date:%s; human:%s" % (
            self.l1, self.l2, secs, sDateFromEpochSec(secs), human_readable(relativedelta(seconds=secs)))

    def isEqual(self, aTleElement):
        return aTleElement.l1 == self.l1 and aTleElement.l2 == self.l2

    # get date in millisec from first line:
    def getDate(self):
        if self.debug > 1:
            print((" getDate from L1:%s" % self.l1))
        toks = self.l1.split(" ")
        if self.debug > 1:
            print(("  tok 5=%s" % toks[5]))

        # dayInyear foes from 1 to 366
        dayInYear = int(toks[5][2:5]) - 1
        if self.debug > 1:
            print(("  dayInYear=%s" % dayInYear))
        y = int(toks[5][0:2])
        if self.debug > 1:
            print(("  y=%s" % y))
        year = 2000 + y

        # xxx is day fraction, test divider is ok
        # divider='100000000'
        xxx = float(toks[5][6:])
        # if len("%s" % int(xxx)) != len(divider)-1:
        #    raise Exception("TLE line 1 has strange day fraction length:'%s'. is %s and should be %s" % (int(xxx),len("%s" % int(xxx)),len(divider)-1))
        if self.debug > 1:
            print(("  xxx=%s" % xxx))
        fdayInYear = dayInYear + (xxx / 100000000)
        if self.debug > 1:
            print(("  float dayInYear=%s" % fdayInYear))
        d = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=fdayInYear)
        if self.debug > 1:
            print((" TLE element.getDate 0 :%s" % d))

        hour = (xxx / 100000000) * 24
        hfloor = math.floor(hour)
        if self.debug > 1:
            print(("  hfloor=%s" % hfloor))
        minutes = math.floor((hour - hfloor) * 60)
        seconds = math.floor((((hour - hfloor) * 60) - minutes) * 60)

        if self.debug > 1:
            print((" TLE element.getDate: year:%s; xxx:%s; daysInYear=%s; hour:%s; minutes:%s; second:%s" % (
                year, xxx, dayInYear, hfloor, minutes, seconds)))
        dt = datetime(year, 1, 1, 0, 0, 0) + timedelta(days=dayInYear, hours=hour)
        sec_since_epoch = mktime(dt.timetuple()) + dt.microsecond / 1000000.0
        if self.debug > 1:
            print((" TLE element.getDate 1:%s, msec=%s" % (dt, sec_since_epoch)))

        mesg = human_readable(relativedelta(seconds=sec_since_epoch))
        if self.debug > 1:
            print((" TLE element mesg:%s" % mesg))
        return sec_since_epoch


#
# run various test
#
def runTest(propPath):
    propertiePath = propPath
    # if len(sys.argv) > 1:
    #    propertiePath = sys.argv[1]
    #    print " will use property file at path:%s:" % propertiePath
    # else:
    #   # print(" please provide property path ")
    #    propertiePath = "/home/gilles/shared/CONVERTERS_REFERENCE/glpkg_converter/eoSip_converter/ressources/services/tleService.props"

    if not os.path.exists(propertiePath):
        raise Exception(" property file %s does not exists !" % propertiePath)
    aService = TleService(name='test tle')
    aService.init(propertiePath)
    aService.setDebug(True)

    if 1 == 2:  # update file
        aDict = {}
        aDict['command'] = 'update'
        aService.processRequest(aDict)

        os._exit(1)

    if 1 == 2:  # update file forever
        aDict = {}
        aDict['command'] = 'updateForever'
        aService.processRequest(aDict)

        os._exit(1)

    # test TLE record
    if 1 == 2:
        now = time.time()
        a = '1 26958U 01049B   13287.84185076  .00000593  00000-0  60719-4 0  4982'
        b = '2 26958  97.4487 296.2658 0078895 142.4163 218.2623 14.91782059651267'
        tleElem = TleElement(a, b)
        tleElem.debug = 1
        secSinceEpoc = tleElem.getDate()
        print(secSinceEpoc)
        print((" TLE record secSinceEpoc=%s; secSinceEpoc human readable=%s; so is old=%s; date=%s" %
               (secSinceEpoc, human_readable(relativedelta(seconds=secSinceEpoc)),
                human_readable(relativedelta(seconds=(now - secSinceEpoc))), sDateFromEpochSec(secSinceEpoc))))

        os._exit(1)

    if 1 == 2:
        # test get closest
        aService.getClosestTleElement('2016-05-01T12:21:00Z')

        # test get closest
        # aService.getClosestTleElement('2017-05-01T12:21:00Z')

        # aService.getClosestTleElement('2001-05-01T12:21:00Z')

        os._exit(1)

    if 1 == 1:
        # test propagate
        aDict = {}
        aDict['command'] = 'propagate'
        aDict['date'] = '2018-03-11T12:21:00Z'
        position, velocity = aService.processRequest(aDict)

        os._exit(1)


#
#
#
def syntax():
    print(
        " syntax: python theService.py -a action -p/--path tleFilePath --prop propertiFilePath\n actions=test, check, append, update, updateForever, updateFromFile")


if __name__ == '__main__':

    try:
        parser = OptionParser()
        parser.add_option("-a", "--action", dest="action",
                          help="action to do, can be: test, check, append, update, updateForever, updateFromFile")
        parser.add_option("-p", "--path", dest="tleFilePath", help="path of the TLE file to use")
        parser.add_option("-d", "--delta", dest="deltaTleFilePath", help="path of the TLE delta file to use")
        parser.add_option("--prop", dest="propPath", help="path of the service property file")
        # parser.add_option("--help", dest="aHelp", help="help")
        options, args = parser.parse_args(sys.argv)

        useAction = None
        tleFilePath = None
        tleUpdatePath = None
        propPath = None

        #
        # if options.aHelp is not None:
        #    syntax()

        if options.action is None:
            useAction = 'test'
            print(" no action provided, will run test method")
        else:
            useAction = options.action

        if options.tleFilePath is not None:
            tleFilePath = options.tleFilePath

        if options.deltaTleFilePath is not None:
            tleUpdatePath = options.deltaTleFilePath

        if options.propPath is not None:
            propPath = options.propPath

        if useAction == 'test':
            runTest(propPath)

        elif useAction == 'updateFromFile':
            if tleUpdatePath is None:
                raise Exception("updateFromFile require a deltaTleFilePath parameter")
            if tleFilePath is None and propPath is None:
                raise Exception("updateFromFile require a tleFilePath parameter; or a propPath parameter")
            if propPath:
                print(" will update TLE file from delta file using Service...")
                aService = TleService(name='test tle')
                aService.setDebug(True)
                aService.init(propPath)
                print(" updating TLE file; service loaded")

            aService.updateFromFile(tleUpdatePath)

        elif useAction == 'update':
            if propPath:
                print(" will update TLE file from web using Service...")
                aService = TleService(name='test tle')
                aService.setDebug(True)
                aService.init(propPath)
                print(" updating TLE file; service loaded")

            aService.updateLocalTleFileFromWeb()

        elif useAction == 'updateForever':
            if propPath:
                print(" will update TLE file from web using Service, FOREVER...")
                aService = TleService(name='test tle')
                aService.setDebug(True)
                aService.init(propPath)
                print(" updating TLE file; service loaded")

            aService.updateLocalTleFileFromWeb()

        elif useAction == 'check':
            if tleFilePath is None and propPath is None:
                raise Exception("check require a tleFilePath parameter; or a propPath parameter")
            if propPath:
                print(" will check TLE file using Service...")
                aService = TleService(name='test tle')
                aService.setDebug(True)
                aService.init(propPath)
                print(" checking TLE file; service loaded")
                aService.lookForMissingEntry()

        else:
            syntax()



    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
