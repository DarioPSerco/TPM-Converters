from .sipMessageBuilder import SipMessageBuilder


class eop_wrsLongitudeGrid(SipMessageBuilder):
    this = []

    REPRESENTATION = [
        "<eop:wrsLongitudeGrid codeSpace=\"@codeSpace_wrsLongitudeGrid@\">@wrsLongitudeGrid@</eop:wrsLongitudeGrid>"]
