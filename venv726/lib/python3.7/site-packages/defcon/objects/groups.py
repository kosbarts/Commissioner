from __future__ import absolute_import
import weakref
from defcon.objects.base import BaseDictObject
from defcon.tools.representations import kerningSide1GroupsRepresentationFactory, kerningSide2GroupsRepresentationFactory, glyphToKerningSide1GroupsRepresentationFactory, glyphToKerningSide2GroupsRepresentationFactory


class Groups(BaseDictObject):

    """
    This object contains all of the groups in a font.

    **This object posts the following notifications:**

    ===================
    Name
    ===================
    Groups.Changed
    Groups.BeginUndo
    Groups.EndUndo
    Groups.BeginRedo
    Groups.EndRedo
    Groups.GroupSet
    Groups.GroupDeleted
    Groups.Cleared
    Groups.Updated
    ===================

    This object behaves like a dict. The keys are group names and the
    values are lists of glyph names::

        {
            "myGroup" : ["a", "b"],
            "myOtherGroup" : ["a.alt", "g.alt"],
        }

    The API for interacting with the data is the same as a standard dict.
    For example, to get a list of all group names::

        groupNames = groups.keys()

    To get all groups including the glyph lists::

        for groupName, glyphList in groups.items():

    To get the glyph list for a particular group name::

        glyphList = groups["myGroup"]

    To set the glyph list for a particular group name::

        groups["myGroup"] = ["x", "y", "z"]

    And so on.

    **Note:** You should not modify the group list and expect the object to
    know about it. For example, this could cause your changes to be lost::

        glyphList = groups["myGroups"]
        glyphList.append("n")

    To make sure the change is noticed, reset the list into the object::

        glyphList = groups["myGroups"]
        glyphList.append("n")
        groups["myGroups"] = glyphList

    This may change in the future.
    """

    changeNotificationName = "Groups.Changed"
    beginUndoNotificationName = "Groups.BeginUndo"
    endUndoNotificationName = "Groups.EndUndo"
    beginRedoNotificationName = "Groups.BeginRedo"
    endRedoNotificationName = "Groups.EndRedo"
    setItemNotificationName = "Groups.GroupSet"
    deleteItemNotificationName = "Groups.GroupDeleted"
    clearNotificationName = "Groups.Cleared"
    updateNotificationName = "Groups.Updated"
    representationFactories = {
    "defcon.groups.kerningSide1Groups" : dict(
        factory=kerningSide1GroupsRepresentationFactory,
        destructiveNotifications=("Groups.Changed")
    ),
    "defcon.groups.kerningSide2Groups" : dict(
        factory=kerningSide2GroupsRepresentationFactory,
        destructiveNotifications=("Groups.Changed")
    ),
    "defcon.groups.kerningGlyphToSide1Group" : dict(
        factory=glyphToKerningSide1GroupsRepresentationFactory,
        destructiveNotifications=("Groups.Changed")
    ),
    "defcon.groups.kerningGlyphToSide2Group" : dict(
        factory=glyphToKerningSide2GroupsRepresentationFactory,
        destructiveNotifications=("Groups.Changed")
    ),
}

    def __init__(self, font=None):
        self._font = None
        if font is not None:
            self._font = weakref.ref(font)
        super(Groups, self).__init__()
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

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Groups, self).endSelfNotificationObservation()
        self._font = None


if __name__ == "__main__":
    import doctest
    doctest.testmod()
