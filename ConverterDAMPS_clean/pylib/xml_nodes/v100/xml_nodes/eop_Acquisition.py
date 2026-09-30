from .sipMessageBuilder import SipMessageBuilder


class eop_Acquisition(SipMessageBuilder):
    this = ["<eop:Acquisition>"]

    REPRESENTATION = [
        # "<eop:orbitNumber>@orbitNumber@</eop:orbitNumber>",
        "eop_orbitNumber",
        "<eop:lastOrbitNumber>@lastOrbitNumber@</eop:lastOrbitNumber>",
        "<eop:orbitDirection>@orbitDirection@</eop:orbitDirection>",
        "eop_wrsLongitudeGrid",
        "eop_wrsLatitudeGrid",
        "<eop:ascendingNodeDate>@ascendingNodedate@</eop:ascendingNodeDate>",
        "<eop:ascendingNodeLongitude uom=\"$$getValidValue('UNIT_ANGLE')$$\">@ascendingNodeLongitude@</eop:ascendingNodeLongitude>",
        "<eop:startTimeFromAscendingNode>@startTimeFromAscendingNode@</eop:startTimeFromAscendingNode>",
        "<eop:completionTimeFromAscendingNode>@completionTimeFromAscendingNode@</eop:completionTimeFromAscendingNode>",
        "<eop:illuminationAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationAzimuthAngle@</eop:illuminationAzimuthAngle>",
        "<eop:illuminationZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationZenithAngle@</eop:illuminationZenithAngle>",
        "<eop:illuminationElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationElevationAngle@</eop:illuminationElevationAngle>",
        "<eop:instrumentAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentAzimuthAngle@</eop:instrumentAzimuthAngle>",
        "<eop:instrumentZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentZenithAngle@</eop:instrumentZenithAngle>",
        "<eop:instrumentElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentElevationAngle@</eop:instrumentElevationAngle>",
        "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>",
        "<eop:acrossTrackIncidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@acrossTrackIncidenceAngle@</eop:acrossTrackIncidenceAngle>",
        "<eop:alongTrackIncidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@alongTrackIncidenceAngle@</eop:alongTrackIncidenceAngle>",
        "<eop:pitch uom=\"$$getValidValue('UNIT_ANGLE')$$\">@pitch@</eop:pitch>",
        "<eop:roll uom=\"$$getValidValue('UNIT_ANGLE')$$\">@roll@</eop:roll>",
        "<eop:yaw uom=\"$$getValidValue('UNIT_ANGLE')$$\">@yaw@</eop:yaw>"]

    OPTIONAL = [
        "<eop:lastOrbitNumber>@lastOrbitNumber@</eop:lastOrbitNumber>",
        "eop_wrsLongitudeGrid",
        "eop_wrsLatitudeGrid",
        "<eop:ascendingNodeDate>@ascendingNodedate@</eop:ascendingNodeDate>",
        "<eop:ascendingNodeLongitude>@ascendingNodeLongitude@</eop:ascendingNodeLongitude>",
        "<eop:startTimeFromAscendingNode>@startTimeFromAscendingNode@</eop:startTimeFromAscendingNode>",
        "<eop:completionTimeFromAscendingNode>@completionTimeFromAscendingNode@</eop:completionTimeFromAscendingNode>",
        "<eop:illuminationAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationAzimuthAngle@</eop:illuminationAzimuthAngle>",
        "<eop:illuminationZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationZenithAngle@</eop:illuminationZenithAngle>",
        "<eop:illuminationElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationElevationAngle@</eop:illuminationElevationAngle>",
        "<eop:instrumentAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentAzimuthAngle@</eop:instrumentAzimuthAngle>",
        "<eop:instrumentZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentZenithAngle@</eop:instrumentZenithAngle>",
        "<eop:instrumentElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentElevationAngle@</eop:instrumentElevationAngle>",
        "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>",
        "<eop:alongTrackIncidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@alongTrackIncidenceAngle@</eop:alongTrackIncidenceAngle>",
        "<eop:acrossTrackIncidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@acrossTrackIncidenceAngle@</eop:acrossTrackIncidenceAngle>",
        "<eop:pitch uom=\"$$getValidValue('UNIT_ANGLE')$$\">@pitch@</eop:pitch>",
        "<eop:roll uom=\"$$getValidValue('UNIT_ANGLE')$$\">@roll@</eop:roll>",
        "<eop:yaw uom=\"$$getValidValue('UNIT_ANGLE')$$\">@yaw@</eop:yaw>"]
