from xml_nodes.sipMessageBuilder import SipMessageBuilder


class alt_Acquisition(SipMessageBuilder):
    this = ["<alt:Acquisition>"]

    REPRESENTATION = [
        "<eop:orbitNumber>@orbitNumber@</eop:orbitNumber>",
        "<eop:lastOrbitNumber>@lastOrbitNumber@</eop:lastOrbitNumber>",
        "<eop:orbitDirection>@orbitDirection@</eop:orbitDirection>",
        "<eop:wrsLongitudeGrid codeSpace=\"\">@wrsLongitudeGrid@</eop:wrsLongitudeGrid>",
        "<eop:wrsLatitudeGrid codeSpace=\"\">@wrsLatitudeGrid@</eop:wrsLatitudeGrid>",
        "<eop:ascendingNodeDate>@ascendingNodedate@</eop:ascendingNodeDate>",
        "<eop:ascendingNodeLongitude uom=\"$$getValidValue('UNIT_ANGLE')$$\">@ascendingNodeLongitude@</eop:ascendingNodeLongitude>",
        "<eop:startTimeFromAscendingNode uom=\"$$getValidValue('UNIT_MSEC')$$\">@startTimeFromAscendingNode@</eop:startTimeFromAscendingNode>",
        "<eop:completionTimeFromAscendingNode uom=\"$$getValidValue('UNIT_MSEC')$$\">@completionTimeFromAscendingNode@</eop:completionTimeFromAscendingNode>",

        "<eop:illuminationAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationAzimuthAngle@</eop:illuminationAzimuthAngle>",
        "<eop:illuminationZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationZenithAngle@</eop:illuminationZenithAngle>",
        "<eop:illuminationElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationElevationAngle@</eop:illuminationElevationAngle>",
        "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>",
        "<eop:instrumentZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentZenithAngle@</eop:instrumentZenithAngle>",
        "<eop:instrumentElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentElevationAngle@</eop:instrumentElevationAngle>",
        "<alt:cycleNumber>@cycleNumber@</alt:cycleNumber>",
        "<alt:isSegment>@isSegment@</alt:isSegment>",
        "<alt:relativePassNumber>@relativePassNumber@</alt:relativePassNumber>"]

    OPTIONAL = ["<eop:lastOrbitNumber>@lastOrbitNumber@</eop:lastOrbitNumber>",
                "<eop:wrsLongitudeGrid codeSpace=\"\">@wrsLongitudeGrid@</eop:wrsLongitudeGrid>",
                "<eop:wrsLatitudeGrid codeSpace=\"\">@wrsLatitudeGrid@</eop:wrsLatitudeGrid>",
                "<eop:ascendingNodeDate>@ascendingNodedate@</eop:ascendingNodeDate>",
                "<eop:ascendingNodeLongitude uom=\"$$getValidValue('UNIT_ANGLE')$$\">@ascendingNodeLongitude@</eop:ascendingNodeLongitude>",
                "<eop:startTimeFromAscendingNode uom=\"$$getValidValue('UNIT_MSEC')$$\">@startTimeFromAscendingNode@</eop:startTimeFromAscendingNode>",
                "<eop:completionTimeFromAscendingNode uom=\"$$getValidValue('UNIT_MSEC')$$\">@completionTimeFromAscendingNode@</eop:completionTimeFromAscendingNode>",

                "<eop:illuminationAzimuthAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationAzimuthAngle@</eop:illuminationAzimuthAngle>",
                "<eop:illuminationZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationZenithAngle@</eop:illuminationZenithAngle>",
                "<eop:illuminationElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@illuminationElevationAngle@</eop:illuminationElevationAngle>",
                "<eop:incidenceAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@incidenceAngle@</eop:incidenceAngle>",
                "<eop:instrumentZenithAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentZenithAngle@</eop:instrumentZenithAngle>",
                "<eop:instrumentElevationAngle uom=\"$$getValidValue('UNIT_ANGLE')$$\">@instrumentElevationAngle@</eop:instrumentElevationAngle>",
                "<alt:cycleNumber>@cycleNumber@</alt:cycleNumber>",
                "<alt:isSegment>@isSegment@</alt:isSegment>",
                "<alt:relativePassNumber>@relativePassNumber@</alt:relativePassNumber>"]
