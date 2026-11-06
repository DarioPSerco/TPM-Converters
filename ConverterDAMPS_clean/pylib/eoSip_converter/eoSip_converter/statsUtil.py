# -*- coding: cp1252 -*-
#
# 
#
#
import time

from .esaProducts import formatUtils

debug = 0


class StatsUtil:
    startTime = None
    totalSize = None
    totalTime = None
    total = None
    numDone = 0
    endDate = "not computed"

    #
    #
    #
    def __init__(self):
        print(" init Stats class")
        self.startTime = None
        self.total = 0
        self.totalTime = 0
        self.totalSize = 0
        self.numDone = 0
        self.endDate = "not computed"

    #
    #
    #
    def start(self, total):
        self.startTime = time.time()
        self.total = total

    #
    #
    #
    def oneDone(self, processingDuration=None, size=None):
        if debug != 0:
            print(" stats: add product[%d], size=%s; duration=%s" % (self.numDone, size, processingDuration))
        self.numDone += 1
        if processingDuration is not None:
            self.totalTime = self.totalTime + processingDuration
        if size is not None:
            self.totalSize = self.totalSize + size
        try:
            self.calcEndDate()
        except:
            print("Error calculating end date")
            #

    #
    #
    def calcEndDate(self):
        if self.startTime is not None:
            avsize = self.totalSize / self.numDone
            avtime = self.totalTime / self.numDone
            if debug != 0:
                print(" stats: calcEndDate: startTime=%s; avsize=%s; avtime=%s; totalSize=%s; totalTime=%s" % (
                self.startTime, avsize, avtime, self.totalSize, self.totalTime))
                print(" stats: calcEndDate: avtime=%s; *=%s" % (avtime, (self.total - self.numDone)))
                print(" stats: calcEndDate: startTime to date:%s" % formatUtils.dateFromSec(self.startTime))
            finalTime = time.time() + (avtime * (self.total - self.numDone))
            self.endDate = formatUtils.dateFromSec(finalTime).replace("T", " ").replace("Z", "")
            if debug != 0:
                print(" stats: calcEndDate: will end at:%s" % self.endDate)
        else:
            print("stats: calcEndDate: can not calculate end time: no start time")

    #
    # get estimated convertion end time
    #
    def getEndDate(self):
        return self.endDate

    #
    # get current time
    #
    def getCurrentDate(self):
        return formatUtils.dateFromSec(time.time()).replace("T", " ").replace("Z", "")


if __name__ == '__main__':
    pass
