import sys


PY3 = sys.version_info[0] >= 3

if PY3:
    text_type = basestring = str
    iterbytes = iter
else: # PY2
    text_type = unicode
    basestring = basestring
    import itertools
    import functools
    iterbytes = functools.partial(itertools.imap, ord)


def ensure_binary(s, encoding="ascii", errors="strict"):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    elif isinstance(s, bytes):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


def ensure_text(s, encoding="ascii", errors="strict"):
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    elif isinstance(s, text_type):
        return s
    else:
        raise TypeError("not expecting type '%s'" % type(s))


# for python 2 on Windows we need to wrap the io.open function in order
# to be able to reopen the standard stdin/stout streams in binary mode.
# By detault, they are opened in 'text' mode by the MSVC runtime, so
# we need to call setmode with the O_BINARY flag.
# In Python 3 the binary flag is always set (python itself takes care
# of the newline translation of standard streams)
if PY3:
    open = open
else:
    import io
    try:
        from msvcrt import setmode  # only available on Windows
    except ImportError:
        # on non-Windows platforms we can use the regular io.open
        open = io.open
    else:
        import os

        def open(file, mode='r', buffering=-1, encoding=None, errors=None,
                 newline=None, closefd=True):
            if isinstance(file, int):
                # the 'file' argument is an integer file descriptor
                fd = file
                if fd < 0:
                    raise ValueError('negative file descriptor')
                if setmode:
                    # `setmode` function sets the line-end translation and
                    # returns the value of the previous mode
                    fdcopy = os.dup(fd)
                    current_mode = setmode(fdcopy, os.O_BINARY)
                    if not (current_mode & os.O_BINARY):
                        # the binary mode was not set: use the copy
                        file = fdcopy
                        if closefd:
                            # close the original file descriptor
                            os.close(fd)
                        else:
                            # ensure the copy is closed when file is closed
                            closefd = True
                    else:
                        # original file already had binary flag, close copy
                        os.close(fdcopy)

            return io.open(
                file, mode, buffering, encoding, errors, newline, closefd)


try:
    from enum import IntEnum
except ImportError:
    from collections import OrderedDict, namedtuple

    # make do without the real Enum type, python3 only... :(
    def IntEnum(typename, field_names, start=1):

        @property
        def __members__(self):
            return OrderedDict([(k, getattr(self, k))
                                for k in self._fields])

        def __call__(self, value):
            if value not in self:
                raise ValueError("%s is not a valid %s" % (value, typename))
            return value

        base = namedtuple(typename, field_names)
        attributes = {"__members__": __members__,
                      "__call__": __call__}
        klass = type(typename, (base,), attributes)
        return klass._make(range(start, len(field_names) + start))
