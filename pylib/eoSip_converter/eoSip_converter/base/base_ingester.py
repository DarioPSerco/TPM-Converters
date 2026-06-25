"""
Base_Ingester is a base class, because the Ingester class was becoming
too big

For Esa/lite dissemination project

Serco 03/2016
Lavaux Gilles

08/06/2016: V: 0.5
"""

import os
import time
from abc import ABC
from typing import Tuple, Type

from .processInfo import processInfo
from ..esaProducts import base_metadata
from ..esaProducts import formatUtils
from ..esaProducts import metadata

GENERATION_TIME_PATTERN = '%Y-%m-%dT%H:%M:%SZ'
DEBUG = 0


class Base_Ingester(ABC):
    def __init__(self):
        self.generationTime = None
        # DEBUG
        self.debug = DEBUG

    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    def getDebug(self) -> int:
        return self.debug

    def getGenerationTime(self, metadata_: Type[base_metadata.Base_Metadata]):
        """generation time: now or a preset value"""
        # if not already set, set it to now
        tmp = metadata_.getMetadataValue(metadata.METADATA_GENERATION_TIME)
        if tmp == base_metadata.VALUE_NOT_PRESENT:
            tmp = time.strftime(GENERATION_TIME_PATTERN)
            metadata_.setMetadataPair(metadata.METADATA_GENERATION_TIME, tmp)
            if self.debug != 0:
                print("METADATA_GENERATION_TIME set to:'%s'" % tmp)
        else:
            if self.debug != 0:
                print("METADATA_GENERATION_TIME already preset:'%s'" % tmp)

        self.generationTime = int(time.mktime(formatUtils.timeFromDatePatterm(tmp).timetuple()))

        if self.debug != 0:
            print("self.generationTime:'%s' type:%s" % (self.generationTime, type(self.generationTime)))

    def checkDestinationAlreadyExists(self, aProcessInfo: Type[processInfo]) -> Tuple[bool, int, str]:
        """Check if the product already exists at destination
        needed to handle duplicate

        if can not handle duplicate case: return False and -1
        if it can, increase the filecounter"""
        if self.debug != 0:
            print("checkDestinationAlreadyExists; aProcessInfo=%s" % aProcessInfo)
        if not aProcessInfo.ingester.want_duplicate:
            # just test if destination exists
            firstPath = aProcessInfo.ingester.outputProductResolvedPaths[0]
            finalPath = "%s%s" % (firstPath, aProcessInfo.destProduct.sipPackageName)
            if self.debug != 0:
                print(" ## checkDestinationAlreadyExists; finalPath=%s" % finalPath)
            exists = os.path.exists(finalPath)
            return exists, -1, finalPath
        else:
            # check if destination exist, + get next counter if needed and < 10
            firstPath = aProcessInfo.ingester.outputProductResolvedPaths[0]
            finalPath = "%s%s" % (firstPath, aProcessInfo.destProduct.sipPackageName)
            if self.debug != 0:
                print(" checkDestinationAlreadyExists; finalPath=%s" % finalPath)
            if not aProcessInfo.ingester.can_autocorrect_filecounter:
                if self.debug != 0:
                    print(" checkDestinationAlreadyExists: return because can not correct duplicate case")
                return False, -1, finalPath

            exists = os.path.exists(finalPath)
            n = 1
            if exists:
                # this method is called only if product_overwrite is False
                if self.debug != 0:
                    print(" checkDestinationAlreadyExists: finalPath exists, can autocorrect filecounter:%s" % aProcessInfo.ingester.can_autocorrect_filecounter)
                    print(" checkDestinationAlreadyExists: overwrite==false: need to increase METADATA_FILECOUNTER")
                tmp = aProcessInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
                if self.debug != 0:
                    print(" checkDestinationAlreadyExists: METADATA_FILECOUNTER=%s" % tmp)
                if tmp is None or tmp == base_metadata.VALUE_NOT_PRESENT:
                    if self.debug != 0:
                        print(" case 1")
                    # assume is 1
                    n = 2
                    if self.debug != 0:
                        print(" case 1: new n=%s" % n)
                else:
                    if self.debug != 0:
                        print(" case 2")
                    n = int(tmp) + 1
                    if self.debug != 0:
                        print(" case 2: new n=%s" % n)
                if n >= 10:
                    raise Exception("checkDestinationAlreadyExists: fileCounter reach limit of 10:'%s'" % n)
                if self.debug != 0:
                    print(" checkDestinationAlreadyExists: METADATA_FILECOUNTER is now:%s" % n)
            else:
                if self.debug != 0:
                    print(" checkDestinationAlreadyExists: finalPath doesn't exists")
            return exists, n, finalPath
