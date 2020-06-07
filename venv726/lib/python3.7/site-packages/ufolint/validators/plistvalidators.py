#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import xml.etree.ElementTree as ETree

from ufolint.data.tstobj import Result
from ufolint.data.ufo import Ufo2, Ufo3
from ufolint.stdoutput import StdStreamer
from ufolint.utilities import file_exists

from fontTools.ufoLib import UFOReader
from fontTools.ufoLib.glifLib import GlyphSet


class AbstractPlistValidator(object):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        self.ufopath = ufopath
        self.ufoversion = ufoversion
        self.glyphs_dir_list = glyphs_dir_list
        self.testfile = None
        if self.ufoversion == 2:
            self.ufoobj = Ufo2(self.ufopath, self.glyphs_dir_list)
        elif self.ufoversion == 3:
            self.ufoobj = Ufo3(self.ufopath, self.glyphs_dir_list)
        self.root_plist_list = self.ufoobj.all_root_plist_files_list
        self.glyphsdir_plist_list = self.ufoobj.all_glyphsdir_plist_files_list
        self.mandatory_filepaths_list = self.ufoobj.get_mandatory_filepaths_list()
        self.test_fail_list = []

    def _parse_xml(self, testpath):
        res = Result(testpath)
        try:
            ETree.parse(testpath)
            res.test_failed = False
            return res
        except Exception as e:
            res.test_failed = True
            if (
                testpath in self.mandatory_filepaths_list
            ):  # if this test is on a mandatory file, exit early with fail
                res.exit_failure = True
            res.test_long_stdstream_string = (
                testpath + " failed XML validation test with error: " + str(e)
            )
            self.test_fail_list.append(res)  # add each failure to test failures list
            return res

    def run_xml_validation(self):
        ss = StdStreamer(self.ufopath)
        if self.testfile in self.root_plist_list:
            testpath = self.ufoobj.get_root_plist_filepath(self.testfile)
            if file_exists(testpath):
                res = self._parse_xml(testpath)
                ss.stream_result(res)
            else:  # there is no file to check, mandatory files have already been checked, this is a success
                res = Result(testpath)
                res.test_failed = False
                ss.stream_result(res)
        elif self.testfile in self.glyphsdir_plist_list:
            testpath_list = self.ufoobj.get_glyphsdir_plist_filepath_list(self.testfile)
            for testpath in testpath_list:
                if file_exists(testpath):
                    res = self._parse_xml(testpath)
                    ss.stream_result(res)
                else:  # there is no file to check, mandatory files have already been checked, this is a success
                    res = Result(testpath)
                    res.test_failed = False
                    ss.stream_result(res)
        return (
            self.test_fail_list
        )  # return to the calling code so that it can be maintained for final user report

    def run_ufolib_import_validation(self):
        raise NotImplementedError


class MetainfoPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(MetainfoPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = "metainfo.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.readMetaInfo method validates the UFO version number.  This method adds validation for
        expected reverse URL name scheme in
        :return: (list) list of test failure Result objects
        """

        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if (
            file_exists(self.testpath) is False
        ):  # fail test, exit early if file is missing
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                "metainfo.plist is not available on the path " + self.testpath
            )
            ss.stream_result(res)
        try:
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.readMetaInfo()
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            self.test_fail_list.append(res)
            ss.stream_result(res)
        return self.test_fail_list


class FontinfoPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(FontinfoPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = "fontinfo.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

        class FontInfoObj(object):
            def __init__(self):
                pass

        self.fontinfo_obj = FontInfoObj()

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.readInfo method validates value types in the fontinfo.plist file
        :return: (list) list of test failure Result objects
        """
        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if file_exists(self.testpath) is False:
            res.test_failed = (
                False
            )  # not a mandatory file in UFO spec, test passes if missing
            ss.stream_result(res)
            return self.test_fail_list
        try:
            # read fontinfo.plist with ufoLib - the ufoLib library performs type validations on values on read
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.readInfo(self.fontinfo_obj)
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            ss.stream_result(res)
            self.test_fail_list.append(res)
        return self.test_fail_list


class GroupsPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(GroupsPlistValidator, self).__init__(ufopath, ufoversion, glyphs_dir_list)
        self.testfile = "groups.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.readGroups method validates the groups.plist file
        :return: (list) list of test failure Result objects
        """
        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if file_exists(self.testpath) is False:
            res.test_failed = (
                False
            )  # not a mandatory file in UFO spec, test passes if missing
            ss.stream_result(res)
            return self.test_fail_list
        try:
            # read groups.plist with ufoLib - the ufoLib library performs type validations on values on read
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.readGroups()
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            ss.stream_result(res)
            self.test_fail_list.append(res)
        return self.test_fail_list


class KerningPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(KerningPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = "kerning.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.readKerning method validates the kerning.plist file
        :return: (list) list of test failure Result objects
        """
        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if file_exists(self.testpath) is False:
            res.test_failed = (
                False
            )  # not a mandatory file in UFO spec, test passes if missing
            ss.stream_result(res)
            return self.test_fail_list
        try:
            # read kerning.plist with ufoLib - the ufoLib library performs type validations on values on read
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.readKerning()
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            ss.stream_result(res)
            self.test_fail_list.append(res)
        return self.test_fail_list


class LibPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(LibPlistValidator, self).__init__(ufopath, ufoversion, glyphs_dir_list)
        self.testfile = "lib.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.readLib method validates the lib.plist file
        :return: (list) list of test failure Result objects
        """
        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if file_exists(self.testpath) is False:
            res.test_failed = (
                False
            )  # not a mandatory file in UFO spec, test passes if missing
            ss.stream_result(res)
            return self.test_fail_list
        try:
            # read lib.plist with ufoLib - the ufoLib library performs type validations on values on read
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.readLib()
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            ss.stream_result(res)
            self.test_fail_list.append(res)
        return self.test_fail_list


class ContentsPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(ContentsPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = (
            "contents.plist"
        )  # can occur in multiple glyphs directories in UFOv3+
        self.glyphs_dir_list = glyphs_dir_list

    def run_ufolib_import_validation(self):
        """
        ufoLib GlyphSet instantiation validates the contents.plist file
        :return: (list) list of test failure Result objects
        """
        ss = StdStreamer(self.ufopath)
        for glyphs_dir in self.ufoobj.glyphsdir_list:
            res = Result(glyphs_dir[1])
            rel_dir_path = os.path.join(self.ufopath, glyphs_dir[1])
            try:
                # read contents.plist with ufoLib as GlyphSet instantiation
                # the ufoLib library performs type validations on values on read
                # glyphs_dir_list is a list of lists mapped to glyphs dir name, glyphs dir path
                GlyphSet(
                    rel_dir_path, ufoFormatVersion=self.ufoversion, validateRead=True
                )  # test for raised exceptions
                res.test_failed = False
                ss.stream_result(res)
            except Exception as e:
                res.test_failed = True
                res.exit_failure = True  # mandatory file
                res.test_long_stdstream_string = (
                    "contents.plist in "
                    + rel_dir_path
                    + " failed ufoLib import test with error: "
                    + str(e)
                )
                self.test_fail_list.append(res)
                ss.stream_result(res)
        return self.test_fail_list


class LayercontentsPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(LayercontentsPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = "layercontents.plist"
        self.testpath = self.ufoobj.get_root_plist_filepath(self.testfile)

    def run_ufolib_import_validation(self):
        """
        ufoLib UFOReader.getLayerNames method validates the layercontents.plist file
        :return: (list) list of test failure Result objects
        """
        res = Result(self.testpath)
        ss = StdStreamer(self.ufopath)
        if (
            file_exists(self.testpath) is False
        ):  # should only meet this condition if not a mandatory file (runner.py checks)
            res.test_failed = False
            ss.stream_result(res)
            return self.test_fail_list
        try:
            # read layercontents.plist with ufoLib - the ufoLib library performs type validations on values on read
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            ufolib_reader.getLayerNames()
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            if (
                self.testpath in self.mandatory_filepaths_list
            ):  # if part of mandatory file spec for UFO version, fail early
                res.test_failed = True
                res.exit_failure = True  # fail early b/c it is mandatory part of spec
            else:
                res.test_failed = (
                    True
                )  # fail the test, but wait to report until all other tests complete
            res.test_long_stdstream_string = (
                self.testpath + " failed ufoLib import test with error: " + str(e)
            )
            self.test_fail_list.append(res)
            ss.stream_result(res)
        return self.test_fail_list


class LayerinfoPlistValidator(AbstractPlistValidator):
    def __init__(self, ufopath, ufoversion, glyphs_dir_list):
        super(LayerinfoPlistValidator, self).__init__(
            ufopath, ufoversion, glyphs_dir_list
        )
        self.testfile = "layerinfo.plist"

        class LayerInfoObj(object):
            def __init__(self):
                pass

        self.layerinfo_obj = LayerInfoObj()

    def run_ufolib_import_validation(self):
        """
        ufoLib GlyphSet.readLayerInfo method performs validations of layerinfo.plist file(s)
        :return: (list) list of test failure Result objects
        """
        ss = StdStreamer(self.ufopath)
        for glyphs_dir in self.ufoobj.glyphsdir_list:
            res = Result(glyphs_dir[1])
            rel_dir_path = os.path.join(self.ufopath, glyphs_dir[1])

            try:
                gs = GlyphSet(
                    rel_dir_path, ufoFormatVersion=self.ufoversion, validateRead=True
                )
                gs.readLayerInfo(self.layerinfo_obj)
                res.test_failed = False
                ss.stream_result(res)
            except Exception as e:
                res.test_failed = True
                res.test_long_stdstream_string = (
                    "layerinfo.plist in "
                    + rel_dir_path
                    + " failed ufoLib import test with error: "
                    + str(e)
                )
                self.test_fail_list.append(res)
                ss.stream_result(res)
        return self.test_fail_list
