from xml_nodes.sipMessageBuilder import SipMessageBuilder


class om_resultTime(SipMessageBuilder):
    this = ["<om:resultTime>"]

    REPRESENTATION = ["gml_TimeInstant"]
