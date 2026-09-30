from pathlib import Path

__version__ = '1.1.0'

VERSION_CHANGES = {
    '1.0.0': 'First record',
    '1.1.0': 'Addition of utils/coordinates.py module. Reduced unnecessary log messages from pyvips/PIL modules.',
}

CONVERTER_DIR = Path(__file__).resolve().parent
ADDON_DIR = CONVERTER_DIR / 'addon_converter'
ADDON_APPS_DIR = ADDON_DIR / 'libs'

STRETCH_APP = ADDON_APPS_DIR / 'stretchApp.jar'
