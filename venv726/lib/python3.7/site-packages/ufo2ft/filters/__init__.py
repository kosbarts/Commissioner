from __future__ import print_function, division, absolute_import, unicode_literals

import importlib
import logging
from fontTools.misc.py23 import SimpleNamespace
from fontTools.misc.loggingTools import Timer
from ufo2ft.util import _LazyFontName, _GlyphSet
from ufo2ft.constants import FILTERS_KEY as UFO2FT_FILTERS_KEY  # keep previous name


logger = logging.getLogger(__name__)


def getFilterClass(filterName, pkg="ufo2ft.filters"):
    """Given a filter name, import and return the filter class.
    By default, filter modules are searched within the ``ufo2ft.filters``
    package.
    """
    # TODO add support for third-party plugin discovery?
    # if filter name is 'Foo Bar', the module should be called 'fooBar'
    filterName = filterName.replace(" ", "")
    moduleName = filterName[0].lower() + filterName[1:]
    module = importlib.import_module(".".join([pkg, moduleName]))
    # if filter name is 'Foo Bar', the class should be called 'FooBarFilter'
    className = filterName[0].upper() + filterName[1:] + "Filter"
    return getattr(module, className)


def loadFilters(ufo):
    """Parse custom filters from the ufo's lib.plist. Return two lists,
    one for the filters that are applied before decomposition of composite
    glyphs, another for the filters that are applied after decomposition.
    """
    preFilters, postFilters = [], []
    for filterDict in ufo.lib.get(UFO2FT_FILTERS_KEY, []):
        namespace = filterDict.get("namespace", "ufo2ft.filters")
        try:
            filterClass = getFilterClass(filterDict["name"], namespace)
        except (ImportError, AttributeError):
            from pprint import pformat

            logger.exception("Failed to load filter: %s", pformat(filterDict))
            continue
        filterObj = filterClass(
            include=filterDict.get("include"),
            exclude=filterDict.get("exclude"),
            *filterDict.get("args", []),
            **filterDict.get("kwargs", {})
        )
        if filterDict.get("pre"):
            preFilters.append(filterObj)
        else:
            postFilters.append(filterObj)
    return preFilters, postFilters


class BaseFilter(object):

    # tuple of strings listing the names of required positional arguments
    # which will be set as attributes of the filter instance
    _args = ()

    # dictionary containing the names of optional keyword arguments and
    # their default values, which will be set as instance attributes
    _kwargs = {}

    def __init__(self, *args, **kwargs):
        self.options = options = SimpleNamespace()

        # process positional arguments
        num_required = len(self._args)
        num_args = len(args)
        if num_args < num_required:
            missing = [repr(a) for a in self._args[num_args:]]
            num_missing = len(missing)
            raise TypeError(
                "missing {0} required positional argument{1}: {2}".format(
                    num_missing, "s" if num_missing > 1 else "", ", ".join(missing)
                )
            )
        elif num_args > num_required:
            extra = [repr(a) for a in args[num_required:]]
            num_extra = len(extra)
            raise TypeError(
                "got {0} unsupported positional argument{1}: {2}".format(
                    num_extra, "s" if num_extra > 1 else "", ", ".join(extra)
                )
            )
        for key, value in zip(self._args, args):
            setattr(options, key, value)

        # process optional keyword arguments
        for key, default in self._kwargs.items():
            setattr(options, key, kwargs.pop(key, default))

        # process special include/exclude arguments
        include = kwargs.pop("include", None)
        exclude = kwargs.pop("exclude", None)
        if include is not None and exclude is not None:
            raise ValueError("'include' and 'exclude' arguments are mutually exclusive")
        if callable(include):
            # 'include' can be a function (e.g. lambda) that takes a
            # glyph object and returns True/False based on some test
            self.include = include
            self._include_repr = lambda: repr(include)
        elif include is not None:
            # or it can be a list of glyph names to be included
            included = set(include)
            self.include = lambda g: g.name in included
            self._include_repr = lambda: repr(include)
        elif exclude is not None:
            # alternatively one can provide a list of names to not include
            excluded = set(exclude)
            self.include = lambda g: g.name not in excluded
            self._exclude_repr = lambda: repr(exclude)
        else:
            # by default, all glyphs are included
            self.include = lambda g: True

        # raise if any unsupported keyword arguments
        if kwargs:
            num_left = len(kwargs)
            raise TypeError(
                "got {0}unsupported keyword argument{1}: {2}".format(
                    "an " if num_left == 1 else "",
                    "s" if len(kwargs) > 1 else "",
                    ", ".join("'{}'".format(k) for k in kwargs),
                )
            )

        # run the filter's custom initialization code
        self.start()

    def __repr__(self):
        items = []
        if self._args:
            items.append(
                ", ".join(repr(getattr(self.options, arg)) for arg in self._args)
            )
        if self._kwargs:
            items.append(
                ", ".join(
                    "{0}={1!r}".format(k, getattr(self.options, k))
                    for k in sorted(self._kwargs)
                )
            )
        if hasattr(self, "_include_repr"):
            items.append("include={}".format(self._include_repr()))
        elif hasattr(self, "_exclude_repr"):
            items.append("exclude={}".format(self._exclude_repr()))
        return "{0}({1})".format(type(self).__name__, ", ".join(items))

    def start(self):
        """ Subclasses can perform here custom initialization code.
        """
        pass

    def set_context(self, font, glyphSet):
        """ Populate a `self.context` namespace, which is reset before each
        new filter call.

        Subclasses can override this to provide contextual information
        which depends on other data in the font that is not available in
        the glyphs objects currently being filtered, or set any other
        temporary attributes.

        The default implementation simply sets the current font and glyphSet,
        and initializes an empty set that keeps track of the names of the
        glyphs that were modified.

        Returns the namespace instance.
        """
        self.context = SimpleNamespace(font=font, glyphSet=glyphSet)
        self.context.modified = set()
        return self.context

    def filter(self, glyph):
        """ This is where the filter is applied to a single glyph.
        Subclasses must override this method, and return True
        when the glyph was modified.
        """
        raise NotImplementedError

    @property
    def name(self):
        return self.__class__.__name__

    def __call__(self, font, glyphSet=None):
        """ Run this filter on all the included glyphs.
        Return the set of glyph names that were modified, if any.

        If `glyphSet` (dict) argument is provided, run the filter on
        the glyphs contained therein (which may be copies).
        Otherwise, run the filter in-place on the font's default
        glyph set.
        """
        fontName = _LazyFontName(font)
        if glyphSet is not None and getattr(glyphSet, "name", None):
            logger.info("Running %s on %s-%s", self.name, fontName, glyphSet.name)
        else:
            logger.info("Running %s on %s", self.name, fontName)

        if glyphSet is None:
            glyphSet = _GlyphSet.from_layer(font)

        context = self.set_context(font, glyphSet)

        filter_ = self.filter
        include = self.include
        modified = context.modified

        with Timer() as t:
            # we sort the glyph names to make loop deterministic
            for glyphName in sorted(glyphSet.keys()):
                if glyphName in modified:
                    continue
                glyph = glyphSet[glyphName]
                if include(glyph) and filter_(glyph):
                    modified.add(glyphName)

        num = len(modified)
        if num > 0:
            logger.debug(
                "Took %.3fs to run %s on %d glyph%s",
                t,
                self.name,
                len(modified),
                "" if num == 1 else "s",
            )
        return modified
