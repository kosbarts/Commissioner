from __future__ import absolute_import
import weakref
from fontTools.ufoLib.kerning import lookupKerningValue
from defcon.objects.base import BaseDictObject


class Kerning(BaseDictObject):

    """
    This object contains all of the kerning pairs in a font.

    **This object posts the following notifications:**

    ===================
    Name
    ===================
    Kerning.Changed
    Kerning.BeginUndo
    Kerning.EndUndo
    Kerning.BeginRedo
    Kerning.EndRedo
    Kerning.PairSet
    Kerning.PairDeleted
    Kerning.Cleared
    Kerning.Updated
    ====================

    This object behaves like a dict. For example, to get a list of all kerning pairs::

        pairs = kerning.keys()

    To get all pairs including the values::

        for (left, right), value in kerning.items():

    To get the value for a particular pair::

        value = kerning["a", "b"]

    To set the value for a particular pair::

        kerning["a", "b"] = 100

    And so on.

    **Note:** This object is not very smart in the way it handles zero values,
    exceptions, etc. This may change in the future.
    """

    changeNotificationName = "Kerning.Changed"
    beginUndoNotificationName = "Kerning.BeginUndo"
    endUndoNotificationName = "Kerning.EndUndo"
    beginRedoNotificationName = "Kerning.BeginRedo"
    endRedoNotificationName = "Kerning.EndRedo"
    setItemNotificationName = "Kerning.PairSet"
    deleteItemNotificationName = "Kerning.PairDeleted"
    clearNotificationName = "Kerning.Cleared"
    updateNotificationName = "Kerning.Updated"
    representationFactories = {}

    def __init__(self, font=None):
        self._font = None
        if font is not None:
            self._font = weakref.ref(font)
        super(Kerning, self).__init__()
        self.beginSelfNotificationObservation()

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        return self.font

    def _get_font(self):
        if self._font is not None:
            return self._font()
        return None

    font = property(_get_font, doc="The :class:`Font` that this object belongs to.")

    # -------------
    # Pair Handling
    # -------------

    def get(self, pair, default=0):
        return super(Kerning, self).get(pair, default)

    def find(self, pair, default=0):
        """
        This will find the value for **pair** even if
        **pair** is not specifically defined. For example:
        You have a group named `public.kern1.A` with
        the contents `["A", "Aacute"]` and you have a
        group named `public.kern2.C` with the contents
        `["C", "Ccedilla"]`. The only defined kerning is
        `("public.kern1.A", public.kern2.C) = 100`.
        If you use this method to find the value for
        `("A", "Ccedilla")` you will get `100`.
        """
        from defcon.errors import DefconError
        font = self.font
        if font is None:
            raise DefconError("The find method requires a parent font.")
        glyphToFirstGroup = font.groups.getRepresentation("defcon.groups.kerningGlyphToSide1Group")
        glyphToSecondGroup = font.groups.getRepresentation("defcon.groups.kerningGlyphToSide2Group")
        return lookupKerningValue(pair, self, font.groups, fallback=default, glyphToFirstGroup=glyphToFirstGroup, glyphToSecondGroup=glyphToSecondGroup)

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Kerning, self).endSelfNotificationObservation()
        self._font = None


if __name__ == "__main__":
    import doctest
    doctest.testmod()
