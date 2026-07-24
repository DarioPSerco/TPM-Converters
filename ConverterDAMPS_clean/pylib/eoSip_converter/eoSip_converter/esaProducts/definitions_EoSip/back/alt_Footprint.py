from xml_nodes.sipMessageBuilder import SipMessageBuilder


class alt_Footprint(SipMessageBuilder):
    this = ["<alt:Footprint gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</alt:Footprint>"]

    REPRESENTATION = ["<eop:multiExtentOf></eop:multiExtentOf>",
                      "<alt:nominalTrack>",
                      "<gml:MultiCurve gml:id=\"@gmlId@_$$getNextCounter()$$\">",
                      "gml_curveMember",
                      "</gml:MultiCurve >",
                      "</alt:nominalTrack>"]
