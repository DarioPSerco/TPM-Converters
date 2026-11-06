from .sipMessageBuilder import SipMessageBuilder


class eop_wrsLatitudeGrid(SipMessageBuilder):
    this = []

    REPRESENTATION = [
        "<eop:wrsLatitudeGrid codeSpace=\"@codeSpace_wrsLatitudeGrid@\">@wrsLatitudeGrid@</eop:wrsLatitudeGrid>"]
