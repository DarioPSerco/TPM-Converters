import re
import time

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

try:
    import queue
except ImportError:
    import queue as queue

from .service import Service


#
# a service class that will 'watch' an inbox folder structure
# using the whatchdog package, which work at inode level
#
# A queue will contains the path of file created in the inbox
# the queue item will be processed one at a time by the ingester.processSingleProduct()
class InboxDaemonServer(Service):
    SETTING_INBOX = 'INBOX'
    SETTING_OUTBOX = 'OUTBOX'
    SETTING_FAILUREBOX = 'FAILUREBOX'
    SETTING_EXCLUSIONS = 'EXCLUSIONS'
    debug = False

    def __init__(self, name=None):
        super(InboxDaemonServer, self).__init__(name)
        self.inbox = None
        self.outbox = None
        self.failurebox = None
        # exclusion setting will be | delimited, like: EXCUSIONS=^.*.part|^.*.txt
        self.exclusions = []
        self.watching = False
        self.workqueue = None
        #
        self.counter = 0

    #
    # init
    # call super class
    #
    # param: p is usually the path of a property file
    #
    def init(self, p=None, ingester=None):
        Service.init(self, p, ingester)
        self.my_init()
        self.observer = None

    #
    # init done after the properties are loaded
    # do:
    # - check if DEBUG option set
    #
    def my_init(self, proxy=0, timeout=5):
        if self.debug:
            print(" InboxDaemonServer init:%s" % self.dumpProperty())

        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            print(" DEBUG setting:%s" % d)
            self.useDebugConfig(d)

        # inbox
        if self.getProperty(self.SETTING_OUTBOX) is not None:
            print(" inbox setting:%s" % self.getProperty(self.SETTING_INBOX))
            self.inbox = self.getProperty(self.SETTING_INBOX)

        # outbox
        if self.getProperty(self.SETTING_INBOX) is not None:
            print(" outbox setting:%s" % self.getProperty(self.SETTING_OUTBOX))
            self.outbox = self.getProperty(self.SETTING_OUTBOX)

        # failurebox
        if self.getProperty(self.SETTING_FAILUREBOX) is not None:
            print(" failurebox setting:%s" % self.getProperty(self.SETTING_FAILUREBOX))
            self.failurebox = self.getProperty(self.SETTING_FAILUREBOX)

        # exclusions
        if self.getProperty(self.SETTING_EXCLUSIONS) is not None:
            print(" exclusions setting:%s" % self.getProperty(self.SETTING_EXCLUSIONS))
            tmp = self.getProperty(self.SETTING_EXCLUSIONS)
            if tmp is not None:
                self.exclusions = []
                n = 0
                for rule in tmp.split('|'):
                    print(" add exclusion rule[%s]:%s" % (n, rule))
                    aRe = re.compile(rule)
                    self.exclusions.append(aRe)
            else:
                print(" no exclusion rule.")
        else:
            print(" no exclusion setting.")

    #
    # Override
    #
    # def setIngester(self, i):
    #    Service.setIngester(self, i)
    #    print " @@@@@@@@@@@@@@@@@@@@@ set ingester:%s" % self.ingester

    #
    # set the filename pattern
    #
    # def setFilenamePattern(self, reName=None, reExt=None):
    #    pass

    #
    # perform server start/stop
    #
    def processRequest(self, data):
        print(" InboxDaemonServer processRequest: data=%s" % data)

        if data is not None and data == 'start':
            self.startServer()
        elif data is not None and data == 'stop':
            self.stopServer()

    #
    # start the server: create an inode observer
    #
    def startServer(self):
        print(" ", time.asctime(), " request server start...")
        self.watching = True
        self.observer = Observer()
        print(" ", time.asctime(), " got observer for path:%s" % self.inbox)
        handler = MyHandler()
        handler.my_init()
        # set handler needed vars
        handler.debug = self.debug
        handler.setExclusions(self.exclusions)
        #
        self.observer.schedule(handler, path=self.inbox, recursive=True)
        self.observer.start()
        print(" ", time.asctime(), " observer started")

        try:
            while self.watching:
                if self.debug:
                    print(" ", time.asctime(), " sleep...")
                time.sleep(5)
                size, aPath = handler.getFromQueue()
                if aPath != None:
                    print(" ", time.asctime(), " queue size:%s; got file to convert: %s" % (size, aPath))
                    self.convertFile(aPath)
        except KeyboardInterrupt:
            print(" ", time.asctime(), " KeyboardInterrupt")
            self.observer.stop()
            print(" ", time.asctime(), " KeyboardInterrupt; observer stopped")

        self.observer.join()
        print(" ", time.asctime(), " KeyboardInterrupt; observer.join() done")

    #
    # stop the http server
    #
    def stopServer(self):
        print(" ", time.asctime(), " request server stop...")
        self.watching = False

    #
    #
    #
    def convertFile(self, path):
        self.counter = self.counter + 1
        print(" ", time.asctime(), " will handle file[%s]: %s" % (self.counter, path))
        if self.ingester is not None:
            status, code, message = self.ingester.processSingleProduct(path, self.counter)
        else:
            print(" ", time.asctime(), " ingester is None !!")


#
# the event handler:
# - we are interrested in the creation and modification
#
class MyHandler(PatternMatchingEventHandler):
    # patterns = ["*.xml", "*.lxml", "*.zip"]

    debug = False
    exclusions = None

    #
    def my_init(self):
        #
        self.workqueue = queue.Queue()

    #
    def setExclusions(self, e):
        self.exclusions = e
        if self.debug:
            print(" set handler exclusions:%s" % self.exclusions)

    #
    def process(self, event):
        if self.debug:
            print(" handler process; exclusions:%s" % self.exclusions)
        """
        event.event_type 
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        # test for exclusion and event creation/modification
        if self.debug:
            print(event.src_path, event.event_type)
        if event.event_type == 'created':
            match = False
            for regex in self.exclusions:
                if regex.match(event.src_path):
                    match = True
                    break
            if not match:
                if self.debug:
                    print(" regex exclusions dont match")
                self.AddToQueue(event)
            else:
                if self.debug:
                    print(" regex exclusions match")
        elif event.event_type == 'modified_DISABLED':
            match = False
            for regex in self.exclusions:
                if regex.match(event.src_path):
                    match = True
                    break
            if not match:
                if self.debug:
                    print(" regex exclusions dont match")
                self.AddToQueue(event)
            else:
                if self.debug:
                    print(" regex exclusions match")
        else:
            if self.debug:
                print(" not interresting event type")

    # PatternMatchingEventHandler event
    def on_modified(self, event):
        if self.debug:
            print(" on_modified")
        self.process(event)

    # PatternMatchingEventHandler event
    def on_created(self, event):
        if self.debug:
            print(" on_created")
        self.process(event)

    # PatternMatchingEventHandler event
    def on_moved(self, event):
        if self.debug:
            print(" on_moved")
        self.process(event)

    # PatternMatchingEventHandler event
    def on_deleted(self, event):
        if self.debug:
            print(" on_deleted")
        self.process(event)

    #
    # add file to be converted in queue
    #
    def AddToQueue(self, event):
        self.workqueue.put(event.src_path)
        print(" event.src_path:%s added to queue" % event.src_path)

    #
    # get file path to be converted from queue
    #
    def getFromQueue(self):
        if not self.workqueue.empty():
            return self.workqueue.qsize(), self.workqueue.get(False)
        else:
            return 0, None
