#
# list of error, exit-code and error messages
# - map error message into defined error code and message
#


#
#
#
ERROR_SUCCESS = 'sucess'
ERROR_FAILURE = 'failure'
ERROR_NOT_DONE = 'not-done'
ERROR_LOW_DISK = 'low disk limit reached'
ERRORS_LIST_DICT = {ERROR_SUCCESS: 0, ERROR_FAILURE: 1, ERROR_NOT_DONE: 2, \
                    ERROR_LOW_DISK: 10, \
                    'metadata-extraction-error': 100, 'make-browse-error': 101, 'incorrect-xml': 102, \
                    'duplicated-output': 200, \
                    'unknown-error': 900}

ERROR_MAPPING = {'refuse to overwite existing product:': 200, \
                 'DISK low limit ': 10}

debug = 0


class Error:

    def __init__(self):
        self.ERROR_SUCCESS = ERROR_SUCCESS
        self.ERROR_FAILURE = ERROR_FAILURE
        self.ERROR_NOT_DONE = ERROR_NOT_DONE
        self.errors = []
        self.codeToError = {}
        self.errorToCode = {}
        self.debug = debug
        for item in ERRORS_LIST_DICT:
            self.errors.append(item)
            code = ERRORS_LIST_DICT[item]
            self.codeToError[code] = item
            self.errorToCode[item] = code
        if self.debug != 0:
            print(' Error class init done, known error number: %s' % len(list(self.codeToError.keys())))

    #
    #
    #
    def errorExists(self, e):
        self.errors.index(e)
        return e

    #
    # get exit code from error message
    #
    def getExitCodeFromError(self, e):
        return self.errorToCode[e]

    #
    # get error message from exit code
    #
    def getErrorFromExitCode(self, c):
        return self.codeToError[c]

    #
    # test that a int code correspond to an error message
    #
    def testCodeIsError(self, c, e):
        # res = c==self.getExitCodeFromError(e)
        # print "@@@@@@@@@@@@@@@ testCodeIsError:%s" % res
        return c == self.getExitCodeFromError(e)

    #
    # receive a sys.exc_info(), return exitCode + error message by looking for presence of message text part
    #
    def handleError(self, exec_info):
        # set defaults
        code = 1
        message = self.getErrorFromExitCode(code)
        #
        exc_type, exc_obj, exc_tb = exec_info
        if self.debug != 0:
            print("HANDLING ERROR: exc_type='%s';  exc_obj='%s'" % (exc_type, exc_obj))

        # has the error mapping
        n = 0
        exc_obj_string = "%s" % exc_obj
        for item in list(ERROR_MAPPING.keys()):
            if self.debug != 0:
                print("  HANDLING ERROR test:%s VS %s;" % (exc_obj_string, item))
            if exc_obj_string.find(item) >= 0:
                code = ERROR_MAPPING[item]
                message = self.getErrorFromExitCode(code)
                # code = self.getExitCodeFromError(item)
                if self.debug != 0:
                    print("  HANDLING ERROR match[%s]:%s; code=%s;" % (n, message, code))
                n = n + 1

        if n > 1:
            raise Exception("exception message match several error: %s" % n)

        return code, message
