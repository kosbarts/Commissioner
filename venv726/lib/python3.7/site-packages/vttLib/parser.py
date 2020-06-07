import string

from pyparsing import (
    Combine,
    Group,
    Literal,
    OneOrMore,
    Optional,
    ParseException,
    Regex,
    Suppress,
    Word,
    alphanums,
    alphas,
    cStyleComment,
    nestedExpr,
    nums,
    oneOf,
    pyparsing_common,
    tokenMap,
)

__all__ = ["AssemblyParser", "ParseException"]


VTT_MNEMONIC_FLAGS = {
    # Direction
    "X": "1",  # X axis
    "Y": "0",  # Y axis
    # Outline
    "O": "1",  # Use original outline
    "N": "0",  # Use gridfitted outline
    # Rounding or Line Relation
    "R": "1",  # Round distance; or perpedicular to line
    "r": "0",  # Do not round distance; or parallel to line
    # Reference Point Autoset
    "M": "1",  # Set rp0 to point number on the stack
    "m": "0",  # Do not set rp0
    # Reference Point Usage
    "1": "1",  # Use rp1
    "2": "0",  # Use rp2
    # Minimum Distance flag
    ">": "1",  # Obey minimum distance
    "<": "0",  # Do not obey minimum distance
    # Color (Distance Type)
    "Gr": "00",  # Gray
    "Bl": "01",  # Black
    "Wh": "10",  # White
}


alpha_upper = string.ascii_uppercase

mnemonic = Word(alpha_upper, bodyChars=alpha_upper + nums).setResultsName("mnemonic")

# XXX can't use pyparsing_common.signedInteger as the latest pyparsing 2.1.5
# has a bug which always converts them to floats. Remove this once 2.1.6 is
# published on PyPI.
signed_integer = (
    Regex(r"[+-]?\d+").setName("signed integer").setParseAction(tokenMap(int))
)

variable = Word(alphas, bodyChars=alphanums)

stack_item = Suppress(",") + (signed_integer | Suppress("*") | variable)

flag = oneOf(list(VTT_MNEMONIC_FLAGS.keys()))
# convert flag to binary string
flag.setParseAction(tokenMap(lambda t: VTT_MNEMONIC_FLAGS[t]))
flags = Combine(OneOrMore(flag)).setResultsName("flags")

delta_point_index = pyparsing_common.integer.setResultsName("point_index")
delta_rel_ppem = pyparsing_common.integer.setResultsName("rel_ppem")
delta_step_no = signed_integer.setResultsName("step_no")
# the step denominator is only used in VTT's DELTA[CP]* instructions,
# and must always be 8 (sic!), so we can suppress it.
delta_spec = (
    delta_point_index
    + Suppress("@")
    + delta_rel_ppem
    + delta_step_no
    + Optional(Literal("/8")).suppress()
)

delta = nestedExpr("(", ")", delta_spec, ignoreExpr=None)

deltas = Group(OneOrMore(delta)).setResultsName("deltas")

args = deltas | flags

stack_items = OneOrMore(stack_item).setResultsName("stack_items")

instruction = Group(
    mnemonic + Suppress("[") + Optional(args) + Suppress("]") + Optional(stack_items)
)

label = Word("#", alphanums)
jump_label = Group(Combine(label + Literal(":")).setResultsName("mnemonic"))
assignment = Group(
    variable.setResultsName("variable")
    + Literal("=").suppress()
    + label.setResultsName("label")
).setResultsName("assignment")
jump_mnemonic = oneOf(["JMPR", "JROT", "JROF"]).setResultsName("mnemonic")
jump = Group(
    jump_mnemonic
    + Suppress("[")
    + Suppress("]")
    + Suppress(",")
    + Suppress("(")
    + assignment
    + Suppress(")")
)

pragma_memonic = Word("#", bodyChars=alpha_upper).setResultsName("mnemonic")

pragma = Group(pragma_memonic + Optional(stack_items))

comment = cStyleComment.suppress()

# this is the only public class
AssemblyParser = OneOrMore(comment | jump_label | pragma | jump | instruction)


if __name__ == "__main__":
    import sys

    infile = sys.argv[1]
    with open(infile, "r") as fp:
        data = fp.read()

    tokens = AssemblyParser.parseString(data, parseAll=True)

    for i, t in enumerate(tokens):
        print(i, repr(t))
