from __future__ import print_function, division, absolute_import

from ctypes import (
    cdll, POINTER, c_char, c_char_p, c_size_t, c_int, byref,
)
from ctypes.util import find_library

from io import open
import sys
import os

from ttfautohint._version import __version__
from ttfautohint import memory
from ttfautohint.options import validate_options, format_varargs, StemWidthMode
from ttfautohint import info
from ttfautohint import progress
from ttfautohint import errors
from ttfautohint.errors import TAError
from ttfautohint import cli


__all__ = ["ttfautohint", "TAError", "StemWidthMode"]


class TALibrary(object):

    def __init__(self, path=None, **kwargs):
        """ Initialize a new handle to the libttfautohint shared library.
        If no path is provided, by default the embedded shared library that
        comes with the binary wheel is loaded first. If this is not found,
        then `ctypes.util.find_library` function is used to search in the
        system's default search paths.
        """
        if path is None:
            if sys.platform == "win32":
                name = "libttfautohint.dll"
            elif sys.platform == "darwin":
                name = "libttfautohint.dylib"
            else:
                name = "libttfautohint.so"
            path = os.path.join(os.path.dirname(__file__), name)
            if not os.path.isfile(path):
                path = find_library("ttfautohint")
                if not path:
                    raise OSError("cannot find '%s'" % name)
        self.lib = lib = cdll.LoadLibrary(path, **kwargs)
        self.path = path

        lib.TTF_autohint_version.argtypes = [POINTER(c_int)] * 3
        lib.TTF_autohint_version.restype = None
        _major, _minor, _revision = c_int(), c_int(), c_int()
        lib.TTF_autohint_version(_major, _minor, _revision)
        self.major = _major.value
        self.minor = _minor.value
        self.revision = _revision.value

        lib.TTF_autohint_version_string.restype = c_char_p
        version_string = lib.TTF_autohint_version_string().decode('ascii')
        self.version_string = version_string

    def _build_info_data(self, options):
        # as a side effect, these arguments are popped from the options dict
        # as they are not part of TTF_autohint API
        family_suffix = options.pop("family_suffix")
        no_info = options.pop("no_info")
        detailed_info = options.pop("detailed_info")
        if no_info:
            info_string = None
        else:
            info_string = info.build_info_string(self.version_string,
                                                 detailed_info, **options)
        return info.InfoData(info_string, family_suffix)

    def ttfautohint(self, **kwargs):
        options = validate_options(kwargs)

        info_data = self._build_info_data(options)

        if info_data.family_suffix:
            info_post_callback = info.info_post_callback
        else:
            info_post_callback = None

        if options.pop("verbose"):
            # by default, it prints to stderr like ttfautohint.exe
            # TODO: figure out a way to implement progress using logging?
            printer = progress.ProgressPrinter()
            progress_callback = printer.callback
        else:
            progress_callback = None
        progress_callback_data = progress.ProgressData()

        error_callback = errors.error_callback
        control_name = options.pop("control_name", None)
        error_callback_data = errors.ErrorData(control_name)

        # pop 'out_file' from options dict since we use 'out_buffer'
        out_file = options.pop('out_file')

        out_buffer_p = POINTER(c_char)()
        out_buffer_len = c_size_t(0)

        option_keys, option_values = format_varargs(
            out_buffer=byref(out_buffer_p),
            out_buffer_len=byref(out_buffer_len),
            alloc_func=memory.alloc_callback,
            free_func=memory.free_callback,
            info_callback=info.info_callback,
            info_post_callback=info_post_callback,
            info_callback_data=byref(info_data),
            progress_callback=progress_callback,
            progress_callback_data=byref(progress_callback_data),
            error_callback=error_callback,
            error_callback_data=byref(error_callback_data),
            **options
        )

        rv = self.lib.TTF_autohint(option_keys, *option_values)
        if rv:
            raise TAError(rv, **error_callback_data.kwargs)

        assert out_buffer_len.value

        data = out_buffer_p[:out_buffer_len.value]
        assert len(data) == out_buffer_len.value

        if out_buffer_p:
            memory.free(out_buffer_p)
            out_buffer_p = None

        if out_file is not None:
            try:
                return out_file.write(data)
            except AttributeError:
                with open(out_file, 'wb') as f:
                    return f.write(data)
        else:
            return data


libttfautohint = TALibrary()

ttfautohint = libttfautohint.ttfautohint
