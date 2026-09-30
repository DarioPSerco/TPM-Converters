# from eoSip_converter.esaProducts.definitions_EoSip.sipMessageBuilder import SipMessageBuilder
from .sipMessageBuilder import SipMessageBuilder


class gin_EarthObservation(SipMessageBuilder):
    this = [
        "<gin:EarthObservation gml:id=\"@gmlId@_$$getNextCounter()$$\" xmlns:eop=\"http://www.opengis.net/eop/2.1\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:gin=\"http://www.esa.int/gin/1.0\"  xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</gin:EarthObservation>"]

    REPRESENTATION = [
        "om_phenomenonTime",
        "om_resultTime",
        "om_procedure",
        "om_observedProperty",
        "om_featureOfInterest",
        "om_result",
        "eop_metaDataProperty"
    ]
