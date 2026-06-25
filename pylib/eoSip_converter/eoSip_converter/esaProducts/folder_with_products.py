# -*- coding: cp1252 -*-
#
# this class represent a folder containing several Eo products
# based on the directory product
# 
#
#
#
import logging
import sys
import traceback

from .product_directory import Product_Directory


class Folder_With_Products(Product_Directory):

    #
    #
    #
    def __init__(self, path, isAFolder=True):
        Product_Directory.__init__(self, path)
        print(" init class Folder_With_Products")

    #
    #
    #
    def getMetadataInfo(self):
        return None


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        p = Folder_With_Products("C:/Users/glavaux/Shared/LITE/testData/Reaper/SGDR")
        p.addFile(
            'C:/Users/glavaux/Shared/LITE/testData/Reaper/GDR/E1_REAP_ERS_ALT_2__19910803T224655_19910804T002529_RP01.NC')
        p.addFile(
            'C:/Users/glavaux/Shared/LITE/testData/Reaper/GDR/E2_TEST_ERS_ALT_2__20010212T060425_20010212T080124_COM5.NC')

        print("product full size:%s" % p.getSize())
        met = p.getMetadataInfo()
        print("metadata:%s" % met)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
