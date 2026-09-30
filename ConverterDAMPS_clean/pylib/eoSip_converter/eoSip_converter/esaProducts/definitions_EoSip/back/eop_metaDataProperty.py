from xml_nodes.sipMessageBuilder import SipMessageBuilder


class eop_metaDataProperty(SipMessageBuilder):
    this = ["<eop:metaDataProperty>", "</eop:metaDataProperty>"]

    REPRESENTATION = ["eop_EarthObservationMetaData"]

    # REPRESENTATION_ATM = ["atm_EarthObservationMetaData"]
