# -*- coding: utf-8 -*-

# Copyright (C) 2009 PSchem Contributors (see CONTRIBUTORS for details)

# This file is part of PSchem.
 
# PSchem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PSchem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PSchem.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui
from Database.Primitives import *
from Database.Design import *
#import sys

class HierarchyModel(QtCore.QAbstractItemModel):
    def __init__(self, designs, parent=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self._designs = designs
        designs.installUpdateHierarchyViewsHook(self)

    def designs(self):
        return self._designs
        
    def update(self):
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        #self.reset()

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()

        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        row = index.row()

        col = index.column()
        data = index.internalPointer()
        if isinstance(data, Design):
            if col == 0:
                return QtCore.QVariant('')
            elif col == 1:
                return QtCore.QVariant(data.cellView().cell().name())
            else:
                return QtCore.QVariant(data.cellView().library().path())
        elif isinstance(data, DesignUnit):
            if col == 0:
                return QtCore.QVariant(data.instance().name())
            elif col == 1:
                return QtCore.QVariant(data.instance().instanceCellName())
            else:
                return QtCore.QVariant(data.instance().instanceLibraryPath())
        else:
            return QtCore.QVariant()


    def index(self, row, column, parent):

        data = None
        if parent.isValid():
            data = parent.internalPointer()

        if not parent.isValid():
        #if isinstance(data, Design):
            children = list(self.designs())
        elif isinstance(data, DesignUnit):
            children = data.childDesignUnits().values() #+ list(data.pins()) + list(data.nets() - data.pins())
        else:
            return QtCore.QModelIndex()

        if row >= 0 and len(children) > row:
            return self.createIndex(row, column, children[row])
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        data = index.internalPointer()
        if isinstance(data, Design):
            return QtCore.QModelIndex()
        if isinstance(data, DesignUnit):
            parent = data.parentDesignUnit()
            #sys.stderr.write('parent' + parent.cellView().cell().name() + "\n")
            if parent:
                pparent = parent.parentDesignUnit()
                if pparent:
                    #sys.stderr.write('pparent' + pparent.cellView().cell().name() + "\n")
                    d = pparent.childDesignUnits().values()
                    n = d.index(parent)
                    return self.createIndex(n, 0, parent)
                else:
                    d = list(self.designs())
                    n = d.index(parent)
                    return self.createIndex(n, 0, parent)
        return QtCore.QModelIndex()

    def hasChildren(self, parent):
        if not parent.isValid():
            return True
        data = parent.internalPointer()
        if isinstance(data, DesignUnit):
            return len(data.childDesignUnits()) > 0
        else:
            return False

    def rowCount(self, parent):
        #if parent.column() > 1:
        #    return 0

        if not parent.isValid():
            return len(self.designs())

        data = parent.internalPointer()
        if isinstance(data, DesignUnit):
            return len(data.childDesignUnits()) #+ list(data.pins()) + list(data.nets() - data.pins())
        return 0

    def columnCount(self, parent):
        if not parent.isValid():
            return 3
        data = parent.internalPointer()
        if isinstance(data, DesignUnit):
            return 3
        return 0


    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return QtCore.QVariant(self.tr("Instance"))
            elif section == 1:
                return QtCore.QVariant(self.tr("Cell"))
            elif section == 2:
                return QtCore.QVariant(self.tr("Library"))
            else:
                return QtCore.QVariant()

        return QtCore.QVariant()


class ProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self):
        QtGui.QSortFilterProxyModel.__init__(self)
        self.libRegExp = QtCore.QRegExp()
        self.cellRegExp = QtCore.QRegExp()

    def filterAcceptsRow(self, row, parent):
        source_idx = self.sourceModel().index(row, 0, parent)

        if not source_idx.isValid():
            return True

        #data = source_idx.internalPointer()
        #if isinstance(data, Library) and not self.libRegExp.isEmpty():
        #    text = self.sourceModel().data(
        #        source_idx, QtCore.Qt.DisplayRole).toString()
        #    return text.contains(self.libRegExp)
        #elif isinstance(data, Cell) and not self.cellRegExp.isEmpty():
        #    text = self.sourceModel().data(
        #        source_idx, QtCore.Qt.DisplayRole).toString()
        #    return text.contains(self.cellRegExp)
        #else:
        return True

    def setRegExps(self, libRegExp, cellRegExp):
        self.libRegExp = libRegExp
        self.cellRegExp = cellRegExp


class HierarchyWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.proxyModel = ProxyModel()
        self.proxyModel.setDynamicSortFilter(True)
        self.treeView = QtGui.QTreeView()
        self.treeView.setUniformRowHeights(True)
        self.treeView.setSortingEnabled(True)
        self.treeView.setAlternatingRowColors(True)
        #self.treeView.setAllColumnsShowFocus(True)

        layout2 = QtGui.QHBoxLayout()
        self.libFilterText = QtGui.QLineEdit()
        self.cellFilterText = QtGui.QLineEdit()
        layout2.addWidget(QtGui.QLabel('Lib'))
        layout2.addWidget(self.libFilterText)
        layout2.addWidget(QtGui.QLabel('Cell'))
        layout2.addWidget(self.cellFilterText)

        layout = QtGui.QVBoxLayout()
        layout.addLayout(layout2)
        layout.addWidget(self.treeView)

        self.connect(self.libFilterText,
                     QtCore.SIGNAL("textChanged(QString)"),
                     self.updateRegExp)
        self.connect(self.cellFilterText,
                     QtCore.SIGNAL("textChanged(QString)"),
                     self.updateRegExp)

        self.setLayout(layout)

    def updateRegExp(self):
        libText = str(self.libFilterText.text())
        cellText = str(self.cellFilterText.text())
        self.proxyModel.setRegExps(
            QtCore.QRegExp(libText, QtCore.Qt.CaseInsensitive,
                           QtCore.QRegExp.Wildcard),
            QtCore.QRegExp(cellText, QtCore.Qt.CaseInsensitive,
                           QtCore.QRegExp.Wildcard))
        self.proxyModel.invalidateFilter()

    def setSourceModel(self, model):
        self.proxyModel.setSourceModel(model)
        self.treeView.setModel(self.proxyModel)


