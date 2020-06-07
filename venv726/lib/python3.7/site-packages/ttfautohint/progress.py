from __future__ import division
import sys
from ctypes import (
    Structure, c_long, c_bool, c_int, c_void_p, CFUNCTYPE, cast, POINTER,
)


class ProgressData(Structure):

    _fields_ = [
        ("last_sfnt", c_long),
        ("begin", c_bool),
        ("last_percent", c_int)
    ]

    def __init__(self, last_sfnt=-1, begin=True, last_percent=0):
        super(ProgressData, self).__init__(last_sfnt, begin, last_percent)


class ProgressPrinter(object):

    def __init__(self, file=sys.stderr):
        self.file = file

    @property
    def callback(self):

        _write = self.file.write

        @CFUNCTYPE(c_int, c_long, c_long, c_long, c_long, c_void_p)
        def progress_callback(curr_idx, num_glyphs, curr_sfnt, num_sfnts,
                              user):
            data = cast(user, POINTER(ProgressData))[0]

            if num_sfnts > 1 and curr_sfnt != data.last_sfnt:
                _write("subfont %d of %d\n" % (curr_sfnt+1, num_sfnts))
                data.last_sfnt = curr_sfnt
                data.last_percent = 0
                data.begin = True

            if data.begin:
                _write("  %d glyphs\n"
                       "   "  % num_glyphs)
                data.begin = False

            # print progress approx. every 10%
            curr_percent = curr_idx * 100 // num_glyphs
            curr_diff = curr_percent - data.last_percent

            if curr_diff >= 10:
                _write(" %d%%" % curr_percent)
                data.last_percent = curr_percent - curr_percent % 10

            if curr_idx + 1 == num_glyphs:
                _write("\n")

            return 0

        return progress_callback
