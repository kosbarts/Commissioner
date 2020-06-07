#!/usr/bin/env python
# -*- coding: utf-8 -*-

#     libfv.py────────────────────────────────────────────────────────────────┐
#     │                                                                       │
#     │ A Python library module that supports read/modification/write of .otf │
#     │ and .ttf font version strings                                         │
#     │                                                                       │
#     │ Copyright 2018 Christopher Simpkins                                   │
#     │ MIT License                                                           │
#     │                                                                       │
#     │ Source: https://github.com/source-foundry/font-v                      │
#     │                                                                       │
#     └───────────────────────────────────────────────────────────────────────┘

from __future__ import unicode_literals

import os
import re

from fontTools import ttLib
from git import Repo

from fontv.utilities import get_git_root_path


class FontVersion(object):
    """
    FontVersion is a ttf and otf font version string class that provides support for font version string reads,
    reporting, modification, & writes.  It provides full support for the OpenFV font versioning specification
    (https://github.com/openfv/openfv).  Support is provided for instantiation from ttf and otf fonts, as well
    as from fontTools.ttLib.ttFont objects (https://github.com/fonttools/fonttools).

    The class works on Python "strings".  String types indicated below refer to the Python2 unicode type and Python3
    string type.

    PUBLIC ATTRIBUTES:

    contains_metadata: (boolean) boolean for presence of metadata in version string

    contains_state: (boolean) boolean for presence of state substring metadata in the version string

    contains_status: (boolean) boolean for presence of development/release status substring in the version string

    develop_string: (string) The string to use for development builds in the absence of git commit SHA1 string

    fontpath: (string) The path to the font file

    is_development: (boolean) boolean for presence of development status substring at version_string_parts[1]

    is_release: (boolean) boolean for presence of release status status substring at version_string_parts[1]

    metadata: (list) A list of metadata substrings in the version string. Either version_string_parts[1:] or empty list

    release_string: (string) The string to use for release builds in the absence of git commit SHA1 string

    sha1_develop: (string) The string to append to the git SHA1 hash string for development builds

    sha1_release: (string) The string to append to the git SHA1 hash string for release builds

    state: (string) The state metadata substring

    ttf: (fontTools.ttLib.TTFont) for font file

    version_string_parts: (list) List that maintains in memory semicolon parsed substrings of font version string

    version: (string) The version number substring formatted as "Version X.XXX"


    PRIVATE ATTRIBUTES

    _nameID_5_dict: (dictionary) {(platformID, platEncID,langID) : fontTools.ttLib.TTFont name record ID 5 object } map

    :parameter font: (string) file path to the .otf or .ttf font file OR (ttLib.TTFont) object for appropriate font file

    :parameter develop: (string) the string to use for development builds in the absence of git commit SHA1 string

    :parameter release: (string) the string to use for release builds in the absence of a git commit SHA1 string

    :parameter sha1_develop: (string) the string to append to the git SHA1 hash string for development builds

    :parameter sha1_release: (string) the string to append to the git SHA1 hash string for release builds

    :raises: fontTools.ttLib.TTLibError if fontpath is not a ttf or otf font

    :raises: IndexError if there are no nameID 5 records in the font name table

    :raises: IOError if fontpath does not exist
    """

    def __init__(
        self,
        font,
        develop="DEV",
        release="RELEASE",
        sha1_develop="-dev",
        sha1_release="-release",
    ):
        try:
            # assume that it is a ttLib.TTFont object and attempt to call object attributes
            self.fontpath = font.reader.file.name
            # if it does not raise AttributeError, we guessed correctly, can set the ttf attr here
            self.ttf = font
        except AttributeError:
            # if above attempt to call TTFont attribute raises AttributeError (as it would with string file path)
            # then instantiate a ttLib.TTFont object and define the fontpath attribute with the file path string
            self.ttf = ttLib.TTFont(file=font, recalcTimestamp=False)
            self.fontpath = font

        self.develop_string = develop
        self.release_string = release
        self.sha1_develop = sha1_develop
        self.sha1_release = sha1_release

        # name.ID = 5 version string substring data
        self.name_ID5_dict = {}

        self.version_string_parts = (
            []
        )  # list of substring items in version string (; delimited parse to list)
        self.version = ""
        self.state = ""
        self.metadata = []

        # truth test values for version string contents, updated with self._parse() method calls following updates to
        #  in memory version string data with methods in this library
        self.contains_metadata = False
        self.contains_state = False
        self.contains_status = False
        self.is_development = False
        self.is_release = False

        # head.fontRevision data.  float type
        self.head_fontRevision = 0.0

        # object instantiation method call (truth test values updated in the following method)
        self._read_version_string()

    def __eq__(self, otherfont):
        """
        Equality comparison between FontVersion objects

        :param otherfont: fontv.libfv.FontVersion object for comparison

        :return: (boolean) True = versions are the same; False = versions are not the same
        """
        if type(otherfont) is type(self):
            return self.version_string_parts == otherfont.version_string_parts
        return False

    def __ne__(self, otherfont):
        """
        Inequality comparison between FontVersion objects

        :param otherfont: fontv.libfv.FontVersion object for comparison

        :return: (boolean) True = versions differ; False = versions are the same
        """
        return not self.__eq__(otherfont)

    def __str__(self):
        """
        Human readable string formatting

        :return: (string)
        """
        return (
            "<fontv.libfv.FontVersion> "
            + os.linesep
            + self.get_name_id5_version_string()
            + os.linesep
            + "file path:"
            " " + self.fontpath
        )

    # TODO: confirm comparisons of version numbers like "Version 1.001", "Version 1.01", "Version 1.1" as not the same
    # TODO:   before this is released.  Will need to be documented as such because this is not obvious behavior
    # def __gt__(self, otherfont):
    #     """
    #
    #     :param otherfont:
    #
    #     :return:
    #     """
    #     return self.get_version_number_tuple() > otherfont.get_version_number_tuple()
    #
    # def __lt__(self, otherfont):
    #     """
    #
    #     :param otherfont:
    #
    #     :return:
    #     """
    #     return self.get_version_number_tuple() < otherfont.get_version_number_tuple()

    def _parse(self):
        """
        Private method that parses version string data to set FontVersion object attributes.  Called on FontVersion
        object instantiation and at the completion of setter methods in the library in order to update object
        attributes with new data.

        :return: None
        """
        # metadata parsing
        self._parse_metadata()  # parse the metadata
        self._parse_state()  # parse the state substring data
        self._parse_status()  # parse the version substring dev/rel status indicator data

    def _read_version_string(self):
        """
        Private method that reads OpenType name ID 5 and head.fontRevision record data from a fontTools.ttLib.ttFont
        object and sets FontVersion object properties.  The method is called on instantiation of a FontVersion object

        :return: None
        """

        # Read the name.ID=5 record
        namerecord_list = self.ttf["name"].names
        # read in name records
        for record in namerecord_list:
            if record.nameID == 5:
                # map dictionary as {(platformID, platEncID, langID) : version string}
                recordkey = (record.platformID, record.platEncID, record.langID)
                self.name_ID5_dict[recordkey] = record.toUnicode()

        # assert that at least one nameID 5 record was obtained from the font in order to instantiate
        # a FontVersion object
        if len(self.name_ID5_dict) == 0:
            raise IndexError(
                "Unable to read nameID 5 version records from the font " + self.fontpath
            )

        # define the version string from the dictionary
        for vs in self.name_ID5_dict.values():
            version_string = vs
            break  # take the first value that dictionary serves up

        # parse version string into substrings
        self._parse_version_substrings(version_string)

        # define version as first substring
        self.version = self.version_string_parts[0]

        # Read the head.fontRevision record (stored as a float)
        self.head_fontRevision = self.ttf["head"].fontRevision

        self._parse()  # update FontVersion object attributes based upon the data read in

    def _get_repo_commit(self):
        """
        Private method that makes a system git call via the GitPython library and returns a short git commit
        SHA1 hash string for the commit at HEAD using `git rev-list`.

        :return: (string) short git commit SHA1 hash string
        """
        repo = Repo(get_git_root_path(self.fontpath))
        gitpy = repo.git
        # git rev-list --abbrev-commit --max-count=1 --format="%h" HEAD - abbreviated unique sha1 for the repository
        # number of sha1 hex characters determined by git (addresses https://github.com/source-foundry/font-v/issues/2)
        full_git_sha_string = gitpy.rev_list(
            "--abbrev-commit", "--max-count=1", '--format="%h"', "HEAD"
        )
        unicode_full_sha_string = full_git_sha_string
        sha_string_list = unicode_full_sha_string.split("\n")
        final_sha_string = sha_string_list[1].replace('"', "")
        return final_sha_string

    def _parse_metadata(self):
        """
        Private method that parses a font version string for semicolon delimited font version
        string metadata.  Metadata are defined as anything beyond the first substring item of a version string.

        See OpenFV specification for version substring definition details (https://github.com/openfv/openfv)

        :return: None
        """
        if len(self.version_string_parts) > 1:
            # set to True if there are > 1 sub strings as others are defined as metadata
            self.contains_metadata = True
            self.metadata = (
                []
            )  # reset to empty and allow following code to define the list items
            for metadata_item in self.version_string_parts[1:]:
                self.metadata.append(metadata_item)
        else:
            self.metadata = []
            self.contains_metadata = False

    def _parse_state(self):
        """
        Private method that parses a font version string for [ ... ] delimited data that represents the State
        substring as defined by the OpenFV specification.  The result of this test is used to define State data
        in the FontVersion object.

        See OpenFV specification for the state substring metadata definition (https://github.com/openfv/openfv)

        :return: None
        """
        if len(self.version_string_parts) > 1:
            # Test for regular expression pattern match for state substring at version string list position 1
            # as defined by OpenFV specification.
            # This method call returns tuple of (truth test for match, matched state string (or empty string))
            response = self._is_state_substring_return_state_match(
                self.version_string_parts[1]
            )
            is_state_substring = response[0]
            state_substring_match = response[1]
            if is_state_substring is True:
                self.contains_state = True
                self.state = state_substring_match
            else:
                self.contains_state = False
                self.state = ""
        else:
            self.contains_state = False
            self.state = ""

    def _parse_status(self):
        """
        Private method that parses a font version string to determine if it contains development/release Status
        substring metadata as defined by the OpenFV specification. The result of this test is used to define Status
        data in the FontVersion object.

        See OpenFV specification for the Status substring metadata definition (https://github.com/openfv/openfv)

        :return: None
        """
        if len(self.version_string_parts) > 1:
            # define as list item 1 as per OpenFV specification
            status_needle = self.version_string_parts[1]
            # reset each time there is a parse attempt and let logic below define
            self.contains_status = False

            if self._is_development_substring(status_needle):
                self.contains_status = True
                self.is_development = True
            else:
                self.is_development = False

            if self._is_release_substring(status_needle):
                self.contains_status = True
                self.is_release = True
            else:
                self.is_release = False
        else:
            self.contains_status = False
            self.is_development = False
            self.is_release = False

    def _parse_version_substrings(self, version_string):
        """
        Private method that splits a full semicolon delimited version string on semicolon characters to a Python list.

        :param version_string: (string) the semicolon delimited version string to split

        :return: None
        """
        # split semicolon delimited list of version substrings
        if ";" in version_string:
            self.version_string_parts = version_string.split(";")
        else:
            self.version_string_parts = [version_string]

        self.version = self.version_string_parts[0]

    def _set_state_status_substring(self, state_status_string):
        """
        Private method that sets the State/Status substring in the FontVersion.version_string_parts[1] list position.
        The method preserves Other metadata when present in the version string.

        See OpenFV specification for State/Status substring and Other metdata definition details
        (https://github.com/openfv/openfv)

        :param state_status_string: (string) the string value to insert at the status substring position of the
                               self.version_string_parts list

        :return: None
        """
        if len(self.version_string_parts) > 1:
            prestring = self.version_string_parts[1]
            state_response = self._is_state_substring_return_state_match(prestring)
            is_state_substring = state_response[0]
            if (
                self._is_release_substring(prestring)
                or self._is_development_substring(prestring)
                or is_state_substring
            ):
                # directly replace when existing status substring
                self.version_string_parts[1] = state_status_string
            else:
                # if the second item of the substring list is not a status string, save it and all subsequent list items
                # then create a new list with inserted status string value
                self.version_string_parts = [
                    self.version_string_parts[0]
                ]  # redefine list as list with version number
                self.version_string_parts.append(
                    state_status_string
                )  # define the status substring as next item
                for (
                    item
                ) in (
                    self.metadata
                ):  # iterate through all previous metadata substrings and append to list
                    self.version_string_parts.append(item)
        else:
            # if the version string is defined as only a version number substring (i.e. list size = 1),
            # write the new status substring to the list.  Nothing else required
            self.version_string_parts.append(state_status_string)

        # update FontVersion truth testing properties based upon the new data
        self._parse()

    def _is_development_substring(self, needle):
        """
        Private method that returns a boolean that indicates whether the needle string meets the OpenFV specification
        definition of a Development Status metadata substring.

        See OpenFV specification for Status substring definition details (https://github.com/openfv/openfv)

        :param needle: (string) test string

        :return: boolean True = is development substring and False = is not a development substring
        """
        if (
            self.develop_string == needle.strip()
            or self.sha1_develop in needle[-len(self.sha1_develop) :]
        ):
            return True
        else:
            return False

    def _is_release_substring(self, needle):
        """
        Private method that returns a boolean that indicates whether the needle string meets the OpenFV specification
        definition of a Release Status metadata substring.

        See OpenFV specification for Status substring definition details (https://github.com/openfv/openfv)

        :param needle: (string) test string

        :return: boolean True = is release substring and False = is not a release substring
        """
        if (
            self.release_string == needle.strip()
            or self.sha1_release in needle[-len(self.sha1_release) :]
        ):
            return True
        else:
            return False

    def _is_state_substring_return_state_match(self, needle):
        """
        Private method that returns a tuple of boolean, string.  The boolean value reflects the truth test needle is a
        State substring.  The match value is defined as the contents inside [ and ] delimiters as defined by the
        regex pattern.  If there is no match, the string item in the tuple is an empty string.

        See OpenFV specification for State substring definition details (https://github.com/openfv/openfv)

        :param needle: (string) test string to attempt match for state substring
        :return: (boolean, string)  see full docstring for details re: interpretation of returned values
        """
        regex_pattern = r"\s?\[([a-zA-Z0-9_\-\.]{1,50})\]"
        p = re.compile(regex_pattern)
        m = p.match(needle)
        if m:
            return True, m.group(1)
        else:
            return False, ""

    def clear_metadata(self):
        """
        Public method that clears all version string metadata in memory.  This results in a version string that ONLY
        includes the version number substring.  The intent is to support removal of unnecessary version string data
        that are included in a font binary.

        See OpenFV specification for Version number substring and Metadata definition details
        (https://github.com/openfv/openfv)

        :return: None
        """
        self.version_string_parts = [self.version_string_parts[0]]
        self._parse()

    def get_version_number_string(self):
        """
        Public method that returns a string of the version number in XXX.XXX format.  A version number match is defined
        according to the OpenFV specification with up to three digits on either side of the period.

        See OpenFV specification for the font version number format definition and semantics
        (https://github.com/openfv/openfv)

        :return: string (Python 3) or unicode (Python 2).  Empty string if unable to parse version number format
        """
        match = re.search(r"\d{1,3}\.\d{1,3}", self.version)
        if match:
            return match.group(0)
        else:
            return ""

    def get_version_number_tuple(self):
        """
        Public method that returns a tuple of integer values with the following definition:

        ( major version, minor version position 1, minor version position 2, minor version position 3 )

        where position is the decimal position of the integer in the minor version string.  The version number format is
        defined by the OpenFV specification.

        See OpenFV specification for the font version number format definition and semantics
        (https://github.com/openfv/openfv)

        :return: tuple of integers or None if the version number substring is inappropriately formatted
        """
        match = re.search(r"\d{1,3}\.\d{1,3}", self.version)
        if match:
            version_number_int_list = []

            version_number_string = match.group(0)
            version_number_list = version_number_string.split(".")
            version_number_major_int = int(version_number_list[0])
            version_number_int_list.append(
                version_number_major_int
            )  # add major version integer

            for minor_int in version_number_list[1]:
                version_number_int_list.append(int(minor_int))

            return tuple(version_number_int_list)
        else:
            return None

    def get_head_fontrevision_version_number(self):
        """
        Public method that returns the version number that is parsed from head.fontRevision record as a float value.

        :return: float
        """
        return self.head_fontRevision

    # TODO: remove this deprecated method (commented out in v0.7.0, deprecation warnings in v0.6.0)
    # def get_version_string(self):
    #     """
    #     DEPRECATED: Please convert to use of FontVersion.get_name_id5_version_string() method
    #     """
    #     warnings.simplefilter('always')
    #     warnstring = "[WARNING] FontVersion.get_version_string is a deprecated method.  Please convert to " \
    #                  "FontVersion.get_name_id5_version_string."
    #     warnings.warn(warnstring, DeprecationWarning, stacklevel=2)
    #     return ";".join(self.version_string_parts)

    def get_name_id5_version_string(self):
        """
        Public method that returns the full version string as the semicolon delimiter joined contents of the
        FontVersion.version_string_parts Python list.

        :return: string (Python 3) or unicode (Python 2)
        """
        return ";".join(self.version_string_parts)

    def get_metadata_list(self):
        """
        Public method that returns a Python list containing metadata substring items generated by splitting the
        string on a semicolon delimiter.  Metadata are defined according to the OpenFV specification.
        The version number string (i.e. "Version X.XXX") is not present in this list.

        See OpenFV specification for the version string Metadata definition (https://github.com/openfv/openfv)

        :return: list of string (Python 3) or list of unicode (Python 2)
        """
        return self.metadata

    def get_state_status_substring(self):
        """
        Public method that returns the State and/or Status substring at position 2 of the semicolon delimited version
        string. This substring may include any of the following metadata according to the OpenFV specification:

        - "DEV"
        - "RELEASE"
        - "[state]-dev"
        - "[state]-release"

        See OpenFV specification for State and Status substring definitions (https://github.com/openfv/openfv)

        :return: string (Python 3) or unicode (Python 2), empty string if this substring is not set in the font
        """
        if len(self.version_string_parts) > 1:
            if self.is_development or self.is_release or self.contains_state:
                return self.version_string_parts[1]
            else:
                return ""
        else:
            return ""

    def set_state_git_commit_sha1(self, development=False, release=False):
        """
        Public method that adds a git commit sha1 hash label to the font version string at the State metadata position
        as defined by the OpenFV specification.  This can be combined with a Development/Release Status metadata
        substring if the calling code defines either the development or release parameter to a value of True.
        Note that development and release are mutually exclusive.  ValueError is raised if both are set to True.  The
        font source must be under git version control in order to use this method.  If the font source is not under
        git version control, an IOError is raised during the attempt to locate the .git directory in the project.

        See OpenFV specification for State substring definition details (https://github.com/openfv/openfv)

        :param development: (boolean) False (default) = do not add development status indicator; True = add indicator

        :param release: (boolean) False (default) = do not add release status indicator; True = add indicator

        :raises: IOError when the git repository root cannot be identified using the directory traversal in the
                 fontv.utilities.get_git_root_path() function

        :raises: ValueError when calling code sets both development and release parameters to True as these are
                 mutually exclusive requests

        :return: None
        """
        git_sha1_hash = self._get_repo_commit()
        git_sha1_hash_formatted = "[" + git_sha1_hash + "]"

        if development and release:
            raise ValueError(
                "Cannot set both development parameter and release parameter to a value of True in "
                "fontv.libfv.FontVersion.set_state_git_commit_sha1() method.  These are mutually "
                "exclusive."
            )

        if (
            development
        ):  # if request for development status label, append FontVersion.sha1_develop to hash digest
            hash_substring = git_sha1_hash_formatted + self.sha1_develop
        elif (
            release
        ):  # if request for release status label, append FontVersion.sha1_release to hash digest
            hash_substring = git_sha1_hash_formatted + self.sha1_release
        else:  # else just use the hash digest
            hash_substring = git_sha1_hash_formatted

        self._set_state_status_substring(hash_substring)

    def set_development_status(self):
        """
        Public method that sets the in memory Development Status metadata substring for the font version string.

        See OpenFV specification for Status substring and Development status definition
        (https://github.com/openfv/openfv)

        :return: None
        """
        self._set_state_status_substring(self.develop_string)

    def set_release_status(self):
        """
        Public method that sets the in memory Release Status metadata substring for the font version string.

        See OpenFV specification for Status substring and Release status definition details
        (https://github.com/openfv/openfv)

        :return: None
        """
        self._set_state_status_substring(self.release_string)

    def set_version_number(self, version_number):
        """
        Public method that sets the version number substring with the version_number parameter.  The version_number
        parameter should follow the OpenFV specification for the font version number format.

        See OpenFV specification for the font version number definition and semantics
        (https://github.com/openfv/openfv)

        The method will raise ValueError if the version_string cannot be cast to a float type.  This is mandatory
        for the definition of the head table fontRevision record definition in the font binary.  Attempts to add
        metadata strings to the version_number violate the OpenFV specification and are intentionally not permitted.

        :param version_number: (string) version number in X.XXX format where X are integers

        :return: None
        """
        version_number_substring = "Version " + version_number
        self.version_string_parts[0] = version_number_substring
        self.version = self.version_string_parts[0]  # "Version X.XXX"
        self.head_fontRevision = float(version_number)  # X.XXX
        self._parse()

    def set_version_string(self, version_string):
        """
        Public method that sets the entire version string (including metadata if desired) with a version_string
        parameter.  The version_string parameter should be formatted according to the OpenFV font versioning
        specification (https://github.com/openfv/openfv) for the OpenType name table ID 5 record version string.

        The method will raise a ValueError if the version number used in the version_string cannot be cast to a
        float type.  This is mandatory for the definition of the head table fontRevision record definition in the
        font binary.  Attempts to add metadata strings to the version_number violate the OpenFV specification and
        are intentionally not permitted.

        :param version_string: (string) The version string with semicolon delimited metadata (if metadata are included)

        :return: None
        """
        self._parse_version_substrings(version_string)
        self._parse()
        self.head_fontRevision = float(self.get_version_number_string())

    def write_version_string(self, fontpath=None):
        """
        Public method that writes the in memory version data to:

        (1) each OpenType name table ID 5 record in original font file
        (2) OpenType head table fontRevision record

        The name table ID 5 record(s) write is with a semicolon joined list of the items in
        FontVersion.version_string_parts

        The head table fontRevision record write is with the version number float value in FontVersion.head_fontRevision

        The write is to a .otf file if the FontVersion object was instantiated from a .otf binary and a .ttf
        file if the FontVersion object was instantiated from a .ttf binary.  By default the write is to the same
        file path that was used for instantiation of the FontVersion object.  This write path default can be modified by
        passing a new file path in the fontpath parameter.

        :param fontpath: (string) optional file path to write out the font version string to a font binary

        :return: None
        """
        # Write to name table ID 5 record
        version_string = self.get_name_id5_version_string()
        namerecord_list = self.ttf["name"].names
        for record in namerecord_list:
            if record.nameID == 5:
                # write to fonttools ttLib object name ID 5 table record for each nameID 5 record found in the font
                record.string = version_string

        # Write version number to head table fontRevision record
        self.ttf["head"].fontRevision = self.head_fontRevision

        # Write changes out to the font binary path
        if fontpath is None:
            self.ttf.save(self.fontpath)
        else:
            self.ttf.save(fontpath)
