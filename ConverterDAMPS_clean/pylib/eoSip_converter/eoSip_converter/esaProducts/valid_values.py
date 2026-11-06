# -*- coding: cp1252 -*-

DESCENDING = "DESCENDING"
ASCENDING = "ASCENDING"

NAME_UNIT_ANGLE = 'UNIT_ANGLE'
NAME_UNIT_DISTANCE = 'UNIT_DISTANCE'
NAME_UNIT_FREQUENCE = 'UNIT_FREQUENCE'
NAME_UNIT_PERCENTAGE = 'UNIT_PERCENTAGE'
NAME_UNIT_SIZE = 'UNIT_SIZE'
NAME_UNIT_MSEC = 'UNIT_MSEC'

KNOWN_NAMES = [NAME_UNIT_ANGLE, NAME_UNIT_DISTANCE, NAME_UNIT_FREQUENCE, NAME_UNIT_PERCENTAGE, NAME_UNIT_SIZE,
               NAME_UNIT_MSEC]
DEFAULT_VALUES = {NAME_UNIT_ANGLE: 'deg', NAME_UNIT_DISTANCE: 'm', NAME_UNIT_FREQUENCE: 'Hz', NAME_UNIT_PERCENTAGE: '%',
                  NAME_UNIT_SIZE: 'bytes', NAME_UNIT_MSEC: 'ms'}

debug = 0


class Valid_Values:

    #
    #
    #
    def __init__(self):
        self.debug = debug
        self.knownNames = KNOWN_NAMES
        self.defaultsValues = DEFAULT_VALUES
        self.validValues = DEFAULT_VALUES.copy()
        if debug != 0:
            print(" init Valid_values done")

    #
    #
    #
    def hasKnownName(self, name):
        if debug != 0:
            print("#### Valid_values.hasKnownName: %s" % name)
        res = name in self.defaultsValues
        if debug != 0:
            print("#### Valid_values.hasKnownName: %s=%s" % (name, res))
        return res

    #
    # return the valid value for name
    #
    def getValidValue(self, name):
        if debug != 0:
            print("#### Valid_values.getValidValue: %s" % name)
        res = self.validValues[name]
        if debug != 0:
            print("#### Valid_values.getValidValue: %s=%s" % (name, res))
        return res

    #
    # set the valid value for name
    #
    def setValidValue(self, key, name):
        if debug != 0:
            print("#### Valid_values.setValidValue: %s=%s" % (key, name))
        self.validValues[key] = name

    #
    # return the default value for name
    #
    def getDefaultValue(self, name):
        return self.defaultsValues[name]
