import http.server
import time

try:
    import queue
except ImportError:
    import queue as queue

from .service import Service


#
# a service class that will start a http server at my_init time
# and wait for conversion requests.
#
# todo : call ingester.processSingleProduct()
#
class HttpDaemonServer(Service):
    SETTING_LISTENING_PORT = 'LISTENING_PORT'
    SETTING_LISTENING_HOST = 'LISTENING_HOST'

    debug = False

    #
    # class init
    # call super class
    #
    def __init__(self, name=None):
        Service.__init__(self, name)
        self.port = None
        self.hostname = None
        self.workqueue = None

    #
    # init
    # call super class
    #
    # param: p is usually the path of a property file
    #
    def init(self, p=None, ingester=None):
        Service.init(self, p, ingester)
        self.my_init()

    #
    # init done after the properties are loaded
    # do:
    # - check if DEBUG option set
    #
    def my_init(self, proxy=0, timeout=5):
        print(" HttpDaemonServer init:%s" % self.dumpProperty())

        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            print(" DEBUG setting:%s" % d)
            self.useDebugConfig(d)

        # LISTENING_PORT setting
        if self.getProperty(self.SETTING_LISTENING_PORT) is not None:
            print(" LISTENING_PORT setting:%s" % self.getProperty(self.SETTING_LISTENING_PORT))
            self.port = int(self.getProperty(self.SETTING_LISTENING_PORT))

        # LISTENING_HOST setting
        if self.getProperty(self.SETTING_LISTENING_HOST) is not None:
            print(" LISTENING_HOST setting:%s" % self.getProperty(self.SETTING_LISTENING_HOST))
            self.hostname = self.getProperty(self.SETTING_LISTENING_HOST)

    #
    # perform server start/stop
    #
    def processRequest(self, data):
        print(" HttpDaemonServer processRequest: data=%s" % data)

        if data is not None and data == 'start':
            self.startServer()
        elif data is not None and data == 'stop':
            self.stopServer()

    #
    # start the http server: listen forever on the port
    #
    def startServer(self):
        print(time.asctime(), "request server start - %s:%s" % (self.hostname, self.port))
        server_class = http.server.HTTPServer
        handler = MyHandler()
        httpd = server_class((self.hostname, self.port), handler)
        print(time.asctime(), "Server Starting - %s:%s" % (self.hostname, self.port))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        print(time.asctime(), "Server Stops - %s:%s" % (self.hostname, self.port))

    #
    # stop the http server
    #
    def stopServer(self):
        print(time.asctime(), "request server stop - %s:%s" % (self.hostname, self.port))


#
# the http request handler
#
class MyHandler(http.server.BaseHTTPRequestHandler):

    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()

    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        s.wfile.write("<html><head><title>Title goes here.</title></head>")
        s.wfile.write("<body><p>Converter Daemon Server</p>")
        # If someone went to "http://something.somewhere.net/foo/bar/",
        # then s.path equals "/foo/bar/".
        s.wfile.write("<p>request:%s</p>" % s.path)
        s.wfile.write("</body></html>")
