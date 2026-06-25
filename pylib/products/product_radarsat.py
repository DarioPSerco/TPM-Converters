"""Contains Product_Radarsat class represent a radarsat directory product

Changes:
 - 2020-09-07: use .prodReport if orbit not found in .xml file
"""
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from subprocess import call

from osgeo import gdal
from osgeo import osr

from . import browse_metadata
import eoSip_converter.imageUtil as imageUtil
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.base.processInfo import processInfo
from eoSip_converter.esaProducts import formatUtils
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory
from xml_nodes import rep_footprint


def getTifCorners(src):
    ulx, xres, xskew, uly, yskew, yres = src.GetGeoTransform()
    lrx = ulx + (src.RasterXSize * xres)
    lry = uly + (src.RasterYSize * yres)
    print((" ######################### tif corners:%s %s %s %s" % (ulx, uly, lrx, lry)))
    return ulx, uly, lrx, lry


def getCoordinates(tifPath):
    print(("######################### getCoordinates of:'%s'" % tifPath))
    src = gdal.Open(tifPath)
    # Setup the source projection - you can also import from epsg, proj4...
    source = osr.SpatialReference()
    proj = src.GetProjection()
    print(("######################### proj:%s" % proj))
    source.ImportFromWkt(proj)

    # The target projection
    target = osr.SpatialReference()
    target.ImportFromEPSG(4326)

    # Create the transform - this can be used repeatedly
    transform = osr.CoordinateTransformation(source, target)

    # Transform the point. You can also create an ogr geometry and use the more generic `point.Transform()`
    ulx, uly, lrx, lry = getTifCorners(src)
    print(("%s" % (transform.TransformPoint(ulx, uly),)))
    # transform.TransformPoint(lrx, lry)
    # print(" ######################### tif coords:%s %s %s %s" % (a, b, c, d))


def GetExtent(gt, cols, rows):
    """ Return list of corner coordinates from a geotransform

        @type gt:   C{tuple/list}
        @param gt: geotransform
        @type cols:   C{int}
        @param cols: number of columns in the dataset
        @type rows:   C{int}
        @param rows: number of rows in the dataset
        @rtype:    C{[float,...,float]}
        @return:   coordinates of each corner
    """
    ext = []
    xarr = [0, cols]
    yarr = [0, rows]

    for px in xarr:
        for py in yarr:
            x = gt[0] + (px * gt[1]) + (py * gt[2])
            y = gt[3] + (px * gt[4]) + (py * gt[5])
            ext.append([x, y])
            print(x, y)
        yarr.reverse()
    return ext


def ReprojectCoords(coords, src_srs, tgt_srs):
    """ Reproject a list of x,y coordinates.

        @type geom:     C{tuple/list}
        @param geom:    List of [[x,y],...[x,y]] coordinates
        @type src_srs:  C{osr.SpatialReference}
        @param src_srs: OSR SpatialReference object
        @type tgt_srs:  C{osr.SpatialReference}
        @param tgt_srs: OSR SpatialReference object
        @rtype:         C{tuple/list}
        @return:        List of transformed [[x,y],...[x,y]] coordinates
    """
    trans_coords = []
    transform = osr.CoordinateTransformation(src_srs, tgt_srs)
    for x, y in coords:
        print((" ## will transform:%s %s" % (x, y)))
        a = [x, y, 0]
        x, y, z = transform.TransformPoint(a)
        trans_coords.append([x, y])
    return trans_coords


def do(raster):
    ds = gdal.Open(raster)

    gt = ds.GetGeoTransform()
    print((" ############## gt:%s" % (gt,)))
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    ext = GetExtent(gt, cols, rows)
    print((" ############## ext:%s" % ext))

    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    print((" ############## src_srs:%s" % src_srs))
    tgt_srs = osr.SpatialReference()
    tgt_srs.ImportFromEPSG(4326)
    print((" ############## tgt_srs:%s" % tgt_srs))
    # tgt_srs = src_srs.CloneGeogCS()

    geo_ext = ReprojectCoords(ext, src_srs, tgt_srs)
    print((" ############## geo_ext:%s" % (geo_ext,)))


#
#
BOUNDING_BOX_TYPECODES = ['SAR_EF_SPG', 'SAR_EF_SSG', 'SAR_EH_SPG', 'SAR_EH_SSG', 'SAR_EL_SPG', 'SAR_EL_SSG',
                          'SAR_FQ_SPG', 'SAR_FQ_SSG', 'SAR_FW_SPG', 'SAR_FW_SSG', 'SAR_FX_SPG', 'SAR_FX_SSG',
                          'SAR_MF_SPG', 'SAR_MF_SSG', 'SAR_MW_SPG', 'SAR_MW_SSG', 'SAR_QF_SPG', 'SAR_QF_SSG',
                          'SAR_QS_SPG', 'SAR_QS_SSG', 'SAR_SL_SPG', 'SAR_SL_SSG', 'SAR_SQ_SPG', 'SAR_SQ_SSG',
                          'SAR_SX_SPG', 'SAR_SX_SSG', 'SAR_UF_SPG', 'SAR_UF_SSG', 'SAR_UW_SPG', 'SAR_UW_SSG',
                          'SAR_WX_SPG', 'SAR_WX_SSG']
REF_TYPECODES = ['SAR_EF_SGF', 'SAR_EF_SGX', 'SAR_EF_SLC', 'SAR_EF_SPG', 'SAR_EF_SSG', 'SAR_EH_SGF', 'SAR_EH_SGX',
                 'SAR_EH_SLC', 'SAR_EH_SPG', 'SAR_EH_SSG', 'SAR_EL_SGF', 'SAR_EL_SGX', 'SAR_EL_SLC', 'SAR_EL_SPG',
                 'SAR_EL_SSG', 'SAR_FQ_SGX', 'SAR_FQ_SLC', 'SAR_FQ_SPG', 'SAR_FQ_SSG', 'SAR_FW_SGF', 'SAR_FW_SGX',
                 'SAR_FW_SLC', 'SAR_FW_SPG', 'SAR_FW_SSG', 'SAR_FX_SGF', 'SAR_FX_SGX', 'SAR_FX_SLC', 'SAR_FX_SPG',
                 'SAR_FX_SSG', 'SAR_MF_SGF', 'SAR_MF_SGX', 'SAR_MF_SLC', 'SAR_MF_SPG', 'SAR_MF_SSG', 'SAR_MW_SGF',
                 'SAR_MW_SGX', 'SAR_MW_SLC', 'SAR_MW_SPG', 'SAR_MW_SSG', 'SAR_QF_SGX', 'SAR_QF_SLC', 'SAR_QF_SPG',
                 'SAR_QF_SSG', 'SAR_QS_SGX', 'SAR_QS_SLC', 'SAR_QS_SPG', 'SAR_QS_SSG', 'SAR_SL_SGF', 'SAR_SL_SGX',
                 'SAR_SL_SLC', 'SAR_SL_SPG', 'SAR_SL_SSG', 'SAR_SN_SCF', 'SAR_SN_SCN', 'SAR_SN_SCS', 'SAR_SQ_SGX',
                 'SAR_SQ_SLC', 'SAR_SQ_SPG', 'SAR_SQ_SSG', 'SAR_SW_SCF', 'SAR_SW_SCS', 'SAR_SW_SCW', 'SAR_SX_SGF',
                 'SAR_SX_SGX', 'SAR_SX_SLC', 'SAR_SX_SPG', 'SAR_SX_SSG', 'SAR_UF_SGF', 'SAR_UF_SGX', 'SAR_UF_SLC',
                 'SAR_UF_SPG', 'SAR_UF_SSG', 'SAR_UW_SGF', 'SAR_UW_SGX', 'SAR_UW_SLC', 'SAR_UW_SPG', 'SAR_UW_SSG',
                 'SAR_WX_SGF', 'SAR_WX_SGX', 'SAR_WX_SLC', 'SAR_WX_SPG', 'SAR_WX_SSG']

#
#
operationalMode = {
    'SX_': 'Standard',
    'WX_': 'Wide',
    'FX_': 'Fine',
    'FW_': 'WideFine',
    'MF_': 'Multi_lookFine',
    'MW_': 'WideMultilookFine',
    'EF_': 'ExtraFine',
    'UF_': 'UltraFine',
    'UW_': 'WideUltra-Fine',
    'EH_': 'ExtendedHigh',
    'EL_': 'ExtendedLow',
    'SQ_': 'StandardQP',
    'QS_': 'WideStandardQP',
    'FQ_': 'FineQP',
    'QF_': 'WideFineQP',
    'SN_': 'ScansarNarrow',
    'SW_': 'ScansarWide',
    'SL_': 'Spotlight'
}

beamModeMnemonic_to_mode = {  # 52-1238_rs2_product_description_v1.14.pdf page 25

    "S1": "Standard",
    "S2": "Standard",
    "S3": "Standard",
    "S4": "Standard",
    "S5": "Standard",
    "S6": "Standard",
    "S7": "Standard",
    "S8": "Standard",

    "W1": "Wide",
    "W2": "Wide",
    "W3": "Wide",

    "F0W1": "WideFine",
    "F0W2": "WideFine",
    "F0W3": "WideFine",

    "EL1": "ExtendedLow",

    "EH1": "ExtendedHigh",
    "EH2": "ExtendedHigh",
    "EH3": "ExtendedHigh",
    "EH4": "ExtendedHigh",
    "EH5": "ExtendedHigh",
    "EH6": "ExtendedHigh",

    "F23": "Fine",
    "F23F": "Fine",
    "F22N": "Fine",
    "F22": "Fine",
    "F22F": "Fine",
    "F21N": "Fine",
    "F21": "Fine",
    "F21F": "Fine",
    "F1N": "Fine",
    "F1": "Fine",
    "F1F": "Fine",
    "F2N": "Fine",
    "F2": "Fine",
    "F2F": "Fine",
    "F3N": "Fine",
    "F3": "Fine",
    "F3F": "Fine",
    "F4N": "Fine",
    "F4": "Fine",
    "F4F": "Fine",
    "F5N": "Fine",
    "F5": "Fine",
    "F5F": "Fine",
    "F6N": "Fine",
    "F6": "Fine",
    "F6F": "Fine",

    "MF23": "Multi_lookFine ",
    "MF23F": "Multi_lookFine ",
    "MF22N": "Multi_lookFine ",
    "MF22": "Multi_lookFine ",
    "MF22F": "Multi_lookFine ",
    "MF21N": "Multi_lookFine ",
    "MF21": "Multi_lookFine ",
    "MF21F": "Multi_lookFine ",
    "MF1N": "Multi_lookFine ",
    "MF1": "Multi_lookFine ",
    "MF1F": "Multi_lookFine ",
    "MF2N": "Multi_lookFine ",
    "MF2F": "Multi_lookFine ",
    "MF3N": "Multi_lookFine ",
    "MF3": "Multi_lookFine ",
    "MF3F": "Multi_lookFine ",
    "MF4N": "Multi_lookFine ",
    "MF4": "Multi_lookFine ",
    "MF4F": "Multi_lookFine ",
    "MF5N": "Multi_lookFine ",
    "MF5F": "Multi_lookFine ",
    "MF6N": "Multi_lookFine ",
    "MF6": "Multi_lookFine ",
    "MF6F": "Multi_lookFine ",
    "MF23W": "WideMultilookFine",
    "MF22W": "WideMultilookFine",
    "MF21W": "WideMultilookFine",
    "MF1W": "WideMultilookFine",
    "MF2W": "WideMultilookFine",
    "MF3W": "WideMultilookFine",
    "MF4W": "WideMultilookFine",
    "MF5W": "WideMultilookFine",
    "MF6W": "WideMultilookFine",

    "XF0W1": "ExtraFine",
    "XF0W2": "ExtraFine",
    "XF0W3": "ExtraFine",
    "XF0S7": "ExtraFine",

    "U70": "UltraFine",
    "U71": "UltraFine",
    "U72": "UltraFine",
    "U73": "UltraFine",
    "U74": "UltraFine",
    "U75": "UltraFine",
    "U76": "UltraFine",
    "U77": "UltraFine",
    "U78": "UltraFine",
    "U79": "UltraFine",
    "U1": "UltraFine",
    "U2": "UltraFine",
    "U3": "UltraFine",
    "U4": "UltraFine",
    "U5": "UltraFine",
    "U6": "UltraFine",
    "U7": "UltraFine",
    "U8": "UltraFine",
    "U9": "UltraFine",
    "U10": "UltraFine",
    "U11": "UltraFine",
    "U12": "UltraFine",
    "U13": "UltraFine",
    "U14": "UltraFine",
    "U15": "UltraFine",
    "U16": "UltraFine",
    "U17": "UltraFine",
    "U18": "UltraFine",
    "U19": "UltraFine",
    "U20": "UltraFine",
    "U21": "UltraFine",
    "U22": "UltraFine",
    "U23": "UltraFine",
    "U24": "UltraFine",
    "U25": "UltraFine",
    "U26": "UltraFine",
    "U27": "UltraFine",
    "U28": "UltraFine",
    "U29": "UltraFine",
    "U30": "UltraFine",
    "U31": "UltraFine",
    "U32": "UltraFine",
    "U33": "UltraFine",
    "U34": "UltraFine",
    "U35": "UltraFine",
    "U36": "UltraFine",

    "U1W2": "WideUltra-Fine",
    "U2W2": "WideUltra-Fine",
    "U3W2": "WideUltra-Fine",
    "U4W2": "WideUltra-Fine",
    "U5W2": "WideUltra-Fine",
    "U6W2": "WideUltra-Fine",
    "U7W2": "WideUltra-Fine",
    "U8W2": "WideUltra-Fine",
    "U9W2": "WideUltra-Fine",
    "U10W2": "WideUltra-Fine",
    "U11W2": "WideUltra-Fine",
    "U12W2": "WideUltra-Fine",
    "U13W2": "WideUltra-Fine",
    "U14W2": "WideUltra-Fine",
    "U15W2": "WideUltra-Fine",
    "U16W2": "WideUltra-Fine",
    "U17W2": "WideUltra-Fine",
    "U18W2": "WideUltra-Fine",
    "U19W2": "WideUltra-Fine",
    "U20W2": "WideUltra-Fine",
    "U21W2": "WideUltra-Fine",
    "U22W2": "WideUltra-Fine",
    "U23W2": "WideUltra-Fine",
    "U24W2": "WideUltra-Fine",
    "U25W2": "WideUltra-Fine",
    "U26W2": "WideUltra-Fine",
    "U27w2": "WideUltra-Fine",

    "SQ1": "StandardQP",
    "SQ2": "StandardQP",
    "SQ3": "StandardQP",
    "SQ4": "StandardQP",
    "SQ5": "StandardQP",
    "SQ6": "StandardQP",
    "SQ7": "StandardQP",
    "SQ8": "StandardQP",
    "SQ9": "StandardQP",
    "SQ10": "StandardQP",
    "SQ11": "StandardQP",
    "SQ12": "StandardQP",
    "SQ13": "StandardQP",
    "SQ14": "StandardQP",
    "SQ15": "StandardQP",
    "SQ16": "StandardQP",
    "SQ17": "StandardQP",
    "SQ18": "StandardQP",
    "SQ19": "StandardQP",
    "SQ20": "StandardQP",
    "SQ21": "StandardQP",
    "SQ22": "StandardQP",
    "SQ23": "StandardQP",
    "SQ24": "StandardQP",
    "SQ25": "StandardQP",
    "SQ26": "StandardQP",
    "SQ27": "StandardQP",
    "SQ28": "StandardQP",
    "SQ29": "StandardQP",
    "SQ30": "StandardQP",
    "SQ31": "StandardQP",

    "FQ1": "FineQP",
    "FQ2": "FineQP",
    "FQ3": "FineQP",
    "FQ4": "FineQP",
    "FQ5": "FineQP",
    "FQ6": "FineQP",
    "FQ7": "FineQP",
    "FQ8": "FineQP",
    "FQ9": "FineQP",
    "FQ10": "FineQP",
    "FQ11": "FineQP",
    "FQ12": "FineQP",
    "FQ13": "FineQP",
    "FQ14": "FineQP",
    "FQ15": "FineQP",
    "FQ16": "FineQP",
    "FQ17": "FineQP",
    "FQ18": "FineQP",
    "FQ19": "FineQP",
    "FQ20": "FineQP",
    "FQ21": "FineQP",
    "FQ22": "FineQP",
    "FQ23": "FineQP",
    "FQ24": "FineQP",
    "FQ25": "FineQP",
    "FQ26": "FineQP",
    "FQ27": "FineQP",
    "FQ28": "FineQP",
    "FQ29": "FineQP",
    "FQ30": "FineQP",
    "FQ31": "FineQP",

    "SQ1W": "WideStandardQP",
    "SQ2W": "WideStandardQP",
    "SQ3W": "WideStandardQP",
    "SQ4W": "WideStandardQP",
    "SQ5W": "WideStandardQP",
    "SQ6W": "WideStandardQP",
    "SQ7W": "WideStandardQP",
    "SQ8W": "WideStandardQP",
    "SQ9W": "WideStandardQP",
    "SQ10W": "WideStandardQP",
    "SQ11W": "WideStandardQP",
    "SQ12W": "WideStandardQP",
    "SQ13W": "WideStandardQP",
    "SQ14W": "WideStandardQP",
    "SQ15W": "WideStandardQP",
    "SQ16W": "WideStandardQP",
    "SQ17W": "WideStandardQP",
    "SQ18W": "WideStandardQP",
    "SQ19W": "WideStandardQP",
    "SQ20W": "WideStandardQP",
    "SQ21W": "WideStandardQP",

    "FQ1W": "WideFineQP",
    "FQ2W": "WideFineQP",
    "FQ3W": "WideFineQP",
    "FQ4W": "WideFineQP",
    "FQ5W": "WideFineQP",
    "FQ6W": "WideFineQP",
    "FQ7W": "WideFineQP",
    "FQ8W": "WideFineQP",
    "FQ9W": "WideFineQP",
    "FQ10W": "WideFineQP",
    "FQ11W": "WideFineQP",
    "FQ12W": "WideFineQP",
    "FQ13W": "WideFineQP",
    "FQ14W": "WideFineQP",
    "FQ15W": "WideFineQP",
    "FQ16W": "WideFineQP",
    "FQ17W": "WideFineQP",
    "FQ18W": "WideFineQP",
    "FQ19W": "WideFineQP",
    "FQ20W": "WideFineQP",
    "FQ21W": "WideFineQP",

    "SCNA": "ScansarNarrow",
    "SCNB": "ScansarNarrow",

    "SCWA": "ScansarWide",
    "SCWB": "ScansarWide",

    # "DVWF" : "ScanSAR Narrow",
    # "OSVN" : "ScanSAR Narrow",

    "SLA70": "Spotlight",
    "SLA71": "Spotlight",
    "SLA72": "Spotlight",
    "SLA73": "Spotlight",
    "SLA74": "Spotlight",
    "SLA75": "Spotlight",
    "SLA76": "Spotlight",
    "SLA77": "Spotlight",
    "SLA78": "Spotlight",
    "SLA79": "Spotlight",

    "SLA1": "Spotlight",
    "SLA2": "Spotlight",
    "SLA3": "Spotlight",
    "SLA4": "Spotlight",
    "SLA5": "Spotlight",
    "SLA6": "Spotlight",
    "SLA7": "Spotlight",
    "SLA8": "Spotlight",
    "SLA9": "Spotlight",
    "SLA10": "Spotlight",
    "SLA11": "Spotlight",
    "SLA12": "Spotlight",
    "SLA13": "Spotlight",
    "SLA14": "Spotlight",
    "SLA15": "Spotlight",
    "SLA16": "Spotlight",
    "SLA17": "Spotlight",
    "SLA18": "Spotlight",
    "SLA19": "Spotlight",
    "SLA20": "Spotlight",
    "SLA21": "Spotlight",
    "SLA22": "Spotlight",
    "SLA23": "Spotlight",
    "SLA24": "Spotlight",
    "SLA25": "Spotlight",
    "SLA26": "Spotlight",
    "SLA27": "Spotlight",
    "SLA28": "Spotlight",
    "SLA29": "Spotlight",
    "SLA30": "Spotlight",
    "SLA31": "Spotlight",
    "SLA32": "Spotlight",
    "SLA33": "Spotlight",
    "SLA34": "Spotlight",
    "SLA35": "Spotlight",
    "SLA36": "Spotlight"
}

mode_to_opMode = {
    "Standard": "SX_",
    "Wide": "WX_",
    "Fine": "FX_",
    "WideFine": "FW_",
    "Multi_lookFine ": "MF_",
    "WideMultilookFine": "MW_",
    "ExtraFine": "EF_",
    "UltraFine": "UF_",
    "WideUltra-Fine": "UW_",
    "ExtendedHigh": "EH_",
    "ExtendedLow": "EL_",
    "StandardQP": "QS_",
    "WideStandardQP": "SQ_",
    "FineQP": "FQ_",
    "WideFineQP": "QF_",
    "ScansarNarrow": "SN_",
    "ScansarWide": "SW_",
    "Spotlight": "SL_"
    # "MODEX": "MODEX",
    # "TOPS": "TOPS",
    # "Ocean Surveillance": "Ocean Surveillance",
    # "Detection of Vessels": "Detection of Vessels",
    # "WideFineQP": "FW_",
    # "Multi_lookFine ": "MF_",
}


class Product_Radarsat(Product_Directory):
    xmlMapping = {
        metadata.METADATA_PROCESSING_TIME: 'imageGenerationParameters/generalProcessingInformation/processingTime',
        metadata.METADATA_SOFTWARE_VERSION: 'imageGenerationParameters/generalProcessingInformation/softwareVersion',
        metadata.METADATA_PROCESSING_LEVEL: 'imageGenerationParameters/generalProcessingInformation/productType',
        metadata.METADATA_PROCESSING_CENTER: 'imageGenerationParameters/generalProcessingInformation/processingFacility',
        metadata.METADATA_START_DATE: 'imageGenerationParameters/sarProcessingInformation/zeroDopplerTimeFirstLine',
        metadata.METADATA_STOP_DATE: 'imageGenerationParameters/sarProcessingInformation/zeroDopplerTimeLastLine',
        metadata.METADATA_ORBIT_DIRECTION: 'sourceAttributes/orbitAndAttitude/orbitInformation/passDirection',
        metadata.METADATA_ORBIT: 'sourceAttributes/orbitAndAttitude/orbitInformation/orbitDataFile',
        metadata.METADATA_POLARISATION_CHANNELS: 'sourceAttributes/radarParameters/polarizations',
        metadata.METADATA_ANTENNA_LOOK_DIRECTION: 'sourceAttributes/radarParameters/antennaPointing',
        metadata.METADATA_ACQUISITION_TYPE: 'sourceAttributes/radarParameters/acquisitionType',
        metadata.METADATA_PRODUCT_TYPE: 'imageGenerationParameters/generalProcessingInformation/productType',
        # metadata.METADATA_START_DATE:'sourceAttributes/rawDataStartTime',
        'beamModeMnemonic': 'sourceAttributes/beamModeMnemonic',
    }

    METADATA_NAME = 'product.xml'
    PREVIEW_NAME = 'BrowseImage.tif'
    IMAGE_PREFIX = 'imagery_'
    IMAGE_SUFFIX = '.tif'
    PRODREPORT_SUFFIX = '.prodReport'

    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        self.metadata_path = None
        self.metContent_data = None
        self.preview_path = None
        self.preview_data = None
        self.first_image_path = None
        self.prodReport_path = None
        self.prodReport_data = None
        self.useBbox = True

        if self.debug != 0:
            print(" init class Product_Radarsat")

    def getSensorMode(self, processInfo):
        tmp = self.metadata.getMetadataValue('beamModeMnemonic')
        if self.debug != 0:
            print((" #### getSensorMode; beamModeMnemonic=%s; will check VS ref:%s" % (
            tmp, list(beamModeMnemonic_to_mode.keys()))))

        # new: plain value dict
        matchesDict = []
        for aKey in beamModeMnemonic_to_mode:
            if aKey == tmp:
                matchesDict.append(beamModeMnemonic_to_mode[aKey])

        self.resolvedBeamMesg = "resolving beamId:%s; matches are:%s " % (tmp, matchesDict)

        if len(matchesDict) != 1:
            raise Exception(
                "problem resolving beamId:%s; not one matches but %s; %s" % (tmp, len(matchesDict), matchesDict))

        if not matchesDict[0] in mode_to_opMode:
            raise Exception("missing mode_to_opMode mapping for:%s" % (matchesDict[0]))

        opMode = mode_to_opMode[matchesDict[0]]
        beam_ok = matchesDict[0]

        self.metadata.setMetadataPair('beamModeMnemonic_resolved', beam_ok)
        if self.debug != 0:
            print((" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  -> beamModeMnemonic_resolved:%s" % beam_ok))
            print((" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  -> sensor operational mode 3 digit:%s" % opMode))
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, opMode)

    def getFootprint(self, proc_info: processInfo):
        tmpBrowse = Path(proc_info.workFolder) / "tmp.tif"
        infoFile = Path(proc_info.workFolder) / "info.txt"
        commandFile = Path(proc_info.workFolder) / "command_browse.sh"
        commandOutputFile = commandFile.with_suffix(".stdout")

        gdal_commands = [
            [
                "gdalwarp", "-ts", "1000", "10000", "-t_srs", "EPSG:4326",
                str(Path(self.first_image_path)), str(Path(tmpBrowse))
            ],
            ["gdalinfo", str(tmpBrowse)]
        ]

        # Remove files if they already exist
        for file in (infoFile, commandFile, commandOutputFile, tmpBrowse):
            file.unlink(missing_ok=True)

        # Write GDAL commands to file as a record
        with open(commandFile, 'wt') as fd:
            fd.write('\n'.join([' '.join(c) for c in gdal_commands]))

        for command, output_file in zip(gdal_commands, (commandOutputFile, infoFile)):
            with open(output_file, "a") as output_fd:
                # Run the command and redirect both stdout and stderr to the output file
                result = subprocess.run(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
                stdout = result.stdout.decode()
                retval = result.returncode
                output_fd.write(stdout)

            if retval is not 0:
                msg = f"Error generating browse [exit code={retval}]: {stdout}"
                print(msg)
                raise Exception(msg)

            if self.debug:
                print(f"  external make browse exit code: {retval}")

        with open(infoFile, 'rt') as fd:
            data = fd.read()

        ul = ll = ur = lr = cc = None
        reg_exp = r"\(.*?\)"  # matches first parentheses group
        for line in data.split('\n'):
            line = line.strip()
            if len(line) > 0:  # are lon, lat
                if line.startswith("Upper Left"):
                    ul = re.sub(r'[\s()]', '', re.search(reg_exp, line).group())
                elif line.startswith("Lower Left"):
                    ll = re.sub(r'[\s()]', '', re.search(reg_exp, line).group())
                elif line.startswith("Upper Right"):
                    ur = re.sub(r'[\s()]', '', re.search(reg_exp, line).group())
                elif line.startswith("Lower Right"):
                    lr = re.sub(r'[\s()]', '', re.search(reg_exp, line).group())
                elif line.startswith("Center"):
                    cc = re.sub(r'[\s()]', '', re.search(reg_exp, line).group())

        print(("ul=%s; ur=%s; ll=%s; lr=%s; cc=%s" % (ul, ll, ur, lr, cc)))
        boundingBox = ' '.join(
            [_ for c in (ul, ll, lr, ur) for _ in c.split(',')[::-1]]
        )
        center = ' '.join(cc.split(',')[::-1])

        print(("\s ## boundingBox=%s; center:%s\n" % (boundingBox, center)))
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, boundingBox)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, center)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, cc.split(',')[1].strip())
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, cc.split(',')[0].strip())

    def afterProductDone(self):
        """Called at the end of the doOneProduct, before the index/shopcart creation"""
        pass

    def getMetadataInfo(self):
        """Read metadata file"""
        pass

    def makeBrowses(self, proc_info: processInfo):
        from eoSip_converter import STRETCH_APP

        if self.debug:
            print(" makeBrowses")

        if self.preview_path is None:
            raise Exception("no browse")

        n = 0
        anEosip = proc_info.destProduct

        browseName = proc_info.destProduct.getSipProductName()
        browseSrcPath = self.preview_path
        browseDestPath = Path(proc_info.workFolder) / f"{browseName}.BI.PNG"
        browseDestPathRaw = Path(proc_info.workFolder) / f"{browseName}.BI.PNG_raw"
        output_file = Path(proc_info.workFolder) / f"{STRETCH_APP.stem}.stdout"

        # Want non-transparent PNG (not JPG)
        # remove blank filling area from PNG using stretcherAppExe
        imageUtil.makeBrowse('PNG', browseSrcPath, browseDestPathRaw)
        command = [
            "java", "-Dlog4j.debug=true", "-Djava.awt.headless=true",
            "-cp", str(STRETCH_APP), "histogramStretcher.StretchApp",
            "-transparent", str(browseDestPathRaw), str(browseDestPath), "0xff000000"
        ]

        # Write executed command to file for records
        with open(Path(proc_info.workFolder) / "command_browse.sh", 'w') as fd:
            fd.write(' '.join(command))

        # Launch the main make_browse script and write its stdout to file
        with open(output_file, 'a') as output_fd:
            result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            stdout = result.stdout.decode()
            retval = result.returncode
            output_fd.write(stdout)

        if self.debug:
            print(f"  external make browse exit code: {retval}")

        if retval is not 0:
            msg = f"Error generating browse [exit code {retval}]: {stdout}"
            print(msg)
            raise Exception(msg)

        anEosip.addSourceBrowse(browseDestPath, [])
        proc_info.addLog("  browse image[%s] added: name=%s; path=%s" % (n, browseName, browseDestPath))

        # set AM time if needed
        proc_info.destProduct.setFileAMtime(browseDestPath)

        # create browse choice for browse metadata report
        bmet = anEosip.browse_metadata_dict[browseDestPath]
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

        reportBuilder = rep_footprint.rep_footprint()
        #
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
        browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                       "rep:browseReport/rep:browse/rep:footprint").strip()
        if self.debug != 0:
            print("browseChoiceBlock:%s" % browseChoiceBlock)
        bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

        # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
        # if specified in configuration
        tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
        if tmp is not None:
            bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

        # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
        if tmp is not None:
            bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

        proc_info.addLog("  browse image[%s] choice created:browseChoiceBlock=\n%s" % (n, browseChoiceBlock))

    # extract the product
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, folder))

        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" Will extract product to path:%s" % folder)

        # keep list of content
        self.contentList = []
        self.num_images = 0
        n = 0
        for root, dirs, files in os.walk(self.folder, topdown=False):
            for name in files:
                n += 1
                eoFile = "%s/%s" % (root, name)
                if self.debug != 0:
                    print(" ########################## product content[%d]:'%s' in:%s" % (n, name, eoFile))

                if name == self.PREVIEW_NAME:
                    self.preview_path = eoFile
                    with open(self.preview_path, 'rb') as fd:
                        self.preview_data = fd.read()

                    shutil.copyfile(self.preview_path, "%s/%s" % (folder, name))
                    if self.debug != 0:
                        print((" #################################### FOUND self.preview_path=%s" % self.preview_path))

                elif name == self.METADATA_NAME:
                    self.metadata_path = eoFile
                    fd = open(self.metadata_path, 'r')
                    self.metContent_data = fd.read()
                    fd.close()
                    shutil.copyfile(self.metadata_path, "%s/%s" % (folder, name))
                    if self.debug != 0:
                        print((" #################################### FOUND self.metadata_path=%s" % self.metadata_path))

                else:
                    base = os.path.basename(name)
                    if base.startswith(self.IMAGE_PREFIX) and base.endswith(self.IMAGE_SUFFIX):
                        if self.first_image_path is None:
                            self.first_image_path = eoFile
                            if self.debug != 0:
                                print((
                                            " #################################### FOUND self.first_image_path=%s" % self.first_image_path))
                        self.num_images += 1

                    elif name.endswith(self.PRODREPORT_SUFFIX):
                        self.prodReport_path = eoFile
                        fd = open(self.prodReport_path, 'r')
                        self.prodReport_data = fd.read()
                        fd.close()
                        if self.debug != 0:
                            print((
                                        " #################################### FOUND self.prodReport_path=%s" % self.prodReport_path))

                relPath = os.path.join(root, name)[len(self.folder) + 1:]
                print("   content[%s] workfolder relative path:%s" % (n, relPath))
                self.contentList.append(relPath)

        if self.debug != 0:
            print("   %s contains %s images" % (name, self.num_images))

        return

        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []
        n = 0
        d = 0
        self.num_previews = 0
        for name in z.namelist():
            n = n + 1
            if self.debug != 0:
                print("  zip content[%d]:%s" % (n, name))
            if name.endswith(self.PREVIEW_NAME):
                self.preview_path = "%s/%s" % (folder, name)
                if self.debug != 0:
                    print((" #################################### FOUND self.preview_path=%s" % self.preview_path))
            elif name.endswith(self.METADATA_NAME):
                self.metadata_path = "%s/%s" % (folder, name)
                if self.debug != 0:
                    print((" #################################### FOUND self.metadata_path=%s" % self.metadata_path))
            else:
                base = os.path.basename(name)
                if base.startswith(self.IMAGE_PREFIX) and base.endswith(self.IMAGE_SUFFIX):
                    if self.first_image_path is None:
                        self.first_image_path = "%s/%s" % (folder, name)
                        if self.debug != 0:
                            print((
                                        " #################################### FOUND self.first_image_path=%s" % self.first_image_path))
                    self.num_previews += 1

            if self.debug != 0:
                print("   %s extracted at path:%s" % (name, folder + '/' + name))
            if name.endswith('/'):
                d = d + 1
            self.contentList.append(name)

        if self.debug != 0:
            print("   %s contains %s images" % (name, self.num_previews))

        if dont_extract != True:
            z.extractall(folder)
        if self.metadata_path != None:
            fd = open(self.metadata_path, 'r')
            self.metContent_data = fd.read()
            fd.close()

        if self.preview_path != None:
            fd = open(self.preview_path, 'r')
            self.preview_data = fd.read()
            fd.close()

        self.EXTRACTED_PATH = folder
        if self.debug != 0:
            print(" ################### self.preview_path:%s" % self.preview_path)

        z.close()
        fh.close()

    def extractRadarsatFootprint(self, helper, direction):
        aNode = helper.getFirstNodeByPath(None, 'imageAttributes/geographicInformation/geolocationGrid', None)
        # print(" geolocationGrid node:%s" % aNode)
        numLines = 0
        numColumns = 0
        if aNode is not None:

            nodeList = []
            helper.getNodeByPath(aNode, 'imageTiePoint', None, nodeList)

            # """
            #         <imageTiePoint>
    		# 			<imageCoordinate>
    		# 				<line>0.00000000e+00</line>
    		# 				<pixel>0.00000000e+00</pixel>
    		# 			</imageCoordinate>
    		# 			<geodeticCoordinate>
    		# 				<latitude units="deg">3.888173047761543e+01</latitude>
    		# 				<longitude units="deg">1.560557539067346e+01</longitude>
    		# 				<height units="m">1.963720855712891e+02</height>
    		# 			</geodeticCoordinate>
    		# 		</imageTiePoint>
    		# """

            currentLineIndex = 0
            currentPixelIndex = 0
            lastPixel = -1
            imCoords = None
            geoCoords = None
            #
            lastImCoords = None
            possibleLastLLNode = None
            ULNode = None
            URNode = None
            #
            lastGeoCoords = None
            possibleLastLLGeoNode = None
            ULGeoNode = None
            URGeoNode = None

            # print(" doing line:%s" % currentLineIndex)
            for aNode in nodeList:
                # print(" a node:%s" % aNode)
                imCoords = helper.getFirstNodeByPath(aNode, '/imageCoordinate')
                geoCoords = helper.getFirstNodeByPath(aNode, '/geodeticCoordinate')
                # print("  imCoords:%s" % imCoords)
                lineNode = helper.getFirstNodeByPath(imCoords, 'line')
                pixelNode = helper.getFirstNodeByPath(imCoords, 'pixel')
                line = eval(helper.getNodeText(lineNode))
                pixel = eval(helper.getNodeText(pixelNode))
                # print("  line:%s; pixel:%s" % (line, pixel))

                if currentPixelIndex == 0:
                    possibleLastLL = imCoords
                    possibleLastLLGeoNode = geoCoords

                if currentLineIndex == 0:
                    if currentPixelIndex == 0:
                        ULNode = imCoords
                        ULGeoNode = geoCoords
                        print(" ## GOT UL")

                currentPixelIndex += 1
                if pixel < lastPixel:  # go to new line
                    if currentLineIndex == 0:
                        print(" ## GOT UR")
                        URNode = lastImCoords
                        URGeoNode = lastGeoCoords

                    currentLineIndex += 1
                    currentPixelIndex = 0
                    # print(" doing line:%s" % currentLineIndex)

                lastImCoords = imCoords
                lastGeoCoords = geoCoords
                lastPixel = pixel

            footprint = ""
            print((" #### UL:%s" % ULNode))
            lineNode = helper.getFirstNodeByPath(ULNode, 'line')
            pixelNode = helper.getFirstNodeByPath(ULNode, 'pixel')
            line = eval(helper.getNodeText(lineNode))
            pixel = eval(helper.getNodeText(pixelNode))
            print(("   -->   line:%s; pixel:%s" % (line, pixel)))
            latNode = helper.getFirstNodeByPath(ULGeoNode, 'latitude')
            lonNode = helper.getFirstNodeByPath(ULGeoNode, 'longitude')
            lat = eval(helper.getNodeText(latNode))
            lon = eval(helper.getNodeText(lonNode))
            print(("   ---->>   lat:%s; lon:%s" % (lat, lon)))
            footprint_ul = "%s %s" % (lat, lon)

            #
            print((" #### UR:%s" % URNode))
            lineNode = helper.getFirstNodeByPath(URNode, 'line')
            pixelNode = helper.getFirstNodeByPath(URNode, 'pixel')
            line = eval(helper.getNodeText(lineNode))
            pixel = eval(helper.getNodeText(pixelNode))
            print(("   -->   line:%s; pixel:%s" % (line, pixel)))
            latNode = helper.getFirstNodeByPath(URGeoNode, 'latitude')
            lonNode = helper.getFirstNodeByPath(URGeoNode, 'longitude')
            lat = eval(helper.getNodeText(latNode))
            lon = eval(helper.getNodeText(lonNode))
            print(("   ---->>   lat:%s; lon:%s" % (lat, lon)))
            footprint_ur = "%s %s" % (lat, lon)

            #
            print((" #### LL:%s" % possibleLastLL))
            lineNode = helper.getFirstNodeByPath(possibleLastLL, 'line')
            pixelNode = helper.getFirstNodeByPath(possibleLastLL, 'pixel')
            line = eval(helper.getNodeText(lineNode))
            pixel = eval(helper.getNodeText(pixelNode))
            print(("   -->   line:%s; pixel:%s" % (line, pixel)))
            latNode = helper.getFirstNodeByPath(possibleLastLLGeoNode, 'latitude')
            lonNode = helper.getFirstNodeByPath(possibleLastLLGeoNode, 'longitude')
            lat = eval(helper.getNodeText(latNode))
            lon = eval(helper.getNodeText(lonNode))
            print(("   ---->>   lat:%s; lon:%s" % (lat, lon)))
            footprint_ll = "%s %s" % (lat, lon)

            #
            print((" #### LR:%s" % imCoords))
            lineNode = helper.getFirstNodeByPath(imCoords, 'line')
            pixelNode = helper.getFirstNodeByPath(imCoords, 'pixel')
            line = eval(helper.getNodeText(lineNode))
            pixel = eval(helper.getNodeText(pixelNode))
            print(("   -->   line:%s; pixel:%s" % (line, pixel)))
            latNode = helper.getFirstNodeByPath(geoCoords, 'latitude')
            lonNode = helper.getFirstNodeByPath(geoCoords, 'longitude')
            lat = eval(helper.getNodeText(latNode))
            lon = eval(helper.getNodeText(lonNode))
            print(("   ---->>   lat:%s; lon:%s" % (lat, lon)))
            footprint_lr = "%s %s" % (lat, lon)

            if direction == "Descending":
                footprint = "%s %s %s %s %s" % (footprint_ul, footprint_ll, footprint_lr, footprint_ur, footprint_ul)
            else:
                footprint = "%s %s %s %s %s" % (footprint_lr, footprint_ur, footprint_ul, footprint_ll, footprint_lr)

            print(" ==> footprint=%s" % footprint)
            return footprint

    #
    # updated xml metadata extract
    #
    def xmlExtract(self, xmlData, aMetadata, xmlMapping):
        # self.debug =1
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)

        helper.setData(xmlData)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        for field in xmlMapping:
            if self.debug != 0:
                print("\n\nmetadata extract field:%s" % field)
            multiple = False
            attr = None
            aPath = None
            aValue = None
            if xmlMapping[field].find("@") >= 0:
                attr = xmlMapping[field].split('@')[1]
                aPath = xmlMapping[field].split('@')[0]
                if aPath.endswith('*'):
                    multiple = True
                    aPath = aPath[0:-1]
                    print(" -> multiple used on path:%s" % aPath)
            else:
                attr = None
                aPath = xmlMapping[field]

            if not multiple:
                aNode = helper.getFirstNodeByPath(None, aPath, None)
                if aNode == None:
                    aValue = None
                else:
                    if attr == None:  # return NODE TEXT
                        aValue = helper.getNodeText(aNode)
                    else:  # return attribute TEXT
                        aValue = helper.getNodeAttributeText(aNode, attr)

                if self.debug != 0:
                    print("  --> metadata[%s]: %s=%s" % (num_added, field, aValue))
                aMetadata.setMetadataPair(field, aValue)
                num_added = num_added + 1
            else:  # will return NODE TEXT
                aList = []
                helper.getNodeByPath(None, aPath, attr, aList)
                print(" -> multiple; list of node found:%s" % len(aList))
                if len(aList) > 0:
                    for aNode in aList:
                        aValue = helper.getNodeText(aNode)
                        if self.debug != 0:
                            print("  --> metadata multiple[%s]: %s=%s" % (num_added, field, aValue))
                        aMetadata.setMetadataPair(field, aValue)
                        num_added = num_added + 1

        footprint = self.extractRadarsatFootprint(helper, aMetadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION))
        aMetadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        return num_added

    #
    #
    #
    def extractMetadata(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        self.metadata = met

        # use what contains the metadata file
        # in the two cases
        if len(self.metContent_data) == 0:
            raise Exception("no metadata to be parsed")

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # set local attributes
        # met.addLocalAttribute("originalName", self.origName)

        # first metadata extract
        num_added = self.xmlExtract(self.metContent_data, met, self.xmlMapping)

        # set single, dual, quad polarization
        if self.num_images == 1:
            met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, 'S')
        elif self.num_images == 2:
            met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, 'D')
        elif self.num_images == 4:
            met.setMetadataPair(metadata.METADATA_POLARISATION_MODE, 'Q')
        else:
            raise Exception("invalid number of images in products:%s" % self.num_images)

        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        print(("metadata extracted: %s" % num_added))

    def extractCoordinates(self, processInfo):
        self.getFootprint(processInfo)

        # get corners
        # getCoordinates(self.first_image_path)
        do(self.first_image_path)
        os._exit(1)

    def getOrbitFromProdReport(self, processInfo):
        # if not foune use 0
        orbit = '0'
        for line in self.prodReport_data.split('\n'):
            if line.find('Orbit Number') > 0:  # like Orbit Number                                   : 11735
                orbit = line.split(':')[1].strip()
                break

        if orbit == '0':
            processInfo.addLog("## orbit not found in .prodReport, set to 0")
        else:
            processInfo.addLog("## orbit found in .prodReport:'%s'" % orbit)
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, orbit)

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo):
        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # get orbit from; is like 23861_PRED.ORB
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        try:
            orbit = int(tmp.split('_')[0])
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, "%s" % orbit)
        except:
            # raise Exception("Cannot get orbit from orbitDataFile value'%s'" % tmp)
            self.getOrbitFromProdReport(processInfo)

        # uppercase
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, tmp.upper())

        # uppercase
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ANTENNA_LOOK_DIRECTION)
        self.metadata.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION, tmp.upper())

        # in order as per spec
        tmp = self.metadata.getMetadataValue(metadata.METADATA_POLARISATION_CHANNELS)
        toks = tmp.split(' ')
        if len(toks) == 1:
            pass
        elif len(toks) == 2:
            if toks[0][0] != toks[1][0]:
                raise Exception("unknown polarisation pair:%s %s" % (toks[0], toks[1]))
            if toks[0][0] == 'V':
                self.metadata.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, 'VV, VH')
            elif toks[0][0] == 'H':
                self.metadata.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, 'HH, HV')
            else:
                raise Exception("unknown polarisation pair:%s %s" % (toks[0], toks[1]))
        elif len(toks) == 4:
            toks.sort()
            res = ""
            for item in toks:
                if len(res) > 0:
                    res += ', '
                res += item
            self.metadata.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS, res)

        # self.extractCoordinates(processInfo)
        self.getFootprint(processInfo)

        # Defining METADATA_START_DATE, METADATA_START_TIME.
        # value is like 2017-09-12T10:45:23.117
        # DOPPLER; like: 2012-07-05T05:02:36.734596Z
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        start_tokens = start.split('T')

        print((" ############# start_tokens:%s" % start_tokens))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME,
                                      "%s.%s" % (start_tokens[1].split('.')[0], start_tokens[1].split('.')[1][:3]))
        print((" ############# start_time:%s" % "%s.%s" % (
        start_tokens[1].split('.')[0], start_tokens[1].split('.')[1][:3])))

        # Defining METADATA_STOP_DATE, METADATA_STOP_TIME.
        stop = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)
        stop_tokens = stop.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME,
                                      "%s.%s" % (stop_tokens[1].split('.')[0], stop_tokens[1].split('.')[1][:3]))
        print((" ############# stop_time:%s" % "%s.%s" % (
        stop_tokens[1].split('.')[0], stop_tokens[1].split('.')[1][:3])))

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))
        # os._exit(1)

        flat = float(self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LAT))
        flon = float(self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LON))
        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
        if flat < 0:
            flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)

        #
        typecode = self.buildTypeCode(processInfo)

        # some typecode have no boundingBox and other fields
        if typecode in BOUNDING_BOX_TYPECODES:
            browseIm = BrowseImage()
            # will wrap longitude if needed
            browseIm.setFootprint(self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
            wrappedFootprint = browseIm.getFootprint()
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, wrappedFootprint)
            if browseIm.footptintChanged():
                self.metadata.setMetadataPair("ORIGINAL_FOOTPRINT", browseIm.origFootprint)
            browseIm.calculateBoondingBox()
            clat, clon = browseIm.calculateCenter()
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, "%s" % clat)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, "%s" % clon)
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
            self.boundingBox = browseIm.boondingBox
            # bounding box
            self.metadata.addLocalAttribute("boundingBox", self.boundingBox)
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, self.boundingBox)
            print((" ######################## typecode %s in BOUNDING_BOX_FLAG map" % typecode))
            self.useBbox = True
        else:
            self.boundingBox = None
            print((" ######################## typecode %s NOT in BOUNDING_BOX_FLAG map" % typecode))
            self.useBbox = False

        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_TYPE, 'NOMINAL')

    #
    #
    #
    def buildTypeCode(self, processInfo):
        self.getSensorMode(processInfo)

        productType = self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_TYPE)
        acqType = self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_TYPE)
        opMode = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        pLevel = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL)

        # special case SGF:
        typeCode = None
        if productType == 'SGF':
            if acqType == 'ScanSAR Narrow':
                typeCode = 'SAR_SN_SCN'
            elif acqType == 'ScanSAR Wide':
                typeCode = 'SAR_SW_SCW'
            else:
                # raise Exception("unknown SGF case acquisition type:%s; opMode:%s" % (acqType, opMode))
                typeCode = 'SAR_%sSGF' % opMode
        else:
            typeCode = "SAR_%s%s" % (opMode, pLevel)
            print(("typeCode:%s" % typeCode))

        if not typeCode in REF_TYPECODES:
            raise Exception("buildTypeCode; unknown type code:%s" % typeCode)

        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typeCode)
        return typeCode
        # os._exit(1)

        # PRECEDENT CODE:
        """if productType != 'SGF' and ( acqType!= 'ScanSAR Narrow' and acqType!= 'ScanSAR Wide'):
            typecode = "SAR_%s%s" % (self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE), self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL))
            if not typecode in REF_TYPECODES:
                print(" #### typecode unknown: '%s'; but STRICTLY_COMPLY_TO_SPEC is False and so we accept it\n" % typecode)

            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
            return typecode
        else:
            if acqType=='ScanSAR Narrow':
                typecode='SAR_SN_SCN'
            elif acqType=='ScanSAR Wide':
                typecode='SAR_SW_SCW'
            else:
                raise Exception("unknown SGF case acquisition type:%s" % acqType)

            if not typecode in REF_TYPECODES:
                raise Exception("buildTypeCode; unknown typecode 2:%s" % typecode)

            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
            return typecode"""

    #
    # 
    #
    def buildTypeCode_old(self):
        self.getSensorMode()

        # STRICTLY_COMPLY_TO_SPEC flag used?
        strict = True
        aFlag = self.metadata.getMetadataValue('STRICTLY_COMPLY_TO_SPEC')
        print(("STRICTLY_COMPLY_TO_SPEC:%s" % aFlag))
        if self.metadata.valueExists(aFlag) and aFlag == 'False':
            strict = False

        productType = self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_TYPE)
        acqType = self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_TYPE)
        if productType != 'SGF' and (acqType != 'ScanSAR Narrow' and acqType != 'ScanSAR Wide'):
            typecode = "SAR_%s%s" % (self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE),
                                     self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_LEVEL))
            if not typecode in REF_TYPECODES:
                if strict:
                    print((" #### typecode unknown: '%s'\n" % typecode))
                    raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
                else:
                    print((
                                " #### typecode unknown: '%s'; but STRICTLY_COMPLY_TO_SPEC is False and so we accept it\n" % typecode))

            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
            return typecode
        else:
            if acqType == 'ScanSAR Narrow':
                typecode = 'SAR_SN_SCN'
            elif acqType == 'ScanSAR Wide':
                typecode = 'SAR_SW_SCW'
            else:
                raise Exception("unknown SGF case acquisition type:%s" % acqType)

            if not typecode in REF_TYPECODES:
                if strict:
                    print((" #### typecode unknown 2: '%s'\n" % typecode))
                    raise Exception("buildTypeCode; unknown typecode 2:%s" % typecode)
                else:
                    print((
                                " #### typecode unknown 2: '%s'; but STRICTLY_COMPLY_TO_SPEC is False and so we accept it\n" % typecode))

            self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
            return typecode

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)
