from __future__ import print_function
import ttfautohint
import logging

log = logging.getLogger("ttfautohint")


def main(args=None):
    options = ttfautohint.options.parse_args(args)

    # `parse_args` can return None instead of raising SystemExit on invalid
    # arguments, when `args` are passed. When it's called with args=None
    # (e.g. from a console script's `main()`), SystemExit is propagated.
    if options is None:
        return 2

    logging.basicConfig(
        level=("DEBUG" if options["debug"] else
               "INFO" if options["verbose"] else "WARNING"),
        format="%(name)s: %(levelname)s: %(message)s",
    )

    try:
        ttfautohint.ttfautohint(**options)
    except ttfautohint.TAError as e:
        log.error(e)
        return e.rv


USAGE = "ttfautohint [OPTION]... [IN-FILE [OUT-FILE]]"

DESCRIPTION = """\
Replace hints in TrueType font IN-FILE and write output to OUT-FILE.
If OUT-FILE is missing, standard output is used instead;
if IN-FILE is missing also, standard input and output are used.

The new hints are based on FreeType's auto-hinter.

This program is a simple front-end to the `ttfautohint' library.
"""

EPILOG = """\
The program accepts both TTF and TTC files as input.
Use option -i only if you have a legal permission to modify the font.
The used PPEM value for option -p is FUnits per em, normally 2048.
With option -s, use default values for standard stem width and height,
otherwise they are derived from script-specific characters
resembling the shape of character `o'.

A hint set contains the optimal hinting for a certain PPEM value;
the larger the hint set range (as given by options -l and -r),
the more hint sets get computed, usually increasing the output font size.
The `gasp' table of the output file always enables grayscale hinting
for all sizes (limited by option -G, which is handled in the bytecode).
Increasing the value of -G does not increase the output font size.

Options -f and -D take a four-letter string that identifies a script.
Option -f sets the script used as a fallback for glyphs that can't be
associated with a known script.  By default, such glyphs are hinted;
if option -S is set, they are scaled only instead.  Option -D sets the
default script for handling OpenType features.

Possible four-letter string values are

  adlm (Adlam),
  arab (Arabic),
  armn (Armenian),
  avst (Avestan),
  bamu (Bamum),
  beng (Bengali),
  buhd (Buhid),
  cakm (Chakma),
  cans (Canadian Syllabics),
  cari (Carian),
  cher (Cherokee),
  copt (Coptic),
  cprt (Cypriot),
  cyrl (Cyrillic),
  deva (Devanagari),
  dsrt (Deseret),
  ethi (Ethiopic),
  geor (Georgian (Mkhedruli)),
  geok (Georgian (Khutsuri)),
  glag (Glagolitic),
  goth (Gothic),
  grek (Greek),
  gujr (Gujarati),
  guru (Gurmukhi),
  hebr (Hebrew),
  kali (Kayah Li),
  khmr (Khmer),
  khms (Khmer Symbols),
  knda (Kannada),
  lao (Lao),
  latn (Latin),
  latb (Latin Subscript Fallback),
  latp (Latin Superscript Fallback),
  lisu (Lisu),
  mlym (Malayalam),
  mong (Mongolian),
  mymr (Myanmar),
  nkoo (N'Ko),
  olck (Ol Chiki),
  orkh (Old Turkic),
  osge (Osage),
  osma (Osmanya),
  saur (Saurashtra),
  shaw (Shavian),
  sinh (Sinhala),
  sund (Sundanese),
  taml (Tamil),
  tavt (Tai Viet),
  telu (Telugu),
  tfng (Tifinagh),
  thai (Thai),
  vaii (Vai),
  none (no script).

A control instructions file contains entries of the form

  [<font idx>] <script> <feature> @ <glyph ids>

  [<font idx>] <script> <feature> w <stem widths>

  [<font idx>] <glyph id> l|r <points> [(<left offset>,<right offset>)]

  [<font idx>] <glyph id> n <points>

  [<font idx>] <glyph id> t|p <points> [x <shift>] [y <shift>] @ <ppems>

<font idx> is the current subfont, <glyph id> is a glyph name or index,
<glyph ids> is a set of <glyph id>s, <stem widths> is an unordered set of
integer stem widths in font units, <shift> is a real number in px,
<points> and <ppems> are integer ranges as with option `-X'.

<script> and <feature> are four-letter tags that define a style
the <glyph ids> are assigned to; possible values for <script> are the same
as with option -D, possible values for <feature> are

  c2cp (petite capitals from capitals),
  c2sc (small capitals from capitals),
  ordn (ordinals),
  pcap (petite capitals),
  ruby (ruby),
  sinf (scientific inferiors),
  smcp (small capitals),
  subs (subscript),
  sups (superscript),
  titl (titling).

`w' assigns stem widths to a style; the first value sets the default.
`l' (`r') creates one-point segments with direction left (right).
<left offset> and <right offset> specify offsets (in font units)
relative to the corresponding points to give the segments a length.
`n' removes points from horizontal segments, making them `weak' points.
`t' (`p') applies delta exceptions to the given points before (after) IUP.

`#' starts a line comment, which gets ignored.
Empty lines are ignored, too.

Key letters `l', `r', `n', `p', `t', `w', `x', and `y'
have the verbose aliases `left', `right', `nodir', `point', `touch',
`width', `xshift', and `yshift', respectively.

Report bugs to: freetype-devel@nongnu.org

ttfautohint home page: <http://www.freetype.org/ttfautohint>
"""
