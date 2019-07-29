# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, 2014 CERN
# Author: Pawel Szostek (pawel.szostek@cern.ch)
# Multi-tool support by Javier D. Garcia-Lasheras (javier@garcialasheras.com)
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
#

"""Module providing the source file class and a set of classes
representing the different possible files and file extensions"""

from __future__ import print_function
from __future__ import absolute_import
import os
import logging

from .util import path as path_mod
from .dep_file import DepFile, File, DepRelation
from .new_dep_solver import DepParser
import six

import re
import io
import mmap

class SourceFile(DepFile):

    """This is a class acting as a base for the different
    HDL sources files, i.e. those that can be parsed"""

    cur_index = 0

    def __init__(self, path, module, library):
        assert isinstance(path, six.string_types)
        self.is_include = False
        self.library = library
        if not library:
            self.library = "work"
        DepFile.__init__(self, file_path=path, module=module)

    def __hash__(self):
        return hash(self.path + self.library)


# SOURCE FILES

class VHDLFile(SourceFile):

    """This is the class providing the generic VHDL file"""

    def __init__(self, path, module, library=None):
        SourceFile.__init__(self, path=path, module=module, library=library)
        from hdlmake.vhdl_parser import VHDLParser
        self.parser = VHDLParser(self)


class VerilogFile(SourceFile):

    """This is the class providing the generic Verilog file"""

    def __init__(self, path, module, library=None,
                 include_dirs=None, is_include=False):
        SourceFile.__init__(self, path=path, module=module, library=library)
        from hdlmake.vlog_parser import VerilogParser
        self.include_dirs = []
        if include_dirs:
            self.include_dirs.extend(include_dirs)
        self.include_dirs.append(path_mod.relpath(self.dirname))
        self.parser = VerilogParser(self)
        self.is_include = is_include


class SVFile(VerilogFile):
    """This is the class providing the generic SystemVerilog file"""
    pass


# TCL COMMAND FILE

class TCLFile(File):
    """This is the class providing the Tool Command Language file"""
    pass


# XILINX FILES

class UCFFile(File):
    """This is the class providing the User Constraint Guide file"""
    pass


class XISEFile(File):
    """This is the class providing the new Xilinx ISE project file"""
    pass


class CDCFile(File):
    """This is the class providing the Xilinx ChipScope Definition
    and Connection file"""
    pass


class XMPFile(File):
    """Xilinx Embedded Micro Processor"""
    pass


class PPRFile(File):
    """Xilinx PlanAhead Project"""
    pass


class XPRFile(File):
    """Xilinx Vivado Project"""
    pass


class BDFile(File):
    """Xilinx Block Design"""
    pass


class XCOFile(File):
    """Xilinx Core Generator File"""
    pass


class NGCFile(File):
    """Xilinx Generated Netlist File"""
    pass


class XDCFile(File):
    """Xilinx Design Constraint File"""
    pass


class XCFFile(File):
    """Xilinx XST Constraint File"""
    pass


class COEFile(File):
    """Xilinx Coefficient File"""
    pass


class MIFFile(File):
    """Xilinx Memory Initialization File"""
    pass


class RAMFile(File):
    """Xilinx RAM  File"""
    pass


class VHOFile(File):
    """Xilinx VHDL Template File"""
    pass


class BMMFile(File):
    """Xilinx Block Memory Map File"""
    pass


class VEOFile(File):
    """Xilinx Verilog Template File"""
    pass


class XCIFile(SourceFile):
    """Xilinx Core IP File"""

    def __init__(self, path, module, library=None):
        SourceFile.__init__(self, path=path, module=module, library=library)
        from hdlmake.xci_parser import XCIParser
        self.parser = XCIParser(self)

XILINX_FILE_DICT = {
    'xise': XISEFile,
    'ise': XISEFile,
    'ngc': NGCFile,
    'ucf': UCFFile,
    'cdc': CDCFile,
    'xmp': XMPFile,
    'ppr': PPRFile,
    'xpr': XPRFile,
    'bd': BDFile,
    'xco': XCOFile,
    'xdc': XDCFile,
    'xcf': XCFFile,
    'coe': COEFile,
    'mif': MIFFile,
    'ram': RAMFile,
    'vho': VHOFile,
    'veo': VEOFile,
    'bmm': BMMFile,
    'xci': XCIFile}


# SYNOPSYS FILES

class SDCFile(File):
    """Synopsys Design Constraints"""
    pass


# LATTICE FILES

class LDFFile(File):
    """Lattice Diamond Project File"""
    pass


class LPFFile(File):
    """Lattice Preference/Constraint File"""
    pass

class PCFFile(File):
    """Icestorm Physical constraints File"""
    pass

class EDFFile(File):
    """EDIF Netlist Files"""
    pass


LATTICE_FILE_DICT = {
    'ldf': LDFFile,
    'lpf': LPFFile,
    'edf': EDFFile,
    'edif': EDFFile,
    'edi': EDFFile,
    'edn': EDFFile,
    'pcf': PCFFile}


# MICROSEMI/ACTEL FILES

class PDCFile(File):
    """Physical Design Constraints"""
    pass


MICROSEMI_FILE_DICT = {
    'pdc': PDCFile}


# OHR FILES

class WBGenFile(File):
    """Wishbone generator file"""
    pass


# INTEL/ALTERA FILES

class QIPFile(File):
    """This is the class providing the Altera Quartus IP file"""
    pass

class IPFile(SourceFile):
    """This is the class providing the Altera Quartus IP file"""
    def __init__(self, path, module):
        assert isinstance(path, six.string_types)
        filename = path_mod.pathsplit(path)[-1]
        library = filename[:-3] # making some poor assumptions here.
        entity = filename[:-3]  # and here.
        SourceFile.__init__(self,
                            path=path,
                            module=module,
                            library=library)
        obj_name = "%s.%s" % (library, entity)
        provides = DepRelation(obj_name, DepRelation.PROVIDE, DepRelation.ENTITY)
        self.add_relation(provides)
        logging.debug("%s -> provides %s" % (filename, obj_name))
        self.is_parsed = True

class QSYSFile(SourceFile):
    """Qsys - Altera's System Integration Tool"""
    def __init__(self, path, module):
        assert isinstance(path, six.string_types)
        filename = path_mod.pathsplit(path)[-1]
        library = filename[:-5] # making some poor assumptions here.
        entity = filename[:-5]  # and here.        
        SourceFile.__init__(self,
                            path=path,
                            module=module,
                            library=library)
        obj_name = "%s.%s" % (library, entity)
        self.add_relation(DepRelation(obj_name, DepRelation.PROVIDE, DepRelation.ENTITY))
        self.add_relation(DepRelation(obj_name, DepRelation.PROVIDE, DepRelation.ARCHITECTURE))
        logging.debug("%s -> provides %s" % (filename, obj_name))
        with io.open(path, 'r', encoding="utf-8") as qsys_file:
            # Avoid loading entire file into memory - since it is a large file.
            with mmap.mmap(qsys_file.fileno(), 0, access=mmap.ACCESS_READ) as qsys_xml:
                child_re = r'<hdlLibraryName>(?P<entity>[\w_\d]+)</hdlLibraryName>'
                pattern = re.compile(child_re.encode("utf-8"))
                for match in pattern.finditer(qsys_xml):
                    entity = str(match.group("entity").decode('utf-8'))
                    library = entity
                    obj_name = "%s.%s" % (library, entity)
                    depends = DepRelation(obj_name, DepRelation.USE, DepRelation.ENTITY)
                    self.add_relation(depends)
                    logging.debug("%s -> depends %s" % (filename, obj_name))
        self.is_parsed = True

class DPFFile(File):
    """This is the class providing Altera Quartus Design Protocol File"""
    pass


class QSFFile(File):
    """Quartus Settings File"""
    pass


class BSFFile(File):
    """Quartus Block Symbol File"""
    pass


class BDFFile(File):
    """Quartus Block Design File"""
    pass


class TDFFile(File):
    """Quartus Text Design File"""
    pass


class GDFFile(File):
    """Quartus Graphic Design File"""
    pass


class SignalTapFile(File):
    """This is the class providing the Altera Signal Tap Language file"""
    pass


ALTERA_FILE_DICT = {
    'stp': SignalTapFile,
    'qip': QIPFile,
    'ip' : IPFile,
    'qsys': QSYSFile,
    'dpf': DPFFile,
    'qsf': QSFFile,
    'bsf': BSFFile,
    'bdf': BDFFile,
    'tdf': TDFFile,
    'gdf': GDFFile}


class SourceFileSet(set):

    """Class providing a extension of the 'set' object that includes
    methods that allow for an easier management of a collection of HDL
    source files"""

    def __init__(self):
        super(SourceFileSet, self).__init__()
        self = []

    def __str__(self):
        return str([str(f) for f in self])

    def add(self, files):
        """Add a set of files to the source fileset instance"""
        if isinstance(files, str):
            raise RuntimeError("Expected object, not a string")
        elif files is None:
            logging.debug("Got None as a file.\n Ommiting")
        else:
            try:
                for file_aux in files:
                    super(SourceFileSet, self).add(file_aux)
            except TypeError:  # single file, not a list
                super(SourceFileSet, self).add(files)

    def filter(self, filetype):
        """Method that filters and returns all of the HDL source files
        contained in the instance SourceFileSet matching the provided type"""
        out = SourceFileSet()
        for file_aux in self:
            if isinstance(file_aux, filetype):
                out.add(file_aux)
        return out

    def sort(self):
        """Return a sorted list of the fileset.  This is useful to have always
        the same output"""
        return sorted(self, key=(lambda x: x.file_path))

def create_source_file(path, module, library=None,
                       include_dirs=None, is_include=False):
    """Function that analyzes the given arguments and returns a new HDL source
    file of the appropriated type"""
    if path is None or path == "":
        raise RuntimeError("Expected a file path, got: " + str(path))
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    tmp = path.rsplit('.')
    extension = tmp[len(tmp) - 1]
    logging.debug("add file " + path)

    new_file = None
    if extension in ['vhd', 'vhdl', 'vho']:
        new_file = VHDLFile(path=path,
                            module=module,
                            library=library)
    elif extension in ['v', 'vh', 'vo', 'vm']:
        new_file = VerilogFile(path=path,
                               module=module,
                               library=library,
                               include_dirs=include_dirs,
                               is_include=is_include)
    elif extension == 'sv' or extension == 'svh':
        new_file = SVFile(path=path,
                          module=module,
                          library=library,
                          include_dirs=include_dirs,
                          is_include=is_include)
    elif extension == 'wb':
        new_file = WBGenFile(path=path, module=module)
    elif extension == 'tcl':
        new_file = TCLFile(path=path, module=module)
    elif extension == 'sdc':
        new_file = SDCFile(path=path, module=module)
    elif extension in XILINX_FILE_DICT:
        new_file = XILINX_FILE_DICT[extension](path=path, module=module)
    elif extension in ALTERA_FILE_DICT:
        new_file = ALTERA_FILE_DICT[extension](path=path, module=module)
    elif extension in LATTICE_FILE_DICT:
        new_file = LATTICE_FILE_DICT[extension](path=path, module=module)
    elif extension in MICROSEMI_FILE_DICT:
        new_file = MICROSEMI_FILE_DICT[extension](path=path, module=module)
    else:
        raise Exception("Cannot create source file %s, "
                        "unknown file extension %s", path, extension)
    return new_file
