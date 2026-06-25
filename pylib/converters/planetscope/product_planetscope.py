"""This class represent a planetscope directory product

Supported type codes:
PSC_DEF_OT: 3-band, 4-band and 5-band Analytic and Visual Ortho Tile level 3A
PSC_DEF_S3: 3-band Analytic and Visual Ortho and Basic Scene (level 1B and level 3B)
PSC_DEF_S4: 4-band Analytic and Visual Ortho and Basic Scene (level 1B and 3B)
PSC_8AO_3B: 8-bands products: level 3B Analytic Ortho Scene.
PSC_8SR_3B: 8-bands products: level 3B Analytic Ortho Surface Reflectance Scene.
PSC_8AB_1B: 8-bands products: level 1A and level 1B Analytic Basic Scene
PSC_4AO_3B: 4-bands products: level 3B Analytic Ortho Scene.
PSC_4SR_3B: 4-bands products: level 3B Analytic Ortho Surface Reflectance Scene.
PSC_4AB_1B: 4-bands products: level 1A and level 1B Analytic Basic Scene.
PSC_3VO_3B: 3-bands products: level 3B Visual Ortho Scene.
PSC_3AO_3B: 3-bands products: level 3B Analytic
PSC_4OT_3A: 4-bands products: level 3A Ortho Tile
"""
import json
import fnmatch
import os
import platform
import shutil
from typing import Optional, Tuple
from pathlib import Path
from subprocess import call

import eoSip_converter.xmlHelper as xmlHelper
import eoSip_converter.imageUtil as imageUtil
from eoSip_converter.esaProducts.product_directory import Product_Directory
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts import browse_metadata
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts import formatUtils
from xml_nodes import rep_footprint

OP_SYS = platform.system()

# gdal commands
GDAL_3B_STEP_0 = 'gdal_translate -b 3 -outsize 20% 20% "@SRC" "@DEST1"'
GDAL_3B_STEP_1 = 'gdal_translate -b 2 -outsize 20% 20% "@SRC" "@DEST2"'
GDAL_3B_STEP_2 = 'gdal_translate -b 1 -outsize 20% 20% "@SRC" "@DEST3"'
# no resize
GDAL_3B_STEP_N0 = 'gdal_translate -b 1 "@SRC" "@DEST1"'
GDAL_3B_STEP_N1 = 'gdal_translate -b 2 "@SRC" "@DEST2"'
GDAL_3B_STEP_N2 = 'gdal_translate -b 3 "@SRC" "@DEST3"'

GDAL_STEP_3 = 'python (Get-Command gdal_merge.py).Source -co "PHOTOMETRIC=rgb" -separate "@DEST1" "@DEST2" "@DEST3" -o "@DEST4"'
GDAL_STEP_4 = 'gdal_translate "@DEST4" -scale 0 4086 -ot Byte -of png "@DEST5"'

GM_STEP_1 = 'gm%s convert "@SRC" -transparent black "@DEST"' % '.exe' if OP_SYS == 'Windows' else ''

# For verification. Not used
REF_TYPECODE = {
    # "PSC_DEF_OT", "PSC_DEF_S3", "PSC_DEF_S4",  # 3-band, 4-band and 5-band Analytic and Visual Ortho Tile level 3A (obsolete)
    "PSC_8AO_3B", "PSC_8SR_3B", "PSC_8AB_1B",    # 8-bands products: level 3B Analytic Ortho Scene
    "PSC_4AO_3B", "PSC_4SR_3B", "PSC_4AB_1B",    # 4-bands products: level 3B Analytic Ortho Scene
    "PSC_3VO_3B", "PSC_3AO_3B",                  # 3-bands products: level 3B Visual Ortho Scene
    "PSC_4OT_3A"                                 # 4-bands products: level 3A Ortho Tile
}

TYPECODES_IN_ORDER_OF_IMPORTANCE = (
    # "PSC_DEF_OT", "PSC_DEF_S3", "PSC_DEF_S4",  # 3-band, 4-band and 5-band Analytic and Visual Ortho Tile level 3A (obsolete)
    "PSC_8AO_3B", "PSC_8SR_3B", "PSC_8AB_1B",    # 8-bands products: level 3B Analytic Ortho Scene
    "PSC_4AO_3B", "PSC_4SR_3B", "PSC_4AB_1B",    # 4-bands products: level 3B Analytic Ortho Scene
    "PSC_3AO_3B",                                # 3-bands Analytic ortho Scene
    "PSC_3VO_3B",                                # 3-bands products: level 3B Visual Ortho Scene
    "PSC_4OT_3A"                                 # 4-bands products: level 3A Ortho Tile
)

# From 'Planetscope products.xlsx' and EO-SIP specification
TYPECODE_REQD_FOLDER_CONTENTS = {
    "PSC_8AO_3B": ("ortho_analytic_8b", "ortho_analytic_8b_xml", "ortho_udm2",),
    "PSC_8SR_3B": ("ortho_analytic_8b_sr", "ortho_analytic_8b_xml", "ortho_udm2",),
    "PSC_8AB_1B": ("basic_analytic_8b", "basic_udm2", "basic_analytic_8b_rpc", "basic_analytic_8b_xml"),
    "PSC_4AO_3B": ("ortho_analytic_4b", "ortho_analytic_4b_xml", "ortho_udm2",),
    "PSC_4SR_3B": ("ortho_analytic_4b_sr", "ortho_analytic_4b_xml", "ortho_udm2",),
    "PSC_4AB_1B": ("basic_analytic_4b", "basic_udm2", "basic_analytic_4b_rpc", "basic_analytic_4b_xml"),
    "PSC_3VO_3B": ("ortho_analytic_3b", "ortho_analytic_3b_xml", "ortho_udm2",),
    "PSC_3AO_3B": ("ortho_visual",),
    "PSC_4OT_3A": "*",  # Take all native assets for PSC_4OT_3A
}

# Mapping whose keys are new product types (EOSIP spec v1.2) and values are dicts detailing the requirements of the old
# native products. Those dicts' keys are:
#   - 'assets': Old native product sub-directories/assets required for conversion to new product type
#   - 'levels': Product/processing levels of natives that are needed
#   - 'bands': Number of observational bands required in native product
OBSOLETE_TO_NEW_TYPECODE_REQS = {
    "PSC_8AO_3B": {
        'assets': ("analytic", "analytic_xml", "udm2",),
        'levels': ('L3B', ),
        'bands': 8
    },
    "PSC_8SR_3B": {
        'assets': ("analytic_sr", "analytic_xml", "udm2",),
        'levels': ('L3B', ),
        'bands': 8
    },
    "PSC_8AB_1B": {
        'assets': ("basic_analytic", "udm2", "basic_analytic_rpc", "basic_analytic_xml"),
        'levels': ('L1B', 'L1A'),
        'bands': 8
    },
    "PSC_4AO_3B": {
        'assets': ("analytic", "analytic_xml", "udm*",),
        'levels': ('L3B', ),
        'bands': 4
    },
    "PSC_4SR_3B": {
        'assets': ("analytic_sr", "analytic_sr_xml", "udm*",),
        'levels': ('L3B', ),
        'bands': 4
    },
    "PSC_4OT_3A": {
        'assets': '*',  # Keep all assets from native product
        'levels': ('L3A', ),
        'bands': 4
    },
    "PSC_4AB_1B": {
        'assets': ("basic_analytic", "basic_udm*", "basic_analytic_rpc", "basic_analytic_xml"),
        'levels': ('L1B', 'L1A'),
        'bands': 4
    },
    "PSC_3VO_3B": {
        'assets': ("visual",),
        'levels': ('L3B', ),
        'bands': 3
    },
    "PSC_3AO_3B": {
        'assets': ("analytic", "analytic_xml", "udm*",),
        'levels': ('L3B', ),
        'bands': 3
    },
}


WITH_TILEID = ['PSC_DEF_OT']  # Not used?

REF_sensorSpecificName = ['PS2', 'PS2.SD', 'PSB.SD']

BROWSE_S4 = "AnalyticMS_SR.tif"
BROWSE_S8 = "AnalyticMS_8b.tif"
BROWSE_OTHER = "Visual.tif"

# Usuable data mask (.tif) file suffixes required for each product type
TYPECODE_UDM_ENDINGS = {
    "PSC_DEF_OT": "udm2.tif",
    "PSC_DEF_S3": "3B_Analytic_DN_udm.tif",
    "PSC_DEF_S4": "3B_udm2.tif",
    "PSC_8AO_3B": "3B_udm2.tif",
    "PSC_8SR_3B": "3B_udm2.tif",
    "PSC_8AB_1B": "1B_udm2.tif",
    "PSC_4AO_3B": "3B_udm2.tif",
    "PSC_4SR_3B": "3B_udm2.tif",
    "PSC_4AB_1B": "1B_udm2.tif",
    "PSC_3VO_3B": "3B_udm2.tif",
    "PSC_3AO_3B": "3B_udm2.tif",
}
TYPECODE_UDM_ENDINGS["PSC_4OT_3A"] = TYPECODE_UDM_ENDINGS['PSC_DEF_OT']

# Image (.tif) file suffixes required for each product type
TYPECODE_BROWSE_IMAGE_ENDINGS = {
    "PSC_DEF_OT": "BGRN_Analytic.tif",
    "PSC_DEF_S3": "3B_Analytic.tif",
    "PSC_DEF_S4": "3B_AnalyticMS.tif",
    "PSC_8AO_3B": "3B_AnalyticMS_8b.tif",
    "PSC_8SR_3B": "3B_AnalyticMS_SR_8b.tif",
    "PSC_8AB_1B": "1B_AnalyticMS_8b.tif",
    "PSC_4AO_3B": "3B_AnalyticMS.tif",
    "PSC_4SR_3B": "3B_AnalyticMS_SR.tif",
    "PSC_4AB_1B": "1B_AnalyticMS.tif",
    "PSC_3VO_3B": "3B_Analytic.tif",
    "PSC_3AO_3B": "3B_Visual.tif",
}
TYPECODE_BROWSE_IMAGE_ENDINGS["PSC_4OT_3A"] = TYPECODE_BROWSE_IMAGE_ENDINGS['PSC_DEF_OT']

XML_SUFFIX = "Visual_metadata.xml"
XML_SUFFIX2 = "AnalyticMS_metadata.xml"
# Metadata (.xml) file suffixes required for each product type
TYPECODE_XML_ENDINGS = {
    "PSC_DEF_OT": "BGRN_Analytic_metadata.xml",
    "PSC_DEF_S3": "3B_Analytic_metadata.xml",
    "PSC_DEF_S4": "3B_AnalyticMS_metadata.xml",
    "PSC_8AO_3B": "3B_AnalyticMS_8b_metadata.xml",
    "PSC_8SR_3B": "3B_AnalyticMS_8b_metadata.xml",
    "PSC_8AB_1B": "1B_AnalyticMS_8b_metadata.xml",
    "PSC_4AO_3B": "3B_AnalyticMS_metadata.xml",
    "PSC_4SR_3B": "3B_AnalyticMS_metadata.xml",
    "PSC_4AB_1B": "1B_AnalyticMS_metadata.xml",
    "PSC_3VO_3B": "3B_Analytic_metadata.xml",
    "PSC_3AO_3B": XML_SUFFIX,
}
TYPECODE_XML_ENDINGS["PSC_4OT_3A"] = TYPECODE_XML_ENDINGS['PSC_DEF_OT']

# constants:
BEGIN_POSITION = 'beginPosition'
END_POSITION = 'endPosition'
LEVEL = 'level'
ORBIT_DIRECTION = 'orbit_direction'
SHAPE = 'shape'


def gdal_bi_from_tif(
        input_file: Path,
        output_file: Path,
        band_idxs: Optional[Tuple[int, int, int]] = None,
        percentile_range: Tuple[float, float] = (2.0, 98.0),
        desired_bi_size: int = 2000
):
    import tempfile
    from os import environ
    from osgeo import gdal, gdalconst


    def percentile_value(percentile, counts, limits):
        threshold = percentile / 100.0 * sum(counts)

        if percentile == 0.0:
            return min(limits)
        elif percentile == 100.0:
            return max(limits)

        cumsum = 0
        for idx, count in enumerate(counts):
            cumsum += count
            if cumsum >= threshold:
                return min(limits) + (max(limits) - min(limits)) * idx / len(counts)


    # Prevent creation of *.aux.xml files
    previous_gdal_pam_enabled_setting = environ.get("GDAL_PAM_ENABLED", None)
    environ["GDAL_PAM_ENABLED"] = "NO"

    input_ds, tmp_ds = None, None
    tmp_dir = Path(tempfile.mkdtemp())
    try:

        input_ds = gdal.Open(str(input_file.resolve()), gdal.GA_ReadOnly)
        info = gdal.Info(input_ds, format="json")
        rescale_factor = min([desired_bi_size / d for d in info['size']])
        options = {
            "resampleAlg": "bilinear",
            "width": round(rescale_factor * info['size'][0]),
            "height": round(rescale_factor * info['size'][1])
        }
        if band_idxs is not None:
            options["bandList"] = [idx + 1 for idx in band_idxs]

        tmp_file = tmp_dir / f'tmp{input_file.suffix}'
        gdal.Translate(
            str(tmp_file.resolve()),
            input_ds,
            options=gdal.TranslateOptions(**options)
        )

        tmp_ds = gdal.Open(str(tmp_file.resolve()), gdal.GA_ReadOnly)
        info = gdal.Info(tmp_ds, format="json", computeMinMax=True, reportHistograms=True)
        low_percentile_vals, high_percentile_vals = [], []
        for band_info in info['bands']:
            counts = band_info['histogram']['buckets']
            hist_min = band_info['histogram']['min']
            hist_max = band_info['histogram']['max']
            low_percentile_vals.append(percentile_value(min(percentile_range), counts, (hist_min, hist_max)))
            high_percentile_vals.append(percentile_value(max(percentile_range), counts, (hist_min, hist_max)))

        low_val = min(low_percentile_vals)
        high_val = max(high_percentile_vals)
        gdal.Translate(
            str(output_file.resolve()),
            tmp_ds,
            options=gdal.TranslateOptions(
                format='PNG',
                outputType=gdalconst.GDT_Byte,
                scaleParams=[[low_val, high_val, 0, 255]] * 3
            )
        )
    except Exception as err:
        raise err
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

        if previous_gdal_pam_enabled_setting is not None:
            environ["GDAL_PAM_ENABLED"] = previous_gdal_pam_enabled_setting
        else:
            environ.pop("GDAL_PAM_ENABLED")

        if tmp_ds is not None:
            del tmp_ds
        if input_ds is not None:
            del input_ds


def writeShellCommand(command, testExit=False, badExitCode=-1):
    if not testExit:
        return command + '\n'

    lines = [command]
    if OP_SYS == 'Windows':
        lines += [
            "if ($LASTEXITCODE -ne 0) {",
            "    exit %s" % badExitCode,
            "}"
        ]
    else:
        lines += [
            "if [ $? -ne 0 ]; then",
            "  exit %s" % badExitCode,
            "fi",
        ]

    return '\n'.join(lines) + '\n'


class Product_Planetscope(Product_Directory):
    jsonMapping = {
        metadata.METADATA_START_DATE_TIME: "['properties']['acquired']",
        metadata.METADATA_CLOUD_COVERAGE: "['properties']['cloud_cover']",
        metadata.METADATA_FOOTPRINT: "['geometry']['coordinates']",
        metadata.METADATA_SUN_ELEVATION: "['properties']['sun_elevation']",
        metadata.METADATA_SUN_AZIMUTH: "['properties']['sun_azimuth']",
        metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE: "['properties']['view_angle']",
        metadata.METADATA_RESOLUTION: "['properties']['pixel_resolution']",
        SHAPE: "['geometry']['type']"
    }

    xmlMapping = {
        BEGIN_POSITION: 'validTime/TimePeriod/beginPosition',
        END_POSITION: 'validTime/TimePeriod/endPosition',
        LEVEL: 'metaDataProperty/EarthObservationMetaData/productType',
        ORBIT_DIRECTION: 'using/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitDirection',
        metadata.METADATA_SOFTWARE_NAME: 'metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/processorName',
        metadata.METADATA_SOFTWARE_VERSION: 'metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/processorVersion',
        metadata.METADATA_NATIVE_PRODUCT_FORMAT: 'metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/nativeProductFormat',
        metadata.METADATA_INSTRUMENT: 'using/EarthObservationEquipment/instrument/Instrument/shortName',
        'azimuthAngle': 'using/EarthObservationEquipment/acquisitionParameters/Acquisition/azimuthAngle',
        'sceneCenter': 'target/Footprint/centerOf/Point/pos',
        'tileId': 'metaDataProperty/EarthObservationMetaData/tileId',
    }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)

        self.metadata_path = path
        with open(self.metadata_path, 'rt') as fd:
            self.metadata_content = json.load(fd)

        self.udm_file = None
        self.preview_s8_path = None
        self.preview_s4_path = None
        self.preview_other_path = None
        self.isOrthoRectified = None
        self.xml_metadata_path = None
        self.xml_metadata = None
        self.typecode = None
        self.productFolderName = os.path.basename(os.path.dirname(self.path))

        # Unify path delimiters
        self.EO_FOLDER = os.path.dirname(path)
        self.EO_FOLDER = self.EO_FOLDER.replace('/' if os.sep == '\\' else '\\', os.sep)

        if self.debug != 0:
            print(" init class Product_Planetscope")

    #
    # read metadata file
    #
    def getMetadataInfo(self, index=0):
        pass

    #
    #
    #
    def makeBrowseFromTif(self, aTifPath, anDestpath, anAlias, processInfo):
        print((" makeBrowseFromTif; src: %s" % aTifPath))
        resize = True
        ratio = 1
        w, h = imageUtil.get_image_size(aTifPath)

        if w == 1 or h == 1:
            resize = False

        if resize and w < 1600 and h < 1600:
            resize = False

        if resize:
            maxd = w if w > h else h
            ratio = 1600.0 / maxd
        print((" source .tif size: w=%s h=%s; resize:%s, ratio=%s" % (w, h, resize, ratio)))

        if resize:
            command1 = GDAL_3B_STEP_0.replace('@SRC', aTifPath)\
                                     .replace('@DEST1', "%s/%s_b1.tif" % (processInfo.workFolder, anAlias))
            command2 = GDAL_3B_STEP_1.replace('@SRC', aTifPath)\
                                     .replace('@DEST2', "%s/%s_b2.tif" % (processInfo.workFolder, anAlias))
            command3 = GDAL_3B_STEP_2.replace('@SRC', aTifPath)\
                                     .replace('@DEST3', "%s/%s_b3.tif" % (processInfo.workFolder, anAlias))
        else:
            command1 = GDAL_3B_STEP_N0.replace('@SRC', aTifPath)\
                                      .replace('@DEST1', "%s/%s_b1.tif" % (processInfo.workFolder, anAlias))
            command2 = GDAL_3B_STEP_N1.replace('@SRC', aTifPath)\
                                      .replace('@DEST2', "%s/%s_b2.tif" % (processInfo.workFolder, anAlias))
            command3 = GDAL_3B_STEP_N2.replace('@SRC', aTifPath)\
                                      .replace('@DEST3', "%s/%s_b3.tif" % (processInfo.workFolder, anAlias))

        # @DEST1 @DEST2 @DEST3 -o @DEST4
        command4 = GDAL_STEP_3.replace('@DEST1', '%s/%s_b1.tif' % (processInfo.workFolder, anAlias))\
                              .replace('@DEST2', '%s/%s_b2.tif' % (processInfo.workFolder, anAlias))\
                              .replace('@DEST3', '%s/%s_b3.tif' % (processInfo.workFolder, anAlias))\
                              .replace('@DEST4', '%s/merged.tif' % processInfo.workFolder)

        # gdal_translate @DEST4 -scale 0 4086 -ot Byte @DEST5
        command5 = GDAL_STEP_4.replace('@DEST4', '%s/merged.tif' % processInfo.workFolder)\
                              .replace('@DEST5', '%s/scaled.tif' % processInfo.workFolder)

        #
        command6 = "%s -transparent %s %s 0xff000000" % (
            self.stretcherApp,
            "%s/scaled.tif" % processInfo.workFolder,
            "%s/transparent.tif" % processInfo.workFolder
        )

        command7 = "%s -stretch %s %s 0.01" % (
            self.stretcherApp,
            "%s/transparent.tif" % processInfo.workFolder,
            anDestpath
        )

        commands = "%s%s%s%s%s%s%s" % (
            writeShellCommand(command1, True),
            writeShellCommand(command2, True),
            writeShellCommand(command3, True),
            writeShellCommand(command4, True),
            writeShellCommand(command5, True),
            writeShellCommand(command6, True),
            writeShellCommand(command7, True)
        )

        if OP_SYS == 'Windows':
            # Add proj.db to PROJ_LIB environmental variable if required:
            if os.environ.get('PROJ_LIB') is None:
                if os.environ.get('CONDA_PREFIX'):
                    venv_path = os.environ.get('CONDA_PREFIX')
                elif os.environ.get('VIRTUAL_ENV'):
                    venv_path = os.environ.get('VIRTUAL_ENV')
                else:
                    raise Exception("No virtual environment found, can't set PROJ_LIB (for proj.db)")
                proj_lib_path = os.path.join(venv_path, 'Library', 'share', 'proj')
                commands = ("$env:PROJ_LIB = %s" % proj_lib_path) + commands
            commands = '%s\nWrite-Output ""\nWrite-Output ""\nWrite-Output "browse aliased: %s done at path: %s"' % (commands, anAlias, anDestpath)
        else:
            commands = "%s\necho\necho\necho 'browse aliased: %s done at path: %s'" % (commands, anAlias, anDestpath)

        commandFile = "%s/command_%s.%s" % (processInfo.workFolder, anAlias, 'ps1' if OP_SYS == 'Windows' else 'sh')
        with open(commandFile, 'w') as fd:
            fd.write(commands)

        # launch the main make_browse script:
        if OP_SYS == 'Windows':
            command = "powershell -File \"%s\" 2>&1 | Tee-Object -FilePath \"%s/make_browses.stdout\""  % (commandFile, processInfo.workFolder)
        else:
            command = "/bin/bash -i -f %s 2>&1 | tee %s/make_browses.stdout" % (commandFile, processInfo.workFolder)

        retval = call(command, shell=False if OP_SYS == 'Windows' else True)
        print("  external make browse exit code:%s" % retval)
        processInfo.addLog("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)

        return "%s/%s_final.png" % (processInfo.workFolder, anAlias)

    #
    #
    #
    def makeBrowses(self, processInfo):
        from pathlib import Path
        import pyvips

        anEosip = processInfo.destProduct
        browseName = processInfo.destProduct.getEoProductName()
        self.browseDestPath = "%s/%s.BI.PNG" % (processInfo.workFolder, browseName)

        if self.preview_s8_path is not None:
            self.preview_path = self.preview_s8_path
        elif self.preview_s4_path is not None:
            self.preview_path = self.preview_s4_path
        elif self.preview_other_path is not None:
            self.preview_path = self.preview_other_path

        if self.preview_path is None:
            raise Exception("no self.preview_path")

        # If 8-band image, extract bands 2, 4, and 6, merge into an RGB image, and take that as the new image to derive
        # the browse from. If 4-band image, extract first 3 bands separately, merge, and use that as the new image to
        # derive the browse from. Otherwise, use as source for browse image as is
        source_img = self.preview_path
        nbands = imageUtil.get_nbands(source_img)

        temp_img, rgb_idxs = None, None
        try:
            if nbands >= 3:
                temp_img = imageUtil.generate_temporary_image_name(Path(processInfo.workFolder), 'tif')
                img_data = imageUtil.get_detailed_img_info(source_img)

                rgb_idxs = []
                for colour in ('red', 'green', 'blue'):
                    for band in img_data['bands']:
                        if band['colorInterpretation'].lower() == colour:
                            rgb_idxs.append(band['band'] - 1)
                            break
                    else:
                        rgb_idxs.append(None)

                try:
                    imageUtil.extract_and_join_bands(source_img, temp_img, rgb_idxs)
                except pyvips.Error as err:
                    imageUtil.extract_and_join_bands(source_img, temp_img, rgb_idxs, color_mode=pyvips.Interpretation.RGB16)
                source_img = temp_img

            # image_mean_brightness, image_std = imageUtil.image_mean_and_std(self.browseDestPath)
            if self.metadata_content.get('properties', {}).get('cloud_percent', 0.0) > 33.0:
                import logging
                import pyvips

                logging.getLogger('pyvips').setLevel(logging.ERROR)

                im = pyvips.Image.new_from_file(source_img)
                im = im.extract_band(0, n=3)
                imageUtil.resize_img_pyvips(im, self.browseDestPath, max_dim=1000)
                imageUtil.boost_brightness_cv2(self.browseDestPath, self.browseDestPath, 0.35)
            else:
                imageUtil.makeBrowse_v2(
                    type="PNG", src=source_img, dest=self.browseDestPath, showTraceback=True,
                    hist_equalisation=False,  # self.metadata_content['properties']['cloud_percent'] > 33.0
                )

            import PIL

            image_mean_brightness, image_std = imageUtil.image_mean_and_std(self.browseDestPath)
            img = PIL.Image.open(self.browseDestPath)
            img = PIL.ImageEnhance.Brightness(img)
            img = img.enhance(90. / image_mean_brightness)
            img.save(self.browseDestPath)

        except Exception as err:
            gdal_bi_from_tif(Path(source_img), Path(self.browseDestPath), band_idxs=rgb_idxs, desired_bi_size=1000)

        finally:
            if temp_img is not None and temp_img.exists():
                temp_img.unlink()
        # if self.preview_s4_path is None or self.preview_s8_path is None:
        #     resize = True
        #     ratio = 1
        #     w, h = imageUtil.get_image_size(self.preview_path)
        #     if w == 1 or h == 1:
        #         resize = False
        #     if resize and w < 1600 and h < 1600:
        #         resize = False
        #     if resize:
        #         maxd = w if w > h else h
        #         ratio = 1600.0 / maxd
        #     print((" source .tif size: w=%s h=%s; resize:%s, ratio=%s" % (w, h, resize, ratio)))
        #     imageUtil.makeBrowse("PNG", self.preview_path, self.browseDestPath, resizePercent=ratio * 100.0,
        #                          transparent=True)
        # else:
        #     self.makeBrowseFromTif(self.preview_path, self.browseDestPath, "browse", processInfo)


        # set AM time if needed
        anEosip.setFileAMtime(self.browseDestPath)
        processInfo.destProduct.addSourceBrowse(self.browseDestPath, [])
        processInfo.addLog(" browse image added: name=%s; path=%s" % (browseName, self.browseDestPath))

        # create browse choice for browse metadata report
        bmet = anEosip.browse_metadata_dict[self.browseDestPath]
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

        reportBuilder = rep_footprint.rep_footprint()
        #
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
        browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                       "rep:browseReport/rep:browse/rep:footprint").strip()
        if self.debug != 0:
            print("browseChoiceBlock :%s" % (browseChoiceBlock))
        bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

        # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
        # if specified in configuration
        tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

        # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

        processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % (browseChoiceBlock))

    def get_nbands_from_xml_file(self, xml_file):
        helper = xmlHelper.XmlHelper()
        helper.loadFile(xml_file)
        helper.parseData()

        product_info_node = helper.getFirstNodeByPath(path='resultOf/EarthObservationResult/product/ProductInformation')
        num_bands = int(helper.getNodeText(helper.getFirstNodeByPath(node=product_info_node, path='numBands')))

        return num_bands

    def get_product_level_from_xml_file(self, xml_file):
        helper = xmlHelper.XmlHelper()
        helper.loadFile(xml_file)
        helper.parseData()

        product_metadata_node = helper.getFirstNodeByPath(path='metaDataProperty/EarthObservationMetaData')
        prod_level = helper.getNodeText(helper.getFirstNodeByPath(node=product_metadata_node, path='productType'))

        return prod_level

    #
    # extract the PlanetScope interesting piece in working folder:
    # - metadata xml
    # - preview images
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will extract directory product '%s' to path:%s" % (self.path, folder))

        self.contentList = []
        self.EXTRACTED_PATH = folder
        self.num_preview = 0
        determined_typecode = self.determineTypeCode()

        raw_udm_endings_order = ()

        raw_browse_path_endings_order = (
            TYPECODE_BROWSE_IMAGE_ENDINGS[determined_typecode],
            BROWSE_S4,
            BROWSE_OTHER
        )
        raw_browse_path_endings = {
            TYPECODE_BROWSE_IMAGE_ENDINGS[determined_typecode]: "preview_s8_path",
            BROWSE_S4: "preview_s4_path",
            BROWSE_OTHER: "preview_other_path"
        }
        raw_xml_endings_order = (
            TYPECODE_XML_ENDINGS[determined_typecode],
            XML_SUFFIX,
            XML_SUFFIX2,
        )

        n = 0
        for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):
            root = root.replace('/' if os.sep == '\\' else '\\', os.sep)
            dirs = [d.replace('/' if os.sep == '\\' else '\\', os.sep) for d in dirs]
            files = [f.replace('/' if os.sep == '\\' else '\\', os.sep) for f in files]

            # ################################################################ #
            # # Extract only sub-products that are part of the typecode specs# #
            # ################################################################ #
            if root != self.EO_FOLDER:
                if self.old_product_type_from_obsolete_native() not in ("PSC_DEF_OT", "PSC_DEF_S3", "PSC_DEF_S4"):
                    folder_name = os.path.basename(root)
                    if (folder_name not in TYPECODE_REQD_FOLDER_CONTENTS[determined_typecode]
                        and
                        TYPECODE_REQD_FOLDER_CONTENTS[determined_typecode] != '*'):
                        continue
            # ################################################################ #

            for name in files:
                n += 1
                eoFile = "%s%s%s" % (root, os.sep, name)
                print(" ## product content[%d]:'%s' in:%s" % (n, name, eoFile))

                if name.endswith(TYPECODE_UDM_ENDINGS[determined_typecode]):
                    self.udm_file = eoFile
                    continue

                for ending in raw_browse_path_endings_order:
                    product_attr = raw_browse_path_endings[ending]
                    if name.endswith(ending):
                        if self.isOrthoRectified is not None:
                            continue

                        # set relevant preview_path attr on self e.g.
                        # self.preview_s8_path, self.preview_s4_path,
                        # self.preview_other_path
                        setattr(self, product_attr, eoFile)
                        shutil.copyfile(
                            getattr(self, product_attr),
                            "%s%s%s" % (self.EXTRACTED_PATH, os.sep, name)
                        )

                        self.num_preview += 1
                        self.isOrthoRectified = 'ortho' in root

                        print((" ## FOUND self.%s=%s" % (product_attr, getattr(self, product_attr))))

                        break

                else:
                    for ending in raw_xml_endings_order:
                        if name.endswith(ending):
                            self.xml_metadata_path = eoFile
                            with open(self.xml_metadata_path, 'rt') as fd:
                                self.xml_metadata = fd.read()

                            shutil.copyfile(self.xml_metadata_path, "%s%s%s" % (self.EXTRACTED_PATH, os.sep, name))
                            print((" ## FOUND self.xml_metadata_path=%s" % self.xml_metadata_path))
                            break

                # If old product type, the tif endings don't make sense to decide which is the preview_path(s)
                # Reassign the images here and xml metadata
                if self.old_product_type_from_obsolete_native() is not None and determined_typecode != 'PSC_4OT_3A':

                    assets = [Path(p).name for p in Path(self.EO_FOLDER).iterdir() if Path(p).is_dir()]
                    found = False
                    assets_with_imgs = []
                    for asset in  OBSOLETE_TO_NEW_TYPECODE_REQS[determined_typecode]['assets']:
                        if 'analytic' in asset and not asset.endswith('xml'):
                            assets_with_imgs.append(asset)

                    if determined_typecode == 'PSC_3VO_3B':
                        self.preview_s8_path = [f for f in (Path(self.EO_FOLDER) / 'visual').iterdir() if f.name.lower().endswith('tif') and f.is_file()][0]
                        self.preview_s8_path = str(self.preview_s8_path.resolve())
                        self.num_preview = 1
                        assets_with_imgs = ("analytic", "analytic_sr", "basic_analytic")  # For xml metadata

                    for req_asset in assets_with_imgs:
                        for asset in assets:
                            if asset == req_asset:
                                asset_dir = Path(self.EO_FOLDER) / asset
                                xml_dir = Path(self.EO_FOLDER) / f"{asset}_xml"

                                # Only use the visual asset if type is PSC_3VO_3B
                                if determined_typecode != 'PSC_3VO_3B':
                                    self.preview_s8_path = [f for f in asset_dir.iterdir() if f.name.lower().endswith('tif') and f.is_file()][0]
                                    self.preview_s8_path = str(self.preview_s8_path.resolve())
                                    self.num_preview = 1

                                self.xml_metadata_path = [f for f in xml_dir.iterdir() if f.name.lower().endswith('xml') and f.is_file()][0]
                                self.xml_metadata_path = str(self.xml_metadata_path.resolve())
                                with open(self.xml_metadata_path, 'rt') as fd:
                                    self.xml_metadata = fd.read()

                                self.isOrthoRectified = 'basic' not in asset
                                found = True
                                break
                        if found:
                            break


        if self.num_preview != 1:
            raise Exception("no preview found: %s" % self.num_preview)

        if self.xml_metadata_path is None:
            raise Exception("no metadata file found")

    #
    # from xml file
    #
    def extractAdditionalInfo(self):
        helper = xmlHelper.XmlHelper()
        #helper.setDebug(1)
        helper.setData(self.xml_metadata);
        helper.parseData()

        num_added = 0
        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  -->%s=%s" % (field, aValue))
            self.metadata.setMetadataPair(field, aValue)
            num_added = num_added + 1

    #
    # from json file
    #
    def extractMetadata(self, met=None, processInfo=None):
        if met is None:
            raise Exception("metadata is None")

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        # save metadata to workfolder for test purpose:
        destPath = "%s/%s" % (processInfo.workFolder, os.path.basename(self.path))
        shutil.copyfile(self.path, destPath)

        numAdded = 0
        for key in self.jsonMapping:
            mapping = self.jsonMapping[key]
            try:
                print((" extracted metadata '%s' using mapping: '%s'" % (key, mapping)))
                value = eval("self.metadata_content%s" % mapping)
                print(("  extracted metadata '%s' value: '%s'" % (key, value)))
                met.setMetadataPair(key, value)
                numAdded = 1
            except:
                print((" !! metadata not found: '%s' using mapping: '%s'" % (key, mapping)))

        self.metadata = met
        self.buildTypeCode(processInfo)
        self.extractAdditionalInfo()
        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    #
    # refine the metada
    #
    def refineMetadata(self, processInfo):
        # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
        # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
        # So we mark it and will substitute with good value before product report write
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # maybe also in the xml file, which has start + stop. If present, use them
        # like: 2017-02-04T20:24:10+00:00
        start = self.metadata.getMetadataValue(BEGIN_POSITION)
        stop = self.metadata.getMetadataValue(END_POSITION)
        print(("start=%s; stop=%s" % (start, stop)))
        if start is not None and stop is not None:
            pos = start.find('+')
            msec = ".000"
            if pos > 0:
                start = start[0:pos] + msec + "Z"
            else:
                raise Exception("unexpected start datetime format: no +: '%s'" % start)
            print(("## START:%s" % start))
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start.split("T")[0])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start.split("T")[1].split('.')[0] + msec)

            #
            pos = stop.find('+')
            msec = ".000"
            if pos > 0:
                stop = stop[0:pos] + msec + "Z"
            else:
                raise Exception("unexpected stop datetime format: no +: '%s'" % stop)
            print(("## stop:%s" % stop))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split("T")[0])
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split("T")[1].split('.')[0] + msec)
        #os._exit(1)
        else:
            # like: 2021-03-14T07:08:03.311795Z
            start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
            pos = start.find('.')
            msec = ".000"
            if pos > 0:
                start = start[0:pos + 4] + "Z"
                msec = "." + start[pos + 1: pos + 4]
            else:
                raise Exception("unexpected start datetime format: no .: '%s'" % start)
            print(("## START:%s" % start))
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start.split("T")[0])
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, start.split("T")[1].split('.')[0] + msec)

            #
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, start)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, start.split("T")[0])
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, start.split("T")[1].split('.')[0] + msec)

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # addLocalAttribute
        self.metadata.addLocalAttribute("originalName", self.productFolderName)

        # cloud coverage
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE)
        if self.metadata.valueExists(tmp):
            tmp = int(float(tmp) * 100.0)
            print(("METADATA_CLOUD_COVERAGE ok: %s" % tmp))
        else:
            processInfo.logger.warning("METADATA_CLOUD_COVERAGE not present. Setting metadata value to -1 as per EOSIP spec")
            tmp = -1
        self.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, tmp)

        # product version
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_VERSION)
        if self.metadata.valueExists(tmp):
            tmp = tmp.replace('.', '')
            if len(tmp) != 3:
                raise Exception("METADATA_SOFTWARE_VERSION as str: '%s' is not 3 digit length" % tmp)
            else:
                tmp = '%s0' % tmp
                print(("METADATA_SOFTWARE_VERSION as str: '%s'" % tmp))
        else:
            raise Exception("METADATA_SOFTWARE_VERSION not present")
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, tmp)

        # REF_sensorSpecificName
        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
        if tmp not in REF_sensorSpecificName:
            raise Exception("invalid METADATA_INSTRUMENT: '%s'" % tmp)

        ## instrument in spec is translated into PlanetScope Camera
        # set local attribute to instrument
        self.metadata.addLocalAttribute("sensorSpecificName", tmp)
        # set instrument to 'PlanetScope Camera' fixed
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT, 'PlanetScope Camera')

        # Two decimal places for following metadata values
        meta_tags_2dp = (
            metadata.METADATA_SUN_AZIMUTH,  # eop:illuminationAzimuthAngle
            metadata.METADATA_SUN_ELEVATION,  # eop:illuminationElevationAngle
            metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE  # eop:incidenceAngle
        )
        for met_tag in meta_tags_2dp:
            self.metadata.setMetadataPair(
                met_tag, format(float(self.metadata.getMetadataValue(met_tag)), '.2f')
            )

        if self.old_product_type_from_obsolete_native() == 'PSC_DEF_OT':
            self.metadata.addLocalAttribute(
                "tileId", self.metadata.getMetadataValue('tileId')
            )

    def product_type_from_obsolete_native(self):
        """Determine the new product type of an obsolete native product"""
        from copy import deepcopy

        # ###################### #
        # New code in this section
        # ###################### #
        poss_types = deepcopy(OBSOLETE_TO_NEW_TYPECODE_REQS)
        if self.metadata_content['properties']['item_type'] == 'PSOrthoTile':
            return 'PSC_4OT_3A'
        del poss_types['PSC_4OT_3A']

        asset_dirs = []
        for asset in os.listdir(self.EO_FOLDER):
            full_path = os.sep.join([self.EO_FOLDER, asset])
            if os.path.isdir(full_path):
                if len(os.listdir(full_path)) > 0:
                    asset_dirs.append(asset)

        # Filter possible types based on native product's assets
        for prod_type, requirements in OBSOLETE_TO_NEW_TYPECODE_REQS.items():
            req_assets = requirements['assets']

            all_reqd_assets_present = all(
                any(
                    [fnmatch.fnmatch(existing_asset, req_asset) for existing_asset in asset_dirs]
                )
                for req_asset in req_assets
            )
            if not all_reqd_assets_present:
                del poss_types[prod_type]

        prod_levels_present, prod_nbands_present = [], []
        for prod_type, requirements in OBSOLETE_TO_NEW_TYPECODE_REQS.items():
            if prod_type not in poss_types:
                continue

            assets_present = requirements['assets']
            for asset in assets_present:
                full_path = os.sep.join([self.EO_FOLDER, asset])
                if asset.endswith('_xml'):
                    xml_filename = [
                        f for f in os.listdir(full_path) if f.lower().endswith('.xml')
                    ][0]
                    xml_file = os.sep.join([full_path, xml_filename])
                    prod_levels_present.append(self.get_product_level_from_xml_file(xml_file))
                    prod_nbands_present.append(self.get_nbands_from_xml_file(xml_file))

            if not requirements['bands'] in prod_nbands_present or not any([level in prod_levels_present for level in requirements['levels']]):
                del poss_types[prod_type]

        for product_type in TYPECODES_IN_ORDER_OF_IMPORTANCE:
            if product_type in poss_types:
                return product_type
        # ###################### #

        xml_files = []
        asset_dirs = []
        for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):
            if root == self.EO_FOLDER:
                asset_dirs += dirs
            elif root.endswith('_xml'):
                xml_files += [root + os.sep + f for f in files if f.endswith('.xml') and not f.startswith('.')]

        prod_info = {
            Path(f).parent.name.replace('_xml', ''): {
                'n_bands': self.get_nbands_from_xml_file(f),
                'prod_level': self.get_product_level_from_xml_file(f)
            }
            for f in xml_files
        }
        max_n_bands = max([p['n_bands'] for p in prod_info.values()])
        prod_level_order = {'L3B': 1, 'L3A': 2, 'L1B': 3, 'L1A': 4}
        best_prod_level = {v: k for k, v in prod_level_order.items()}[
            min(
                [prod_level_order[v['prod_level']] for v in prod_info.values() if v['n_bands'] == max_n_bands]
            )
        ]

        # First, filter possible new product types based on number of bands of the product
        poss_types = list(
            filter(
                lambda x: OBSOLETE_TO_NEW_TYPECODE_REQS[x]['bands'] == max_n_bands,
                OBSOLETE_TO_NEW_TYPECODE_REQS
            )
        )

        # Some PSOrthoTile products have max_n_bands == 5, which results in no possible product types, therefore add
        # the relevant type
        if self.metadata_content['properties']['item_type'] == 'PSOrthoTile' and 'PSC_4OT_3A' not in poss_types:
            poss_types.append('PSC_4OT_3A')

        # Second, filter possible new product types based on presence of sub-folders ('assets') in native product and
        # processing level of native products
        poss_types = [
            t for t in poss_types
            if (
                all(
                    any(fnmatch.fnmatch(_, req_asset) for _ in asset_dirs)
                    for req_asset in OBSOLETE_TO_NEW_TYPECODE_REQS[t]['assets']
                )
                or
                OBSOLETE_TO_NEW_TYPECODE_REQS[t]['assets'] == '*'
            )
            and
            best_prod_level in OBSOLETE_TO_NEW_TYPECODE_REQS[t]['levels']
        ]

        for product_type in TYPECODES_IN_ORDER_OF_IMPORTANCE:
            if product_type in poss_types:
                return product_type

    def old_product_type_from_obsolete_native(self):
        item_type = self.metadata_content['properties']['item_type']

        item_type_to_typecodes_mapping = {
            "PSOrthoTile": 'PSC_DEF_OT',
            "PSScene3Band": 'PSC_DEF_S3',
            "PSScene4Band": 'PSC_DEF_S4',
            "PSScene": None,
        }

        if item_type not in item_type_to_typecodes_mapping:
            return None

        # Determine new product type for old native products
        if item_type_to_typecodes_mapping.get(item_type) is not None:
            return item_type_to_typecodes_mapping[item_type]

    def determineTypeCode(self):
        """Determine the product typecode from the raw product folder's
        underscore-delimited suffix. If not found, determine the typecode from
        the raw product root directory's contents. Returns None if no valid
        typecode is found.

        Parameters
        ----------
        processInfo : ProcessInfo
            The process info object. NOT USED. Kept for backwards compatibility.

        Returns
        -------
        str or None
            The typecode if found, otherwise None.
        """
        # item_type = self.EO_FOLDER.split('_')[-1]
        item_type = self.metadata_content['properties']['item_type']

        item_type_to_typecodes_mapping = {
            "PSOrthoTile": 'PSC_DEF_OT',
            "PSScene3Band": 'PSC_DEF_S3',
            "PSScene4Band": 'PSC_DEF_S4',
            "PSScene": None,
        }

        if item_type not in item_type_to_typecodes_mapping:
            return None

        # Determine new product type for old native products
        if item_type_to_typecodes_mapping.get(item_type) is not None:
            return self.product_type_from_obsolete_native()
            # return item_type_to_typecodes_mapping[item_type]

        assets = [p.name for p in Path(self.EO_FOLDER).iterdir() if p.is_dir()]
        for typecode in TYPECODES_IN_ORDER_OF_IMPORTANCE:
            required_assets = TYPECODE_REQD_FOLDER_CONTENTS[typecode]
            if all(map(lambda req: req in assets, required_assets)) or required_assets == '*':
                return typecode


    def buildTypeCode(self, processInfo):
        # Get type code from folder name (suffix like: PSOrthoTile; PSScene4Band, PSScene3Band
        determined_typecode = self.determineTypeCode()

        if determined_typecode is None:
            assets = [p.name for p in Path(self.EO_FOLDER).iterdir() if p.is_dir()]
            raise Exception(
                "{} does not contain any of the required sets of assets, only: {}".format(
                    self.EO_FOLDER, ', '.join(assets)
                )
            )

        self.typecode = determined_typecode

        print(("Typecode: '%s'" % self.typecode))
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    def calculateMultiPolygonFootprint(self, processInfo, footprint):
        no_of_polygons = len(footprint)
        #keep a copy
        self.metadata.setMetadataPair("json-multipolygon-footprint", "%s" % footprint)
        self.metadata.setMetadataPair("no_of_polygons", "%s" % no_of_polygons)

        browseIm = BrowseImage()
        self.browseIm = browseIm

        tmp = ''
        polygon_list = []
        # loop through each polygon to get all coordinates
        for x in range(no_of_polygons):
            for n in range(len(footprint[x][0])):
                fpLen = len(footprint[x][0])
                print(("Footprint %s length is %s" % (x + 1, fpLen)))
                # testCoord = footprint[x][0][0]
                # print("testCoord in Footprint %s is %s" % (x+1,testCoord))
                testCoordFloat = footprint[x][0][0][1]
                print(("testCoordFloat in Footprint %s is %s" % (x + 1, testCoordFloat)))
                #os._exit(1)
                if len(tmp) > 0:
                    tmp += ' '
                tmp += "%s %s" % (footprint[x][0][n][1], footprint[x][0][n][0])
            print(("FOOTPRINT %s: %s" % (x + 1, tmp)))
        print(("FINAL FOOTPRINT: %s" % tmp))

        # calculate bounding box using all coordinates with browseIm
        footprint = tmp
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox(calculateCenter=False)
        browseIm.calculateCenterFromBoundingBox()
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.getBoundingBox())
        bBox = self.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)
        print(("FOOTPRINT: %s" % browseIm.getFootprint()))
        print(("BOUNDINGBOX: %s" % bBox))
        print(("CENTER: %s %s" % (browseIm.centerLat, browseIm.centerLon)))

        # Add first pair of coords as the 5th coords to the bounding box and save as footprint
        print("#############################################")
        firstPair = bBox.split(" ")[0:2]
        firstPair = " ".join(firstPair)
        fivePointFootprint = bBox + " " + firstPair
        print(("TEST Final: %s" % fivePointFootprint))
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, fivePointFootprint)
        footprint = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)

        print(("TEST Saved Final Footprint: %s" % footprint))
        browseIm.setFootprint(footprint)

    # print ("browseIm:%s" % browseIm.info())
    # print("#############################################")

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, processInfo):
        from eoSip_converter.utils.coordinates import GeodeticCoordinate, plot_eo_outline

        # keep a copy
        self.metadata.setMetadataPair("json-footprint",
                                      "%s" % self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        tmp = self.metadata.getMetadataValue(
            metadata.METADATA_FOOTPRINT)  # is a list because we get what is parsed: json. So we get str/int/float...
        print(("FOOTPRINT 0:%s type:%s; size=%s" % (tmp, type(tmp), len(tmp[0]))))
        footprint_size = len(tmp[0])

        shapeType = self.metadata.getMetadataValue(SHAPE)

        browseIm = BrowseImage()
        self.browseIm = browseIm

        if shapeType == "MultiPolygon":
            self.calculateMultiPolygonFootprint(processInfo, tmp)
            footprint = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
        else:
            if len(tmp[0]) == 5:
                pass
            tmp1 = ''
            for n in range(len(tmp[0])):
                if len(tmp1) > 0:
                    tmp1 += ' '
                tmp1 += "%s %s" % (tmp[0][n][1], tmp[0][n][0])
            print(("FOOTPRINT 1:%s" % (tmp1)))
            self.metadata.setMetadataPair("footprint_json_to_lat-lon", tmp1)
            self.metadata.setMetadataPair("footprint_json_num-pairs", len(tmp[0]))
            footprint = tmp1
        #self.metadata.setMetadataPair("first-footprint", footprint)

        # Re-order footprint so upper-left is first (ortho-rectified) or first on right if not ortho-rectified
        scene_center = GeodeticCoordinate(*[float(_) for _ in self.metadata.getMetadataValue('sceneCenter').split()][::-1])
        coords = [float(c.strip()) for c in footprint.split()]
        coords = [GeodeticCoordinate(coords[i * 2], coords[i * 2 + 1]) for i in range(len(coords) // 2 - 1)]

        def sort_function(origin, coord, azimuth=0.0, ccw: bool = True) -> float:
            from eoSip_converter.utils.coordinates import wrap_angle

            angle = wrap_angle(origin.bearing_to(coord) * (-1 if ccw else 1))
            angle = wrap_angle(angle + azimuth * (1 if ccw else -1))

            return angle

        # This sorts out the footprint coordinates CCW from first right in
        # flight direction if not ortho-rectified, or top-left otherwise
        azimuth = 0.0 if self.isOrthoRectified else float(self.metadata.getMetadataValue('azimuthAngle'))
        coords = sorted(coords, key=lambda c: sort_function(scene_center, c, azimuth, ccw=True))
        coords.append(coords[0])
        footprint=' '.join([f"{c.lat:.3f} {c.lon:.3f}" for c in coords])

        if len(tmp[0]) == 5:
            # 5 point footprint, normal case
            footprint = "%s %s %s %s %s %s %s %s %s %s" % (tmp[0][0][1], tmp[0][0][0],
                                                           tmp[0][1][1], tmp[0][1][0],
                                                           tmp[0][2][1], tmp[0][2][0],
                                                           tmp[0][3][1], tmp[0][3][0],
                                                           tmp[0][0][1], tmp[0][0][0],
                                                           )
            browseIm.setFootprint(footprint)
            # browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox()
        else:
            # n point footprint:
            # use as it is in footprint
            # get center from boundingbox
            #footprint = tmp1
            browseIm.setFootprint(footprint)
            browseIm.calculateBoondingBox(calculateCenter=False)
            browseIm.calculateCenterFromBoundingBox()


        self.metadata.setMetadataPair("not-4-points-footprint", footprint)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())

        bbox_str = ' '.join([format(float(_), '.3f') for _ in browseIm.getBoundingBox().split()])
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, bbox_str)
        self.metadata.addLocalAttribute("boundingBox", bbox_str)

        print(("FOOTPRINT: %s" % browseIm.getFootprint()))
        print(("BOUNDINGBOX: %s" % browseIm.getBoundingBox()))
        print(("CENTER: %s %s" % (browseIm.centerLat, browseIm.centerLon)))

        #os._exit(1)

        if self.debug != 0:
            print("browseIm:%s" % browseIm.info())
        if not browseIm.getIsCCW():
            # reverse
            if self.debug != 0:
                print("############### reverse the footprint; before:%s" % (footprint))
            browseIm.reverseFootprint()
            if self.debug != 0:
                print("###############             after;%s" % (browseIm.getFootprint()))
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        # Footprint lat/lon coordinates to 3 decimal places
        footprint_str = ' '.join([format(float(_), '.3f') for _ in self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT).split()])
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint_str)

        # Try/except blocks and calculateCenterFromBoundingBox added for Planetscope
        try:
            flat, flon = browseIm.calculateCenter()
        except:
            flat, flon = browseIm.calculateCenterFromBoundingBox()

        flat = float(flat)
        flon = float(flon)

        #
        self.metadata.setMetadataPair(
            metadata.METADATA_SCENE_CENTER, f"{flat:.3f} {flon:.3f}"
        )

        #
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

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)

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