﻿# -*- coding: utf-8 -*-

# Copyright (C) 2009 PSchem Contributors (see CONTRIBUTORS for details)

# This file is part of PSchem Database
 
# PSchem is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PSchem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with PSchem Database.  If not, see <http://www.gnu.org/licenses/>.

#print 'Cells in'

#from Database.CellViews import *
from Database.Design import *
from xml.etree import ElementTree as et

#print 'Cells out'

class Cell():
    def __init__(self, name, library):
        self._cellViews = set()
        self._cellViewNames = {}
        self._name = name
        self._library = library
        library.cellAdded(self)

    def addCellView(self, cellView):
        self._cellViews.add(cellView)
        cellView.setCell(self)
        self._cellViewNames[cellView.name()] = cellView
        self.database().updateDatabaseViews()

    def removeCellView(self, cellView):
        cellView.remove()
        self._cellViews.remove(cellView)
        del(self._cellViewNames[cellView.name()])
        self.database().updateDatabaseViews()

    def cellViews(self):
        return self._cellViews

    def cellViewNames(self):
        return self._cellViewNames.keys()

    def cellViewByName(self, cellViewName):
        if self._cellViewNames.has_key(cellViewName):
            return self._cellViewNames[cellViewName]
        else:
            return None

    def cellViewAdded(self, cellView):
        self._cellViews.add(cellView)
        self._cellViewNames[cellView.name()] = cellView
        self.library().cellChanged(self)

    def cellViewRemoved(self, cellView):
        self._cellViews.remove(cellView)
        del self._cellViewNames[cellView.name()]
        self.library().cellChanged(self)
        
    def cellViewChanged(self, cellView):
        self.library().cellChanged(self)

    def name(self):
        return self._name

    def implementation(self):
        return self.cellViewByName('schematic')  #currently assume it is 'schematic'

    def symbol(self):
        return self.cellViewByName('symbol')  #currently assume it is 'symbol'

    def library(self):
        return self._library
        
    def database(self):
        return self.library().database()

    def remove(self):
        for c in list(self.cellViews()):
            c.remove()

class Library():
    def __init__(self, name, database, parentLibrary = None):
        self._cells = set()
        self._cellNames = {}
        self._libraries = set()
        self._libraryNames = {}
        self._parentLibrary = parentLibrary
        self._name = name
        self._database = database
        if parentLibrary:
            parentLibrary.libraryAdded(self)
        else:
            database.libraryAdded(self)

    def cells(self):
        return self._cells

    def cellNames(self):
        return self._cellNames.keys()

    def cellAdded(self, cell):
        self._cells.add(cell)
        self._cellNames[cell.name()] = cell
        self.database().libraryChanged(self)

    def cellRemoved(self, cell):
        self._cells.remove(cell)
        del self._cellNames[cell.name()]
        self.database().libraryChanged(self)
        
    def cellChanged(self, cell):
        self.database().libraryChanged(self)

    def libraryAdded(self, library):
        self._libraries.add(library)
        self._libraryNames[library.name()] = library
        self.database().libraryChanged(self)

    def libraryRemoved(self, library):
        self._libraries.remove(library)
        del self._libraryNames[library.name()]
        self.database().libraryChanged(self)
        
    def libraryChanged(self, library):
        self.database().libraryChanged(self)

    def libraries(self):
        return self._libraries

    def libraryNames(self):
        return self._libraryNames.keys()

    def libraryByPath(self, libraryPath):
        (first, sep, rest) = libraryPath.partition('/')
        if first == '..':
            return self.parentLibrary().libraryByPath(rest)
        elif first == '.':
            return self.libraryByPath(rest)
        elif first == '':
            return self.database().libraryByPath(rest)
        elif self._libraryNames.has_key(first):
            if rest == '':
                return self._libraryNames[first]
            else:
                return self._libraryNames[first].libraryByPath(rest)
        else:
            return None

    @classmethod
    def concatenateLibraryPaths(cls, libPath1, libPath2):
        (beginning1, sep, last1) = libPath1.rpartition('/')
        (first2, sep, rest2) = libPath2.partition('/') 
        if libPath2.find('/') == 0: #is absolute
            return libPath2
        elif len(libPath2) == 0:
            return libPath1
        elif first2 == '.':
            return Library.concatenateLibraryPaths(libPath1, rest2)
        elif first2 == '..' and beginning1 != '':
            return Library.concatenateLibraryPaths(beginning1, rest2)
        elif first2 == '..':
            return '/' + libPath2
        else:
            return libPath1 + '/' + libPath2

    def cellByName(self, cellName):
        if self._cellNames.has_key(cellName):
            return self._cellNames[cellName]
        else:
            return None

    def cellViewByName(self, cellName, cellViewName):
        cell = self.cellByName(cellName)
        if cell:
            return cell.cellViewByName(cellViewName)
        else:
            return None

    def name(self):
        return self._name

    def path(self):
        if self.parentLibrary():
            return self.parentLibrary().path() + '/' + self.name()
        else:
            return '/' + self.name()

    def database(self):
        if not self._database:
            self._database = self.parentLibrary().database()
        return self._database
        
    def parentLibrary(self):
        return self._parentLibrary
        
    def remove(self):
        # remove child libraries&cells
        for c in list(self.cells()):
            c.remove()
        for l in list(self.libraries()):
            l.remove()
        # notify parent library or database
        if self.parentLibrary():
            self.parentLibrary().libraryRemoved(self)
        else:
            self.database().libraryRemoved(self)
        

class Database():
    def __init__(self):
        self._libraries = set()
        self._libraryNames = {}
        self._databaseViews = set()
        self._layers = None
        self._designs = Designs()

    def installUpdateDatabaseViewsHook(self, view):
        self._databaseViews.add(view)

    def updateDatabaseViewsPreparation(self):
        """
        Some views may require notification before layout
        of the database changes
        """
        for v in self._databaseViews:
            v.prepareForUpdate()
        
    def updateDatabaseViews(self):
        "Notify views that the database layout has changed"
        for v in self._databaseViews:
            v.update()

    def updateDatabaseViewsPreparation(self):
        """
        Some views may require notification before layout
        of the design hierarchy changes
        """
        for v in self._databaseViews:
            v.prepareForUpdate()
        
    def libraryAdded(self, library):
        self._libraries.add(library)
        #library.setDatabase(self)
        self._libraryNames[library.name()] = library
        self.updateDatabaseViews()

    def libraryRemoved(self, library):
        self._libraries.remove(library)
        del self._libraryNames[library.name()]
        self.updateDatabaseViews()
        
    def libraryChanged(self, library):
        self.updateDatabaseViews()

    def libraries(self):
        return self._libraries

    def libraryNames(self):
        return self._libraryNames.keys()

    def makeLibraryFromPath(self, libraryPath, rootLib=None):
        (first, sep, rest) = libraryPath.partition('/')
        if libraryPath == '' or first == '..':
            return None
        if first == '' or first == '.':
            return self.makeLibraryFromPath(rest)
        if rootLib:
            lib = rootLib.libraryByPath(first)
            if not lib:
                lib = Library(first, self, rootLib)
        else:
            lib = self.libraryByPath(first)
            if not lib:
                lib = Library(first, self)
        if rest == '':
            return lib
        return self.makeLibraryFromPath(rest, lib)
        
    def libraryByPath(self, libraryPath):
        if libraryPath == '':
            return None
        (first, sep, rest) = libraryPath.partition('/')
        if first == '' or first == '.':
            return self.libraryByPath(rest)
        elif self._libraryNames.has_key(first):
            if rest == '':
                return self._libraryNames[first]
            else:
                return self._libraryNames[first].libraryByPath(rest)
        else:
            return None

    def cellByName(self, libraryPath, cellName):
        lib = self.libraryByPath(libraryPath)
        if lib:
            return lib.cellByName(cellName)
        else:
            return None

    def cellViewByName(self, libraryPath, cellName, cellViewName):
        lib = self.libraryByPath(libraryPath)
        if lib:
            return lib.cellViewByName(cellName, cellViewName)
        else:
            return None

    def setLayers(self, layers):
        self._layers = layers
        #self.updateViews()

    def layers(self):
        return self._layers
        
    def designs(self):
        return self._designs


class Importer:
    def __init__(self, database):
        self._database = database
        self.reset()

    def reset(self):
        self._importedCellsView = set()
        self._reader = None
        self._fileList = []
        self._targetLibrary = 'work'
        self._overwrite = False
        self._recursive = True
