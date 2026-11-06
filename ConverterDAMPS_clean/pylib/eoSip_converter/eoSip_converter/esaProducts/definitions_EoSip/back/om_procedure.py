from xml_nodes.sipMessageBuilder import SipMessageBuilder


class om_procedure(SipMessageBuilder):
    this = ["<om:procedure>"]

    REPRESENTATION = ["eop_EarthObservationEquipment"]

    # REPRESENTATION_ALT = ["alt_EarthObservationEquipment"]

    REPRESENTATION_OPT = ["opt_EarthObservationEquipment"]

    # REPRESENTATION_ATM = ["atm_EarthObservationEquipment"]
