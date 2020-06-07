#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# Version Number
# ------------------------------------------------------------------------------
major_version = "1"
minor_version = "0"
patch_version = "0"

# ------------------------------------------------------------------------------
# Help String
# ------------------------------------------------------------------------------

HELP = """====================================================
ufolint
Copyright 2019 Source Foundry Authors
MIT License
Source: https://github.com/source-foundry/ufolint
====================================================

ufolint is a UFO source file linter.

Usage:

  $ ufolint [UFO path 1] ([UFO path2] [UFO path ...])

The application returns exit status code 0 if all tests are successful and exit status code 1 if any failures are detected.

See documentation on the source repository (link above) for testing details.

"""

# ------------------------------------------------------------------------------
# Version String
# ------------------------------------------------------------------------------

VERSION = "ufolint v" + major_version + "." + minor_version + "." + patch_version


# ------------------------------------------------------------------------------
# Usage String
# ------------------------------------------------------------------------------
USAGE = "ufolint [UFO path 1] ([UFO path2] [UFO path ...])"
