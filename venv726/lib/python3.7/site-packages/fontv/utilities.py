#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ====================================================
# Copyright 2018 Christopher Simpkins
# MIT License
# ====================================================

from __future__ import unicode_literals

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


def get_git_root_path(filepath):
    """
    Recursively searches for git root path over 4 directory levels above working directory
    :param filepath: (string) - path to the font file that is under git version control
    :return: validated git root path as string
    :raises: IOError if unable to detect the root of the git repository through this path traversal
    """

    # begin by defining directory that contains font as the git root needle
    unverified_gitroot_path = os.path.dirname(os.path.abspath(filepath))

    # check to see if this assumption is correct
    if dir_exists(os.path.join(unverified_gitroot_path, ".git")):
        verified_gitroot_path = unverified_gitroot_path
    else:  # if not, recursive search up to three directories above for the git repo root
        one_level_up = os.path.abspath(os.path.join(unverified_gitroot_path, os.pardir))
        two_levels_up = os.path.dirname(one_level_up)
        three_levels_up = os.path.dirname(two_levels_up)

        one_level_up_path = os.path.join(one_level_up, ".git")
        two_levels_up_path = os.path.join(two_levels_up, ".git")
        three_levels_up_path = os.path.join(three_levels_up, ".git")

        if dir_exists(one_level_up_path):  # check one directory level up
            verified_gitroot_path = os.path.dirname(one_level_up_path)
        elif dir_exists(two_levels_up_path):  # check two directory levels up
            verified_gitroot_path = os.path.dirname(two_levels_up_path)
        elif dir_exists(three_levels_up_path):  # check three directory levels up
            verified_gitroot_path = os.path.dirname(three_levels_up_path)
        else:
            raise IOError(
                "Unable to determine git repository root for font file " + filepath
            )

    return verified_gitroot_path


def is_font(filepath):
    """
    Tests filepath argument to determine if it has a .ttf or .otf file extension (definition of "font" for this
    application)

    :param filepath: (string) file path to a font file for testing
    :return: (boolean) True = appears to be a font file path; False = does not appear to be a font file path
    """
    if len(filepath) > 4:
        if filepath[-4:].lower() == ".ttf" or filepath[-4:].lower() == ".otf":
            return True
        else:
            return False
    else:
        return False
