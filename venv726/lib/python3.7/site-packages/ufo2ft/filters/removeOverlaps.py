from __future__ import print_function, division, absolute_import, unicode_literals

from ufo2ft.filters import BaseFilter
from enum import Enum

import logging


logger = logging.getLogger(__name__)


class RemoveOverlapsFilter(BaseFilter):
    class Backend(Enum):
        BOOLEAN_OPERATIONS = "booleanOperations"
        SKIA_PATHOPS = "pathops"

    # use booleanOperations by default, unless pathops specified as backend
    _kwargs = {"backend": Backend.BOOLEAN_OPERATIONS}

    def start(self):
        self.options.backend = self.Backend(self.options.backend)

        if self.options.backend is self.Backend.BOOLEAN_OPERATIONS:
            from booleanOperations import union, BooleanOperationsError

            self.union = union
            self.Error = BooleanOperationsError
            self.penGetter = "getPointPen"

            logger.debug("using booleanOperations as RemoveOverlapsFilter backend")
        elif self.options.backend is self.Backend.SKIA_PATHOPS:
            from pathops import union, PathOpsError

            self.union = union
            self.Error = PathOpsError
            self.penGetter = "getPen"

            logger.debug("using skia-pathops as RemoveOverlapsFilter backend")
        else:
            raise AssertionError(self.options.backend)

    def filter(self, glyph):
        if not len(glyph):
            return False

        contours = list(glyph)
        glyph.clearContours()
        pen = getattr(glyph, self.penGetter)()
        try:
            self.union(contours, pen)
        except self.Error:
            logger.error("Failed to remove overlaps for %s", glyph.name)
            raise
        return True
