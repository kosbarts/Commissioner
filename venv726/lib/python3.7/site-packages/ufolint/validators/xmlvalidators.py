#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as Etree  # python 3


def is_valid_xml_path(filepath):
    """
    Attempts to parse XML file at filepath.  ElementTree.parse() raises informative exceptions as ParseError if cannot
    parse as valid XML.  This function catches them and returns as part of the function response to caller.

    Returns tuple of (boolean, message string) where True = valid XML, False = invalid XML.

    :param filepath: (string) filepath to attempt to parse as XML formatted text file
    :return: (boolean, message string) tuple
    """
    try:
        tree = Etree.parse(filepath)
        return True, tree
    except Exception as e:
        return False, str(e)
