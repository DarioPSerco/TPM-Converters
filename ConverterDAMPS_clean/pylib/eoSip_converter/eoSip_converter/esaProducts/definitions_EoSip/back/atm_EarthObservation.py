from xml_nodes.sipMessageBuilder import SipMessageBuilder


class atm_EarthObservation(SipMessageBuilder):
    this = [
        "<atm:EarthObservation gml:id=\"@gmlId@_$$getNextCounter()$$\" xmlns:atm=\"http://www.opengis.net/atm/2.1\" xmlns:eop=\"http://www.opengis.net/eop/2.1\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</atm:EarthObservation>"]

    REPRESENTATION = [
        "om_phenomenonTime",
        "om_resultTime",
        "om_procedure",
        "om_observedProperty",
        "om_featureOfInterest",
        "om_result",
        "eop_metaDataProperty"
    ]
