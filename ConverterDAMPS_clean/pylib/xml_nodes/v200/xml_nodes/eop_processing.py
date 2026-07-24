from .sipMessageBuilder import SipMessageBuilder


class eop_processing(SipMessageBuilder):
    this = ["<eop:processing>"]

    REPRESENTATION = ["eop_ProcessingInformation"]
