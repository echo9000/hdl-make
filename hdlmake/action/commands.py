#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 CERN
# Author: Pawel Szostek (pawel.szostek@cern.ch)
#
# This file is part of Hdlmake.
#
# Hdlmake is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hdlmake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hdlmake.  If not, see <http://www.gnu.org/licenses/>.

"""This module provides the core actions to the pool"""

from __future__ import absolute_import
from __future__ import print_function
import logging
import os
import sys
import os.path

import hdlmake.fetch as fetch
import hdlmake.new_dep_solver as dep_solver
from hdlmake.util import path as path_mod
from hdlmake.fetch.svn import Svn
from hdlmake.fetch.git import Git, GitSM
from hdlmake.fetch.local import Local
from .action import Action
from hdlmake.srcfile import VHDLFile, VerilogFile, IPFile, QSYSFile

class ActionCore(Action):

    """Class that contains the methods for core actions"""

    def __init__(self, *args):
        super(ActionCore, self).__init__(*args)
        self.git_backend = Git()
        self.gitsm_backend = GitSM()
        self.svn_backend = Svn()
        self.local_backend = Local()

    def _check_all_fetched(self):
        """Check if every module in the pool is fetched"""

        if not len([m for m in self.manifests if not m.isfetched]) == 0:
            raise Exception(
                "Fetching should be done before continuing.\n"
                "The following modules remains unfetched:\n"
                " {}".format(
                    "\n ".join([str(m) for m in self.manifests
                                if not m.isfetched])))

    def makefile(self):
        """Write the Makefile for the current design"""
        self._check_all_fetched()
        self.build_file_set()
        self.solve_file_set()
        combined_fileset = self.parseable_fileset
        combined_fileset.add(self.privative_fileset)
        if self.tool == None:
            logging.error("No tool selected. You may need to set an action in your Manifest.py before a Makefile can be generated.")
            logging.error("    Either action='simulation', or action='synthesis'.")
            quit()
        self.tool.write_makefile(self.config,
                                 combined_fileset,
                                 filename=self.options.filename)

    def _fetch_all(self):
        """Fetch all the modules declared in the design"""

        def _fetch_module(module):
            """Fetch the given module from the remote origin"""
            new_modules = []
            logging.debug("Fetching module: %s", str(module))
            if module.source == 'svn':
                result = self.svn_backend.fetch(module)
            elif module.source == 'git':                
                result = self.git_backend.fetch(module)
            else:
                assert module.source == 'gitsm'
                result = self.gitsm_backend.fetch(module)
            if result is False:
                raise Exception("Unable to fetch module %s", str(module.url))
            module.parse_manifest()
            for m in module.modules:
                new_modules.extend(module.modules[m])
            return new_modules

        fetch_queue = [m for m in self.manifests]

        while len(fetch_queue) > 0:
            cur_mod = fetch_queue.pop()
            new_modules = []
            if cur_mod.isfetched:
                new_modules = cur_mod.submodules()
            else:
                new_modules = _fetch_module(cur_mod)
            for mod in new_modules:
                if not mod.isfetched:
                    logging.debug("Appended to fetch queue: "
                                  + str(mod.url))
                    self._add(mod)
                    fetch_queue.append(mod)
                else:
                    logging.debug("NOT appended to fetch queue: "
                                  + str(mod.url))

    def fetch(self):
        """Fetch the missing required modules from their remote origin"""
        logging.info("Fetching needed modules.")
        for mod in self.manifests:
            if mod.isfetched and not mod.manifest_dict == None:
                if 'fetch_pre_cmd' in mod.manifest_dict:
                    os.system(mod.manifest_dict.get("fetch_pre_cmd", ''))
        self._fetch_all()
        for mod in self.manifests:
            if mod.isfetched and not mod.manifest_dict == None:
                if 'fetch_post_cmd' in mod.manifest_dict:
                    os.system(mod.manifest_dict.get("fetch_post_cmd", ''))
        logging.info("All modules fetched.")

    def clean(self):
        """Delete the local copy of the fetched modules"""
        logging.info("Removing fetched modules..")
        remove_list = [mod_aux for mod_aux in self.manifests
                       if mod_aux.source in ['git', 'gitsm', 'svn']
                       and mod_aux.isfetched]
        remove_list.reverse()  # we will remove modules in backward order
        if len(remove_list):
            for mod_aux in remove_list:
                logging.info("... clean: " + mod_aux.url +
                             " [from: " + mod_aux.path + "]")
                mod_aux.remove_dir_from_disk()
        else:
            logging.info("There are no modules to be removed")
        logging.info("Modules cleaned.")

    def list_files(self):
        """List the files added to the design across the pool hierarchy"""
        unfetched_modules = [mod_aux for mod_aux in self.manifests
                             if not mod_aux.isfetched]
        for mod_aux in unfetched_modules:
            logging.warning(
                "List incomplete, module %s has not been fetched!", mod_aux)
        if self.options.top != None:
            self.top_entity = self.options.top
        self.build_file_set()
        self.solve_file_set()
        file_list = dep_solver.make_dependency_sorted_list(
            self.parseable_fileset)
        if self.options.qip:
            self._write_qip(file_list, self.options.qip)
            return
        files_str = [file_aux.path for file_aux in file_list]
        if self.options.reverse is True:
            files_str.reverse()
        if self.options.delimiter is None:
            delimiter = "\n"
        else:
            delimiter = self.options.delimiter
        print(delimiter.join(files_str))

    def _write_qip(self, file_list, filename):
        tcl = []
        for file_aux in file_list:
            path = os.path.relpath(file_aux.path)
            lib  = file_aux.library
            if isinstance(file_aux, VHDLFile):
                ftype = "VHDL_FILE"
            elif isinstance(file_aux, VerilogFile):
                ftype = "VERILOG_FILE"
            elif isinstance(file_aux, IPFile):
                ftype = "IP_FILE"
            elif isinstance(file_aux, QSYSFile):
                ftype = "QSYS_FILE"
            else:
                ftype = "MISC_FILE"

                #[file join $::quartus(qip_path) {path}]
            tcl.append('''set_global_assignment -library "{lib}" -name {ftype}  "{path}"'''.format(lib=lib, ftype=ftype, path=path))

        #qip_filename = self.get_top_module().manifest_dict["qip_filename"]
        if not filename:
            filename = self.top_entity
        outfile = open(filename, "w")
        outfile.write("\n".join(tcl))
        outfile.write("\n")
        outfile.close()


    def _print_comment(self, message):
        """Private method that prints a message to stdout if not terse"""
        if not self.options.terse:
            print(message)

    def _print_file_list(self, file_list):
        """Print file list to standard out"""
        if not len(file_list):
            self._print_comment("# * This module has no files")
        else:
            for file_aux in file_list:
                print("%s\t%s" % (
                    path_mod.relpath(file_aux.path), "file"))

    def list_modules(self):
        """List the modules that are contained by the pool"""

        for mod_aux in self.manifests:
            if not mod_aux.isfetched:
                logging.warning("Module not fetched: %s", mod_aux.url)
                self._print_comment("# MODULE UNFETCHED! -> %s" % mod_aux.url)
            else:
                self._print_comment("# MODULE START -> %s" % mod_aux.url)
                if mod_aux.source in ['svn', 'git', 'gitsm']:
                    self._print_comment("# * URL: " + mod_aux.url)
                if (mod_aux.source
                        in ['svn', 'git', 'gitsm', 'local']
                        and mod_aux.parent):
                    self._print_comment("# * The parent for this module is: %s"
                                        % mod_aux.parent.url)
                else:
                    self._print_comment("# * This is the root module")
                print("%s\t%s" % (mod_aux.path, mod_aux.source))
                if self.options.withfiles:
                    self._print_file_list(mod_aux.files)
                self._print_comment("# MODULE END -> %s" % mod_aux.url)
            self._print_comment("")

    def update(self):
        """Pull updates to modules"""
        for mod_aux in self.manifests:
            if not mod_aux.isfetched:
                logging.warning("Module not fetched: %s", mod_aux.url)
                self._print_comment("# MODULE UNFETCHED! -> %s" % mod_aux.url)
            else:                
                if mod_aux.source == 'git':
                    self.git_backend.update(mod_aux)
                