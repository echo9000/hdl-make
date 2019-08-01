"""Provides the core functionality for the HDLMake module"""

from __future__ import absolute_import
import os
import sys
import logging

from hdlmake import fetch
from hdlmake.util import path as path_mod


class ModuleConfig(object):

    """This class containt the base properties and methods that
    need to be initialized for a proper behavior"""

    def __init__(self):
        self.source = None
        self.parent = None
        self.url = None
        self.branch = None
        self.revision = None
        self.path = None
        self.isfetched = False
        self.library_overide = None

    def process_manifest(self):
        """process_manifest does nothing for ModuleConfig"""
        pass

    def basename(self):
        """Get the basename for the module"""
        if self.source == 'svn':
            return path_mod.svn_basename(self.url)
        else:
            return path_mod.url_basename(self.url)

    def fetchto(self):
        """Get the fetchto folder for the module"""
        return os.path.dirname(os.path.join(".", self.path))

    def init_config(self, module_args):
        """This initializes the module configuration.
        The function is executed by Module constructor"""
        parent = module_args.parent
        url = module_args.url
        source = module_args.source
        fetchto = module_args.fetchto

        self.source = source
        self.parent = parent

        if self.source != 'local':
            if self.source == 'svn':
                self.url, self.revision = path_mod.svn_parse(url)
            else:
                self.url, self.branch, self.revision, self.library_overide = path_mod.url_parse(url)
            basename = self.basename()
            if self.library_overide:
                basename += "-" + self.library_overide
            path = path_mod.relpath(os.path.abspath(
                os.path.join(fetchto, basename)))

            # Check if the module dir exists and is not empty
            if os.path.exists(path) and os.listdir(path):
                self.path = path
                self.isfetched = True
                logging.debug("Module %s (parent: %s) is fetched.",
                              url, self.parent.path)
            else:
                self.path = path
                self.isfetched = False
                logging.warning("Module %s (parent: %s) is NOT fetched.",
                              url, self.parent.path)
        else:
            self.url, self.branch, self.revision = url, None, None

            if not os.path.exists(url):
                raise Exception(
                    "Path to the local module doesn't exist:\n" + url
                    + "\nThis module was instantiated in: " + str(self.parent))
            self.path = path_mod.relpath(url)
            self.isfetched = True

    def _check_filepath(self, filepath):
        """Check the provided filepath against several conditions"""
        if filepath:
            if path_mod.is_abs_path(filepath):
                logging.warning(
                    "Specified path seems to be an absolute path: " +
                    filepath + "\nOmitting.")
                return False
            filepath = os.path.join(self.path, filepath)
            if not os.path.exists(filepath):
                raise Exception(
                    "Path specified in manifest {} doesn't exist: {}".format(
                    self.path, filepath))

            filepath = path_mod.rel2abs(filepath, self.path)
            if os.path.isdir(filepath):
                logging.warning(
                    "Path specified in manifest %s is a directory: %s",
                    self.path, filepath)
        return True

    def _make_list_of_paths(self, list_of_paths):
        """Get a list with only the valid absolute paths from the provided"""
        paths = []
        for filepath in list_of_paths:
            if self._check_filepath(filepath):
                paths.append(path_mod.rel2abs(filepath, self.path))
        return paths


class ModuleCore(ModuleConfig):

    """This is the class providing the module core functionality"""

    def __init__(self):
        # Universal Manifest Properties
        self.library = "work"
        self.action = None
        self.pool = None
        self.top_manifest = None
        self.manifest_dict = None
        super(ModuleCore, self).__init__()

    def set_pool(self, pool):
        """Set the associated pool for the module instance"""
        self.pool = pool
        self.top_manifest = pool.get_top_manifest()

    def process_manifest(self):
        """Method that process the core manifest section"""
        self._process_manifest_universal()
        super(ModuleCore, self).process_manifest()

    def _process_manifest_universal(self):
        """Method processing the universal manifest directives;
           set library (inherited if not set) and action"""
        # Libraries
        if self.library_overide is not None:
            self.library = self.library_overide
        elif "library" in self.manifest_dict:
            self.library = self.manifest_dict["library"]
        elif self.parent:
            self.library = self.parent.library

        if "action" in self.manifest_dict:
            self.action = self.manifest_dict["action"].lower()
