#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ====================================================
# Copyright 2018 Source Foundry Authors
# MIT License
# ====================================================

import os
import sys

from commandlines import Command

from ufolint.settings import HELP, VERSION, USAGE
from ufolint.controllers.runner import MainRunner


def main():
    c = Command()

    if c.does_not_validate_missing_args():
        sys.stderr.write(
            "[ufolint] ERROR: Please include one or more UFO directory arguments with your command."
            + os.linesep
        )
        sys.exit(1)

    if c.is_help_request():
        print(HELP)
        sys.exit(0)
    elif c.is_version_request():
        print(VERSION)
        sys.exit(0)
    elif c.is_usage_request():
        print(USAGE)
        sys.exit(0)

    for argument in sys.argv:
        if argument[-4:] == ".ufo":
            hh = MainRunner(argument)
            hh.run()

    sys.exit(
        0
    )  # if the script completes without status code 1 SystemExit being raised, then all tests passed
