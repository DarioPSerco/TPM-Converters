#
#
import time
from io import StringIO
from datetime import datetime

DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"

debug = 1


class ReportMaker:

    def __init__(self):
        print("ReportMaker init done")

    #
    #
    #
    def makeReport(self, ingester):
        out = StringIO()
        date = dateNow()
        print("At:%s" % date, file=out)
        print(ingester.summary(), file=out)
        print("\n####################################\n\nEoSip created:", file=out)
        # add list of product created
        for item in ingester.products_done:
            print(item, file=out)

        return out.getvalue()


#
# return the now date string
# dateNow('%Y-%m-%dT%H:%M:%SZ')=2015-10-15 14:08:45Z
#
def dateNow(pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(time.time())
    return d.strftime(pattern)
