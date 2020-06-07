#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from fontTools.ufoLib.validators import pngValidator

from ufolint.utilities import file_exists, dir_exists
from ufolint.data.tstobj import Result
from ufolint.stdoutput import StdStreamer


def run_all_images_validations(ufoobj):
    """
    Tests images directory without testing to confirm that directory is present.  Directory existence testing performed
    in calling code.  Uses ufoLib.validators.pngValidator public method to validate files identified in 'images' dir
    :param ufoobj: ufolint.data.ufo.Ufo object
    :return: (list) list of failed test results as ufolint.tstobj.Result objects
    """
    test_error_list = []
    ss = StdStreamer(ufoobj.ufopath)
    images_dir_path = os.path.join(ufoobj.ufopath, "images")

    if dir_exists(images_dir_path) is False:
        return (
            []
        )  # if the directory path does not exist, return an empty test_error_list to calling code

    for testimage_rel_path in os.listdir(images_dir_path):
        testimage_path = os.path.join(images_dir_path, testimage_rel_path)
        if file_exists(testimage_path):
            if (
                testimage_rel_path[0] == "."
            ):  # ignore files that are dotfiles in directory (e.g. .DS_Store on OS X)
                pass
            else:
                passed_ufolib_tests, error = pngValidator(
                    path=testimage_path
                )  # call ufoLib PNG validator directly
                res = Result(testimage_path)

                if passed_ufolib_tests is True:
                    res.test_failed = False
                    ss.stream_result(res)
                else:
                    res.test_failed = True
                    res.test_long_stdstream_string = (
                        testimage_path + " failed with error: " + error
                    )
                    test_error_list.append(
                        res
                    )  # add to error list returned to calling code
                    ss.stream_result(res)
    return test_error_list  # return list of identified errors to the calling code
