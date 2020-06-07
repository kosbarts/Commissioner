#!/usr/bin/env python
# -*- coding: utf-8 -*-


class CommandlinesError(Exception):
    """Base exception class for all exceptions raised by the commandlines library"""
    def __init__(self, message):
        Exception.__init__(self, message)


class MissingArgumentError(CommandlinesError):
    """Missing argument exception"""
    def __init__(self, argument):
        self.error_message = "Missing argument exception: the argument '" + argument + "' was not found."
        CommandlinesError.__init__(self, self.error_message)


class MissingDictionaryKeyError(CommandlinesError):
    """Missing dictionary key exception"""
    def __init__(self, dict_key):
        self.error_message = "Missing dictionary key exception: the dictionary key '" + dict_key + "' was not found."
        CommandlinesError.__init__(self, self.error_message)


class IndexOutOfRangeError(CommandlinesError, IndexError):
    """Index out of range exception"""
    def __init__(self):
        self.error_message = "Index out of range exception.  The requested index fell outside of the index range."
        IndexError.__init__(self)
        CommandlinesError.__init__(self, self.error_message)

