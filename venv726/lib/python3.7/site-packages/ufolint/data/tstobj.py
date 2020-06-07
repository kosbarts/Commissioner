#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Result(object):
    """
    Data object that maintains test result success status and test result message (intended for std output to user)
    """

    def __init__(self, filepath):
        self.test_filepath = filepath
        self.test_failed = (
            None
        )  # test result indicator, True = test failed, False = test succeeded
        self.exit_failure = (
            None
        )  # when set to True, sys.exit(1) raised immediately on this error result
        self.test_long_stdstream_string = (
            ""
        )  # maintains std output string to be presented to user for each test result
