#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from fontTools.ufoLib.glifLib import GlyphSet, glyphNameToFileName

from ufolint.data.tstobj import Result
from ufolint.stdoutput import StdStreamer


class GlifObj(object):
    """
    A simple object for use in ufoLib attribute assignments for *.glif file testing.
    """

    def __init__(self):
        pass


def run_all_glif_validations(ufoobj):
    glyphsdir_path_list = ufoobj.get_glyphsdir_path_list()
    ufoversion = ufoobj.get_ufo_version()
    ss = StdStreamer(ufoobj.ufopath)
    test_error_list = []
    for (
        glyphsdir
    ) in glyphsdir_path_list:  # for each directory that containts .glif files
        print(" ")
        sys.stdout.write(" - " + glyphsdir + "  ")
        sys.stdout.flush()
        res = Result(glyphsdir)
        try:
            gs = GlyphSet(
                glyphsdir, ufoFormatVersion=ufoversion, validateRead=True
            )  # create a ufoLib GlyphSet
            # do not report success for this, previous testing has passed this
        except Exception as e:
            res.test_failed = True
            res.test_long_stdstream_string = (
                " Failed to read glif file paths from "
                + glyphsdir
                + ". Error: "
                + str(e)
            )
            ss.stream_result(res)
            test_error_list.append(res)
            break  # break out loop as it was not possible to read the GlyphSet for this directory, gs not instantiated

        glif_count = 0  # reset glyphs directory .glif file counter
        for (
            glyphname
        ) in (
            gs.contents.keys()
        ):  # for each .glif file (read from glyph name in glyph set contents dict)
            res = Result(gs.contents[glyphname])
            try:
                go = GlifObj()
                gs.readGlyph(
                    glyphname, glyphObject=go
                )  # read the glif file and perform ufoLib validations, requires the glyphObject for validations
                res.test_failed = False
                ss.stream_result(res)
                glif_count += 1
            except Exception as e:
                res.test_failed = True
                filename = os.path.join(glyphsdir, glyphNameToFileName(glyphname, None))
                res.test_long_stdstream_string = '{} (glyph "{}"): Test failed with error: {}'.format(
                    filename, glyphname, e
                )
                ss.stream_result(res)
                test_error_list.append(res)
                glif_count += 1
        print("   " + str(glif_count) + " .glif tests completed")
    return test_error_list
