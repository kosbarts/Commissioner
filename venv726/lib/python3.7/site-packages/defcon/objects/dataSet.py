from __future__ import absolute_import
import os
import weakref
from fontTools.ufoLib import UFOReader, UFOLibError
from defcon.objects.base import BaseObject


class DataSet(BaseObject):

    """
    This object manages all contents of the data directory in the font.

    **This object posts the following notifications:**

    ===============
    Name
    ===============
    DataSet.Changed
    ===============

    """

    changeNotificationName = "DataSet.Changed"
    representationFactories = {}

    def __init__(self, font=None):
        self._font = None
        if font is not None:
            self._font = weakref.ref(font)
        super(DataSet, self).__init__()
        self.beginSelfNotificationObservation()
        self._data = {}
        self._scheduledForDeletion = {}

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

    # ----------
    # File Names
    # ----------

    def _get_fileNames(self):
        return list(self._data.keys())

    def _set_fileNames(self, fileNames):
        assert not self._data
        for fileName in fileNames:
            self._data[fileName] = _dataDict()

    fileNames = property(_get_fileNames, _set_fileNames, doc="A list of all file names. This should not be set externally.")

    # -------------
    # Dict Behavior
    # -------------

    def __getitem__(self, fileName):
        if self._data[fileName]["data"] is None:
            path = self.font.path
            reader = UFOReader(path, validate=False)
            path = "%s/%s" % ("data", fileName)
            data = reader.readBytesFromPath(path)
            onDiskModTime = reader.getFileModificationTime(path)
            self._data[fileName] = _dataDict(data=data, onDisk=True, onDiskModTime=onDiskModTime)
        return self._data[fileName]["data"]

    def __setitem__(self, fileName, data):
        assert data is not None
        onDisk = False
        onDiskModTime = None
        if fileName in self._scheduledForDeletion:
            assert fileName not in self._data
            self._data[fileName] = self._scheduledForDeletion.pop(fileName)
        if fileName in self._data:
            n = self[fileName] # force it to load so that the stamping is correct
            onDisk = self._data[fileName]["onDisk"]
            onDiskModTime = self._data[fileName]["onDiskModTime"]
            del self._data[fileName] # now remove it
        self._data[fileName] = _dataDict(data=data, dirty=True, onDisk=onDisk, onDiskModTime=onDiskModTime)
        self.dirty = True

    def __delitem__(self, fileName):
        n = self[fileName] # force it to load so that the stamping is correct]
        self._scheduledForDeletion[fileName] = dict(self._data.pop(fileName))
        self.dirty = True

    # ----
    # Save
    # ----

    def getSaveProgressBarTickCount(self, formatVersion):
        """
        Get the number of ticks that will be used by a progress bar
        in the save method. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        return 0

    def save(self, writer, saveAs=False, progressBar=None):
        """
        Save data. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        if saveAs:
            font = self.font
            if font is not None and font.path is not None and os.path.exists(font.path):
                reader = UFOReader(font.path, validate=False)
                readerDataDirectoryListing = reader.getDataDirectoryListing()
                for fileName, data in self._data.items():
                    path = "%s/%s" % ("data", fileName)
                    if data["data"] is not None or fileName not in readerDataDirectoryListing:
                        continue
                    writer.copyFromReader(reader, path, path)
        for fileName in self._scheduledForDeletion:
            # instead of trying to maintain a list of in UFO
            # vs. in memory, simply skip and move on when
            # something can't be deleted because it isn't
            # in the UFO.
            writer.removePath("%s/%s" % ("data", fileName), force=True)
        self._scheduledForDeletion.clear()
        for fileName, data in self._data.items():
            if not data["dirty"]:
                continue
            writer.writeBytesToPath("%s/%s" % ("data", fileName), data["data"])
            data["dirty"] = False
            data["onDisk"] = True
            data["onDiskModTime"] = writer.getFileModificationTime("%s/%s" % ("data", fileName))
        self.dirty = False

    # ---------------------
    # External Edit Support
    # ---------------------

    def testForExternalChanges(self, reader):
        """
        Test for external changes. This should not be called externally.
        """
        filesOnDisk = reader.getDataDirectoryListing()
        modified = []
        added = []
        deleted = []
        for fileName in set(filesOnDisk) - set(self.fileNames):
            if fileName not in self._scheduledForDeletion:
                added.append(fileName)
            elif not self._scheduledForDeletion[fileName]["onDisk"]:
                added.append(fileName)
            elif self._scheduledForDeletion[fileName]["onDiskModTime"] != reader.getFileModificationTime(
                "%s/%s" % ("data", fileName)
            ):
                added.append(fileName)
        for fileName, data in self._data.items():
            # file on disk and has been loaded
            if fileName in filesOnDisk and data["data"] is not None:
                path = "%s/%s" % ("data", fileName)
                newModTime = reader.getFileModificationTime(path)
                if newModTime != data["onDiskModTime"]:
                    newData = reader.readBytesFromPath(path)
                    if newData != data["data"]:
                        modified.append(fileName)
                continue
            # file removed
            if fileName not in filesOnDisk and data["onDisk"]:
                deleted.append(fileName)
                continue
        return modified, added, deleted

    def reloadData(self, fileNames):
        """
        Reload specified data. This should not be called externally.
        """
        for fileName in fileNames:
            self._data[fileName] = _dataDict()
            data = self[fileName]

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(DataSet, self).endSelfNotificationObservation()
        self._font = None

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        simple_get = lambda key: self[key]

        getters = []
        for k in self.fileNames:
            getters.append((k, simple_get))

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        self._data = {}
        self._scheduledForDeletion = {}
        for k in data:
            self[k] = data[k]


def _dataDict(data=None, dirty=False, onDisk=True, onDiskModTime=None):
    return dict(data=data, dirty=dirty, onDisk=onDisk, onDiskModTime=onDiskModTime)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
