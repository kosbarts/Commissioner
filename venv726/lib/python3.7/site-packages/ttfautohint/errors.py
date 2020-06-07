from ctypes import (
    CFUNCTYPE, Structure, c_int, c_char_p, c_uint, c_void_p, cast, POINTER,
    py_object, string_at, c_char, addressof,
)


# error codes from ttfautohint-errors.h
TA_Err_Ok = 0x00
TA_Err_Invalid_FreeType_Version = 0x0E
TA_Err_Missing_Legal_Permission = 0x0F
TA_Err_Invalid_Stream_Write = 0x5F
TA_Err_Hinter_Overflow = 0xF0
TA_Err_Missing_Glyph = 0xF1
TA_Err_Missing_Unicode_CMap = 0xF2
TA_Err_Missing_Symbol_CMap = 0xF3
TA_Err_Canceled = 0xF4
TA_Err_Already_Processed = 0xF5
TA_Err_Invalid_Font_Type = 0xF6
TA_Err_Unknown_Argument = 0xF7
TA_Err_XHeightSnapping_Invalid_Character = 0x101
TA_Err_XHeightSnapping_Overflow = 0x102
TA_Err_XHeightSnapping_Invalid_Range = 0x103
TA_Err_XHeightSnapping_Overlapping_Ranges = 0x104
TA_Err_XHeightSnapping_Not_Ascending = 0x105
TA_Err_XHeightSnapping_Allocation_Error = 0x106
TA_Err_Control_Syntax_Error = 0x201
TA_Err_Control_Invalid_Font_Index = 0x202
TA_Err_Control_Invalid_Glyph_Index = 0x203
TA_Err_Control_Invalid_Glyph_Name = 0x204
TA_Err_Control_Invalid_Character = 0x205
TA_Err_Control_Invalid_Style = 0x206
TA_Err_Control_Invalid_Script = 0x207
TA_Err_Control_Invalid_Feature = 0x208
TA_Err_Control_Invalid_Shift = 0x209
TA_Err_Control_Invalid_Offset = 0x20A
TA_Err_Control_Invalid_Range = 0x20B
TA_Err_Control_Invalid_Glyph = 0x20C
TA_Err_Control_Overflow = 0x20D
TA_Err_Control_Overlapping_Ranges = 0x20E
TA_Err_Control_Ranges_Not_Ascending = 0x20F
TA_Err_Control_Allocation_Error = 0x210
TA_Err_Control_Flex_Error = 0x211
TA_Err_Control_Too_Much_Widths = 0x212


class TAError(Exception):

    def __init__(self, rv, error_string=None, control_name=None, errlinenum=0,
                 errline=None, errpos=-1):
        self.rv = int(rv)

        if error_string is not None:
            error_string = error_string.decode("utf-8", errors="replace")
        self.error_string = error_string

        self.control_name = control_name
        self.errlinenum = int(errlinenum)

        if errline is not None:
            errline = errline.decode("utf-8", errors="replace")
        self.errline = errline
        self.errpos = int(errpos)

    def __str__(self):
        error = self.rv
        error_string = self.error_string
        errlinenum = self.errlinenum
        errline = self.errline
        errpos = self.errpos

        if error == TA_Err_Invalid_FreeType_Version:
            s = ("FreeType version 2.4.5 or higher is needed.\n"
                 "Perhaps using a wrong FreeType DLL?")
        elif error == TA_Err_Invalid_Font_Type:
            s = ("This font is not a valid font in SFNT format with "
                 "TrueType outlines.\n"
                 "In particular, CFF outlines are not supported.")
        elif error == TA_Err_Already_Processed:
            s = "This font has already been processed with ttfautohint"
        elif error == TA_Err_Missing_Legal_Permission:
            s = ("Bit 1 in the `fsType' field of the `OS/2' table is set:\n"
                 "This font must not be modified without permission of the "
                 "legal owner.\n"
                 "Use command line option `-i' to continue if you have such "
                 "a permission.")
        elif error == TA_Err_Missing_Unicode_CMap:
            s = "No Unicode character map"
        elif error == TA_Err_Missing_Symbol_CMap:
            s = "No symbol character map"
        elif error == TA_Err_Missing_Glyph:
            s = ("No glyph for a standard character to derive standard "
                 "width and height.\n"
                 "Please check the documentation for a list of script-"
                 "specific standard characters,\n"
                 "or use option `--symbol'.")
        if error >= 0x100 and error < 0x200:
            s = ("An error with code 0x%03X occurred while parsing the "
                 "argument of option `-X'" % error)
            s += (":" if errline else ".")
            if errline:
                s += "\n  %s" % errline
                if errpos > -1:
                    s += "\n  %s^" % (" "*errpos)
        elif error >= 0x200 and error < 0x300:
            s = "%s:" % self.control_name
            if errlinenum > -1:
                s += "%d:" % errlinenum
            if errpos > -1 and errline:
                s += "%r:" % errpos
            if error_string:
                s += " %s" % error_string
            s += " (0x%02X)" % error
            if errline:
                s += "\n  %s" % errline
                if errpos > -1:
                    s += "\n  %s^" % (" "*errpos)
        elif error >= 0x300 and error < 0x400:
            error -= 0x300
            s = "error while loading the reference font"
            if error_string:
                s += ": %s" % error_string
            s += " (0x%02X)" % error
        else:
            s = "0x%02X" % error
            if error_string:
                s += ": %s" % error_string

        return s


class ErrorData(Structure):

    _fields_ = [
        ("kwargs", py_object),
    ]

    def __init__(self, control_name=None):
        kwargs = dict(control_name=control_name)
        super(ErrorData, self).__init__(kwargs)


@CFUNCTYPE(None, c_int, c_char_p, c_uint, POINTER(c_char), POINTER(c_char),
           c_void_p)
def error_callback(error, error_string, errlinenum, errline, errpos, user):
    e = cast(user, POINTER(ErrorData))[0]
    if not error:
        return
    e.kwargs["error_string"] = error_string
    e.kwargs["errlinenum"] = errlinenum
    if not errline:
        return
    e.kwargs["errline"] = string_at(errline)
    if errpos:
        e.kwargs["errpos"] = (addressof(errpos.contents) -
                              addressof(errline.contents) + 1)
