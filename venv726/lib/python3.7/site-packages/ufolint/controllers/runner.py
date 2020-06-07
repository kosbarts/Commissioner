#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from plistlib import load

from fontTools.ufoLib import UFOReader

from ufolint.data.tstobj import Result
from ufolint.data.ufo import Ufo2, Ufo3
from ufolint.stdoutput import StdStreamer
from ufolint.utilities import file_exists, dir_exists
from ufolint.validators.glifvalidators import run_all_glif_validations
from ufolint.validators.imagesvalidators import run_all_images_validations
from ufolint.validators.plistvalidators import (
    MetainfoPlistValidator,
    FontinfoPlistValidator,
    GroupsPlistValidator,
)
from ufolint.validators.plistvalidators import (
    KerningPlistValidator,
    LibPlistValidator,
    ContentsPlistValidator,
)
from ufolint.validators.plistvalidators import (
    LayercontentsPlistValidator,
    LayerinfoPlistValidator,
)


class MainRunner(object):
    def __init__(self, ufopath):
        self.ufopath = ufopath
        self.ufolib_reader = None
        self.ufoversion = None
        self.failures_list = (
            []
        )  # list of strings that include all failures across all tests for final report
        self.ufo_glyphs_dir_list = (
            []
        )  # list of glyphs directory(ies) available in the source (>1 permitted in UFOv3+)
        self.ufoobj = None

    def run(self):
        # Print UFO filepath header
        print(" ")
        print("ufolint:")
        print("~" * len(self.ufopath))
        print(self.ufopath)
        print("~" * len(self.ufopath))
        print(" ")

        # [START] EARLY FAIL TESTS ----------------------------------------------------------------
        #      UFO directory filepath
        #      .ufo directory extension
        #      import with ufoLib
        #      version check
        #      ufo obj define
        #        v3 only: presence of layercontents.plist to define the glyphs directories in source
        #        v2 only: no layercontents.plist, define as single glyphs directory
        ss = StdStreamer(self.ufopath)
        ss.stream_testname("UFO directory")
        self._check_ufo_dir_path_exists()  # tests user defined UFO directory path
        self._check_ufo_dir_extension()  # tests for .ufo extension on directory
        self._check_metainfo_plist_exists()  # confirm presence of metainfo.plist to define UFO version
        self._validate_read_data_types_metainfo_plist()  # validate the version data type as integer (workaround for bug in ufoLib)
        self._check_ufo_import_and_define_ufo_version()  # confirm ufoLib can import directory. defines UFOReader object as class property
        if self.ufoversion == 3:
            self._check_layercontents_plist_exists()  # tests for presence of a layercontents.plist in root of UFO
            self._validate_read_load_glyphsdirs_layercontents_plist()  # validate layercontents.plist xml and load glyphs dirs
        elif self.ufoversion == 2:
            self.ufo_glyphs_dir_list = [
                ["public.default", "glyphs"]
            ]  # define as single glyphs directory for UFOv2
        else:  # pragma nocoverage fail if unsupported UFO version (ufolint fail in case behind released UFO version)
            sys.stderr.write(
                os.linesep
                + "[ufolint] UFO v"
                + self.ufoversion
                + " is not supported in ufolint"
                + os.linesep
            )
            sys.exit(1)
        print(" ")
        print("   Found UFO v" + str(self.ufoversion))
        print("   Detected glyphs directories: ")
        for glyphs_dir in self.ufo_glyphs_dir_list:
            # TODO: add glyphs directory validation here : confirm naming = 'glyphs.*'
            sys.stdout.write(
                "     -- " + glyphs_dir[1] + " "
            )  # display the name of the specified glyphs dirs
            res = Result(glyphs_dir[1])
            if dir_exists(
                os.path.join(self.ufopath, glyphs_dir[1])
            ):  # test for presence of specified glyphs dir
                res.test_failed = False
                ss.stream_result(res)
            else:
                res.test_failed = True
                res.exit_failure = True
                res.test_long_stdstream_string = (
                    "Unable to find the UFO directory '"
                    + glyphs_dir[1]
                    + "' defined in layercontents.plist"
                )
                ss.stream_result(res)
            print(" ")

        # create Ufo objects for subsequent tests - all Ufo object dependent tests must take place below this level
        if self.ufoversion == 2:
            self.ufoobj = Ufo2(self.ufopath, self.ufo_glyphs_dir_list)
        elif self.ufoversion == 3:
            self.ufoobj = Ufo3(self.ufopath, self.ufo_glyphs_dir_list)

        # [START] Mandatory file path tests
        ss.stream_testname("UFO v" + str(self.ufoversion) + " mandatory files")

        mandatory_file_list = self.ufoobj.get_mandatory_filepaths_list()
        for mandatory_file in mandatory_file_list:
            res = Result(mandatory_file)
            if file_exists(mandatory_file):
                res.test_failed = False
                ss.stream_result(res)
            else:
                res.test_failed = True
                res.exit_failure = True
                res.test_long_stdstream_string = (
                    mandatory_file + " was not found in " + self.ufopath
                )
                ss.stream_result(res)
        print(" ")
        # [END] Mandatory file path tests
        # [END] EARLY FAIL TESTS ----------------------------------------------------------------

        # [START] XML VALIDATION TESTS  -----------------------------------------------------------
        ss.stream_testname("XML formatting")
        meta_val = MetainfoPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        fontinfo_val = FontinfoPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        groups_val = GroupsPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        kerning_val = KerningPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        lib_val = LibPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        contents_val = ContentsPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        layercont_val = LayercontentsPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )
        layerinfo_val = LayerinfoPlistValidator(
            self.ufopath, self.ufoversion, self.ufo_glyphs_dir_list
        )

        # excute validations, returns list of failure Result() objects
        mv_xml_fail_list = meta_val.run_xml_validation()
        fi_xml_fail_list = fontinfo_val.run_xml_validation()
        g_xml_fail_list = groups_val.run_xml_validation()
        k_xml_fail_list = kerning_val.run_xml_validation()
        l_xml_fail_list = lib_val.run_xml_validation()
        c_xml_fail_list = contents_val.run_xml_validation()
        lc_xml_fail_list = layercont_val.run_xml_validation()
        li_xml_fail_list = layerinfo_val.run_xml_validation()

        # xml validations return lists of all failures, append these to the class failures_list Python list
        for thelist in (
            mv_xml_fail_list,
            fi_xml_fail_list,
            g_xml_fail_list,
            k_xml_fail_list,
            l_xml_fail_list,
            c_xml_fail_list,
            lc_xml_fail_list,
            li_xml_fail_list,
        ):
            for failed_test_result in thelist:
                self.failures_list.append(failed_test_result)
        print(" ")
        # [END] XML VALIDATION TESTS  --------------------------------------------------------------

        # [START] plist FILE VALIDATION TESTS (includes numerous ufoLib library validations on plist file reads)
        ss.stream_testname("*.plist spec")
        mv_ufolib_import_fail_list = meta_val.run_ufolib_import_validation()
        fi_ufolib_import_fail_list = fontinfo_val.run_ufolib_import_validation()
        g_ufolib_import_fail_list = groups_val.run_ufolib_import_validation()
        k_ufolib_import_fail_list = kerning_val.run_ufolib_import_validation()
        l_ufolib_import_fail_list = lib_val.run_ufolib_import_validation()
        c_ufolib_import_fail_list = contents_val.run_ufolib_import_validation()
        lc_ufolib_import_fail_list = layercont_val.run_ufolib_import_validation()
        li_ufolib_import_fail_list = layerinfo_val.run_ufolib_import_validation()

        for thelist in (
            mv_ufolib_import_fail_list,
            fi_ufolib_import_fail_list,
            g_ufolib_import_fail_list,
            k_ufolib_import_fail_list,
            l_ufolib_import_fail_list,
            c_ufolib_import_fail_list,
            lc_ufolib_import_fail_list,
            li_ufolib_import_fail_list,
        ):
            for failed_test_result in thelist:
                self.failures_list.append(failed_test_result)

        # [END] plist FILE VALIDATION TESTS

        # [START] features.fea TESTS
        print(" ")
        ss.stream_testname("features.fea")
        ff_path = os.path.join(self.ufopath, "features.fea")
        res = Result(ff_path)
        if file_exists(ff_path):
            res.test_failed = False
            ss.stream_result(res)
        else:
            sys.stdout.write("not present")  # not a mandatory file, not a failure
        # [END] features.fea TESTS

        # [START] DATA DIRECTORY TESTS - no fails in these tests, reporting only
        if self.ufoversion == 3:  # UFOv3+ only
            print(" ")
            ss.stream_testname("data")
            data_dir_path = os.path.join(self.ufopath, "data")

            if dir_exists(data_dir_path):
                ufo_reader = UFOReader(self.ufopath, validate=True)
                raw_data_list = ufo_reader.getDataDirectoryListing()
                data_list = []
                for item in raw_data_list:
                    if (
                        not item[0] == "."
                    ):  # eliminate dotfiles picked up by the ufoLib method (e.g. .DS_Store on OSX)
                        data_list.append(item)
                if len(data_list) == 0:
                    sys.stdout.write("empty")
                else:
                    sys.stdout.write(str(len(data_list)) + " data files")
            else:
                sys.stdout.write(
                    "not present"
                )  # not a mandatory directory, not a failure
        # [END] DATA DIRECTORY TESTS

        # [START] IMAGES DIRECTORY TESTS
        if self.ufoversion == 3:  # UFO v3+ only
            print(" ")
            ss.stream_testname("images")
            images_dir_path = os.path.join(self.ufopath, "images")

            if dir_exists(images_dir_path):
                images_dir_failures = run_all_images_validations(self.ufoobj)
                for images_failure_result in images_dir_failures:
                    self.failures_list.append(images_failure_result)
            else:
                sys.stdout.write(
                    "not present"
                )  # not a mandatory directory, not a failure
        # [END] IMAGES DIRECTORY TESTS

        # [START] *.glif VALIDATION TESTS
        print(" ")
        ss.stream_testname("*.glif spec")
        glif_validation_failures = run_all_glif_validations(self.ufoobj)
        for glif_failure_result in glif_validation_failures:
            self.failures_list.append(glif_failure_result)
        # [END] *.glif VALIDATION TESTS

        # TESTS COMPLETED --------------------------------------------------------------------------
        #   stream all failure results as a newline delimited list to user and exit with status code 1
        #   if failures are present, status code 0 if failures are not present
        ss = StdStreamer(self.ufopath)
        ss.stream_final_failures(self.failures_list)

    # =====================================
    #
    #  TESTS
    #
    # =====================================

    def _check_layercontents_plist_exists(self):
        """
        UFO 3+ test for layercontents.plist file in the top level of UFO directory
        :return: None - method leads to early exit with status code 1 if file not found
        """
        ss = StdStreamer(self.ufopath)
        lcp_test_filepath = os.path.join(self.ufopath, "layercontents.plist")
        res = Result(lcp_test_filepath)

        if file_exists(lcp_test_filepath):
            res.test_failed = False
            ss.stream_result(res)
        else:
            res.test_failed = True
            res.exit_failure = (
                True
            )  # early exit if cannot find this file to define glyphs directories in UFO source
            res.test_long_stdstream_string = (
                "layercontents.plist was not found in " + self.ufopath
            )
            ss.stream_result(res)

    def _check_metainfo_plist_exists(self):
        """
        Test for presence of metainfo.plist file in the UFO directory. Mandatory file that defines UFO version.
        :return: None = method leads to early exit with status code 1 if file not found
        """
        ss = StdStreamer(self.ufopath)
        meta_test_filepath = os.path.join(self.ufopath, "metainfo.plist")
        res = Result(meta_test_filepath)

        if file_exists(meta_test_filepath):
            res.test_failed = False
            ss.stream_result(res)
        else:
            res.test_failed = True
            res.exit_failure = (
                True
            )  # early exit if cannot find this file to define glyphs directories in UFO source
            res.test_long_stdstream_string = (
                "metainfo.plist was not found in " + self.ufopath
            )
            ss.stream_result(res)

    def _check_ufo_import_and_define_ufo_version(self):
        """
        Tests UFO directory import with ufoLib UFOReader object and defines class property (ufo) with the
        ufoLib UFOReader object.  This object is used for additional tests in this module.  Failures added to the
        class property failures_list for final report
        :return: None
        """
        ss = StdStreamer(self.ufopath)
        res = Result(self.ufopath)
        try:
            ufolib_reader = UFOReader(self.ufopath, validate=True)
            self.ufoversion = ufolib_reader.formatVersion
            self.ufolib_reader = ufolib_reader
            res.test_failed = False
            ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                "ufoLib raised an exception with import of "
                + self.ufopath
                + os.linesep
                + str(e)
            )
            self.failures_list.append(res)
            ss.stream_result(res)

    def _check_ufo_dir_extension(self):
        """
        Tests for .ufo extension on the user defined (command line) directory path. Results
        streamed through std output stream. Failures added to the
        class property failures_list for final report
        :return: None
        """
        ss = StdStreamer(self.ufopath)
        res = Result(self.ufopath)
        if self.ufopath[-4:] == ".ufo":
            res.test_failed = False
            ss.stream_result(res)
        else:
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                self.ufopath + " directory does not have a .ufo extension"
            )
            self.failures_list.append(res)
            ss.stream_result(res)

    def _check_ufo_dir_path_exists(self):
        """
        Tests existence of a directory on the user defined (command line) directory path
        Results streamed through std output stream. Failures added to the
        class property failures_list for final report
        :return: None
        """
        ss = StdStreamer(self.ufopath)
        if dir_exists(self.ufopath):
            res = Result(self.ufopath)
            res.test_failed = False
            ss.stream_result(res)

        else:
            res = Result(self.ufopath)
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                self.ufopath + " does not appear to be a valid UFO directory"
            )
            self.failures_list.append(res.test_long_stdstream_string)
            ss.stream_result(res)  # raises sys.exit(1) on this failure

    def _validate_read_data_types_metainfo_plist(self):
        metainfo_plist_path = os.path.join(self.ufopath, "metainfo.plist")
        res = Result(metainfo_plist_path)
        ss = StdStreamer(metainfo_plist_path)
        try:
            with open(metainfo_plist_path, "rb") as f:
                meta_dict = load(f)
                if "formatVersion" in meta_dict.keys():
                    if isinstance(meta_dict["formatVersion"], int):
                        res.test_failed = False
                        ss.stream_result(res)
                    else:
                        res.test_failed = True
                        res.exit_failure = True  # early exit if fails
                        res.test_long_stdstream_string = (
                            metainfo_plist_path
                            + " 'formatVersion' value must be specified as"
                            " an integer"
                        )
                        ss.stream_result(res)
                else:
                    res.test_failed = True
                    res.exit_failure = True  # early exit if fails
                    res.test_long_stdstream_string = (
                        "Failed to read the 'formatVersion' value in "
                        + metainfo_plist_path
                    )
                    ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.exit_failure = True  # early exit if fails
            res.test_long_stdstream_string = (
                "Failed to read the 'formatVersion' value in "
                "the file " + metainfo_plist_path + ". Error: " + str(e)
            )
            ss.stream_result(res)

    def _validate_read_load_glyphsdirs_layercontents_plist(self):
        layercontents_plist_path = os.path.join(self.ufopath, "layercontents.plist")
        res = Result(layercontents_plist_path)
        ss = StdStreamer(layercontents_plist_path)
        try:
            # loads as [ ['layername1', 'glyphsdir1'], ['layername2', 'glyphsdir2'] ]
            with open(layercontents_plist_path, "rb") as f:
                self.ufo_glyphs_dir_list = load(f)
                res.test_failed = False
                ss.stream_result(res)
        except Exception as e:
            res.test_failed = True
            res.exit_failure = True
            res.test_long_stdstream_string = (
                "Failed to read " + layercontents_plist_path + ". Error: " + str(e)
            )
            ss.stream_result(res)
