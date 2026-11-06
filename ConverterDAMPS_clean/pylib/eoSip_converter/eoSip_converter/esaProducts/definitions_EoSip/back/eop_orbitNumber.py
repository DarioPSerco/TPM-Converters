from xml_nodes.sipMessageBuilder import SipMessageBuilder


class eop_orbitNumber(SipMessageBuilder):
    this = []

    REPRESENTATION = ["<eop:orbitNumber>@orbitNumber@</eop:orbitNumber>"]
