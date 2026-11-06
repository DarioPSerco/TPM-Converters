#
# This class use multiprocessing to convert several products at once
#
# Serco 10/2015
# Lavaux Gilles 
#
#
#
#
#
import multiprocessing
import os
import random
import sys
import time
import traceback

import multiprocessing.managers

from . import errors
from . import infoKeeper


#
#
class MyManager(multiprocessing.managers.BaseManager):
    """
    Need a proxy class to an infoKeeper, because if not it will be empty
    when readed at the end from within the ingester
    """
    pass


def Manager():
    """The manager"""
    m = MyManager()
    m.start()
    return m


class InfoKeeperProxy(object):
    """The Infokeeper"""

    def __init__(self):
        pass
        self.keeper = infoKeeper.InfoKeeper()

    def addInfo(self, key, value):
        self.keeper.addInfo(key, value)

    def getKeyValues(self, key):
        return self.keeper.getKeyValues(key)

    def getKeys(self):
        return self.keeper.getKeys()

    def has_key(self, key):
        return key in self.keeper

    def toString(self):
        return self.keeper.toString()


def updateAppInfoKeeper(proxy, thread_id, key, value):
    """The update method"""
    proxy.addInfo(key, value)


# register into manager
MyManager.register('infoProxy', InfoKeeperProxy)

debug = 0
strict = True


class MultiProcessor(object):
    def __init__(self):
        self.cpuCount = multiprocessing.cpu_count()
        self.function = None
        self.exitCode = 0
        self.manager = None
        self.debug = debug
        self.strict = strict
        print(" MultiProcessor init; number of cpu:%s" % self.cpuCount)

    def setDebug(self, d):
        self.debug = d
        print(" MultiProcessor set DEBUG to:%s" % self.debug)

    def getDebug(self):
        return self.debug

    def setStrict(self, s):
        self.strict = s
        print(" MultiProcessor set strict to:%s" % self.strict)

    def getStrict(self):
        return self.strict

    def setCpuCount(self, n):
        self.cpuCount = n
        print(" MultiProcessor set process count to:%s" % self.cpuCount)

    def getCpuCount(self):
        return self.cpuCount

    #
    def getInfoProxy(self):
        """
        Get a infokeeper proxy. Will be also used from within the
        ingester
        """
        self.manager = Manager()
        return self.manager.infoProxy()

    def start(self, items, aFunction=None):
        """Start the processor, use multiple process. Will use the processSingleProduct function

        NOTE:
        - the kill pill + direct join scenarion is not working well for big queues. Probably because a deadlock suceed arround
          the done queue extremities(process produce and fiil, this part read and join).
        - So I tested several thing and do now:
          - create n process, add n kill pill (used in the worker process)
          - loop until all items are done using counter (proxied)
          - read from output queue untill empty
          - join all process
          - strict flag is used to os._exit(-10) if some number don't match, to avoid having the join wait forever.
        TODO: kill each process instead??
        """
        self.function = aFunction
        if self.debug != 0:
            print(" MultiProcessor start, num items:%s; processed by function:%s" % (len(items), aFunction))

        # m2bs test
        # self.cpuCount=6

        # get the infoKeeper proxy
        infProxy = self.getInfoProxy()

        # set queues with size, add small extra
        extra = self.cpuCount
        self.inputQueue = multiprocessing.Queue(len(items) + self.cpuCount + extra)
        self.outputQueue = multiprocessing.Queue(len(items) + self.cpuCount + extra)

        if self.debug != 0:
            print("input queue:%s; size:%s; dir:%s" % (self.inputQueue, self.inputQueue.qsize(), dir(self.inputQueue)))

        # feed items in inputQueue
        numToBeDone = len(items)
        for item in items:
            self.inputQueue.put(item)

        # start n processes
        self.processes = []
        counter = Counter(start=-1)
        counter2 = Counter(start=0)
        for w in range(self.cpuCount):
            p = multiprocessing.Process(target=self.worker,
                                        args=(self.inputQueue, self.outputQueue, counter, infProxy, w, counter2))
            p.start()
            self.processes.append(p)
        # add kill pill, not need now that check is done based on done counter. TODO: suppress?
        for w in range(self.cpuCount):
            self.inputQueue.put('STOP')

        # test if all process completed using done counter
        loop = True
        # get results available in the output queue
        res = []
        k = 0
        while loop:
            print("@@@@@@ multiprocessor: test num done:%s; qsize:%s" % (counter2.getValue(), self.outputQueue.qsize()))
            if numToBeDone == counter2.getValue():
                break
            else:
                # get results
                if not self.outputQueue.empty():
                    self.getAvailableresults(k, res)
                    k += 1
                    time.sleep(0.5)
                else:
                    time.sleep(5)
        print("@@@@@@@ multiprocessor: all item done")  # ; dir:%s" % dir(multiprocessing.Process)

        # get remaining results
        n = 0
        while not self.outputQueue.empty():
            self.getAvailableresults(k, res)
            k += 1
            if 1 == 2:  # disabled
                try:
                    status = self.outputQueue.get()
                    if self.debug != 0:
                        print("@@@ multiprocessor: status[%s]:%s" % (n, status))
                    # if n % 100==0:
                    #    print "@@@ collected %s result" % n
                    res.append(status)
                    n += 1
                except:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    print(" self.outputQueue problem is:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
                    self.forceShutdown(infProxy)

        print("@@@ collected all results")
        # if self.DEBUG!=0:
        print("@@@  multiprocessor: res size:%s" % len(res))

        # test result length == num to be done
        if self.strict and len(res) != numToBeDone:
            # raise Exception("multiprocessor: less result:%s that to be done:%s" % (len(res), numToBeDone))
            print("multiprocessor: less result:%s that to be done:%s" % (len(res), numToBeDone))
            # os._exit(-10)
            self.forceShutdown(infProxy)

        # wail a little bit
        time.sleep(10)

        # for status in iter(self.outputQueue.get, 'STOP'):
        #    print "@@@@@ status[%s]:%s" % (n, status)
        #    res.append(status)

        if 1 == 2:  # disabled code
            self.outputQueue.put('STOP')
            res = []
            for status in iter(self.outputQueue.get, 'STOP'):
                # print status
                res.append(status)
            print("@@@@@@  res size:%s" % len(res))

        # join
        if self.debug != 0:
            print("@@@@@@ multiprocessor: will join")
        n = 0
        for p in self.processes:
            try:
                print("@@@@@@@@@@ multiprocessor: try to join process[%d]:%s" % (n, p))
                p.join()
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("@@@@@@@@@@\n@@@@@@@@@@\n@@@@@@@@@@\n multiprocessor: join problem is:%s  %s\n%s\n" % (
                    exc_type, exc_obj, traceback.format_exc()))
                if self.strict:
                    # raise Exception("multiprocessor: join problem:%s  %s\n%s\n" %  (exc_type, exc_obj, traceback.format_exc()))
                    print("multiprocessor: join problem:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
                    # os._exit(-10)
                    self.forceShutdown(infProxy)
            n += 1
        print("@@@@@@@@@@ multiprocessor: all process joined")

        if 1 == 2:  # disabled code
            self.outputQueue.put('STOP')
            res = []
            for status in iter(self.outputQueue.get, 'STOP'):
                print(status)
                res.append(status)
            print("res size:%s" % len(res))

        #
        # if self.DEBUG!=0:
        print("multiprocessor: keeped info:\n%s" % infProxy.toString())

        print("multiprocessor: completed well.")

        return res, infProxy

    #
    # get the currently available result from output queue
    #
    def getAvailableresults(self, k, res):
        n = 0
        while not self.outputQueue.empty():
            try:
                status = self.outputQueue.get()
                # use status, if not don't get all result in res, strange
                # if self.DEBUG!=0:
                print("@@@ multiprocessor: getAvailableresults[%s:%s]:%s" % (k, n, status))
                res.append(status)
                n += 1
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" multiprocessor: getAvailableresults problem is:%s  %s\n%s\n" % (
                    exc_type, exc_obj, traceback.format_exc()))
                raise e

    #
    # TODO
    #
    def getExitCode(self):
        return self.exitCode

    def forceShutdown(self, infProxy):
        print(" multiprocessor: forceShutdown...")
        self.terminateChildrens(infProxy)
        print(" multiprocessor: forceShutdown done")
        sys.exit(-10)

    def terminateChildrens(self, infProxy):
        """Terminate children pid"""
        print(" multiprocessor: terminateChildrens...")
        for item in infProxy.getKeyValues("child-pid"):
            print("  terminateChildrens: will terminate process:%s" % item)
        print(" multiprocessor: terminateChildrens done")

    #
    def worker(self, work_queue, done_queue, aCounter, infProxy, procNum, aCounter2):
        """The worker: process one item from the work_queue, fill the
        done_queue with result

        aCounter: counter for ?
        infProxy: infoKepper proxy class
        procNum: process number
        aCounter2: contains number of request done-ok by worker

        TODO: supress one of the counters??
        """
        try:
            # print "type counter:%s" % type(aCounter)
            pid = os.getpid()
            print("@@ %s @@ multiprocessing: pid=%s" % (procNum, pid))
            infProxy.addInfo("child-pid", "%s" % pid)
            for item in iter(work_queue.get, 'STOP'):
                try:
                    # get current item num 
                    n = aCounter.increment()
                    if self.debug != 0:
                        print("@@ %s @@ multiprocessing: will start job; n=%s; self:%s; dir self:%s" % (
                            procNum, n, self, dir(self)))
                    status, status_code, message = self.function(item, n)
                    if self.debug != 0:
                        print("@@ %s @@ multiprocessing: job done; n=%s; status=%s; status_code=%s" % (
                            procNum, n, status, status_code))
                    if status_code == errors.ERROR_SUCCESS:
                        done_queue.put("%s - %s on item[%s]:%s; status_code:%s" % (
                            multiprocessing.current_process().name, errors.ERROR_SUCCESS, n, item, status_code))
                    else:
                        done_queue.put("%s - %s on item[%s]:%s; status_code:%s" % (
                            multiprocessing.current_process().name, errors.ERROR_FAILURE, n, item, status_code))
                    if self.debug != 0:
                        print("@@ %s @@ multiprocessing: done_queue.put done n=%s" % (procNum, n))
                    # infProxy.addInfo("Done", item)
                    if self.debug != 0:
                        print("@@ %s @@ multiprocessing: infProxy.addInfo done n=%s" % (procNum, n))
                except Exception as e:
                    # infProxy.addInfo("Failure", item)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    print(" problem is:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
                    done_queue.put("%s - %s on item[%s]:%s; status_code:%s" % (
                        multiprocessing.current_process().name, errors.ERROR_FAILURE, aCounter.value(), item,
                        e.message))
                # get current item num bis
                doneNum = aCounter2.increment()
                if self.debug != 0:
                    print("@@ %s @@ multiprocessing: aCounter2 done=%s" % (procNum, doneNum))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" problem is:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # print " problem is:%s  %s\n%s\n" %  (exc_type, exc_obj, traceback.format_exc())
            # raise Exception("MultiProcessor error: %s %s" % (exc_type, exc_obj))
        print("@@ %s @@ multiprocessing: worker done" % procNum)
        # try:
        #    self.terminate()
        # except Exception, e:
        #    exc_type, exc_obj, exc_tb = sys.exc_info()
        #    print "self.terminate problem:%s  %s\n%s\n" %  (exc_type, exc_obj, traceback.format_exc())


#
#
class Counter(object):
    """Proxy class to integer counter"""

    def __init__(self, start=0):
        self.val = multiprocessing.Value('i', start)

    def increment(self, n=1):
        with self.val.get_lock():
            self.val.value += n
            return self.val.value

    def getValue(self):
        with self.val.get_lock():
            return self.val.value

    @property
    def value(self):
        return self.val.value


#
# test function for worker
# return like the real processSingleProduct function
#
def aFunction(items, n):
    # print " -> start aFunction; items=%s; n=%s" % (items, n)
    delay = random.random() * 2
    # time.sleep(delay)
    status = {}
    code = -1
    message = ' --> done, no message for %s:%s' % (n, items)
    print(message)
    return status, code, message


#
# for test:
#
if __name__ == '__main__':
    try:
        processor = MultiProcessor()
        processor.setCpuCount(24)
        # processor.DEBUG=1
        items = []  # '1','22','333','444','555','666']
        for i in range(200000):
            items.append('%s' % random.random())
        results, infoKeeper = processor.start(items, aFunction)
        print("HOHOHOHOHO")
        # aFunction(items=items, n=1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
