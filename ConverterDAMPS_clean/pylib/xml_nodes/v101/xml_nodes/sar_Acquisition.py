from .sipMessageBuilder import SipMessageBuilder


class sar_Acquisition(SipMessageBuilder):
    this = ["<sar:Acquisition>"]

    REPRESENTATION = [
        "<eop:orbitNumber>@orbitNumber@</eop:orbitNumber>",
        "<eop:orbitDirection>@orbitDirection@</eop:orbitDirection>",
        "eop_wrsLongitudeGrid",
        "eop_wrsLatitudeGrid",
        "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>",
        "<sar:polarisationMode>@polarisationMode@</sar:polarisationMode>",
        "<sar:polarisationChannels>@polarisationChannels@</sar:polarisationChannels>",
        "<sar:antennaLookDirection>@antennaLookDirection@</sar:antennaLookDirection>",
        "<sar:minimumIncidenceAngle>@minimumIncidenceAngle@</sar:minimumIncidenceAngle>",
        "<sar:maximumIncidenceAngle>@maximumIncidenceAngle@</sar:maximumIncidenceAngle>",
        "<sar:incidenceAngleVariation>@incidenceAngleVariation@</sar:incidenceAngleVariation>",
        "<sar:dopplerFrequency uom=\"$$getValidValue('UNIT_FREQUENCE')$$\">@dopplerFrequency@</sar:dopplerFrequency>"
    ]

    OPTIONAL = [
        "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>"
    ]
