#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


def dir_exists(dirpath):
    """Tests for existence of a directory on the string filepath"""
    if os.path.exists(dirpath) and os.path.isdir(
        dirpath
    ):  # test that exists and is a directory
        return True
    else:
        return False


def file_exists(filepath):
    """Tests for existence of a file on the string filepath"""
    if os.path.exists(filepath) and os.path.isfile(
        filepath
    ):  # test that exists and is a file
        return True
    else:
        return False
