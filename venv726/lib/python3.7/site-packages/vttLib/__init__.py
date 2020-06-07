import array
import io
import logging
import os
import re
import shutil
from collections import OrderedDict, defaultdict, deque, namedtuple

import ufoLib2
from fontTools.ttLib import (
    TTFont,
    TTLibError,
    identifierToTag,
    newTable,
    tagToIdentifier,
)
from fontTools.ttLib.tables._g_l_y_f import (
    ROUND_XY_TO_GRID,
    SCALED_COMPONENT_OFFSET,
    UNSCALED_COMPONENT_OFFSET,
    USE_MY_METRICS,
)
from fontTools.ttLib.tables.ttProgram import Program

import vttLib.transfer
from vttLib.parser import AssemblyParser, ParseException

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"

log = logging.getLogger(__name__)


MAXP_ATTRS = {
    "maxZones",
    "maxTwilightPoints",
    "maxStorage",
    "maxFunctionDefs",
    "maxInstructionDefs",
    "maxStackElements",
    "maxSizeOfInstructions",
}
LEGACY_VTT_DATA_FILES = (
    "com.daltonmaag.vttLib.plist",
    "com.github.fonttools.ttx/T_S_I__0.ttx",
    "com.github.fonttools.ttx/T_S_I__1.ttx",
    "com.github.fonttools.ttx/T_S_I__2.ttx",
    "com.github.fonttools.ttx/T_S_I__3.ttx",
    "com.github.fonttools.ttx/T_S_I__5.ttx",
)


class VTTLibError(TTLibError):
    pass


class VTTLibInvalidComposite(VTTLibError):
    pass


class VTTLibArgumentError(VTTLibError):
    pass


def set_cvt_table(font, data):
    data = re.sub(r"/\*.*?\*/", "", data, flags=re.DOTALL)
    values = array.array("h")
    # control values are defined in VTT Control Program as colon-separated
    # INDEX: VALUE pairs
    for m in re.finditer(r"^\s*([0-9]+)\s*:\s*(-?[0-9]+)", data, re.MULTILINE):
        index, value = int(m.group(1)), int(m.group(2))
        for _ in range(1 + index - len(values)):
            # missing CV indexes default to zero
            values.append(0)
        values[index] = value
    if len(values):
        if "cvt " not in font:
            font["cvt "] = newTable("cvt ")
        font["cvt "].values = values


OffsetComponent = namedtuple(
    "OffsetComponent",
    ["index", "x", "y", "round_to_grid", "use_my_metrics", "scaled_offset"],
)
AnchorComponent = namedtuple(
    "AnchorComponent", ["index", "first", "second", "use_my_metrics", "scaled_offset"]
)

JUMP_INSTRUCTIONS = frozenset(["JMPR", "JROT", "JROF"])


class JumpVariable(object):
    def __init__(self, positions=None, to_label=None, from_offset=None):
        if positions:
            self.positions = defaultdict(list, **positions)
        else:
            self.positions = defaultdict(list)
        self.to_label = to_label
        self.from_offset = from_offset
        self.relative_offset = None

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={}".format(k, v) for k, v in sorted(self.__dict__.items())),
        )


def split_functions(fpgm_tokens):
    funcs = []
    tokens = iter(fpgm_tokens)
    for t in tokens:
        mnemonic = t.mnemonic
        if mnemonic.startswith("FDEF"):
            body = [t]
            for t in tokens:
                body.append(t)
                if t.mnemonic.startswith("ENDF"):
                    break
            funcs.append(body)
            continue
        # some version of VTT has #PUSHON between function definitions
        if t.mnemonic.startswith("#PUSHON"):
            continue
        assert 0, "Unexpected token in fpgm: %s" % t
    return funcs


def merge_functions(functions, include=None):
    asm = []
    for line in "\n".join(functions).splitlines():
        asm.extend(line.strip().split())
    funcs = {}
    stack = []
    tokens = iter(asm)
    for token in tokens:
        if token.startswith("PUSH") or token.startswith("NPUSH"):
            for token in tokens:
                try:
                    num = int(token)
                    stack.append(num)
                except ValueError:
                    break
        if token.startswith("FDEF"):
            num = stack.pop()
            body = [token]
            for token in tokens:
                body.append(token)
                if token.startswith("ENDF"):
                    break
            funcs[num] = body
            continue
        assert 0, "Unexpected token in fpgm: %s" % token
    if include is not None:
        include = set(include)
        funcs = {num: body for num, body in funcs.items() if num in include}
    result = ["PUSH[]"] + [str(n) for n in sorted(funcs, reverse=True)]
    for num in sorted(funcs):
        result.extend(funcs[num])
    return result


def tokenize(data, parseAll=True):
    return AssemblyParser.parseString(data, parseAll=parseAll)


def transform(tokens, components=None):
    push_on = True
    push_indexes = [0]
    stream = [deque()]
    pos = 1
    if components is None:
        components = []
    jump_labels = {}
    jump_variables = defaultdict(JumpVariable)
    round_to_grid = False
    use_my_metrics = False
    scaled_offset = None
    for t in tokens:
        mnemonic = t.mnemonic

        if mnemonic == "OVERLAP":
            # this component flag is ignored by VTT so we ignore it too
            continue
        elif mnemonic == "USEMYMETRICS":
            use_my_metrics = True
            continue
        elif mnemonic == "SCALEDCOMPONENTOFFSET":
            scaled_offset = True
            continue
        elif mnemonic == "UNSCALEDCOMPONENTOFFSET":
            scaled_offset = False
            continue
        elif mnemonic == "OFFSET":
            round_to_grid = t.flags == "1"
            index, x, y = t.stack_items
            component = OffsetComponent(
                index, x, y, round_to_grid, use_my_metrics, scaled_offset
            )
            components.append(component)
            use_my_metrics = round_to_grid = False
            scaled_offset = None
            continue
        elif mnemonic == "ANCHOR":
            index, first, second = t.stack_items
            component = AnchorComponent(
                index, first, second, use_my_metrics, scaled_offset
            )
            components.append(component)
            use_my_metrics = False
            scaled_offset = None

        elif mnemonic == "#PUSHON":
            push_on = True
            continue
        elif mnemonic == "#PUSHOFF":
            push_on = False
            continue

        elif mnemonic == "#BEGIN":
            # XXX shouldn't these be ignored in #PUSHOFF mode?
            push_indexes.append(pos)
            stream.append(deque())
            pos += 1
            continue
        elif mnemonic == "#END":
            pi = push_indexes.pop()
            stack = stream[pi]
            if len(stack):
                stream[pi] = ["PUSH[]"] + list(stack)
            continue

        elif mnemonic == "#PUSH":
            assert len(t.stack_items) > 0

            last_type = None
            push_groups = []
            for item in t.stack_items:
                curr_type = type(item)
                if curr_type is not last_type:
                    push_groups.append([item])
                else:
                    push_groups[-1].append(item)
                last_type = curr_type

            column = 1
            for args in push_groups:
                is_variable = isinstance(args[0], str)
                if is_variable:
                    # initialize jump variables with the row and column in which
                    # they appear in the stream
                    for column, item in enumerate(args, start=1):
                        jump_variables[item].positions[pos].append(column)
                    # we explicitly push words for variable stack items to
                    # prevent optimization from breaking relative jump offsets
                    # Here '-999' is just an arbitrary word value which will
                    # be replaced with the actual relative offset
                    args = [-999] * len(args)
                    if len(args) > 8:
                        stream.append(["NPUSHW[]", len(args)] + args)
                    else:
                        stream.append(["PUSHW[]"] + args)
                else:
                    # let fonttools do the automatic push optimization for
                    # normal integer stack items
                    stream.append(["PUSH[]"] + args)
                pos += 1

            continue

        elif mnemonic.startswith(("DLTC", "DLTP", "DELTAP", "DELTAC")):
            assert push_on
            n = len(t.deltas)
            assert n > 0
            stack = stream[push_indexes[-1]]
            stack.appendleft(n)

            deltas = OrderedDict()
            for point_index, rel_ppem, step_no in reversed(t.deltas):
                deltas.setdefault(point_index, []).append((rel_ppem, step_no))

            for point_index, delta_specs in deltas.items():
                for rel_ppem, step_no in sorted(delta_specs, reverse=True):
                    if mnemonic.startswith(("DELTAP", "DELTAC")):
                        # DELTAC1 and DELTAP1: delta_base to delta_base+15
                        if mnemonic.endswith("1"):
                            delta_base = 9
                        # DELTAC2 and DELTAP2: delta_base+16 to delta_base+31
                        elif mnemonic.endswith("2"):
                            delta_base = 25
                        # DELTAC3 and DELTAP3: delta_base+32 to delta_base+47
                        elif mnemonic.endswith("3"):
                            delta_base = 41
                        # subtract the default 'delta base'
                        rel_ppem -= delta_base
                    stack.appendleft(point_index)
                    # -8: 0, ... -1: 7, 1: 8, ... 8: 15
                    selector = (step_no + 7) if step_no > 0 else (step_no + 8)
                    stack.appendleft((rel_ppem << 4) | selector)
            if mnemonic.startswith("DLT"):
                mnemonic = mnemonic.replace("DLT", "DELTA")
        elif mnemonic.startswith("#") and mnemonic.endswith(":"):
            # collect goto labels used with relative jump instructions
            label = mnemonic[:-1]
            jump_labels[label] = pos
            continue
        elif mnemonic in JUMP_INSTRUCTIONS:
            # record the current offset of jump instruction and the label which
            # it should jumps to
            variable, label = t.assignment
            jump_variables[variable].to_label = label
            jump_variables[variable].from_offset = pos
        else:
            if push_on:
                for i in reversed(t.stack_items):
                    stream[push_indexes[-1]].appendleft(i)
            else:
                assert not t.stack_items

        stream.append(["{}[{}]".format(mnemonic, t.flags)])
        pos += 1

    # calculate the relative offsets of each jump variables
    for variable in jump_variables.values():
        to_offset = jump_labels[variable.to_label]
        from_offset = variable.from_offset
        assert to_offset != from_offset
        start, end = sorted([from_offset, to_offset])
        sign = 1 if to_offset > from_offset else -1
        size = _calc_stream_size(stream[start:end])
        variable.relative_offset = sign * size

    # replace variable push args with the computed relative offsets
    for variable in jump_variables.values():
        for row, columns in variable.positions.items():
            for column in columns:
                stream[row][column] = variable.relative_offset

    assert len(push_indexes) == 1 and push_indexes[0] == 0, push_indexes
    stack = stream[0]
    if len(stack):
        stream[0] = ["PUSH[]"] + list(stack)

    return _concat_stream(stream)


def transform_assembly(data, name=None, components=None):
    data = data.strip()
    if not data:
        # input data just contains empty whitespace; skip it
        return ""

    tokens = tokenize(data)

    if name == "fpgm":
        # we transform each function in the fpgm individually, since different
        # functions may refer to jump variables with the same name, however
        # the relative jumps must occur within the same functions (I think...)
        funcs = [transform(f) for f in split_functions(tokens)]
        return merge_functions(funcs)
    else:
        return transform(tokens, components=components)


def _concat_stream(stream):
    return "\n".join(" ".join(str(i) for i in item) for item in stream if item)


def _calc_stream_size(stream):
    program = make_ft_program(_concat_stream(stream))
    return len(program.getBytecode())


def make_ft_program(assembly):
    program = Program()
    program.fromAssembly(assembly)
    # need to compile bytecode for PUSH optimization
    program._assemble()
    del program.assembly
    return program


_indentRE = re.compile("^FDEF|IF|ELSE\\[ \\]\t.+")
_unindentRE = re.compile("^ELSE|ENDF|EIF\\[ \\]\t.+")


def pformat_tti(program, preserve=True):
    from fontTools.ttLib.tables.ttProgram import _pushCountPat

    assembly = program.getAssembly(preserve=preserve)
    stream = io.StringIO()
    i = 0
    indent = 0
    nInstr = len(assembly)
    while i < nInstr:
        instr = assembly[i]
        if _unindentRE.match(instr):
            indent -= 1
        stream.write("  " * indent)
        stream.write(instr)
        stream.write("\n")
        m = _pushCountPat.match(instr)
        i = i + 1
        if m:
            nValues = int(m.group(1))
            line = []
            j = 0
            for j in range(nValues):
                if j and not (j % 25):
                    stream.write(" ".join(line))
                    stream.write("\n")
                    line = []
                line.append(assembly[i + j])
            stream.write("  " * indent)
            stream.write(" ".join(line))
            stream.write("\n")
            i = i + j + 1
        if _indentRE.match(instr):
            indent += 1
    return stream.getvalue()


def log_program_error(name, error):
    log.error(
        "An error occurred while parsing %sprogram:\n%s\n\n"
        % ('"%s" ' % name if name else "", error.markInputline())
    )


def make_program(vtt_assembly, name=None, components=None):
    try:
        ft_assembly = transform_assembly(vtt_assembly, name=name, components=components)
    except ParseException as e:
        log_program_error(name, e)
        raise VTTLibError(e)
    return make_ft_program(ft_assembly)


def make_glyph_program(vtt_assembly, name=None):
    components = []
    program = make_program(vtt_assembly, name, components)
    return program, components


def get_extra_assembly(font, name):
    if name not in ("cvt", "cvt ", "prep", "ppgm", "fpgm"):
        raise ValueError("Invalid name: %r" % name)
    if name == "prep":
        name = "ppgm"
    return get_vtt_program(font, name.strip())


def get_glyph_assembly(font, name):
    return get_vtt_program(font, name, is_glyph=True)


def get_glyph_talk(font, name):
    return get_vtt_program(font, name, is_talk=True, is_glyph=True)


def get_vtt_program(font, name, is_talk=False, is_glyph=False):
    tag = "TSI3" if is_talk else "TSI1"
    if tag not in font:
        raise VTTLibError("%s table not found" % tag)
    try:
        if is_glyph:
            data = font[tag].glyphPrograms[name]
        else:
            data = font[tag].extraPrograms[name]
    except KeyError:
        raise KeyError(
            "%s program missing from %s: '%s'"
            % ("Glyph" if is_glyph else "Extra", tag, name)
        )
    return data.replace("\r", "\n")


def set_extra_assembly(font, name, data):
    if name not in ("cvt", "cvt ", "prep", "ppgm", "fpgm"):
        raise ValueError("Invalid name: %r" % name)
    if name == "prep":
        name = "ppgm"
    set_vtt_program(font, name, data)


def set_glyph_assembly(font, name, data):
    set_vtt_program(font, name, data, is_glyph=True)


def set_glyph_talk(font, name, data):
    return set_vtt_program(font, name, data, is_talk=True, is_glyph=True)


def set_vtt_program(font, name, data, is_talk=False, is_glyph=False):
    tag = "TSI3" if is_talk else "TSI1"
    if tag not in font:
        raise VTTLibError("%s table not found" % tag)
    data = "\r".join(data.splitlines()).rstrip() + "\r"
    if is_glyph:
        font[tag].glyphPrograms[name] = data
    else:
        font[tag].extraPrograms[name] = data


def check_composite_info(name, glyph, vtt_components, glyph_order, check_flags=False):
    n_glyf_comps = len(glyph.components)
    n_vtt_comps = len(vtt_components)
    if n_vtt_comps != n_glyf_comps:
        raise VTTLibInvalidComposite(
            "'%s' has incorrect number of components: expected %d, "
            "found %d." % (name, n_glyf_comps, n_vtt_comps)
        )
    for i, comp in enumerate(glyph.components):
        vttcomp = vtt_components[i]
        base_name = comp.glyphName
        index = glyph_order.index(base_name)
        if vttcomp.index != index:
            raise VTTLibInvalidComposite(
                "Component %d in '%s' has incorrect index: "
                "expected %d, found %d." % (i, name, index, vttcomp.index)
            )
        if hasattr(comp, "firstPt"):
            if not hasattr(vttcomp, "first") and hasattr(vttcomp, "x"):
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has incorrect type: "
                    "expected ANCHOR[], found OFFSET[]." % (i, name)
                )
            if comp.firstPt != vttcomp.first:
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has wrong anchor point: expected"
                    " %d, found %d." % (i, name, comp.firstPt, vttcomp.first)
                )
            if comp.secondPt != vttcomp.second:
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has wrong anchor point: expected"
                    " %d, found %d." % (i, name, comp.secondPt, vttcomp.second)
                )
        else:
            assert hasattr(comp, "x")
            if not hasattr(vttcomp, "x") and hasattr(vttcomp, "first"):
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has incorrect type: "
                    "expected OFFSET[], found ANCHOR[]." % (i, name)
                )
            if comp.x != vttcomp.x:
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has wrong x offset: expected"
                    " %d, found %d." % (i, name, comp.x, vttcomp.x)
                )
            if comp.y != vttcomp.y:
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has wrong y offset: expected"
                    " %d, found %d." % (i, name, comp.y, vttcomp.y)
                )
            if check_flags and (
                (comp.flags & ROUND_XY_TO_GRID and not vttcomp.round_to_grid)
                or (not comp.flags & ROUND_XY_TO_GRID and vttcomp.round_to_grid)
            ):
                raise VTTLibInvalidComposite(
                    "Component %d in '%s' has wrong 'ROUND_XY_TO_GRID' flag."
                    % (i, name)
                )
        if not check_flags:
            continue
        if (comp.flags & USE_MY_METRICS and not vttcomp.use_my_metrics) or (
            not comp.flags & USE_MY_METRICS and vttcomp.use_my_metrics
        ):
            raise VTTLibInvalidComposite(
                "Component %d in '%s' has wrong 'USE_MY_METRICS' flag." % (i, name)
            )
        if (comp.flags & SCALED_COMPONENT_OFFSET and not vttcomp.scaled_offset) or (
            not comp.flags & SCALED_COMPONENT_OFFSET and vttcomp.scaled_offset
        ):
            raise VTTLibInvalidComposite(
                "Component %d in '%s' has wrong 'SCALED_COMPONENT_OFFSET' flag."
                % (i, name)
            )
        if (comp.flags & UNSCALED_COMPONENT_OFFSET and not vttcomp.scaled_offset) or (
            not comp.flags & UNSCALED_COMPONENT_OFFSET and vttcomp.scaled_offset
        ):
            raise VTTLibInvalidComposite(
                "Component %d in '%s' has wrong 'UNSCALED_COMPONENT_OFFSET' flag."
                "flag" % (i, name)
            )


_use_my_metrics = r"^USEMYMETRICS\[\][\r\n]?"
_overlap = r"^OVERLAP\[\][\r\n]?"
_scaled_component_offset = r"^(?:UN)?SCALEDCOMPONENTOFFSET\[\][\r\n]?"
_anchor = r"^ANCHOR\[\](?:, *-?[0-9]+){3}[\r\n]?"
_offset = r"^OFFSET\[[rR]\](?:, *-?[0-9]+){3}[\r\n]?"
composite_info_RE = re.compile(
    "(%s)|(%s)|(%s)|(%s)|(%s)"
    % (_use_my_metrics, _overlap, _scaled_component_offset, _anchor, _offset),
    re.MULTILINE,
)


def set_components_flags(glyph, components, vtt_version=6):
    assert len(components) == len(glyph.components)
    for i, comp in enumerate(glyph.components):
        vttcomp = components[i]
        if vttcomp.use_my_metrics:
            comp.flags |= USE_MY_METRICS
        else:
            comp.flags &= ~USE_MY_METRICS
        if vttcomp.round_to_grid:
            comp.flags |= ROUND_XY_TO_GRID
        else:
            comp.flags &= ~ROUND_XY_TO_GRID
        if vtt_version < 6 or vttcomp.scaled_offset is None:
            continue
        if vttcomp.scaled_offset:
            comp.flags |= SCALED_COMPONENT_OFFSET
            comp.flags &= ~UNSCALED_COMPONENT_OFFSET
        else:
            comp.flags |= UNSCALED_COMPONENT_OFFSET
            comp.flags &= ~SCALED_COMPONENT_OFFSET


def write_composite_info(glyph, glyph_order, data="", vtt_version=6):
    head = ""
    last = 0
    for m in composite_info_RE.finditer(data):
        start, end = m.span()
        head += data[last:start]
        last = end
    tail = ""
    if last < len(data):
        tail += data[last:]
    instructions = []
    for comp in glyph.components:
        if comp.flags & USE_MY_METRICS:
            instructions.append("USEMYMETRICS[]\n")
        if vtt_version >= 6:
            if comp.flags & SCALED_COMPONENT_OFFSET:
                instructions.append("SCALEDCOMPONENTOFFSET[]\n")
            if comp.flags & UNSCALED_COMPONENT_OFFSET:
                instructions.append("UNSCALEDCOMPONENTOFFSET[]\n")
        index = glyph_order.index(comp.glyphName)
        if hasattr(comp, "firstPt"):
            instructions.append(
                "ANCHOR[], %d, %d, %d\n" % (index, comp.firstPt, comp.secondPt)
            )
        else:
            flag = "R" if comp.flags & ROUND_XY_TO_GRID else "r"
            instructions.append(
                "OFFSET[%s], %d, %d, %d\n" % (flag, index, comp.x, comp.y)
            )
    return head, "".join(instructions), tail


def update_composites(font, glyphs=None, vtt_version=6):
    glyph_order = font.getGlyphOrder()
    if glyphs is None:
        glyphs = glyph_order
    glyf_table = font["glyf"]
    for glyph_name in glyphs:
        glyph = glyf_table[glyph_name]
        vtt_components = []
        try:
            data = get_glyph_assembly(font, glyph_name)
        except KeyError:
            # the glyph is not in the TSI1 table; create a new one
            data = ""
        else:
            # found glyph in TSI1 table; check it contains any VTT components;
            # 'vtt_components' list is updated in place; we don't care about
            # the return value (i.e. transformed FontTools assembly) here
            try:
                transform_assembly(data, components=vtt_components)
            except ParseException as e:
                log_program_error(glyph_name, e)
                raise VTTLibError(e)
        if not glyph.isComposite():
            if vtt_components:
                log.warning(
                    "Glyph '%s' contains components in VTT assembly but not"
                    "in glyf table; drop assembly" % glyph_name
                )
                set_glyph_assembly(font, glyph_name, "")
            continue
        new_data = "".join(write_composite_info(glyph, glyph_order, data, vtt_version))
        set_glyph_assembly(font, glyph_name, new_data)


def compile_instructions(font, ship=True):
    if "glyf" not in font:
        raise VTTLibError("Missing 'glyf' table; not a TrueType font")
    if "TSI1" not in font:
        raise VTTLibError("The font contains no 'TSI1' table")

    control_program = get_extra_assembly(font, "cvt")
    set_cvt_table(font, control_program)

    for tag in ("prep", "fpgm"):
        if tag not in font:
            font[tag] = newTable(tag)
        data = get_extra_assembly(font, tag)
        font[tag].program = make_program(data, tag)

    glyph_order = font.getGlyphOrder()
    glyf_table = font["glyf"]
    for glyph_name in glyph_order:
        try:
            data = get_glyph_assembly(font, glyph_name)
        except KeyError:
            continue
        program, components = make_glyph_program(data, glyph_name)
        if program or components:
            glyph = glyf_table[glyph_name]
            if components:
                if not glyph.isComposite():
                    log.warning(
                        "Glyph '%s' contains components in VTT assembly but "
                        "not in glyf table; drop assembly and skip "
                        "compilation" % glyph_name
                    )
                    set_glyph_assembly(font, glyph_name, "")
                else:
                    check_composite_info(glyph_name, glyph, components, glyph_order)
                    set_components_flags(glyph, components)
            if program:
                glyph.program = program

    if ship:
        for tag in ("TSI%s" % i for i in (0, 1, 2, 3, 5, "C")):
            if tag in font:
                del font[tag]


comment_re = r"/\*%s\*/[\r\n]*"
# strip the timestamps
gui_generated_re = re.compile(comment_re % (r" GUI generated .*?"))
vtt_compiler_re = re.compile(  # keep the VTT version
    comment_re % (r" (VTT [0-9]+\.[0-9][0-9A-Z]* compiler) .*?")
)
# strip glyph indexes
glyph_re = re.compile(comment_re % (r" (?:TT|VTTTalk) glyph [0-9]+.*?"))


def normalize_vtt_programs(font):
    for tag in ("cvt", "ppgm", "fpgm"):
        try:
            program = get_extra_assembly(font, tag)
        except KeyError:
            # extra program missing; nothing to normalize
            continue
        program = vtt_compiler_re.sub(r"/* \1 */\n", program)
        set_extra_assembly(font, tag, program)

    glyph_order = font.getGlyphOrder()
    for name in glyph_order:
        for is_talk in (True, False):
            try:
                program = get_vtt_program(font, name, is_talk, is_glyph=True)
            except KeyError:
                continue
            if is_talk:
                program = gui_generated_re.sub("", program)
            program = vtt_compiler_re.sub(r"/* \1 */\r", program)
            program = glyph_re.sub("", program)
            set_vtt_program(font, name, program, is_talk, is_glyph=True)

    if len(font["TSI3"].extraPrograms):
        # VTT sometimes stores 'reserved' data in TSI3 which isn't needed
        font["TSI3"].extraPrograms = {}


def subset_vtt_glyph_programs(font, glyph_names):
    for tag in ("TSI1", "TSI3"):
        programs = font[tag].glyphPrograms
        for name in list(programs.keys()):
            if name not in glyph_names:
                del programs[name]

    groups = font["TSI5"].glyphGrouping
    for name in list(groups.keys()):
        if name not in glyph_names:
            del groups[name]


def vtt_dump_file(infile, outfile=None, **_):
    """Write VTT data from a TTF to a TTX dump."""
    if not os.path.exists(infile):
        raise vttLib.VTTLibArgumentError("'%s' not found" % infile)

    if outfile is None:
        outfile = os.path.splitext(infile)[0] + "_VTT_Hinting.ttx"

    font = TTFont(infile)
    vttLib.transfer.dump_to_file(font, outfile)


def vtt_merge_file(infile, outfile=None, **_):
    """Write VTT data from a TTX dump to a TTF."""
    if not os.path.exists(infile):
        raise vttLib.VTTLibArgumentError("Input file '%s' not found" % infile)

    if not os.path.exists(outfile):
        raise vttLib.VTTLibArgumentError("Output file '%s' not found" % outfile)

    font = TTFont(outfile)
    vttLib.transfer.merge_from_file(font, infile)
    font.save(outfile)


def vtt_move_ufo_data_to_file(infile, outfile=None, **_):
    """Write VTT data from UFO data to a TTX dump."""
    if not os.path.exists(infile) or not os.path.isdir(infile):
        raise vttLib.VTTLibArgumentError(
            "Input UFO '%s' not found or not a directory." % infile
        )

    if outfile is None:
        outfile = os.path.splitext(infile)[0] + "_VTT_Hinting.ttx"

    ufo = ufoLib2.Font.open(infile)
    vttLib.transfer.copy_from_ufo_data_to_file(ufo, outfile)
    ufo.save()


def vtt_compile(
    infile, outfile=None, ship=False, inplace=None, force_overwrite=False, **_
):
    if not os.path.exists(infile):
        raise vttLib.VTTLibArgumentError("Input TTF '%s' not found." % infile)

    font = TTFont(infile)

    if outfile:
        pass
    elif inplace:
        # create (and overwrite exising) backup first
        import shutil

        shutil.copyfile(infile, infile + inplace)
        outfile = infile
    elif force_overwrite:
        # save to input file (no backup)
        outfile = infile
    else:
        # create new unique output file
        from fontTools.ttx import makeOutputFileName

        outfile = makeOutputFileName(infile, None, ".ttf")

    vttLib.compile_instructions(font, ship=ship)
    font.save(outfile)
