from __future__ import absolute_import


class Point(object):

    """
    This object represents a single point.
    """

    __slots__ = ["_x", "_y", "_segmentType", "_smooth", "_name", "_identifier"]

    def __init__(self, coordinates, segmentType=None, smooth=False, name=None, identifier=None):
        (x, y) = coordinates
        super(Point, self).__init__()
        self._x = x
        self._y = y
        self._segmentType = segmentType
        self._smooth = smooth
        self._name = name
        self._identifier = identifier

    def __repr__(self):
        return "<%s position: (%s, %s) type: %s smooth: %s name: %s identifier: %s>" % (self.__class__.__name__, self.x, self.y, str(self.segmentType), str(self.smooth), str(self.name), str(self.identifier))

    def _get_segmentType(self):
        return self._segmentType

    def _set_segmentType(self, value):
        self._segmentType = value

    segmentType = property(_get_segmentType, _set_segmentType, doc="The segment type. The positibilies are *move*, *line*, *curve*, *qcurve* and *None* (indicating that this is an off-curve point).")

    def _get_x(self):
        return self._x

    def _set_x(self, value):
        self._x = value

    x = property(_get_x, _set_x, doc="The x coordinate.")

    def _get_y(self):
        return self._y

    def _set_y(self, value):
        self._y = value

    y = property(_get_y, _set_y, doc="The y coordinate.")

    def _get_smooth(self):
        return self._smooth

    def _set_smooth(self, value):
        self._smooth = value

    smooth = property(_get_smooth, _set_smooth, doc="A boolean indicating the smooth state of the point.")

    def _get_name(self):
        return self._name

    def _set_name(self, value):
        self._name = value

    name = property(_get_name, _set_name, doc="An arbitrary name for the point.")

    def move(self, values):
        """
        Move the component by **(x, y)**.
        """
        (x, y) = values
        self.x += x
        self.y += y

    # ----------
    # Identifier
    # ----------

    def _get_identifier(self):
        return self._identifier

    def _set_identifier(self, value):
        # don't allow overwritting an existing identifier
        if self._identifier is not None:
            return
        self._identifier = value

    identifier = property(_get_identifier, _set_identifier, doc="The identifier.")


if __name__ == "__main__":
    import doctest
    doctest.testmod()
