from io import StringIO
from datetime import datetime

# This table lists information about ERS-1 cycles
#
# Each record lists the information for one repeat cycle:
# - Mission phase
# - Cycle number
# - First internal pass number
# - Last internal pass number
# - Start time in UTC YYMMDDHHMMSS.sss (with sss fraction of seconds)
# - Stop time in UTC YYMMDDHHMMSS.sss (with sss fraction of seconds)
# - Number of tracks available
# - Number of records for this cycle
#
# HEADER="ph cyc pass0 pass1 starttime        endtime          #trx  #recs"

# DATA="a 000 0530 1002 950429093900.086 950515215935.555  348  628364"

SHORT_DATE_PATTERN = "%Y%m%d%H%M%S"
DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_DATE_PATTERN_MSEC = "%Y-%m-%dT%H:%M:%S.000Z"

import re


#
#
#
def tsplit(string, delimiters):
    pattern = ' +'
    return re.split(pattern, string)


#
# convert from 950429093900.086 to 1995-04-29T09:39:00.086Z
#
def shortDateToDefaultDate(s):
    msec = "000"
    pos = s.find('.')
    if pos > 0:
        msec = s[pos + 1:]
        s = s[0:pos]

    d = datetime.strptime(s, SHORT_DATE_PATTERN)
    tmp = "%s" % d.strftime(DEFAULT_DATE_PATTERN_MSEC)
    return tmp.replace(".000Z", ".%sZ" % msec)


#
# convert from 1995-04-29T09:39:00.086Z to 19950429093900.086
#
def defaultDateToShortDate(s):
    msec = "000"
    pos = s.find('.')
    if pos > 0:
        msec = s[pos + 1:-1]
        s = s[0:pos]

    d = datetime.strptime("%sZ" % s, DEFAULT_DATE_PATTERN)
    tmp = "%s" % d.strftime(SHORT_DATE_PATTERN)
    return "%s.%s" % (tmp, msec)


#
# convert from 1995-04-29T09:39:00.086Z to datetime
#
def defaultDateTodatetime(s):
    msec = "000"
    pos = s.find('.')
    if pos > 0:
        msec = s[pos + 1:-1]
        s = s[0:pos]

    d = datetime.strptime("%sZ" % s, DEFAULT_DATE_PATTERN)
    return d


#
# convert from 19950429093900.086 to datetime
#
def shortDateTodatetime(s):
    # print "shortDateTodatetime:%s" % s
    msec = "000"
    pos = s.find('.')
    if pos > 0:
        msec = s[pos + 1:-1]
        s = s[0:pos]

    d = datetime.strptime("%s" % s, SHORT_DATE_PATTERN)
    return d


DEBUG = False


class SatPhasesCycles:

    #
    #
    #
    def __init__(self, label=None, header=None, data=None):
        self.debug = DEBUG
        #
        self.label = label
        self.header = header
        self.data = data

        # map phase: list of cycle
        self.phasesDict = {}
        print("loading data...")
        self.loadData()
        print("done")

    #
    # return the phase and cycle from a certain datetime of format: 19950429093900
    #
    def getPhaseAndCycleFromShortTime(self, dateTimeString):
        datetime = shortDateTodatetime("%s.000" % dateTimeString)
        if self.debug:
            print(" getPhaseAndCycleFromShortTime: datetime %s" % datetime)
        a = list(self.phasesDict.keys())
        a.sort()
        p = None
        c = None
        for key in a:
            start = self.phasesDict[key].start()
            stop = self.phasesDict[key].stop()
            d1 = shortDateTodatetime(start)
            d2 = shortDateTodatetime(stop)
            if datetime > d1 and datetime <= d2:
                p = key
                if self.debug:
                    print(" getPhaseAndCycleFromShortTime: is in phase %s" % key)
                phase = self.getPhase(key)
                cycles = phase.getCycleKeys()
                cycles.sort()
                for cycleNum in cycles:
                    cycle = phase.getCycle(cycleNum)
                    d1 = shortDateTodatetime(cycle.start)
                    d2 = shortDateTodatetime(cycle.stop)
                    if self.debug:
                        print(" getPhaseAndCycleFromShortTime: %s  %s" % (d1, d2))
                    if datetime > d1 and datetime <= d2:
                        c = cycleNum
                        break
                break
            # else:
            # print "is not in phase %s" % key
        return p, c

    #
    # return the phase and cycle from a certain datetime of format: 1995-04-29T09:39:00.086Z
    #
    def getPhaseAndCycleFromTime(self, dateTimeString):
        datetime = defaultDateTodatetime(dateTimeString)
        a = list(self.phasesDict.keys())
        a.sort()
        p = None
        c = None
        for key in a:
            start = self.phasesDict[key].start()
            stop = self.phasesDict[key].stop()
            d1 = shortDateTodatetime(start)
            d2 = shortDateTodatetime(stop)
            if datetime > d1 and datetime <= d2:
                p = key
                if self.debug:
                    print(" getPhaseAndCycleFromTime: is in phase %s" % key)
                phase = self.getPhase(key)
                cycles = phase.getCycleKeys()
                cycles.sort()
                for cycleNum in cycles:
                    cycle = phase.getCycle(cycleNum)
                    d1 = shortDateTodatetime(cycle.start)
                    d2 = shortDateTodatetime(cycle.stop)
                    if self.debug:
                        print(" getPhaseAndCycleFromTime: %s  %s" % (d1, d2))
                    if datetime > d1 and datetime <= d2:
                        c = cycleNum
                        break
                break
            # else:
            # print "is not in phase %s" % key
        return p, c

    #
    # load the satellite data from the package
    #
    def loadData(self):
        print("loadData()")
        n = 0
        for line in self.data.split(','):
            line = line.strip()
            if self.debug:
                print("\n\nline:'%s'" % line)
            toks = tsplit(line, ' ')
            if self.debug:
                print("  num of tokens:%d" % len(toks))
            if len(toks) == 8:
                phase = toks[0]
                cycle = toks[1]
                start = toks[4]
                stop = toks[5]
                # set year to 4 digits
                if start[0:1] == '9':
                    start = "19%s" % start
                else:
                    start = "20%s" % start
                if stop[0:1] == '9':
                    stop = "19%s" % stop
                else:
                    stop = "20%s" % stop
                aCycle = ERS_cycles(phase, cycle, start, stop)
                self.addCycle(aCycle)

            n = n + 1

        list(self.phasesDict.keys()).sort()
        print("readed %d lines" % n)

    #
    # add one phase
    #
    def addPhaseByName(self, phaseDigit):
        if self.debug:
            print(" SatPhasesCycles addPhaseByName(%s)" % phaseDigit)

        aPhase = self.getPhase(phaseDigit)
        if aPhase == None:
            aPhase = ERS_phases(phaseDigit)
        else:
            if self.debug:
                print(" SatPhasesCycles addPhase(%s): already exists")

    #
    # get one phase
    #
    def getPhase(self, phaseDigit):
        if self.debug:
            print(" SatPhasesCycles getPhase(%s)" % phaseDigit)

        aPhase = None
        if self.phaseExists(phaseDigit):
            return self.phasesDict[phaseDigit]
        else:
            return None

    #
    # test if phase exists
    #
    def phaseExists(self, phaseDigit):
        if self.debug:
            print(" SatPhasesCycles phaseExists(%s)" % phaseDigit)
        try:
            index = list(self.phasesDict.keys()).index(phaseDigit)
            if self.debug:
                print("  exists")
            return True
        except:
            if self.debug:
                print("  don't exists")
            return False

    #
    # add a cycle
    #
    def addCycle(self, cycle):
        if self.debug:
            print(" SatPhasesCycles addCycle(%s)" % cycle)
        aPhase = self.getPhase(cycle.phase)
        if aPhase == None:
            aPhase = ERS_phases(cycle.phase)
            aPhase.addCycle(cycle)
            self.phasesDict[cycle.phase] = aPhase
        else:
            aPhase.addCycle(cycle)

    #
    #
    #
    def info(self):
        out = StringIO()
        print(("%s SatPhasesCycles: num phases=%s" % (self.label, len(self.phasesDict))), file=out)
        a = list(self.phasesDict.keys())
        a.sort()
        for key in a:
            print(("  phase %s: num cycles:%s  start=%s  stop=%s" % (
            key, self.phasesDict[key].numCycles(), self.phasesDict[key].start(), self.phasesDict[key].stop())), file=out)
            phase = self.getPhase(key)
            a = phase.getCycleKeys()
            a.sort()
            for cycleNum in a:
                cycle = phase.getCycle(cycleNum)
                print(("    cycle %s: %s[%s]  %s[%s]" % (
                cycleNum, cycle.start, shortDateToDefaultDate(cycle.start), cycle.stop,
                shortDateToDefaultDate(cycle.stop))), file=out)
                print(("                [%s]    [%s]" % (
                defaultDateToShortDate(shortDateToDefaultDate(cycle.start)),
                defaultDateToShortDate(shortDateToDefaultDate(cycle.stop)))), file=out)
        return out.getvalue()


class ERS_phases:

    #
    #
    #
    def __init__(self, phaseDigit):
        self.debug = DEBUG
        self.phaseDigit = phaseDigit
        self.cycles = {}
        self.minStart = None
        self.maxStop = None
        self.duration = None
        if self.debug:
            print("create ERS_phases: %s" % self.info())

    def addCycle(self, cycle):
        if self.debug:
            print(" ERS_phases addCycle(%s)" % cycle)
        self.cycles[cycle.num] = cycle
        if self.minStart == None:
            self.minStart = cycle.start
        elif cycle.start < self.minStart:
            self.minStart = cycle.start

        if self.maxStop == None:
            self.maxStop = cycle.stop
        elif cycle.stop > self.maxStop:
            self.maxStop = cycle.stop

    def getDuration(self):
        return self.duration

    def setDuration(self, d):
        self.duration = d

    def getCycleKeys(self):
        return list(self.cycles.keys())

    def getCycle(self, cycleNum):
        return self.cycles[cycleNum]

    def numCycles(self):
        return len(self.cycles)

    def start(self):
        return self.minStart

    def stop(self):
        return self.maxStop

    def info(self):
        return "ERS_phases: phase=%s; num cycles:%s; start=%s  stop=%s" % (
        self.phaseDigit, len(self.cycles), self.minStart, self.maxStop)


class ERS_cycles:

    #
    #
    #
    def __init__(self, phase, num, start, stop):
        self.debug = DEBUG
        self.phase = phase
        self.num = num
        self.start = start
        self.stop = stop
        if self.debug:
            print("create ERS_cycles: %s" % self.info())

    def info(self):
        return "ERS_cycles: phase=%s num=%s start=%s stop=%s" % (self.phase, self.num, self.start, self.stop)


if __name__ == '__main__':
    print("ERS  cycles")
    ers = SatPhasesCycles("ERS1")

    print("\n\ndump: %s" % ers.info())
