# -*- coding: cp1252 -*-
#
# this class implement access to an remote graphite events system
#
#
import json
import time

#
SERVICE_GRAPHITE_EVENT = "graphiteEvents"


#


#
#
#
class GraphiteEventsClient:
    debug = 0
    service = None
    url = None

    #
    # class init
    #
    def __init__(self, processInfo):
        self.clientName = SERVICE_GRAPHITE_EVENT
        if self.debug != 0:
            print(" init class GraphiteEventsClient")
        self.service = processInfo.ingester.getService(SERVICE_GRAPHITE_EVENT)
        if self.debug != 0:
            print("@@@@@@@@@@@@@@@@ GraphiteEventsClient: got service:%s" % self.service)

    #
    #
    #
    def processRequest(self, kvarg):
        if self.debug != 0:
            print(" @@@@@ GraphiteEventsClient processRequest; kvarg=%s" % kvarg)

        action = kvarg['action']
        if action == 'postEvent':
            # check if local time is older then updateTimeInterval
            payload = kvarg['payload']
            if self.debug != 0:
                print(" @@@@@ GraphiteEventsClient processRequest; postEvent; payload=%s" % payload)
            return self.sendJasonNotification(payload)
        else:
            raise Exception("unknown GraphiteEventsClient service action:%s" % action)

    #
    # payload is a {}
    #
    def sendNotification(self, what='default', tags=None, data='test data'):
        if tags is None:
            tags = []
        aDict = self.buildGraphiteEventMessage(what, tags, data)
        return self.sendJasonPayload(aDict)

    #
    # payload is a {}
    #
    def sendJasonPayload(self, payload):
        if self.debug != 0:
            print(" @@@@@ GraphiteEventsClient sendJasonPayload; payload=%s" % payload)
        res = self.service.postdata(data=json.dumps(payload))
        if self.debug != 0:
            print(" @@@@@ GraphiteEventsClient sendJasonPayload; res=%s" % res)
        if res is not None:
            if res.status_code != 200:
                print(" @@@@@ GraphiteEventsClient sendJasonPayload to graphite failled, status code=%s" % res.status_code)
        else:
            print(" @@@@@ GraphiteEventsClient sendJasonPayload to graphite failled")

        return res

    #
    # build graphite event message
    #

    def buildGraphiteEventMessage(self, what='default', tags=None, data='test data'):
        if tags is None:
            tags = []
        aDict = {}
        aDict['what'] = what
        aDict['tags'] = tags
        aDict['when'] = time.time()
        aDict['data'] = data
        return aDict
