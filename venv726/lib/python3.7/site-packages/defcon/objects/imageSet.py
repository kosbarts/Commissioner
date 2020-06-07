from __future__ import absolute_import
import os
import hashlib
import weakref
from defcon.objects.base import BaseObject
from fontTools.misc.py23 import unicode
from fontTools.ufoLib import UFOReader, UFOLibError
from fontTools.ufoLib.filenames import (
    userNameToFileName, illegalCharacters, reservedFileNames, maxFileNameLength
)
from fontTools.ufoLib.validators import pngSignature


class ImageSet(BaseObject):

    """
    This object manages all images in the font.

    **This object posts the following notifications:**

    ===========================
    Name
    ===========================
    ImageSet.Changed
    ImageSet.FileNamesChanged
    ImageSet.ImageChanged
    ImageSet.ImageWillBeAdded
    ImageSet.ImageAdded
    ImageSet.ImageWillBeDeleted
    ImageSet.ImageDeleted
    ===========================

    This object behaves like a dict. For example, to get the
    raw image data for a particular image::

        image = images["image file name"]

    To add an image, do this::

        images["image file name"] = rawImageData

    When setting an image, the provided file name must be a file
    system legal string. This will be checked by comparing the
    provided file name to the results of :py:meth:`ImageSet.makeFileName`.
    If the two don't match an error will be raised.

    Before setting an image, the :py:meth:`ImageSet.findDuplicateImage`
    method should be called. If a file name is retruend, the new image
    data should not be added. The UFO spec recommends (but doesn't require)
    that duplicate images be avoided. This will help with that.

    To remove an image from this object, and from the UFO during save,
    do this::

        del images["image file name"]
    """

    changeNotificationName = "ImageSet.Changed"
    representationFactories = {}

    def __init__(self, font=None):
        self._font = None
        if font is not None:
            self._font = weakref.ref(font)
        super(ImageSet, self).__init__()
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
        oldValue = list(self._data.keys())
        for fileName in fileNames:
            self._data[fileName] = _imageDict(onDisk=True)
        self.postNotification("ImageSet.FileNamesChanged", data=dict(oldValue=oldValue, newValue=fileNames))

    fileNames = property(_get_fileNames, _set_fileNames, doc="A list of all image file names. This should not be set externally.")

    def _get_unreferencedFileNames(self):
        font = self.font
        if font is None:
            return []
        unreferenced = set(self.fileNames)
        for layer in font.layers:
            unreferenced -= set(layer.imageReferences.keys())
        return list(unreferenced)

    unreferencedFileNames = property(_get_unreferencedFileNames, doc="A list of all file names not referenced by a glyph.")

    # -------------
    # Dict Behavior
    # -------------

    def __contains__(self, fileName):
        return fileName in self._data

    def __getitem__(self, fileName):
        d = self._data[fileName]
        if d["data"] is None:
            path = self.font.path
            reader = UFOReader(path, validate=False)
            data = reader.readImage(fileName, validate=self.ufoLibReadValidate)
            d["data"] = data
            d["digest"] = _makeDigest(data)
            d["onDisk"] = True
            d["onDiskModTime"] = reader.getFileModificationTime("%s/%s" % ("images", fileName))
        return d["data"]

    def __setitem__(self, fileName, data):
        if fileName not in self._data:
            test = fileName
            if fileName.lower().endswith(".png"):
                test = os.path.splitext(fileName)[0]
            assert fileNameValidator(test)
        assert data.startswith(pngSignature), "Image does not begin with the PNG signature."
        isNewImage = fileName not in self._data
        onDisk = False
        onDiskModTime = None
        if fileName in self._scheduledForDeletion:
            # preserve exsiting stamping
            assert fileName not in self._data
            self._data[fileName] = self._scheduledForDeletion.pop(fileName)
        digest = _makeDigest(data)
        if fileName in self._data:
            n = self[fileName] # force it to load so that the stamping is correct
            if self._data[fileName]["digest"] == digest:
                return
            onDisk = self._data[fileName]["onDisk"]
            onDiskModTime = self._data[fileName]["onDiskModTime"]
            del self._data[fileName] # now remove it
        if isNewImage:
            self.postNotification("ImageSet.ImageWillBeAdded", data=dict(name=fileName))
        self._data[fileName] = _imageDict(data=data, dirty=True, digest=digest, onDisk=onDisk, onDiskModTime=onDiskModTime)
        if isNewImage:
            self.postNotification("ImageSet.ImageAdded", data=dict(name=fileName))
        else:
            self.postNotification("ImageSet.ImageChanged", data=dict(name=fileName))
        self.dirty = True

    def __delitem__(self, fileName):
        n = self[fileName] # force it to load so that the stamping is correct
        self.postNotification("ImageSet.ImageWillBeDeleted", data=dict(name=fileName))
        self._scheduledForDeletion[fileName] = dict(self._data.pop(fileName))
        self.postNotification("ImageSet.ImageDeleted", data=dict(name=fileName))
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

    def save(self, writer, removeUnreferencedImages=False, saveAs=False, progressBar=None):
        """
        Save images. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        if removeUnreferencedImages:
            self.disableNotifications()
            for fileName in self.unreferencedFileNames:
                del self[fileName]
            self.enableNotifications()
        if saveAs:
            font = self.font
            if font is not None and font.path is not None and os.path.exists(font.path):
                reader = UFOReader(font.path, validate=False)
                readerImageNames = reader.getImageDirectoryListing(validate=self.ufoLibReadValidate)
                for fileName, data in self._data.items():
                    if data["data"] is not None or fileName not in readerImageNames:
                        continue
                    writer.copyImageFromReader(reader, fileName, fileName, validate=self.ufoLibWriteValidate)
        for fileName in self._scheduledForDeletion:
            try:
                writer.removeImage(fileName, validate=self.ufoLibWriteValidate)
            except UFOLibError:
                # this will be raised if the file doesn't exist.
                # instead of trying to maintain a list of in UFO
                # vs. in memory, simply fail and move on when
                # something can't be deleted because it isn't
                # in the UFO.
                pass
        self._scheduledForDeletion.clear()
        for fileName, data in self._data.items():
            if not data["dirty"]:
                continue
            writer.writeImage(fileName, data["data"], validate=self.ufoLibWriteValidate)
            data["dirty"] = False
            data["onDisk"] = True
            data["onDiskModTime"] = writer.getFileModificationTime("%s/%s" % ("images", fileName))
        self.dirty = False

    # ---------------
    # File Management
    # ---------------

    def makeFileName(self, fileName):
        """
        Make a file system legal version of **fileName**.
        """
        fileName = unicode(fileName)
        suffix = ""
        if fileName.lower().endswith(".png"):
            suffix = fileName[-4:]
            fileName = fileName[:-4]
        existing = set([i.lower() for i in self.fileNames])
        return userNameToFileName(fileName, existing, suffix=suffix)

    def findDuplicateImage(self, data):
        """
        Search the images to see if an image matching
        **image** already exists. If so, the file name
        for the existing image will be returned.
        """
        digest = _makeDigest(data)
        notYetLoaded = []
        for fileName, image in self._data.items():
            # skip if the image hasn't been loaded
            if image["data"] is None:
                notYetLoaded.append(fileName)
                continue
            otherDigest = image["digest"]
            if otherDigest == digest:
                return fileName
        for fileName in notYetLoaded:
            d = self[fileName]
            image = self._data[fileName]
            otherDigest = image["digest"]
            if otherDigest == digest:
                return fileName
        return None

    # ---------------------
    # External Edit Support
    # ---------------------

    def testForExternalChanges(self, reader):
        """
        Test for external changes. This should not be called externally.
        """
        filesOnDisk = reader.getImageDirectoryListing()
        modifiedImages = []
        addedImages = []
        deletedImages = []
        for fileName in set(filesOnDisk) - set(self.fileNames):
            if fileName not in self._scheduledForDeletion:
                addedImages.append(fileName)
            elif not self._scheduledForDeletion[fileName]["onDisk"]:
                addedImages.append(fileName)
            elif self._scheduledForDeletion[fileName]["onDiskModTime"] != reader.getFileModificationTime(
                "%s/%s" % ("images", fileName)
            ):
                addedImages.append(fileName)
        for fileName, imageData in self._data.items():
            # file on disk and has been loaded
            if fileName in filesOnDisk and imageData["data"] is not None:
                newModTime = reader.getFileModificationTime("%s/%s" % ("images", fileName))
                if newModTime != imageData["onDiskModTime"]:
                    newData = reader.readImage(fileName)
                    newDigest = _makeDigest(newData)
                    if newDigest != imageData["digest"]:
                        modifiedImages.append(fileName)
                continue
            # file removed
            if fileName not in filesOnDisk and imageData["onDisk"]:
                deletedImages.append(fileName)
                continue
        return modifiedImages, addedImages, deletedImages

    def reloadImages(self, fileNames):
        """
        Reload specified images. This should not be called externally.
        """
        for fileName in fileNames:
            self._data[fileName] = _imageDict()
            image = self[fileName]

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(ImageSet, self).endSelfNotificationObservation()
        self._font = None

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        simple_get = lambda k: self[k]

        getters = []
        for k in self.fileNames:
            getters.append((k, simple_get))

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        self._data = {}
        self._scheduledForDeletion = {}
        for k in data:
            self[k] = data[k]

def _imageDict(data=None, dirty=False, digest=None, onDisk=True, onDiskModTime=None):
    return dict(data=data, digest=digest, dirty=dirty, onDisk=onDisk, onDiskModTime=onDiskModTime)

def _makeDigest(data):
    m = hashlib.md5()
    m.update(data)
    return m.digest()

def fileNameValidator(value):
    """
    >>> fileNameValidator(u'a')
    True
    >>> fileNameValidator(u'A_')
    True
    >>> fileNameValidator(u'A_E_')
    True
    >>> fileNameValidator(u'A_e')
    True
    >>> fileNameValidator(u'ae')
    True
    >>> fileNameValidator(u'aE_')
    True
    >>> fileNameValidator(u'a.alt')
    True
    >>> fileNameValidator(u'A_.alt')
    True
    >>> fileNameValidator(u'A_.A_lt')
    True
    >>> fileNameValidator(u'A_.aL_t')
    True
    >>> fileNameValidator(u'A_.alT_')
    True
    >>> fileNameValidator(u'T__H_')
    True
    >>> fileNameValidator(u'T__h')
    True
    >>> fileNameValidator(u't_h')
    True
    >>> fileNameValidator(u'F__F__I_')
    True
    >>> fileNameValidator(u'f_f_i')
    True
    >>> fileNameValidator(u'A_acute_V_.swash')
    True
    >>> fileNameValidator(u'_notdef')
    True
    >>> fileNameValidator(u'_con')
    True
    >>> fileNameValidator(u'C_O_N_')
    True
    >>> fileNameValidator(u'_con.alt')
    True
    >>> fileNameValidator(u'alt._con')
    True
    >>> fileNameValidator('A')
    False
    >>> fileNameValidator(u'A'*256)
    False
    >>> fileNameValidator(u'A')
    False
    >>> fileNameValidator(u'con')
    False
    >>> fileNameValidator(u'a/alt')
    False
    >>> fileNameValidator(u"A_bC_dE_f")
    True
    """
    # must be a unicode
    if not isinstance(value, unicode):
        return False
    # must not be longer then the max fileName length
    if len(value) > maxFileNameLength:
        return False
    for i, character in enumerate(value):
        # must not contain any illegal characters
        if character in illegalCharacters:
            return False
        # its a capital and it should be followed by an _ (underscore)
        elif character != character.lower():
            if i == len(value)-1:
                return False
            if value[i+1] != "_":
                return False
    # check reserved file names
    for reservedFileName in reservedFileNames:
        # all reserved file names are being prefix with an _ (underscore)
        # if the replaced value is the same there is no correct prefix
        if reservedFileName in value:
            if value == value.replace("_%s" % reservedFileName, ""):
                return False
    return True

if __name__ == "__main__":
    import doctest
    doctest.testmod()
