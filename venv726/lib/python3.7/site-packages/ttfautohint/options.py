import sys
import os
from collections import OrderedDict
from ttfautohint._compat import (
    ensure_binary, ensure_text, basestring, open, IntEnum,
)

USER_OPTIONS = dict(
    in_file=None,
    in_buffer=None,
    out_file=None,
    control_file=None,
    control_buffer=None,
    reference_file=None,
    reference_buffer=None,
    reference_index=0,
    reference_name=None,
    hinting_range_min=8,
    hinting_range_max=50,
    hinting_limit=200,
    hint_composites=False,
    adjust_subglyphs=False,
    increase_x_height=14,
    x_height_snapping_exceptions="",
    windows_compatibility=False,
    default_script="latn",
    fallback_script="none",
    fallback_scaling=False,
    symbol=False,
    fallback_stem_width=0,
    ignore_restrictions=False,
    family_suffix=None,
    detailed_info=False,
    no_info=False,
    TTFA_info=False,
    dehint=False,
    epoch=None,
    debug=False,
    verbose=False,
)

StemWidthMode = IntEnum("StemWidthMode",
                        [
                            "NATURAL",    # -1
                            "QUANTIZED",  # 0
                            "STRONG",     # 1
                        ],
                        start=-1)

STEM_WIDTH_MODE_OPTIONS = OrderedDict([
    ("gray_stem_width_mode", StemWidthMode.QUANTIZED),
    ("gdi_cleartype_stem_width_mode", StemWidthMode.STRONG),
    ("dw_cleartype_stem_width_mode", StemWidthMode.QUANTIZED),
])

USER_OPTIONS.update(STEM_WIDTH_MODE_OPTIONS)

# Deprecated; use stem width mode options
STRONG_STEM_WIDTH_OPTIONS = dict(
    gdi_cleartype_strong_stem_width=True,
    gray_strong_stem_width=False,
    dw_cleartype_strong_stem_width=False,
)

PRIVATE_OPTIONS = frozenset([
    "in_buffer_len",
    "control_buffer_len",
    "reference_buffer_len",
    "out_buffer",
    "out_buffer_len",
    "error_string",
    "alloc_func",
    "free_func",
    "info_callback",
    "info_post_callback",
    "info_callback_data",
    "progress_callback",
    "progress_callback_data",
    "error_callback",
    "error_callback_data",
])

ALL_OPTIONS = frozenset(USER_OPTIONS) | PRIVATE_OPTIONS

# used when the control file does not have a name on the filesystem
CONTROL_NAME_FALLBACK = u"<control-instructions>"


def validate_options(kwargs):
    opts = {k: kwargs.pop(k, USER_OPTIONS[k]) for k in USER_OPTIONS}
    if kwargs:
        raise TypeError(
            "unknown keyword argument%s: %s" % (
                "s" if len(kwargs) > 1 else "",
                ", ".join(repr(k) for k in kwargs)))

    if opts["no_info"] and opts["detailed_info"]:
        raise ValueError("no_info and detailed_info are mutually exclusive")

    in_file, in_buffer = opts.pop("in_file"), opts.pop("in_buffer")
    if in_file is None and in_buffer is None:
        raise ValueError("No input file or buffer provided")
    elif in_file is not None and in_buffer is not None:
        raise ValueError("in_file and in_buffer are mutually exclusive")
    if in_file is not None:
        try:
            in_buffer = in_file.read()
        except AttributeError:
            with open(in_file, "rb") as f:
                in_buffer = f.read()
    if not isinstance(in_buffer, bytes):
        raise TypeError("in_buffer type must be bytes, not %s"
                        % type(in_buffer).__name__)
    opts['in_buffer'] = in_buffer
    opts['in_buffer_len'] = len(in_buffer)

    control_file = opts.pop('control_file')
    control_buffer = opts.pop('control_buffer')
    if control_file is not None:
        if control_buffer is not None:
            raise ValueError(
                "control_file and control_buffer are mutually exclusive")
        try:
            control_buffer = control_file.read()
        except AttributeError:
            with open(control_file, "rt", encoding="utf-8") as f:
                control_buffer = f.read()
            opts["control_name"] = control_file
        else:
            try:
                opts["control_name"] = control_file.name
            except AttributeError:
                pass
    if control_buffer is not None:
        opts['control_buffer'] = ensure_binary(control_buffer, "utf-8")
        opts['control_buffer_len'] = len(control_buffer)
    if "control_name" in opts:
        opts["control_name"] = ensure_text(
            opts["control_name"], encoding=sys.getfilesystemencoding())
    else:
        opts["control_name"] = CONTROL_NAME_FALLBACK

    reference_file = opts.pop('reference_file')
    reference_buffer = opts.pop('reference_buffer')
    if reference_file is not None:
        if reference_buffer is not None:
            raise ValueError(
                "reference_file and reference_buffer are mutually exclusive")
        try:
            reference_buffer = reference_file.read()
        except AttributeError:
            with open(reference_file, "rb") as f:
                reference_buffer = f.read()
            if opts["reference_name"] is None:
                opts["reference_name"] = reference_file
        else:
            if opts["reference_name"] is None:
                try:
                    opts["reference_name"] = reference_file.name
                except AttributeError:
                    pass
    if reference_buffer is not None:
        if not isinstance(reference_buffer, bytes):
            raise TypeError("reference_buffer type must be bytes, not %s"
                            % type(reference_buffer).__name__)
        opts['reference_buffer'] = reference_buffer
        opts['reference_buffer_len'] = len(reference_buffer)
    if opts["reference_name"] is not None:
        opts["reference_name"] = ensure_binary(
            opts["reference_name"], encoding=sys.getfilesystemencoding())

    for key in ('default_script', 'fallback_script',
                'x_height_snapping_exceptions'):
        opts[key] = ensure_binary(opts[key])

    if opts['epoch'] is not None:
        from ctypes import c_ulonglong
        opts['epoch'] = c_ulonglong(opts['epoch'])

    if opts["family_suffix"] is not None:
        opts["family_suffix"] = ensure_text(opts["family_suffix"])

    for mode_option in STEM_WIDTH_MODE_OPTIONS:
        # raises ValueError if integer value is not a valid stem width mode
        opts[mode_option] = StemWidthMode(opts[mode_option])

    return opts


def format_varargs(**options):
    items = sorted((k, v) for k, v in options.items()
                   if k in ALL_OPTIONS and v is not None)
    format_string = b", ".join(ensure_binary(k.replace("_", "-"))
                               for k, v in items)
    values = tuple(v for k, v in items)
    return format_string, values


def strong_stem_width(s):
    if len(s) > 3:
        import argparse
        raise argparse.ArgumentTypeError(
            "string can only contain up to 3 letters")
    valid = {
        "g": "gray_stem_width_mode",
        "G": "gdi_cleartype_stem_width_mode",
        "D": "dw_cleartype_stem_width_mode"}
    chars = set(s)
    invalid = chars - set(valid)
    if invalid:
        import argparse
        raise argparse.ArgumentTypeError(
            "invalid value: %s" % ", ".join(
                repr(v) for v in sorted(invalid)))
    result = {}
    for char, opt_name in valid.items():
        is_strong = char in chars
        result[opt_name] = (StemWidthMode.STRONG if is_strong
                            else StemWidthMode.QUANTIZED)
    return result


def stem_width_mode(s):
    if len(s) != 3:
        import argparse
        raise argparse.ArgumentTypeError(
            "Stem width mode string must consist of exactly three letters")
    modes = {k[0].lower(): v
             for k, v in StemWidthMode.__members__.items()}
    result = {}
    for i, option in enumerate(STEM_WIDTH_MODE_OPTIONS):
        m = s[i]
        if m not in modes:
            import argparse
            letters = sorted(repr(k) for k in modes)
            raise argparse.ArgumentTypeError(
                "Stem width mode letter for %s must be %s, or %s"
                % (option, ", ".join(letters[:-1]), letters[-1]))
        result[option] = modes[m]
    return result


def stdin_or_input_path_type(s):
    # the special argument "-" means sys.stdin
    if s == "-":
        try:
            if sys.stdin.isatty():  # ignore if interactive
                return None
            return open(sys.stdin.fileno(), mode="rb", closefd=False)
        except (AttributeError, IOError):
            # if stdout was redirected (e.g. inside pytest), fileno may raise
            # io.UnsupportedOperation
            return None
    return s


def stdout_or_output_path_type(s):
    # the special argument "-" means sys.stdout
    if s == "-":
        try:
            if sys.stdout.isatty():  # ignore if interactive
                return None
            return open(sys.stdout.fileno(), mode="wb", closefd=False)
        except (AttributeError, IOError):
            # if stdout was redirected (e.g. inside pytest), fileno may raise
            # io.UnsupportedOperation
            return None
    return s


def parse_args(args=None):
    """Parse command line arguments and return a dictionary of options
    for ttfautohint.ttfautohint function.

    `args` can be either None, a list of strings, or a single string,
    that is split into individual options with `shlex.split`.

    When `args` is None, the console's default sys.argv are used, and any
    SystemExit exceptions raised by argparse are propagated.

    If args is a string list or a string, it is assumed that the function
    was not called from a console script's `main` entry point, but from
    other client code, and thus the SystemExit exceptions are muted and
    a `None` value is returned.
    """
    import argparse
    from ttfautohint import __version__, libttfautohint
    from ttfautohint.cli import USAGE, DESCRIPTION, EPILOG

    version_string = "ttfautohint-py %s (libttfautohint %s)" % (
        __version__, libttfautohint.version_string)

    if args is None:
        capture_sys_exit = False
    else:
        capture_sys_exit = True
        if isinstance(args, basestring):
            import shlex
            args = shlex.split(args)

    parser = argparse.ArgumentParser(
        prog="ttfautohint",
        usage=USAGE,
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "in_file", nargs="?", metavar="IN-FILE", default="-",
        type=stdin_or_input_path_type,
        help="input file (default: standard input)")
    parser.add_argument(
        "out_file", nargs="?", metavar="OUT-FILE", default="-",
        type=stdout_or_output_path_type,
        help="output file (default: standard output)")
    parser.add_argument(
        "--debug", action="store_true", help="print debugging information")

    stem_width_group = parser.add_mutually_exclusive_group(required=False)
    stem_width_group.add_argument(
        "-a", "--stem-width-mode", type=stem_width_mode, metavar="S",
        default=STEM_WIDTH_MODE_OPTIONS,
        help=("select stem width mode for grayscale, GDI ClearType, and DW "
              "ClearType, where S is a string of three letters with possible "
              "values 'n' for natural, 'q' for quantized, and 's' for strong "
              "(default: qsq)"))
    stem_width_group.add_argument(  # deprecated
        "-w", "--strong-stem-width", type=strong_stem_width, metavar="S",
        help=argparse.SUPPRESS)

    parser.add_argument(
        "-c", "--composites", dest="hint_composites", action="store_true",
        help="hint glyph composites also")
    parser.add_argument(
        "-d", "--dehint", action="store_true", help="remove all hints")
    parser.add_argument(
        "-D", "--default-script", metavar="SCRIPT",
        default=USER_OPTIONS["default_script"],
        help="set default OpenType script (default: %(default)s)")
    parser.add_argument(
        "-f", "--fallback-script", metavar="SCRIPT",
        default=USER_OPTIONS["fallback_script"],
        help="set fallback script (default: %(default)s)")
    parser.add_argument(
        "-F", "--family-suffix", metavar="SUFFIX",
        help="append SUFFIX to the family name string(s) in the `name' table")
    parser.add_argument(
        "-G", "--hinting-limit", type=int, metavar="PPEM",
        default=USER_OPTIONS["hinting_limit"],
        help=("switch off hinting above this PPEM value (default: "
              "%(default)s); value 0 means no limit"))
    parser.add_argument(
        "-H", "--fallback-stem-width", type=int, metavar="UNITS",
        default=USER_OPTIONS["fallback_stem_width"],
        help=("set fallback stem width (default: %(default)s font units at "
              "2048 UPEM)"))
    parser.add_argument(
        "-i", "--ignore-restrictions", action="store_true",
        help="override font license restrictions")
    parser.add_argument(
        "-I", "--detailed-info", action="store_true",
        help=("add detailed ttfautohint info to the version string(s) in "
              "the `name' table"))
    parser.add_argument(
        "-l", "--hinting-range-min", type=int, metavar="PPEM",
        default=USER_OPTIONS["hinting_range_min"],
        help="the minimum PPEM value for hint sets (default: %(default)s)")
    parser.add_argument(
        "-m", "--control-file", metavar="FILE",
        help="get control instructions from FILE")
    parser.add_argument(
        "-n", "--no-info", action="store_true",
        help=("don't add ttfautohint info to the version string(s) in the "
              "`name' table"))
    parser.add_argument(
        "-p", "--adjust-subglyphs", action="store_true",
        help="handle subglyph adjustments in exotic fonts")
    parser.add_argument(
        "-r", "--hinting-range-max", type=int, metavar="PPEM",
        default=USER_OPTIONS["hinting_range_max"],
        help="the maximum PPEM value for hint sets (default: %(default)s)")
    parser.add_argument(
        "-R", "--reference", dest="reference_file", metavar="FILE",
        help="derive blue zones from reference font FILE")
    parser.add_argument(
        "-s", "--symbol", action="store_true",
        help="input is symbol font")
    parser.add_argument(
        "-S", "--fallback-scaling", action="store_true",
        help="use fallback scaling, not hinting")
    parser.add_argument(
        "-t", "--ttfa-table", action="store_true", dest="TTFA_info",
        help="add TTFA information table")
    parser.add_argument(
        "-T", "--ttfa-info", dest="show_TTFA_info", action="store_true",
        help="display TTFA table in IN-FILE and exit")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="show progress information")
    parser.add_argument(
        "-V", "--version", action="version",
        version=version_string,
        help="print version information and exit")
    parser.add_argument(
        "-W", "--windows-compatibility", action="store_true",
        help=("add blue zones for `usWinAscent' and `usWinDescent' to avoid "
              "clipping"))
    parser.add_argument(
        "-x", "--increase-x-height", type=int, metavar="PPEM",
        default=USER_OPTIONS["increase_x_height"],
        help=("increase x height for sizes in the range 6<=PPEM<=N; value "
              "0 switches off this feature (default: %(default)s)"))
    parser.add_argument(
        "-X", "--x-height-snapping-exceptions", metavar="STRING",
        default=USER_OPTIONS["x_height_snapping_exceptions"],
        help=('specify a comma-separated list of x-height snapping exceptions'
              ', for example "-9, 13-17, 19" (default: "%(default)s")'))
    parser.add_argument(
        "-Z", "--reference-index", type=int, metavar="NUMBER",
        default=USER_OPTIONS["reference_index"],
        help="face index of reference font (default: %(default)s)")

    try:
        options = vars(parser.parse_args(args))
    except SystemExit:
        if capture_sys_exit:
            return None
        raise

    # if either input/output are interactive, print help and exit
    if (not capture_sys_exit and
            (options["in_file"] is None or options["out_file"] is None)):
        parser.print_help()
        parser.exit(1)

    # check SOURCE_DATE_EPOCH environment variable
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch:
        try:
            options["epoch"] = int(source_date_epoch)
        except ValueError:
            import warnings
            warnings.warn(
                UserWarning("invalid SOURCE_DATE_EPOCH: %r" % source_date_epoch))

    if options.pop("show_TTFA_info"):
        # TODO use fonttools to dump TTFA table?
        raise NotImplementedError()

    stem_width_options = options.pop("stem_width_mode")
    strong_stem_width_options = options.pop("strong_stem_width")
    if strong_stem_width_options:
        import warnings
        warnings.warn(
            UserWarning("Option '-w' is deprecated! Use option '-a' instead"))
        stem_width_options = strong_stem_width_options
    options.update(stem_width_options)

    return options
