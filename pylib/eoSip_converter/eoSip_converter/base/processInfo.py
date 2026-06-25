#
"""Class used during the product processing hold
- the source and destination product
- the tmpWorkig folder
- the ingester used
"""
import logging
import sys
import time
import traceback
from datetime import datetime
from io import StringIO
from typing import Optional

from eoSip_converter.esaProducts.product_directory import Product_Directory
from eoSip_converter.esaProducts.product_EOSIP import Product_EOSIP

DEFAULT_DATE_PATTERN = "%Y-%m-%d %H:%M:%S"


def dateNow(pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(time.time())
    return d.strftime(pattern)


class processInfo:
    def __init__(self):
        self.test_dont_do_browse = False
        self.test_dont_extract = False
        self.test_dont_write = False

        self.num = -1

        self.create_kmz = None
        self.create_sys_items = None
        self.create_thumbnail = None
        self.destProduct: Optional[Product_EOSIP] = None
        self.eosipTmpFolder = None
        self.errorHandler = None
        self.ingester = None
        self.infoKeeper = None
        self.logger = None
        self.srcPath = None
        self.srcProduct: Optional[Product_Directory] = None
        self.test_just_extract_metadata = None
        self.verify_xml = None
        self.workFolder = None

        self.errorLogSIO = StringIO()
        self.prodLogSIO = StringIO()

    def setLogger(self, logger: logging.Logger):
        """Set the ingester logger"""
        self.logger = logger

    def setIngester(self, ingester):
        """Set the ingester"""
        self.ingester = ingester

    def addIngesterLog(self, mess, level="INFO"):
        """Add info in ingester log"""
        if self.logger is not None:
            if level == 'DEBUG':
                self.logger.debug(mess)
            elif level == 'INFO':
                self.logger.info(mess)
            elif level == 'WARNING':
                self.logger.warning(mess)
            elif level == 'ERROR':
                self.logger.error(mess)
            # added for joborder stdout reformatting:
            elif level == 'PROGRESS':
                self.logger.info("[PROGRESS] %s" % mess)
            elif level == 'PINFO':
                self.logger.info("[PINFO] %s" % mess)
            elif level == 'PERROR':
                self.logger.info("[PERROR] %s" % mess)
            else:
                print("ERROR: unknown log level:%s" % level)
        else:
            print("ERROR: NO LOGGER SET")

    def addInfo(self, n, v):
        """Add info in KEPT info dictionnary"""
        if self.infoKeeper is not None:
            self.infoKeeper.addInfo(n, v)
        else:
            raise Exception("no infoKeeper")

    def addLog(self, mess):
        """Add info in production log"""
        try:
            print("%s: %s" % (dateNow(), mess), file=self.prodLogSIO)
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("%s %s" % (exc_type, exc_obj), file=self.errorLogSIO)
            print(" processInfo.addLog error: %s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc()))

    def getProdLog(self):
        return self.prodLogSIO.getvalue()

    def getErrorLog(self):
        return self.errorLogSIO.getvalue()

    def toString(self):
        out = StringIO()
        print('\n workFolder:%s' % self.workFolder, file=out)
        print(' srcPath:%s' % self.srcPath, file=out)
        print(' num:%s' % self.num, file=out)
        if self.srcProduct is not None:
            print(' srcProduct:%s' % self.srcProduct.path, file=out)
        else:
            print(' srcProduct: None', file=out)
        if self.destProduct is not None:
            print(' destProduct:%s' % self.destProduct.path, file=out)
        else:
            print(' destProduct: None', file=out)
        print(' ingester:%s' % self.ingester, file=out)
        print(' eosipTmpFolder:%s' % self.eosipTmpFolder, file=out)

        print('  !! test_dont_extract:%s' % self.test_dont_extract, file=out)
        print('  !! test_dont_write:%s' % self.test_dont_write, file=out)
        print('  !! test_dont_do_browse:%s' % self.test_dont_do_browse, file=out)

        print('  !! create kmz:%s' % self.create_kmz, file=out)
        print('  !! create sys items:%s' % self.create_sys_items, file=out)

        print('\nError:%s' % self.errorLogSIO.getvalue(), file=out)
        print('\nLOG:\n%s' % self.prodLogSIO.getvalue(), file=out)
        return out.getvalue()
