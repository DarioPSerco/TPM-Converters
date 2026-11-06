import sys
import urllib.request, urllib.error, urllib.parse

debug = True

#
# classe that can perform http GET and POST calls 
#
#
#

from .service import Service


class HttpCall(Service):
    SETTING_TIMEOUT = 'TIMEOUT'
    SETTING_PROXY = 'PROXY'
    DEFAULT_TIMEOUT = 15

    #
    # class init
    # call super class
    #
    def __init__(self, name=None):
        Service.__init__(self, name)

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
    # - handle proxy + timeout options
    #
    def my_init(self):  # , proxy=0, timeout=5):
        self.timeout = self.DEFAULT_TIMEOUT
        self.request = None
        self.url = None
        self.params = None
        self.postData = None
        self.encodedParams = None
        self.proxy = None
        self.opener = None

        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            self.useDebugConfig(d)

        # TIMEOUT setting
        if self.getProperty(self.SETTING_TIMEOUT) is not None:
            if self.debug != 0:
                print(" TIMEOUT setting:%s" % self.getProperty(self.SETTING_TIMEOUT))
            self.timeout = int(self.getProperty(self.SETTING_TIMEOUT))

        # PROXY setting
        if self.getProperty(self.SETTING_PROXY) == None:
            if self.debug != 0:
                print(" disabling proxy")
            proxy_handler = urllib.request.ProxyHandler({})
            self.opener = urllib.request.build_opener(proxy_handler)
            if self.debug != 0:
                print(" proxy disabled")
        else:
            if self.debug != 0:
                print(" enabling proxy")
            self.proxy = self.getProperty(self.SETTING_PROXY)
            print(" set proxy to:%s" % self.proxy)
            proxy = urllib.request.ProxyHandler({'http': self.proxy})
            self.opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(self.opener)

    #
    # url: is the url to call
    # data: is the data to send. can be a string or a dictionnary of names/values
    #
    def processRequest(self, url, data, usePost=True, decode=False):
        if self.debug != 0:
            print(" processRequest, timeout=%d" % self.timeout)
        if usePost:
            return self.retrieveUsingPost(url, data, None, decode)
        else:
            return self.retrieveUsingGet(url, data, None, decode)

    #
    # perform GET 
    # - u is URL path
    # - p are params: url encoded string or dictionnary(that will be url encoded)
    # - p is proxies
    #
    def retrieveUsingGet(self, u, p="", pr=None, decodeReply=True):
        self.url = u
        self.params = p
        self.proxy = pr
        if self.debug != 0:
            print(" will do GET: url=%s; params=%s;" % (self.url, self.params))
        # self.encodedParams = urllib.quote(self.params)
        if self.debug != 0:
            print(" encodedParams=%s" % self.encodedParams)

        # prepare the 'key=value&key2=value2&...'
        encodedData = ""
        # if the passed params str or dict?
        if isinstance(self.params, dict):
            if self.debug != 0:
                print(" httpService: params are in a dict")
            for key in list(self.params.keys()):
                if len(encodedData) > 0:
                    encodedData = "%s&" % encodedData
                encodedData = "%s%s=%s" % (encodedData, key, self.params[key])

                if len(encodedData) > 0:
                    self.request = urllib.request.Request(url="%s?%s" % (self.url, encodedData))
                    if self.debug != 0:
                        print(" get serviceRequest:%s?%s" % (self.url, encodedData))
                else:
                    self.request = urllib.request.Request(url=self.url)
                    if self.debug != 0:
                        print(" get serviceRequest:%s" % self.url)

        else:
            if self.debug != 0:
                print(" httpService: params are in a string")
            if self.params is not None:
                self.request = urllib.request.Request(url="%s?%s" % (self.url, self.params))
                if self.debug != 0:
                    print(" get serviceRequest:%s?%s" % (self.url, self.params))
            else:
                self.request = urllib.request.Request(url=self.url)
                if self.debug != 0:
                    print(" get serviceRequest:%s" % self.url)

        if self.opener == None:
            if self.debug != 0:
                print(" use default proxy")
            f = urllib.request.urlopen(self.request, timeout=self.timeout)
        else:
            if self.debug != 0:
                print(" dont use proxy")
            f = self.opener.open(self.request, timeout=self.timeout)
        if decodeReply:
            return f.read().decode()
        else:
            return f.read()

    #
    # perform POST
    # - u is URL path
    # - p are params: url encoded string or dictionnary
    # - pr is proxies
    #
    def retrieveUsingPost(self, u, d="", pr=None, decodeReply=True):
        self.url = u
        self.postData = d
        self.proxy = pr

        if self.debug != 0:
            print(" will do POST: url=%s; params=%s;" % (self.url, self.params))

        self.request = urllib.request.Request(url=self.url)

        if self.debug != 0:
            print(" post serviceRequest:%s" % self.url)

        self.request.data = bytes(self.postData, 'utf-8')

        if self.opener is None:
            if self.debug != 0:
                print(" use default proxy")
            f = urllib.request.urlopen(self.request, timeout=self.timeout)
        else:
            if self.debug != 0:
                print(" don't use proxy")
            f = self.opener.open(self.request, timeout=self.timeout)

        if decodeReply:
            return f.read().decode()
        else:
            return f.read()

    def info(self):
        result = "HttpCall; url:" + self.url


if __name__ == '__main__':
    a = "C:/Users/glavaux/Shared/LITE/spaceTmp/SP1_OPER_HRV1_X__1P_19881009T114531_19881009T114540_000029_0022_0322.MD_before.XML"
    b = "C:/Users/glavaux/LITE/OGC_Schemas/opt.xsd"
    data = "XML_PATH=%s&XSD_PATH=%s" % (a, b)
    dataBad = "XSD_PATH=%s" % b

    if 1 == 2:
        url = 'http://addf2.evo-pdgs.com/addf/search/L1B_Products'
        data = 'search=true&baseline=&product_type=ALD_U_N_1B&lower_left=&upper_right=&tc_from=2007-10-01&tc_to=2007-10-31&gt_from=&gt_to=&pt_from=&pt_to=&srf=html&eo-sip=eo-sip&eo-product=eo-product'

        call = HttpCall()
        call.init()

        # POST
        print("\n\n\n\nSHOULD BE OK:\n\n")
        print("returned:\n%s" % call.retrieveUsingPost(url, data))

        sys.exit(0)

    propertiePath = None
    if len(sys.argv) > 1:
        propertiePath = sys.argv[1]
        print(" will use property file at path:%s:" % propertiePath)
        # E:/Shared/soft/eoSip_converter/ressources/services/m2bs.props

    call = HttpCall(name='test http call')
    call.setDebug(True)
    call.init(propertiePath)

    # GET
    print("\n\n\nnSHOULD BE OK:")
    print("returned:%s" % call.retrieveUsingGet("http://localhost/DataStore/Doc", None))

    # GET
    print("\n\n\nnSHOULD BE OK:")
    print("returned:%s" % call.retrieveUsingGet("http://127.0.0.1:7000/validate", data))

    print("\n\n\n\nSHOULD BE BAD:")
    print("returned:%s" % call.retrieveUsingGet("http://127.0.0.1:7001/validate", dataBad))
    ##print "returned:%s" % call.retrieveUsingGet("http://127.0.0.1:7000/validate1", data)
    sys.exit(0)

    # POST
    print("\n\n\n\nSHOULD BE OK:")
    print("returned:%s" % call.retrieveUsingPost("http://127.0.0.1:7000/validate", data))

    print("\nSHOULD BE BAD:")
    print("returned:%s" % call.retrieveUsingPost("http://127.0.0.1:7000/validate", dataBad))
    print("returned:%s" % call.retrieveUsingGet("http://127.0.0.1:7000/validate1", data))
