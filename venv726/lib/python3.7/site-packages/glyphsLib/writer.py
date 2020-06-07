# Copyright 2016 Georg Seifert. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: #www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import glyphsLib.classes
from glyphsLib.types import floatToString5
import logging
import datetime
from collections import OrderedDict
from io import StringIO

"""
    Usage

    >> fp = open('Path/to/File.glyphs', 'w')
    >> writer = Writer(fp)
    >> writer.write(font)
    >> fp.close()
"""

logger = logging.getLogger(__name__)


class Writer:
    def __init__(self, fp):
        # figure out whether file object expects bytes or unicodes
        try:
            fp.write(b"")
        except TypeError:
            fp.write("")  # this better not fail...
            # file already accepts unicodes; use it directly
            self.file = fp
        else:
            # file expects bytes; wrap it in a UTF-8 codecs.StreamWriter
            import codecs

            self.file = codecs.getwriter("utf-8")(fp)

    def write(self, rootObject):
        self.writeDict(rootObject)
        self.file.write("\n")

    def writeDict(self, dictValue):
        self.file.write("{\n")
        forType = None
        if hasattr(dictValue, "_keyOrder"):
            keys = dictValue._keyOrder
        elif hasattr(dictValue, "_classesForName"):
            keys = sorted(dictValue._classesForName.keys())
        else:
            keys = dictValue.keys()
            if not isinstance(dictValue, OrderedDict):
                keys = sorted(keys)
        for key in keys:
            if hasattr(dictValue, "_classesForName"):
                forType = dictValue._classesForName[key]
            try:
                if isinstance(dictValue, (dict, OrderedDict)):
                    value = dictValue[key]
                else:
                    getKey = key
                    if hasattr(dictValue, "_wrapperKeysTranslate"):
                        getKey = dictValue._wrapperKeysTranslate.get(key, key)
                    value = getattr(dictValue, getKey)
            except AttributeError:
                continue
            if value is None:
                continue
            if hasattr(
                dictValue, "shouldWriteValueForKey"
            ) and not dictValue.shouldWriteValueForKey(key):
                continue
            self.writeKey(key)
            self.writeValue(value, key, forType=forType)
            self.file.write(";\n")
        self.file.write("}")

    def writeArray(self, arrayValue):
        self.file.write("(\n")
        idx = 0
        length = len(arrayValue)
        if hasattr(arrayValue, "plistArray"):
            arrayValue = arrayValue.plistArray()
        for value in arrayValue:
            self.writeValue(value)
            if idx < length - 1:
                self.file.write(",\n")
            else:
                self.file.write("\n")
            idx += 1
        self.file.write(")")

    def writeUserData(self, userDataValue):
        self.file.write("{\n")
        keys = sorted(userDataValue.keys())
        for key in keys:
            value = userDataValue[key]
            self.writeKey(key)
            self.writeValue(value, key)
            self.file.write(";\n")
        self.file.write("}")

    def writeValue(self, value, forKey=None, forType=None):
        if hasattr(value, "plistValue"):
            value = value.plistValue()
            if value is not None:
                self.file.write(value)
        elif forKey == "color" and hasattr(value, "__iter__"):
            # We have to write color tuples on one line or Glyphs 2.4.x
            # misreads it.
            self.file.write(str(tuple(value)))
        elif isinstance(value, (list, glyphsLib.classes.Proxy)):
            if isinstance(value, glyphsLib.classes.UserDataProxy):
                self.writeUserData(value)
            else:
                self.writeArray(value)
        elif isinstance(value, (dict, OrderedDict, glyphsLib.classes.GSBase)):
            self.writeDict(value)
        elif type(value) == float:
            self.file.write(floatToString5(value))
        elif type(value) == int:
            self.file.write(str(value))
        elif type(value) == bool:
            if value:
                self.file.write("1")
            else:
                self.file.write("0")
        elif type(value) == datetime.datetime:
            self.file.write('"%s +0000"' % str(value))
        else:
            value = str(value)
            if forKey != "unicode":
                value = escape_string(value)
            self.file.write(value)

    def writeKey(self, key):
        key = escape_string(key)
        self.file.write("%s = " % key)


def dump(obj, fp):
    """Write a GSFont object to a .glyphs file.
    'fp' should be a (writable) file object.
    """
    writer = Writer(fp)
    logger.info("Writing .glyphs file")
    writer.write(obj)


def dumps(obj):
    """Serialize a GSFont object to a .glyphs file format.
    Return a (unicode) str object.
    """
    fp = StringIO()
    dump(obj, fp)
    return fp.getvalue()


NSPropertyListNameSet = (
    # 0
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    # 16
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    # 32
    False,
    False,
    False,
    False,
    True,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    False,
    True,
    False,
    # 48
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    False,
    # 64
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    # 80
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
    False,
    False,
    True,
    # 96
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    # 112
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
    False,
    False,
    False,
)


def _needs_quotes(string):
    if len(string) == 0:
        return True

    # Does it need quotes because of special characters?
    for c in string:
        d = ord(c)
        if d >= 128 or not NSPropertyListNameSet[d]:
            return True

    # Does it need quotes because it could be confused with a number?
    try:
        int(string)
    except ValueError:
        pass
    else:
        return True

    try:
        float(string)
    except ValueError:
        return False
    else:
        return True


def escape_string(string):
    if _needs_quotes(string):
        string = string.replace("\\", "\\\\")
        string = string.replace('"', '\\"')
        string = string.replace("\n", "\\012")
        string = '"%s"' % string
    return string
