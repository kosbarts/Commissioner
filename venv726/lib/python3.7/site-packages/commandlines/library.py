#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The commandlines.library module contains the Command, Arguments, Definitions, Mops, MultiDefinitions, and Switches
classes.  These objects are used to parse command line argument strings to command line syntax specific Python objects.

The Command class is a high level object that is intended to be the public facing portion of the library.  The
commandlines Command object can be imported into projects with the following import statement:

`from commandlines import Command`

Exceptions raised by this module are in the `commandlines.exceptions` module.
"""

import sys
from commandlines.exceptions import IndexOutOfRangeError, MissingArgumentError, MissingDictionaryKeyError


class Command(object):
    """An object that maintains syntax specific components of a command line string and provides methods to support
    the development of Python command line applications.

    The class is instantiated from the list of command line arguments that are passed to a Python script in `sys.argv`.

    Attributes:
        arg0 : (string)
               Argument at index position 0
        arg1 : (string)
               Argument at index position 1
        arg2 : (string)
               Argument at index position 2
        arg3 : (string)
               Argument at index position 3
        arg4 : (string)
               Argument at index position 4
        argc : (int)
               Length of the arguments list
        arglp : (string)
                Argument at last index position in the arguments list
        arguments: (Arguments, list)
                   List of all ordered positional arguments in the command string
        defaults: (dict)
                  Dictionary of default key : value mapped as option : argument value
        defs: (Definitions, dict)
               Dictionary of key=option : value=argument definition pairs
        mdefs: (MultiDefinitions, Definitions, dict)
                Dictionary of key=option : value=argument definition pairs for options included more than once in command
        mops: (set)
               Set of multi-option short syntax (i.e. single dash) switches
        subcmd: (string)
                 The first positional argument (=arg0)
        subsubcmd: (string)
               The second positional argument (=arg1)
        switches: (set)
               Set of long and short switch syntax arguments
    """
    def __init__(self):
        self.argv = sys.argv[1:]
        self.arguments = Arguments(self.argv)
        self.defaults = {}
        self.switches = Switches(self.argv)
        self.mops = Mops(self.argv)
        self.defs = Definitions(self.argv)
        self.mdefs = MultiDefinitions(self.argv)
        self.argc = len(self.argv)
        self.arg0 = self.arguments.get_argument_for_commandobj(0)
        self.arg1 = self.arguments.get_argument_for_commandobj(1)
        self.arg2 = self.arguments.get_argument_for_commandobj(2)
        self.arg3 = self.arguments.get_argument_for_commandobj(3)
        self.arg4 = self.arguments.get_argument_for_commandobj(4)
        self.arglp = self.arguments.get_argument_for_commandobj(self.argc - 1)
        self.subcmd = self.arg0
        self.subsubcmd = self.arg1
        self.has_args = (len(self.arguments) > 0)
        self.has_switches = (len(self.switches) > 0)
        self.has_mops = (len(self.mops) > 0)
        self.has_defs = (len(self.defs) > 0)
        self.has_mdefs = (len(self.mdefs) > 0)

    # TODO: implement support for short / long option alternatives

    def __repr__(self):
        return "< Command object > instantiated from arguments: " + self.argv.__str__()

    def __str__(self):
        return "< Command object > instantiated from arguments: " + self.argv.__str__()

    # //////////////////////////////////////////////////////////////
    #
    #  Validation methods
    #
    # //////////////////////////////////////////////////////////////

    def does_not_validate_missing_args(self):
        """Command string validation for missing arguments to the executable.

        :returns: boolean. True = does not validate. False = validates"""

        return self.argc == 0

    def does_not_validate_missing_defs(self):
        """Command string validation for missing definitions to the executable

        :returns: boolean. True = does not validate. False = validates"""

        return len(self.defs) == 0 and len(self.mdefs) == 0

    def does_not_validate_missing_mops(self):
        """Command string validation for missing multi-option short syntax arguments to the executable

        :returns: boolean. True = does not validate. False = validates"""

        return len(self.mops) == 0

    def does_not_validate_missing_switches(self):
        """Command string validation for missing switches to the executable

        :returns: boolean. True = does not validate. False = validates"""

        return len(self.switches) == 0

    def does_not_validate_n_args(self, number):
        """Command string validation for inclusion of exactly n arguments to executable.

           :param number: (integer) Defines the number of expected arguments for this test
           :returns: boolean. True = does not validate. False = validates"""

        if self.argc == number:
            return False
        else:
            return True

    def validates_includes_args(self):
        """Command string validation for inclusion of at least one argument to the executable

        :returns: boolean. True = validates. False = does not validate."""

        return self.argc > 0

    def validates_includes_definitions(self):
        """Command string validation for inclusion of at least one definition (option-argument) to the executable

        :returns: boolean. True = validates. False = does not validate."""

        return len(self.defs) > 0

    def validates_includes_mops(self):
        """Command string validation for inclusion of at least one multi-option short syntax argument to the
        executable.

        :returns: boolean. True = validates. False = does not validate."""

        return len(self.mops) > 0

    def validates_includes_switches(self):
        """Command string validation for inclusion of at least one switch argument to the executable.

        :returns: boolean. True = validates. False = does not validate."""

        return len(self.switches) > 0

    def validates_includes_n_args(self, number):
        """Command string validation for inclusion of exactly `number` arguments to the executable.

        :param number: (integer)  Defines the number of expected arguments for this test
        :returns: boolean. True = validates. False = does not validate."""

        return self.argc == number

    # //////////////////////////////////////////////////////////////
    #
    # Default option:argument mapping methods
    #
    # //////////////////////////////////////////////////////////////

    def set_defaults(self, default_dictionary):
        """Sets default option : argument definitions with a dictionary parameter. The option keys should not include
        dashes at the beginning of the option string.  One or more key:value pairs can be included in the
        default_dictionary parameter.

        :param default_dictionary: (dict) Defines the default key=option : value=argument mapping
        :returns: None"""

        self.defaults.update(default_dictionary)

    def contains_defaults(self, *default_needles):
        """Tests for the presence of one or more default option : argument definitions in the Command.defaults parameter

        :param default_needles: (tuple) One or more test default option strings
        :returns: boolean.  True = the default options are defined. False = the default options are not defined"""

        for needle in default_needles:
            if needle in self.defaults.keys():
                pass
            else:
                return False   # if any needle is absent, returns False
        return True   # if all tests pass, returns True

    def get_default(self, default_needle):
        """Gets the value for an existing default option : argument definition in the Command.defaults
        parameter.  The default_needle option string should not include dashes at the beginning of the string.

        :param default_needle: (string) The existing default option for which a value is requested
        :returns: User-specified type.  A value of any type that is permissible as a value in Python dictionaries
        :raises: MissingDictionaryKeyError if the key is not found in the Command.defaults dictionary"""

        if default_needle in self.defaults.keys():
            return self.defaults[default_needle]
        else:
            raise MissingDictionaryKeyError(default_needle)

    # //////////////////////////////////////////////////////////////
    #
    # Application logic methods
    #
    # //////////////////////////////////////////////////////////////

    def contains_switches(self, *switch_needles):
        """Test for the presence of one or more switches in the command string. Returns boolean that indicates presence
        (True) or absence (False) of switches.  Dashes should not be used at the beginning of the strings in the
        `switch_needles` parameter.

        :param switch_needles: (tuple) One or more expected switch strings.
        :returns: boolean"""

        return self.switches.contains(switch_needles)

    def contains_mops(self, *mops_needles):
        """Returns boolean that indicates presence (True) or absence (False) of one or more multi-option
        short syntax switch characters.

        :type mops_needles: tuple of one or more expected single character switches
        :returns: boolean"""

        return self.mops.contains(mops_needles)

    def contains_definitions(self, *def_needles):
        """Test for the presence of one or more option-argument definitions in the command string.  Returns boolean
        that indicates presence (True) or absence (False) of definition options.  Dashes should not be used at the
        beginning of the strings in the `def_needles` parameter.

        :param def_needles: (tuple) One or more expected definition option key(s).
        :returns: boolean"""

        return self.defs.contains(def_needles)

    def contains_multi_definitions(self, *def_needles):
        """Test for the presence of multiple option-argument definitions that use the same option string.  An example is

        `$ executable -o file1 -o file2`

        The dashes in the argument strings should not be included in the `def_needles` parameter. Returns boolean that
        indicates presence (True) or absence (False) of one or more multi-definition options.

        :param def_needles: (tuple) One or more expected definition option key(s).
        :returns: boolean"""

        return self.mdefs.contains(def_needles)

    def has_command_sequence(self, *cmd_list):
        """Test for a sequence of command line tokens in the command string.  The test begins at index position 0
        of the argument list and is case-sensitive.

        :param cmd_list: (tuple) Expected commands in expected order starting at Command.argv index position 0
        :returns: boolean"""

        if len(cmd_list) > len(self.argv):   # request does not inlude more args than the Command.argv property includes
            return False
        else:
            index = 0
            for test_arg in cmd_list:
                if self.argv[index] == test_arg:   # test that argument at index position matches in parameter order
                    index += 1
                else:
                    return False
            return True

    def has_args_after(self, argument_needle, number=1):
        """Test for the presence of at least one (default) positional arguments following an existing argument
        (argument_needle).  The number of expected arguments is modified by defining the `number` method parameter.

        :param number: (integer) The number of expected arguments after the test argument
        :param argument_needle: (string) The test argument that is known to be present in the command
        :raises: MissingArgumentError when argument_needle is not found in the parsed argument list"""

        if argument_needle in self.arguments:
            position = self.arguments.get_arg_position(argument_needle)
            if len(self.argv) > (position + number):
                return True
            else:
                return False
        else:
            raise MissingArgumentError(argument_needle)

    def next_arg_is_in(self, start_argument, supported_at_next_position):
        """Test for the presence of a supported argument in the n+1 index position for a known argument at the
        n position.  start_argument is called as the full argument string including any expected dashes.

        :param start_argument: (string) The argument string including any beginning dashes as used on the command line.
        :param supported_at_next_position: (list) list of strings that define supported arguments in the n+1 index
        :raises: MissingArgumentError when start_argument is not found in the parsed argument list"""

        if start_argument in self.arguments:
            position = self.arguments.get_arg_position(start_argument)
            test_argument = self.arguments.get_arg_next(position)
            if test_argument in supported_at_next_position:
                return True
            else:
                return False
        else:
            raise MissingArgumentError(start_argument)

    # //////////////////////////////////////////////////////////////
    #
    # Special command line idiom testing methods
    #
    # //////////////////////////////////////////////////////////////

    def has_double_dash(self):
        """Test for the presence of the double dash `--` command line idiom.

        :returns: boolean. True = has double dash token. False = does not contain double dash token."""

        if "--" in self.arguments:
            return True
        else:
            return False

    # //////////////////////////////////////////////////////////////
    #
    # Getter methods for command line argument strings
    #
    # //////////////////////////////////////////////////////////////

    def get_definition(self, def_needle):
        """Returns the argument to an option that is part of an option-argument definition pair.

        :param def_needle: (string) The option string of the option-argument pair
        :returns: string
        :raises: MissingDictionaryKeyError when the option string is not found"""

        return self.defs.get_def_argument(def_needle)

    def get_multiple_definitions(self, def_needle):
        """Returns a list of argument strings to an option that is included multiple times using option-argument
        syntax on the command line (e.g. `$ executable -o file1 -o file2`)

        :param def_needle: (string) The option string of the option-argument pair
        :returns: string
        :raises: MissingDictionaryKeyError when the option string is not found"""

        return self.mdefs.get_def_argument(def_needle)

    def get_arg_after(self, target_arg):
        """Returns the next positional argument at index position n + 1 to a command line argument at index position n.

           :param target_arg: (string) Argument string for the test.
           :returns: string
           :raises: MissingArgumentError when target_arg is not found in the parsed argument list
           :raises: IndexOutOfRangeError when target_arg is the last positional argument"""

        if target_arg in self.argv:
            recipient_position = self.arguments.get_arg_position(target_arg)
            return self.arguments.get_arg_next(recipient_position)
        else:
            raise MissingArgumentError(target_arg)

    def get_double_dash_args(self):
        """Returns the arguments after the double dash `--` command line idiom as a list.

        :returns: list of strings"""

        if "--" in self.arguments:
            dd_position = self.arguments.get_arg_position("--")
            start_position = dd_position + 1
            return self.arguments[start_position:]
        else:
            raise MissingArgumentError("--")

    # /////////////////////////////////////////////////////////////
    #
    #  Default parsing methods for commonly used options/switches
    #    - Includes support for POSIX / Gnu standard options
    #
    # /////////////////////////////////////////////////////////////

    def is_help_request(self):
        """Tests for `-h` and `--help` options in command string

        :returns: boolean. True = included help option. False = did not include help option."""

        if "help" in self.switches or "h" in self.switches:
            return True
        else:
            return False

    def is_quiet_request(self):
        """Tests for `--quiet` option in command string

        :returns: boolean. True = included quiet option.  False = did not include quiet option."""

        if "quiet" in self.switches:
            return True
        else:
            return False

    def is_usage_request(self):
        """Tests for `--usage` option in command string

        :returns: boolean. True = included usage option. False = did not include usage option."""

        if "usage" in self.switches:
            return True
        else:
            return False

    def is_verbose_request(self):
        """Tests for `--verbose` option in command string

        :returns: boolean. True = included verbose option. False = did not include verbose option."""

        if "verbose" in self.switches:
            return True
        else:
            return False

    def is_version_request(self):
        """Tests for `-v` and `--version` options in command string.

        :returns: boolean. True = included version option. False = did not include version option."""

        if "version" in self.switches or "v" in self.switches:
            return True
        else:
            return False

    # /////////////////////////////////////////////////////////////
    #
    #  Development + Testing methods
    #
    # /////////////////////////////////////////////////////////////

    def obj_string(self):
        """Returns a string of the instance attributes of the Command object intended for standard output use.
        Print the returned string to view the parsed arguments in the standard output stream.

        :returns: string"""

        the_string = "obj.argc = " + str(self.argc)
        the_string = the_string + "\n" + "obj.arguments = " + str(self.arguments)
        the_string = the_string + "\n" + "obj.defaults = " + str(self.defaults)
        the_string = the_string + "\n" + "obj.switches = " + str(self.switches)
        the_string = the_string + "\n" + "obj.defs = " + str(self.defs)
        the_string = the_string + "\n" + "obj.mdefs = " + str(self.mdefs)
        the_string = the_string + "\n" + "obj.mops = " + str(self.mops)
        the_string = the_string + "\n" + "obj.arg0 = " + self._get_obj_string_format_arg(self.arg0)
        the_string = the_string + "\n" + "obj.arg1 = " + self._get_obj_string_format_arg(self.arg1)
        the_string = the_string + "\n" + "obj.arg2 = " + self._get_obj_string_format_arg(self.arg2)
        the_string = the_string + "\n" + "obj.arg3 = " + self._get_obj_string_format_arg(self.arg3)
        the_string = the_string + "\n" + "obj.arg4 = " + self._get_obj_string_format_arg(self.arg4)
        the_string = the_string + "\n" + "obj.arglp = " + self._get_obj_string_format_arg(self.arglp)
        the_string = the_string + "\n" + "obj.subcmd = " + self._get_obj_string_format_arg(self.subcmd)
        the_string = the_string + "\n" + "obj.subsubcmd = " + self._get_obj_string_format_arg(self.subsubcmd)

        return the_string

    def _get_obj_string_format_arg(self, the_string):
        """Formats argument strings for standard output display

        :returns: string"""

        if the_string == "":
            return "''"
        else:
            return "'" + the_string + "'"


class Arguments(list):
    """A class that includes all command line arguments with positional argument order maintained.  Instantiated with
    a list of command line string tokens.

      The class is derived from the Python list type.

      :param argv: A list of command line arguments that maintain the argument order that was entered on command line"""
    def __init__(self, argv):
        list.__init__(self, argv)

    def __repr__(self):
        argument_string = ""
        if len(self) > 0:
            for argument in self:
                argument_string = argument_string + "'" + argument + "', "
        argument_string = argument_string.rstrip()
        argument_string = argument_string.rstrip(',')

        return "[" + argument_string + "]"

    def __str__(self):
        argument_string = ""
        if len(self) > 0:
            for argument in self:
                argument_string = argument_string + "'" + argument + "', "
        argument_string = argument_string.rstrip()
        argument_string = argument_string.rstrip(',')

        return "[" + argument_string + "]"

    def get_argument_for_commandobj(self, position):
        """An argument parsing method for the instantation of the Command object.  This is not intended for public use.
        Public calls should use the get_argument() method instead.

        :param position: The command line index position
        :returns: string or empty string if the index position is out of the index range"""

        if (len(self) > position) and (position >= 0):
            return self[position]
        else:
            return ""   # intentionally set as empty string rather than raise exception for Command obj instantation

    def get_argument(self, position):
        """Returns an argument string by the argument list index position.

        :param position: (integer) The command line index position
        :returns: string
        :raises: IndexOutOfRangeError if the requested index falls outside of the list index range"""

        if (len(self) > position) and (position >= 0):
            return self[position]
        else:
            raise IndexOutOfRangeError()

    def get_arg_position(self, test_arg):
        """Returns the index position of the `test_arg` parameter candidate argument string.  The argument string
        should include the dashes at the beginning of the argument string that would be expected with use on the
        command line.

        :param test_arg: (string) The argument string for which the index position is requested
        :returns: string
        :raises: MissingArgumentError if the requested argument is not in the Argument list"""

        if test_arg in self:
            return self.index(test_arg)
        else:
            raise MissingArgumentError(test_arg)

    def get_arg_next(self, position):
        """Returns the next argument at index `position` + 1 in the command sequence.

        :param position: (integer) The argument index position in the Argument list
        :returns: string
        :raises: IndexOutOfRangeError if the `position` + 1 index falls outside of the existing index range"""

        if len(self) > (position + 1):
            return self[position + 1]
        else:
            raise IndexOutOfRangeError()

    def contains(self, needle):
        """Returns boolean that indicates the presence (True) or absence (False) of a tuple of one or more test
        arguments.

        :param needle: (iterable) An iterable that contains one or more test argument strings.
        :returns: boolean"""

        for expected_argument in needle:
            if expected_argument in self:
                pass
            else:
                return False

        return True  # if all tests above pass


class Switches(set):
    """A class that is instantiated with all command line switches that have the syntax `-s`, `--longswitch`,
    or `-onedashlong`.

    The class is derived from the Python set type and arguments with this syntax are saved as set items.

    :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
    """
    def __init__(self, argv):
        set.__init__(self, self._make_switch_set(argv))

    def __repr__(self):
        switch_string = ""
        if len(self) > 0:
            for switch in self:
                switch_string = switch_string + "'" + switch + "', "
            switch_string = switch_string.rstrip()
            switch_string = switch_string.rstrip(",")

        return "{" + switch_string + "}"

    def __str__(self):
        switch_string = ""
        if len(self) > 0:
            for switch in self:
                switch_string = switch_string + "'" + switch + "', "
            switch_string = switch_string.rstrip()
            switch_string = switch_string.rstrip(",")

        return "{" + switch_string + "}"

    def _make_switch_set(self, argv):
        """Returns a set that includes all switches that are parsed from the command string.  Used to instantiate Switch
        objects.

        :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
        :returns: set"""

        switchset = set()
        for switch_candidate in argv:
            if "-" in switch_candidate[0] and "=" not in switch_candidate:
                # ignore everything after the double dash idiom, no longer considered switch context
                if switch_candidate == "--":
                    break
                else:
                    switch_candidate = switch_candidate.lstrip("-")
                    switchset.add(switch_candidate)

        return switchset

    def contains(self, needle):
        """Returns boolean that indicates the presence (True) or absence (False) of a tuple of test switches.
        Switch parameters in needle tuple should be passed without initial dash character(s) in the test switch
        argument name.

        :param needle: (iterable) An iterable that contains one or more test argument strings.
        :returns: boolean"""

        for expected_argument in needle:
            if expected_argument in self:
                pass
            else:
                return False

        return True  # if all tests above pass


class Mops(set):
    """A class that is instantiated with unique switches from multi-option command line options that use short,
    single dash syntax.

    Examples: -rnj -tlx

    Each alphabetic character in the option token is parsed to a separate option token.

    The class is derived from the Python set type and the single character option switches are stored as set items.

    :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
    """

    def __init__(self, argv):
        set.__init__(self, self._make_mops_set(argv))

    def __repr__(self):
        mops_string = ""
        if len(self) > 0:
            for switch in self:
                mops_string = mops_string + "'" + switch + "', "
            mops_string = mops_string.rstrip()
            mops_string = mops_string.rstrip(",")

        return "{" + mops_string + "}"

    def __str__(self):
        mops_string = ""
        if len(self) > 0:
            for switch in self:
                mops_string = mops_string + "'" + switch + "', "
            mops_string = mops_string.rstrip()
            mops_string = mops_string.rstrip(",")

        return "{" + mops_string + "}"

    def _make_mops_set(self, argv):
        """Returns a set of multi-option short syntax option characters that are parsed from a list of ordered
        command string arguments in the parameter `argv`.

        :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
        :returns: set"""

        mopsset = set()
        for mops_candidate in argv:
            if "-" in mops_candidate[0] and "=" not in mops_candidate:
                if len(mops_candidate) > 2:  # the argument includes '-' and more than one character following dash
                    if mops_candidate[1] != "-":  # it is not long option syntax (e.g. --long)
                        mops_candidate = mops_candidate.replace("-", "")
                        for switch in mops_candidate:
                            mopsset.add(switch)
        return mopsset

    def contains(self, needle):
        """Returns boolean that indicates the presence (True) or absence (False) of a tuple of test Mops syntax option
        switches.  The test strings should each be a single character without the dash that is used at the beginning of
        the entire token.

        :param needle: (iterable) An iterable that contains one or more test argument characters as strings.
        :returns: boolean"""

        for expected_argument in needle:
            if expected_argument in self:
                pass
            else:
                return False

        return True


class Definitions(dict):
    """A class that is instantiated with all command line definition options as defined by the syntax
    `-s <defintion argument>`,  `--longoption <defintion argument>`,
    `--longoption=<definition argument>`, or `-longoption <definition argument>`.

    To parse as a definition option, the argument to the option must not contain any dashes at the beginning of
    the argument string.  For example, `-o --long` is not considered a definition option-arg pair, whereas
    `-o long` is.

    This class is derived from the Python dictionary type.  The mapping is:

    key = option string with all dash '-' character(s) at the beginning of the string removed.  Internal dashes are
    maintained.

    value = definition argument string.

    :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
    """
    def __init__(self, argv):
        dict.__init__(self, self._make_definitions_obj(argv))

    def _make_definitions_obj(self, argv):
        """Parses definition options from a list of ordered command line arguments to define the dictionary that
        is used to instantiate the Definitions class.  Option string keys are stripped of dash characters before the
        first alphabetic character in the option name.

        :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
        :returns: dictionary with {key = option string : value = definition argument string} mapping"""

        defmap = {}
        arglist_length = len(argv)
        counter = 0
        for def_candidate in argv:
            # performance improvement to eliminate multiple string testing calls within this loop
            # dash_truth_test = def_candidate.startswith("-")
            dash_truth_test = ("-" in def_candidate[0])
            if dash_truth_test is True:
                # ignore all definition syntax strings after the double dash `--` command line idiom
                if def_candidate == "--":
                    break
                else:
                    # defines -option=definition syntax
                    if "=" in def_candidate:
                        split_def = def_candidate.split("=")
                        cleaned_key = split_def[0].lstrip("-")  # remove dash characters from the option
                        defmap[cleaned_key] = split_def[1]
                    # defines -d <positional def> or --define <positional def> syntax
                    elif counter < (arglist_length - 1):
                        if not argv[counter + 1].startswith("-"):
                            def_candidate = def_candidate.lstrip("-")
                            defmap[def_candidate] = argv[counter + 1]

            counter += 1

        return defmap

    def contains(self, needle):
        """Returns boolean that indicates the presence (True) or absence (False) of a tuple of option-argument
        definitions by option match attempt.

        The definition option string should be used without any initial dash characters in the definition argument name
        in contrast to how they were used on the command line.

        :param needle: (tuple) A tuple of one or more option strings from expected definition option-argument string pairs
        :returns: boolean"""

        for expected_definition in needle:
            if expected_definition in self.keys():
                pass
            else:
                return False

        return True  # if all tests above pass returns True

    def get_def_argument(self, needle):
        """Returns the definition argument string for a definition option test.  The needle parameter should not include
        dash characters at the beginning of the option string (i.e. use 'test' rather than '--test' and 't' rather than
        '-t').

        :param needle: (string) The requested option string from the definition option-argument pair.
        :returns: string
        :raises: MissingDictionaryKeyError if the option needle is not a key defined in the Definitions object"""

        if needle in self.keys():
            return self[needle]
        else:
            raise MissingDictionaryKeyError(needle)


class MultiDefinitions(Definitions):
    """A class that is used to parse option-argument definitions from a command line argument list where command line
    use includes multiple same option strings with different argument definitions.  An example is:

    `$ executable -o file1 -o file2`

    The class is derived from the commandlines.Definitions class (which is derived from Python dict). The
    commandlines.Definitions.contains and commandlines.Definitions.get_def_arguments methods are inherited from the
    Definitions class.

    The dictionary mapping is:

    key = option string with all dash '-' character(s) at the beginning of the string removed.  Internal dashes are
    maintained.

    value = list of all argument strings associated with the option string on the command line

    :param argv: (list) A list of command line arguments that maintain the argument order that was entered on command line
    """
    def __init__(self, argv):
        Definitions.__init__(self, argv)

    def _make_definitions_obj(self, argv):
        defmap = {}
        arglist_length = len(argv)
        counter = 0
        for def_candidate in argv:
            # performance improvement to eliminate multiple string testing calls within this loop
            # dash_truth_test = def_candidate.startswith("-")
            dash_truth_test = ("-" in def_candidate[0])
            if dash_truth_test is True:
                # ignore all definition syntax strings after the double dash `--` command line idiom
                if def_candidate == "--":
                    break
                else:
                    # defines -option=definition syntax
                    if "=" in def_candidate:
                        split_def = def_candidate.split("=")
                        cleaned_key = split_def[0].lstrip("-")  # remove dash characters from the option
                        if cleaned_key in defmap.keys():
                            defmap[cleaned_key].append(split_def[1])
                        else:
                            defmap[cleaned_key] = [split_def[1]]
                    # defines -d <positional def> or --define <positional def> syntax
                    elif counter < (arglist_length - 1):
                        if not argv[counter + 1].startswith("-"):
                            def_candidate = def_candidate.lstrip("-")
                            if def_candidate in defmap.keys():
                                defmap[def_candidate].append(argv[counter + 1])
                            else:
                                defmap[def_candidate] = [argv[counter + 1]]

            counter += 1

        # keep only the dictionary key:value pairs that include multiple values from key:value items parsed above
        multi_map = {}
        for key in defmap.keys():
            if len(defmap[key]) > 1:
                multi_map[key] = defmap[key]

        return multi_map
