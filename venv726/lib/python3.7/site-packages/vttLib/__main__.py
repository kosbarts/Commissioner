import logging
import os
import sys
from argparse import ArgumentParser

import fontTools.ttLib

import vttLib


def main(args=None):
    parser = ArgumentParser(
        prog="python -m vttLib",
        description="Dump, merge or compile Visual TrueType data with FontTools",
    )
    parser.add_argument("--version", action="version", version=vttLib.__version__)
    parser_group = parser.add_subparsers(title="sub-commands")
    parser_dumpfile = parser_group.add_parser(
        "dumpfile",
        description="Export VTT tables and 'maxp' values from a TTF into a TTX dump",
    )
    parser_mergefile = parser_group.add_parser(
        "mergefile",
        description="Import VTT source data stored in a TTX dump into a TTF.",
    )
    parser_compile = parser_group.add_parser(
        "compile",
        description=(
            "Generate 'fpgm', 'prep', 'cvt ' and 'glyf' programs from VTT assembly."
        ),
    )
    parser_dumpfile_from_ufo = parser_group.add_parser(
        "dumpfile_from_ufo", description="Export VTT data from UFO3 data to a TTX dump."
    )
    for subparser in (
        parser_compile,
        parser_dumpfile,
        parser_mergefile,
        parser_dumpfile_from_ufo,
    ):
        group = subparser.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="print more messages to console",
        )
        group.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="do not print messages to console",
        )

    parser_dumpfile.add_argument("infile", metavar="INPUT.ttf")
    parser_dumpfile.add_argument("outfile", nargs="?", metavar="OUTPUT.ttx")
    parser_dumpfile.set_defaults(func=vttLib.vtt_dump_file)

    parser_mergefile.add_argument("infile", metavar="INPUT.ttx")
    parser_mergefile.add_argument("outfile", metavar="OUTPUT.ttf")
    parser_mergefile.set_defaults(func=vttLib.vtt_merge_file)

    parser_compile.add_argument(
        "infile",
        metavar="INPUT.ttf",
        help="the source TTF font containing VTT TSI* tables",
    )
    parser_compile.add_argument(
        "--ship",
        action="store_true",
        help="remove all the TSI* tables from the output font.",
    )
    parser_compile.set_defaults(func=vttLib.vtt_compile)
    output_group = parser_compile.add_mutually_exclusive_group()
    output_group.add_argument(
        "outfile",
        nargs="?",
        metavar="OUTPUT.ttf",
        help=(
            "the destination TTF with compiled TrueType bytecode (default: "
            'INTPUT + "#{n}.ttf").'
        ),
    )
    output_group.add_argument(
        "-i",
        "--inplace",
        metavar=".bak",
        help="save input file in place, and create backup with specified extension",
    )
    output_group.add_argument(
        "-f",
        "--force-overwrite",
        action="store_true",
        help="overwrite existing input file (CAUTION!)",
    )

    parser_dumpfile_from_ufo.add_argument("infile", metavar="SOURCE.ufo")
    parser_dumpfile_from_ufo.add_argument("outfile", nargs="?", metavar="OUTPUT.ttx")
    parser_dumpfile_from_ufo.set_defaults(func=vttLib.vtt_move_ufo_data_to_file)

    options = parser.parse_args(args)

    if "quiet" in options or "verbose" in options:
        logging.basicConfig(
            level=(
                "ERROR" if options.quiet else "DEBUG" if options.verbose else "INFO"
            ),
            format="%(name)s: %(levelname)s: %(message)s",
        )

    try:
        if "func" in options:
            options.func(**vars(options))
        else:
            parser.print_help()
    except vttLib.VTTLibArgumentError as e:
        parser.error(e)


if __name__ == "__main__":
    sys.exit(main())
