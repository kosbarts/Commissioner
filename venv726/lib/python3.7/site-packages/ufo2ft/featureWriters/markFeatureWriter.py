from __future__ import print_function, division, absolute_import, unicode_literals
import re
from collections import OrderedDict
from functools import partial
import itertools
from fontTools.misc.py23 import tostr, tounicode
from fontTools.misc.fixedTools import otRound
from ufo2ft.featureWriters import BaseFeatureWriter, ast
from ufo2ft.util import unicodeInScripts, classifyGlyphs
from ufo2ft.fontInfoData import getAttrWithFallback


class AbstractMarkPos(object):
    """Object containing all the mark attachments for glyph 'name'.
    The 'marks' is a list of NamedAnchor objects.
    Provides methods to filter marks given some callable, and convert
    itself to feaLib AST 'pos' statements for mark2base, mark2liga and
    mark2mark lookups.
    """

    Statement = None

    def __init__(self, name, marks):
        self.name = name
        self.marks = marks

    def _filterMarks(self, include):
        return [anchor for anchor in self.marks if include(anchor)]

    def _marksAsAST(self):
        return [
            (ast.Anchor(x=otRound(anchor.x), y=otRound(anchor.y)), anchor.markClass)
            for anchor in sorted(self.marks, key=lambda a: a.name)
        ]

    def asAST(self):
        marks = self._marksAsAST()
        return self.Statement(ast.GlyphName(self.name), marks)

    def __str__(self):
        return self.asAST().asFea()  # pragma: no cover

    def filter(self, include):
        marks = self._filterMarks(include)
        return self.__class__(self.name, marks) if any(marks) else None


class MarkToBasePos(AbstractMarkPos):

    Statement = ast.MarkBasePosStatement


class MarkToMarkPos(AbstractMarkPos):

    Statement = ast.MarkMarkPosStatement


class MarkToLigaPos(AbstractMarkPos):

    Statement = ast.MarkLigPosStatement

    def _filterMarks(self, include):
        return [
            [anchor for anchor in component if include(anchor)]
            for component in self.marks
        ]

    def _marksAsAST(self):
        return [
            [
                (ast.Anchor(x=otRound(anchor.x), y=otRound(anchor.y)), anchor.markClass)
                for anchor in sorted(component, key=lambda a: a.name)
            ]
            for component in self.marks
        ]


MARK_PREFIX = LIGA_SEPARATOR = "_"
LIGA_NUM_RE = re.compile(r".*?(\d+)$")


def parseAnchorName(
    anchorName,
    markPrefix=MARK_PREFIX,
    ligaSeparator=LIGA_SEPARATOR,
    ligaNumRE=LIGA_NUM_RE,
    ignoreRE=None,
):
    """Parse anchor name and return a tuple that specifies:
    1) whether the anchor is a "mark" anchor (bool);
    2) the "key" name of the anchor, i.e. the name after stripping all the
       prefixes and suffixes, which identifies the class it belongs to (str);
    3) An optional number (int), starting from 1, which identifies that index
       of the ligature component the anchor refers to.

    The 'ignoreRE' argument is an optional regex pattern (str) identifying
    sub-strings in the anchor name that should be ignored when parsing the
    three elements above.
    """
    number = None
    if ignoreRE is not None:
        anchorName = re.sub(ignoreRE, "", anchorName)

    m = ligaNumRE.match(anchorName)
    if not m:
        key = anchorName
    else:
        number = m.group(1)
        key = anchorName.rstrip(number)
        separator = ligaSeparator
        if key.endswith(separator):
            assert separator
            key = key[: -len(separator)]
            number = int(number)
        else:
            # not a valid ligature anchor name
            key = anchorName
            number = None

    if anchorName.startswith(markPrefix) and key:
        if number is not None:
            raise ValueError("mark anchor cannot be numbered: %r" % anchorName)
        isMark = True
        key = key[len(markPrefix) :]
        if not key:
            raise ValueError("mark anchor key is nil: %r" % anchorName)
    else:
        isMark = False

    return isMark, key, number


class NamedAnchor(object):
    """A position with a name, and an associated markClass."""

    __slots__ = ("name", "x", "y", "isMark", "key", "number", "markClass")

    # subclasses can customize these to use different anchor naming schemes
    markPrefix = MARK_PREFIX
    ignoreRE = None
    ligaSeparator = LIGA_SEPARATOR
    ligaNumRE = LIGA_NUM_RE

    def __init__(self, name, x, y, markClass=None):
        self.name = tounicode(name)
        self.x = x
        self.y = y
        isMark, key, number = parseAnchorName(
            name,
            markPrefix=self.markPrefix,
            ligaSeparator=self.ligaSeparator,
            ligaNumRE=self.ligaNumRE,
            ignoreRE=self.ignoreRE,
        )
        if number is not None:
            if number < 1:
                raise ValueError("ligature component indexes must start from 1")
        else:
            assert key, name
        self.isMark = isMark
        self.key = key
        self.number = number
        self.markClass = markClass

    @property
    def markAnchorName(self):
        return self.markPrefix + self.key

    def __repr__(self):
        items = ("%s=%r" % (tostr(k), getattr(self, k)) for k in ("name", "x", "y"))
        return tostr("%s(%s)") % (type(self).__name__, ", ".join(items))


class MarkFeatureWriter(BaseFeatureWriter):
    """Generates a mark, mkmk, abvm and blwm features based on glyph anchors.

    The default mode is 'skip': i.e. if any of the supported features is
    already present in the feature file, it is not generated again.

    The optional 'append' mode will add extra lookups to already existing
    features, if any. New markClass definitions with unique names are
    generated when the mark anchors from UFO glyphs are different from those
    already defined in the feature file, otherwise the existing markClass
    definitions are reused in the newly appended lookups.

    Anchors prefixed with "_" are considered mark anchors; any glyph
    containing those is as such considered a mark glyph, thus added to
    markClass definitions, and in mark-to-mark lookups (if the glyph also
    contains other non-underscore-prefixed anchors).

    Anchors suffixed with a number, e.g. "top_1", "bottom_2", etc., are used
    for ligature glyphs. The number refers to the index (counting from 1) of
    the ligature component where the mark is meant to be attached.

    It is possible that a ligature component has no marks defined, in which
    case one can have an anchor with an empty name and only the number (e.g.
    '_3'), which is encoded as '<anchor NULL>' in the generated 'pos ligature'
    statement.

    If the glyph set contains glyphs whose unicode codepoint's script extension
    property intersects with one of the "Indic" script codes defined below,
    then the "abvm" and "blwm" features are also generated for those glyphs,
    as well as for alternate glyphs only accessible via GSUB substitutions.

    The "abvm" (above-base marks) and "blwm" (below-base marks) features
    include all mark2base, mark2liga and mark2mark attachments for Indic glyphs
    containing anchors from predefined lists of "above" and "below" anchor
    names (see below). If Indic glyphs contain anchors with names not in those
    lists, the anchors' vertical position relative to the half of the UPEM
    square is used to decide whether they are considered above or below.
    """

    tableTag = "GPOS"
    features = frozenset(["mark", "mkmk", "abvm", "blwm"])

    # subclasses may override this to use different anchor naming schemes
    NamedAnchor = NamedAnchor

    # @MC_top, @MC_bottom, etc.
    markClassPrefix = "MC"

    # The anchor names and list of scripts for which 'abvm' and 'blwm'
    # features are generated is the same as the one Glyphs.app uses, see:
    # https://github.com/googlei18n/ufo2ft/issues/179
    abvmAnchorNames = {"top", "topleft", "topright", "candra", "bindu", "candrabindu"}
    blwmAnchorNames = {"bottom", "bottomleft", "bottomright", "nukta"}
    indicScripts = {
        "Beng",  # Bengali
        "Cham",  # Cham
        "Deva",  # Devanagari
        "Gujr",  # Gujarati
        "Guru",  # Gurmukhi
        "Knda",  # Kannada
        "Mlym",  # Malayalam
        "Orya",  # Oriya
        "Taml",  # Tamil
        "Telu",  # Telugu
    }

    # Glyphs moves "_bottom" and "_top" (if present) to the top of
    # the list and then picks the first to use in the mark feature.
    # https://github.com/googlei18n/noto-source/issues/122
    # #issuecomment-403952188
    anchorSortKey = {"_bottom": -2, "_top": -1}

    def setContext(self, font, feaFile, compiler=None):
        ctx = super(MarkFeatureWriter, self).setContext(
            font, feaFile, compiler=compiler
        )
        ctx.gdefClasses = ast.getGDEFGlyphClasses(feaFile)
        ctx.anchorLists = self._getAnchorLists()
        ctx.anchorPairs = self._getAnchorPairs()

    def shouldContinue(self):
        if not self.context.anchorPairs:
            self.log.debug("No mark-attaching anchors found; skipped")
            return False
        return super(MarkFeatureWriter, self).shouldContinue()

    def _getAnchorLists(self):
        gdefClasses = self.context.gdefClasses
        if gdefClasses.base is not None:
            # only include the glyphs listed in the GDEF.GlyphClassDef groups
            include = gdefClasses.base | gdefClasses.ligature | gdefClasses.mark
        else:
            # no GDEF table defined in feature file, include all glyphs
            include = None
        result = OrderedDict()
        for glyphName, glyph in self.getOrderedGlyphSet().items():
            if include is not None and glyphName not in include:
                continue
            anchorDict = OrderedDict()
            for anchor in glyph.anchors:
                anchorName = anchor.name
                if not anchorName:
                    self.log.warning(
                        "unnamed anchor discarded in glyph '%s'", glyphName
                    )
                    continue
                if anchorName in anchorDict:
                    self.log.warning(
                        "duplicate anchor '%s' in glyph '%s'", anchorName, glyphName
                    )
                a = self.NamedAnchor(name=anchorName, x=anchor.x, y=anchor.y)
                anchorDict[anchorName] = a
            if anchorDict:
                result[glyphName] = list(anchorDict.values())
        return result

    def _getAnchorPairs(self):
        markAnchorNames = set()
        for anchors in self.context.anchorLists.values():
            markAnchorNames.update(a.name for a in anchors if a.isMark)
        anchorPairs = {}
        for anchors in self.context.anchorLists.values():
            for anchor in anchors:
                if anchor.isMark:
                    continue
                markAnchorName = anchor.markAnchorName
                if markAnchorName in markAnchorNames:
                    anchorPairs[anchor.name] = markAnchorName
        return anchorPairs

    def _pruneUnusedAnchors(self):
        baseAnchorNames = set(self.context.anchorPairs.keys())
        markAnchorNames = set(self.context.anchorPairs.values())
        attachingAnchorNames = baseAnchorNames | markAnchorNames
        for glyphName, anchors in list(self.context.anchorLists.items()):
            for anchor in list(anchors):
                if anchor.name not in attachingAnchorNames and anchor.key:
                    anchors.remove(anchor)
            if not anchors:
                del self.context.anchorLists[glyphName]

    def _groupMarkGlyphsByAnchor(self):
        def sort_key(a):
            return self.anchorSortKey.get(a.name, 0)

        gdefMarks = self.context.gdefClasses.mark
        markAnchorNames = set(self.context.anchorPairs.values())
        markGlyphNames = set()
        groups = {}
        for glyphName, anchors in self.context.anchorLists.items():
            # if the feature file has a GDEF table with GlyphClassDef defined,
            # only include mark glyphs that are referenced in there, otherwise
            # include any glyphs that contain an "_" prefixed anchor.
            if gdefMarks is not None and glyphName not in gdefMarks:
                continue
            markAnchors = [a for a in anchors if a.name in markAnchorNames]
            if not markAnchors:
                continue
            # only use the first mark anchor, using a predefined sorting, to
            # determine which markClass a mark glyph belongs. This is to avoid
            # overlapping mark classes within the same lookup
            anchor = sorted(markAnchors, key=sort_key)[0]
            group = groups.setdefault(anchor.name, OrderedDict())
            assert glyphName not in group
            group[glyphName] = anchor
            markGlyphNames.add(glyphName)
        self.context.markGlyphNames = markGlyphNames
        return groups

    def _makeMarkClassDefinitions(self):
        markGlyphSets = self._groupMarkGlyphsByAnchor()
        currentClasses = self.context.feaFile.markClasses
        allMarkClasses = self.context.markClasses = {}
        classPrefix = self.markClassPrefix
        newDefs = []
        for markAnchorName, glyphAnchorPairs in sorted(markGlyphSets.items()):
            className = ast.makeFeaClassName(classPrefix + markAnchorName)
            for glyphName, anchor in glyphAnchorPairs.items():
                mcd = self._defineMarkClass(
                    glyphName, anchor.x, anchor.y, className, currentClasses
                )
                if mcd is not None:
                    newDefs.append(mcd)
                    # this may be different because of name clashes
                    className = mcd.markClass.name
                allMarkClasses[anchor.key] = currentClasses[className]
        return newDefs

    def _defineMarkClass(self, glyphName, x, y, className, markClasses):
        anchor = ast.Anchor(x=otRound(x), y=otRound(y))
        markClass = markClasses.get(className)
        if markClass is None:
            markClass = ast.MarkClass(className)
            markClasses[className] = markClass
        else:
            if glyphName in markClass.glyphs:
                mcdef = markClass.glyphs[glyphName]
                if self._anchorsAreEqual(anchor, mcdef.anchor):
                    self.log.debug(
                        "Glyph %s already defined in markClass @%s",
                        glyphName,
                        className,
                    )
                    return None
                else:
                    # same mark glyph defined with different anchors for the
                    # same markClass; make a new unique markClass definition
                    newClassName = ast.makeFeaClassName(className, markClasses)
                    markClass = ast.MarkClass(newClassName)
                    markClasses[newClassName] = markClass
        glyphName = ast.GlyphName(glyphName)
        mcdef = ast.MarkClassDefinition(markClass, anchor, glyphName)
        markClass.addDefinition(mcdef)
        return mcdef

    @staticmethod
    def _anchorsAreEqual(a1, a2):
        # TODO add __eq__ to feaLib AST objects?
        return all(
            getattr(a1, attr) == getattr(a2, attr)
            for attr in ("x", "y", "contourpoint", "xDeviceTable", "yDeviceTable")
        )

    def _setBaseAnchorMarkClasses(self):
        markClasses = self.context.markClasses
        for anchors in self.context.anchorLists.values():
            for anchor in anchors:
                if anchor.isMark or not anchor.key or anchor.key not in markClasses:
                    continue
                anchor.markClass = markClasses[anchor.key]

    def _makeMarkToBaseAttachments(self):
        markGlyphNames = self.context.markGlyphNames
        baseClass = self.context.gdefClasses.base
        result = []
        for glyphName, anchors in self.context.anchorLists.items():
            # exclude mark glyphs, or glyphs not listed in GDEF Base
            if glyphName in markGlyphNames or (
                baseClass is not None and glyphName not in baseClass
            ):
                continue
            baseMarks = []
            for anchor in anchors:
                if anchor.markClass is None or anchor.number is not None:
                    # skip anchors for which no mark class is defined; also
                    # skip '_1', '_2', etc. suffixed anchors for this lookup
                    # type; these will be are added in the mark2liga lookup
                    continue
                assert not anchor.isMark
                baseMarks.append(anchor)
            if not baseMarks:
                continue
            result.append(MarkToBasePos(glyphName, baseMarks))
        return result

    def _makeMarkToMarkAttachments(self):
        markGlyphNames = self.context.markGlyphNames
        # we make a dict of lists containing mkmk pos rules keyed by
        # anchor name, so we can create one mkmk lookup per markClass
        # each with different mark filtering sets.
        results = {}
        for glyphName, anchors in self.context.anchorLists.items():
            if glyphName not in markGlyphNames:
                continue
            for anchor in anchors:
                # skip anchors for which no mark class is defined
                if anchor.markClass is None or anchor.isMark:
                    continue
                if anchor.number is not None:
                    self.log.warning(
                        "invalid ligature anchor '%s' in mark glyph '%s'; " "skipped",
                        anchor.name,
                        glyphName,
                    )
                    continue
                pos = MarkToMarkPos(glyphName, [anchor])
                results.setdefault(anchor.key, []).append(pos)
        return results

    def _makeMarkToLigaAttachments(self):
        markGlyphNames = self.context.markGlyphNames
        ligatureClass = self.context.gdefClasses.ligature
        result = []
        for glyphName, anchors in self.context.anchorLists.items():
            # exclude mark glyphs, or glyphs not listed in GDEF Ligature
            if glyphName in markGlyphNames or (
                ligatureClass is not None and glyphName not in ligatureClass
            ):
                continue
            componentAnchors = {}
            for anchor in anchors:
                if anchor.markClass is None and anchor.key:
                    # skip anchors for which no mark class is defined
                    continue
                assert not anchor.isMark
                number = anchor.number
                if number is None:
                    # we handled these in the mark2base lookup
                    continue
                # unnamed anchors with only a number suffix "_1", "_2", etc.
                # are understood as the ligature component having <anchor NULL>
                if not anchor.key:
                    componentAnchors[number] = []
                else:
                    componentAnchors.setdefault(number, []).append(anchor)
            if not componentAnchors:
                continue
            ligatureMarks = []
            # ligature components are indexed from 1; any missing intermediate
            # anchor number means the component has <anchor NULL>
            for number in range(1, max(componentAnchors.keys()) + 1):
                ligatureMarks.append(componentAnchors.get(number, []))
            result.append(MarkToLigaPos(glyphName, ligatureMarks))
        return result

    @staticmethod
    def _iterAttachments(attachments, include=None, marksFilter=None):
        for pos in attachments:
            if include is not None and not include(pos.name):
                continue
            if marksFilter is not None:
                pos = pos.filter(marksFilter)
                if pos is None:
                    continue
            yield pos

    def _makeMarkLookup(self, lookupName, attachments, include, marksFilter=None):
        statements = [
            pos.asAST()
            for pos in self._iterAttachments(attachments, include, marksFilter)
        ]
        if statements:
            lkp = ast.LookupBlock(lookupName)
            lkp.statements.extend(statements)
            return lkp

    def _makeMarkFilteringSetClass(self, lookupName, attachments, markClass, include):
        markGlyphs = (glyphName for glyphName in markClass.glyphs if include(glyphName))
        baseGlyphs = (
            pos.name for pos in attachments if pos.name not in markClass.glyphs
        )
        members = itertools.chain(markGlyphs, baseGlyphs)
        className = "MFS_%s" % lookupName
        return ast.makeGlyphClassDefinitions(
            {className: members}, feaFile=self.context.feaFile
        )[className]

    def _makeMarkToMarkLookup(
        self, anchorName, attachments, include, marksFilter=None, featureTag=None
    ):
        attachments = list(self._iterAttachments(attachments, include, marksFilter))
        if not attachments:
            return
        prefix = (featureTag + "_") if featureTag is not None else ""
        lookupName = "%smark2mark_%s" % (prefix, anchorName)
        filteringClass = self._makeMarkFilteringSetClass(
            lookupName,
            attachments,
            markClass=self.context.markClasses[anchorName],
            include=include,
        )
        lkp = ast.LookupBlock(lookupName)
        lkp.statements.append(filteringClass)
        lkp.statements.append(ast.makeLookupFlag(markFilteringSet=filteringClass))
        lkp.statements.extend(pos.asAST() for pos in attachments)
        return lkp

    def _makeMarkFeature(self, include):
        baseLkp = self._makeMarkLookup(
            "mark2base", self.context.markToBaseAttachments, include
        )
        ligaLkp = self._makeMarkLookup(
            "mark2liga", self.context.markToLigaAttachments, include
        )
        if baseLkp is None and ligaLkp is None:
            return

        feature = ast.FeatureBlock("mark")
        if baseLkp:
            feature.statements.append(baseLkp)
        if ligaLkp:
            feature.statements.append(ligaLkp)
        return feature

    def _makeMkmkFeature(self, include):
        feature = ast.FeatureBlock("mkmk")

        for anchorName, attachments in sorted(
            self.context.markToMarkAttachments.items()
        ):
            lkp = self._makeMarkToMarkLookup(anchorName, attachments, include)
            if lkp is not None:
                feature.statements.append(lkp)

        return feature if feature.statements else None

    def _getVerticalThreshold(self):
        # anchors with unknown names whose Y coordinate is greater or equal to
        # the line that cuts the UPEM square in half will be treated as "above
        # base" marks, those that fall below the threshold as "below base".
        return getAttrWithFallback(self.context.font.info, "unitsPerEm") // 2

    def _isAboveMark(self, anchor):
        if anchor.name in self.abvmAnchorNames:
            return True
        if anchor.name in self.blwmAnchorNames:
            return False
        if anchor.y >= self.context.threshold:
            return True
        return False

    def _isBelowMark(self, anchor):
        return not self._isAboveMark(anchor)

    def _makeAbvmOrBlwmFeature(self, tag, include):
        if tag == "abvm":
            marksFilter = self._isAboveMark
        elif tag == "blwm":
            marksFilter = self._isBelowMark
        else:
            raise AssertionError(tag)

        baseLkp = self._makeMarkLookup(
            "%s_mark2base" % tag,
            self.context.markToBaseAttachments,
            include=include,
            marksFilter=marksFilter,
        )
        ligaLkp = self._makeMarkLookup(
            "%s_mark2liga" % tag,
            self.context.markToLigaAttachments,
            include=include,
            marksFilter=marksFilter,
        )
        mkmkLookups = []
        for anchorName, attachments in sorted(
            self.context.markToMarkAttachments.items()
        ):
            lkp = self._makeMarkToMarkLookup(
                anchorName,
                attachments,
                include=include,
                marksFilter=marksFilter,
                featureTag=tag,
            )
            if lkp is not None:
                mkmkLookups.append(lkp)

        if not any([baseLkp, ligaLkp, mkmkLookups]):
            return

        feature = ast.FeatureBlock(tag)
        if baseLkp:
            feature.statements.append(baseLkp)
        if ligaLkp:
            feature.statements.append(ligaLkp)
        feature.statements.extend(mkmkLookups)
        return feature

    def _makeFeatures(self):
        ctx = self.context

        ctx.markToBaseAttachments = self._makeMarkToBaseAttachments()
        ctx.markToLigaAttachments = self._makeMarkToLigaAttachments()
        ctx.markToMarkAttachments = self._makeMarkToMarkAttachments()

        indicGlyphs = self._getIndicGlyphs()

        def isIndic(glyphName):
            return glyphName in indicGlyphs

        def isNotIndic(glyphName):
            return glyphName not in indicGlyphs

        features = {}
        todo = ctx.todo
        if "mark" in todo:
            mark = self._makeMarkFeature(include=isNotIndic)
            if mark is not None:
                features["mark"] = mark
        if "mkmk" in todo:
            mkmk = self._makeMkmkFeature(include=isNotIndic)
            if mkmk is not None:
                features["mkmk"] = mkmk
        if "abvm" in todo or "blwm" in todo:
            if indicGlyphs:
                self.context.threshold = self._getVerticalThreshold()
                for tag in ("abvm", "blwm"):
                    if tag not in todo:
                        continue
                    feature = self._makeAbvmOrBlwmFeature(tag, include=isIndic)
                    if feature is not None:
                        features[tag] = feature

        return features

    def _getIndicGlyphs(self):
        cmap = self.makeUnicodeToGlyphNameMapping()
        unicodeIsIndic = partial(unicodeInScripts, scripts=self.indicScripts)
        if any(unicodeIsIndic for uv in cmap):
            # If there are any characters from Indic scripts in the cmap, we
            # compile a temporary GSUB table to resolve substitutions and get
            # the set of all the "Indic" glyphs, including alternate glyphs.
            gsub = self.compileGSUB()
            glyphGroups = classifyGlyphs(unicodeIsIndic, cmap, gsub)
            # the 'glyphGroups' dict is keyed by the return value of the
            # classifying include, so here 'True' means all the Indic glyphs
            return glyphGroups.get(True, set())
        else:
            return set()

    def _write(self):
        self._pruneUnusedAnchors()

        newClassDefs = self._makeMarkClassDefinitions()
        self._setBaseAnchorMarkClasses()

        features = self._makeFeatures()
        if not features:
            return False

        feaFile = self.context.feaFile
        feaFile.statements.extend(newClassDefs)
        # add empty line to separate classes from following statements
        feaFile.statements.append(ast.Comment(""))
        for _, feature in sorted(features.items()):
            feaFile.statements.append(feature)
        return True
