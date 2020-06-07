#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path


class Ufo(object):
    def __init__(self, ufopath, glyphsdir_list):
        self.ufopath = ufopath
        self.ufoversion = (
            None
        )  # defined on instantiation in the classes that inherit Ufo
        self.glyphsdir_list = glyphsdir_list
        self.mandatory_root_basefilepaths = None
        self.mandatory_glyphsdir_basefilepaths = None
        self.all_root_plist_files_list = None
        self.all_glyphsdir_plist_files_list = None

    def _make_root_plist_path(self, basefilename):
        if basefilename == "metainfo.plist":
            return os.path.join(self.ufopath, basefilename)
        elif basefilename == "fontinfo.plist":
            return os.path.join(self.ufopath, basefilename)
        elif basefilename == "groups.plist":
            return os.path.join(self.ufopath, basefilename)
        elif basefilename == "kerning.plist":
            return os.path.join(self.ufopath, basefilename)
        elif basefilename == "lib.plist":
            return os.path.join(self.ufopath, basefilename)
        elif basefilename == "layercontents.plist":
            return os.path.join(self.ufopath, basefilename)

    def _make_glyphsdir_plist_path(self, glyphsdirname, basefilename):
        if basefilename == "contents.plist":
            return os.path.join(self.ufopath, glyphsdirname, basefilename)
        elif basefilename == "layerinfo.plist":
            return os.path.join(self.ufopath, glyphsdirname, basefilename)

    def get_root_plist_filepath(self, basefilename):
        return self._make_root_plist_path(basefilename)

    def get_glyphsdir_plist_filepath_list(self, basefilename):
        path_list = []
        for glyphsdir in self.glyphsdir_list:
            glyphsdir_basename = glyphsdir[1]
            path_list.append(
                self._make_glyphsdir_plist_path(glyphsdir_basename, basefilename)
            )
        return path_list

    def get_mandatory_filepaths_list(self):
        """
        Creates a list of relative filepaths to mandatory files in UFO source.  These files are defined in the
        Ufo2 and Ufo3 classes that inherit from Ufo
        :return: list of filepath strings
        """
        mandatory_filepath_list = []
        for mandatory_root_basefile in self.mandatory_root_basefilepaths:
            mandatory_filepath_list.append(
                self.get_root_plist_filepath(mandatory_root_basefile)
            )
        for mandatory_glyphs_basefile in self.mandatory_glyphsdir_basefilepaths:
            glyphsdirs_filelist = self.get_glyphsdir_plist_filepath_list(
                mandatory_glyphs_basefile
            )
            for a_file in glyphsdirs_filelist:
                mandatory_filepath_list.append(a_file)
        return mandatory_filepath_list

    def get_glyphsdir_path_list(self):
        raise NotImplementedError

    def get_ufo_version(self):
        return self.ufoversion


class Ufo2(Ufo):
    def __init__(self, ufopath, glyphsdir_list):
        super(Ufo2, self).__init__(ufopath, glyphsdir_list)
        self.ufopath = ufopath
        self.ufoversion = 2
        self.glyphsdir_list = glyphsdir_list
        self.mandatory_root_basefilepaths = ["metainfo.plist"]
        self.mandatory_glyphsdir_basefilepaths = ["contents.plist"]
        self.all_root_plist_files_list = [
            "metainfo.plist",
            "fontinfo.plist",
            "groups.plist",
            "kerning.plist",
            "lib.plist",
        ]
        self.all_glyphsdir_plist_files_list = ["contents.plist"]

    def get_glyphsdir_path_list(self):
        glyphsdir_path = os.path.join(
            self.ufopath, "glyphs"
        )  # UFOv2 includes only one glyphs directory
        return [glyphsdir_path]


class Ufo3(Ufo):
    def __init__(self, ufopath, glyphsdir_list):
        super(Ufo3, self).__init__(ufopath, glyphsdir_list)
        self.ufopath = ufopath
        self.ufoversion = 3
        self.glyphsdir_list = glyphsdir_list
        self.mandatory_root_basefilepaths = ["metainfo.plist", "layercontents.plist"]
        self.mandatory_glyphsdir_basefilepaths = ["contents.plist"]
        self.all_root_plist_files_list = [
            "metainfo.plist",
            "fontinfo.plist",
            "groups.plist",
            "kerning.plist",
            "lib.plist",
            "layercontents.plist",
        ]
        self.all_glyphsdir_plist_files_list = ["contents.plist", "layerinfo.plist"]

    def get_glyphsdir_path_list(self):
        glyphsdir_path_list = []
        for glyphsdir in self.glyphsdir_list:
            glyphsdir_path = os.path.join(self.ufopath, glyphsdir[1])
            glyphsdir_path_list.append(glyphsdir_path)
        return glyphsdir_path_list
