import os

from eoSip_converter.esaProducts.namingConvention import *

if __name__ == '__main__':
    try:
        a = 'C:/Users/glavaux/Shared/LITE/testData/Aeolus/ADM/1B/AE_TEST_ALD_U_N_1B_20101002T000000059_000936000_017071_0001.DBL'
        b = 'C:/Users/glavaux/Shared/LITE/testData/Aeolus/ADM/1B/AE_TEST_ALD_U_N_1B_20101002T000000059_000936000_017071_0001.HDF'

        print(" a exists:%s" % os.path.exists(a))
        print(" b exists:%s" % os.path.exists(b))
        sys.exit(1)

        n = NamingConvention(NamingConvention.PATTERN_OGC)
        met = metadata.Metadata()
        met.setMetadataPair(metadata.METADATA_PLATFORM, "AL")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, "1")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_START_DATE, "20140302")
        met.setMetadataPair(metadata.METADATA_START_TIME, "01:02:03")
        met.setMetadataPair(metadata.METADATA_STOP_DATE, "20150302")
        met.setMetadataPair(metadata.METADATA_STOP_TIME, "21:02:03")
        met.setMetadataPair(metadata.METADATA_FILECLASS, "OPER")
        met.setMetadataPair(metadata.METADATA_ORBIT, "1000")
        met.setMetadataPair(metadata.METADATA_TRACK, "273")
        met.setMetadataPair(metadata.METADATA_FRAME, "34")
        met.setMetadataPair(metadata.METADATA_SIP_VERSION, "00001")
        print(n.buildProductName(met))
    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
