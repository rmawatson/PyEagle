"""
 (C) Copyright 2013 Rob Watson rmawatson [at] hotmail.com  and others.

 All rights reserved. This program and the accompanying materials
 are made available under the terms of the GNU Lesser General Public License
 (LGPL) version 2.1 which accompanies this distribution, and is available at
 http://www.gnu.org/licenses/lgpl-2.1.html

 This library is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 Lesser General Public License for more details.

 Contributors:
     Rob Watson ( rmawatson [at] hotmail )
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import platform,sys,os,re,math
from math import *
import outliner_rsc
import Eaglepy

class OutlinerTree(QTreeWidget):

    newGroup = pyqtSignal()

    itemObjectRole  = Qt.UserRole+1
    itemTypeRole    = Qt.UserRole+2
    
    GROUP_KEY_ID = 71
    
    ICON_ELEMENT  = None
    ICON_SIGNAL   = None
    ICON_GROUP    = None
    
    TYPE_GROUP    = 1 
    TYPE_ITEM     = 2
    
    def __init__(self):
        QTreeWidget.__init__(self)
        
        self.isInitialized = False
        self.currentObjectList = []
        self.setColumnCount(2)
        
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels(["Name", "Type"])

        self.setColumnWidth(0,200)
        
        self.ICON_SIGNAL   = self.ICON_SIGNAL  or QIcon(QPixmap(":/outliner/icon_signal.png"))
        self.ICON_ELEMENT  = self.ICON_ELEMENT or QIcon(QPixmap(":/outliner/icon_element.png"))
        self.ICON_GROUP    = self.ICON_GROUP   or QIcon(QPixmap(":/outliner/icon_group.png"))
        
        self.iconMappings = {Eaglepy.ULElement:self.ICON_ELEMENT,
                             Eaglepy.ULSignal:self.ICON_SIGNAL}
        
        
        self.itemSelectionChanged.connect(self.updateSelection)



    def initialize(self):
        if self.isInitialized:
            return
            
        self.isInitialized = True
        self.groupSet   = Eaglepy.ULContext().groups()
        self.allObjects = Eaglepy.allobjects()
        self.populateGroups()
        self.populateItems()
        self.loadSelected()
        self.lastMouseButtons = Qt.NoButton
    
    def mousePressEvent (self,event):
        if event.button() == Qt.RightButton:
            event.accept()
            return
            
        return QTreeWidget.mousePressEvent(self,event)
    
    def contextMenuEvent(self,event):
       
       
        item = self.itemAt(event.pos())
        if not item: return
        
        if item.data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
            menu = QMenu(self)
            group = item.data(0,OutlinerTree.itemObjectRole).toPyObject()
           
            selectedGroups = self.selectedGroups()
            if len(selectedGroups) == 1:
                renameGroupAction = menu.addAction("Rename Group")
                renameGroupAction.setData(item)
                renameGroupAction.triggered.connect(self.renameGroup)
                
                for itemObject in self.currentObjectList:
                    if itemObject.name() not in (groupObject.name() for groupObject in group):
                        updateGroupAction = menu.addAction("Update Group")
                        updateGroupAction.setData(group)
                        updateGroupAction.triggered.connect(self.updateGroup)
                        break
                            
            
            

            if len(selectedGroups) > 1:
 
                mergeGroupAction = menu.addAction("Merge Groups")
                mergeGroupAction.setData(selectedGroups)
                mergeGroupAction.triggered.connect(self.mergeGroups)
                
            if len(selectedGroups):
                deleteGroupAction = menu.addAction("Delete Group" if len(selectedGroups) == 1 else  "Delete Groups")
                deleteGroupAction.setData(selectedGroups)
                deleteGroupAction.triggered.connect(self.deleteGroup)
      
            menu.popup(self.mapToGlobal(event.pos()))
            
        elif item.data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_ITEM and self.indexOfTopLevelItem(item.parent()) > -1:
        
            menu = QMenu(self)
            itemObjectList = []
            itemObject = item.data(0,OutlinerTree.itemObjectRole).toPyObject()
            group = item.parent().data(0,OutlinerTree.itemObjectRole).toPyObject()
            for childIndex in range(item.parent().childCount()):
                if item.parent().child(childIndex).isSelected():
                    itemObjectList.append( item.parent().child(childIndex).data(0,OutlinerTree.itemObjectRole).toPyObject())
            
            removeThisItemAction = menu.addAction("Remove This Item")
            removeThisItemAction.triggered.connect(self.removeItems)
            removeThisItemAction.setData((group,[itemObject]))
            
            if len(itemObjectList) > 1:
                removeItemAction = menu.addAction("Remove Selected Items")
                removeItemAction.triggered.connect(self.removeItems)
                removeItemAction.setData((group,itemObjectList))
            #elif len(itemObjectList) == 1:
                #renameItemAction = menu.addAction("Rename This Item")
                #renameItemAction.triggered.connect(self.renameItem)
                #renameItemAction.setData(item)
                
                
            menu.popup(self.mapToGlobal(event.pos()))

    def renameItem(self,checked):
        action = self.sender()
        item = action.data().toPyObject()
        
        itemWidget = action.data().toPyObject()
        itemWidget.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable )
        self.previousText = str(itemWidget.text(0))
        self.itemChanged.connect(self.renameItemFinished)
        self.editItem(itemWidget)
        
    def renameItemFinished(self,itemWidget,column):
        self.itemChanged.disconnect(self.renameItemFinished)
        if not re.match("[a-z0-9$_\-\s]+",str(itemWidget.text(0)),re.IGNORECASE) or not re.search("[a-z0-9]",str(itemWidget.text(0)),re.IGNORECASE):
            itemWidget.setText(0,self.previousText)
        else:
            newName = str(itemWidget.text(0))
            while True:
                uniqueName = True
                for existingItem in self.allObjects:
                    if hasattr(existingItem,"name") and existingItem.name() == newName:
                        newName = newName + "1"
                        uniqueName  = False
                if not uniqueName:
                    continue
                break    
                
            itemWidget.setText(0,newName)
            item = itemWidget.data(0,OutlinerTree.itemObjectRole).toPyObject()
            item.rename(newName)
            
            
        itemWidget.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable )
        self.populateItems()
        
    def removeItems(self,checked):
        action = self.sender()
        group,itemList = action.data().toPyObject()
        
        group.enableupdates(False)
        for itemObject in itemList:
            group.remove(itemObject)
        group.enableupdates(True)
        group.update()
        
        self.populateGroups()
        
            
    def deleteGroup(self,checked):
        action = self.sender()
        
        grouplist = action.data().toPyObject()
        parentSet = grouplist[0].parentset()
        parentSet.enableupdates(False)
        for group in grouplist:
            group.parentset().remove(group)
        parentSet.enableupdates(True)
        parentSet.update()
        self.populateGroups()
        
        
    def renameGroup(self,checked):
        action = self.sender()
        itemWidget = action.data().toPyObject()
        itemWidget.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable )
        self.previousText = str(itemWidget.text(0))
        self.itemChanged.connect(self.renameGroupFinished)
        self.editItem(itemWidget)
        
    def renameGroupFinished(self,itemWidget,column):
        self.itemChanged.disconnect(self.renameGroupFinished)
        if not re.match("[a-z0-9_\-\s]+",str(itemWidget.text(0)),re.IGNORECASE) or not re.search("[a-z0-9]",str(itemWidget.text(0)),re.IGNORECASE):
            itemWidget.setText(0,self.previousText)
        else:
            group = itemWidget.data(0,OutlinerTree.itemObjectRole).toPyObject()
            group.rename(itemWidget.text(0))
            
        itemWidget.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable )
        
    def mergeGroups(self,checked):
        action = self.sender()
        itemGroups = action.data().toPyObject()
        
        itemGroups[0].parentset().enableupdates(False)

        
        for releaseGroup in itemGroups[1:]:
            for ritem in releaseGroup:
                if ritem.name() not in (fitem.name() for fitem in itemGroups[0]):
                    itemGroups[0].append(ritem)
            itemGroups[0].parentset().remove(releaseGroup)
            
        itemGroups[0].parentset().enableupdates(True)
        itemGroups[0].parentset().update()
        
        self.populateGroups()
        
        
        
    
    def updateGroup(self,checked):
        action = self.sender()
        group = action.data().toPyObject()
        
        group.enableupdates(False)
        for itemObject in self.currentObjectList:
            if itemObject.name() not in (groupObject.name() for groupObject in group):
               group.append(itemObject)

        group.enableupdates(True)
        group.update()
        self.populateGroups()
        
    def keyPressEvent (self,event):
        if event.key() == self.GROUP_KEY_ID and event.modifiers() == Qt.ControlModifier:
            self.createGroup()
            self.newGroup.emit()
        QTreeWidget.keyPressEvent(self,event)
        
        
    def loadSelected(self):
    

        self.blockSignals(True)  
        
        for selected in Eaglepy.selected():
            for index in range(self.invisibleRootItem().childCount()):
                if self.invisibleRootItem().child(index).data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_ITEM and \
                    str(self.invisibleRootItem().child(index).text(0)) == selected.name():
                        self.invisibleRootItem().child(index).setSelected(True)
                        item = self.invisibleRootItem().child(index).data(0,OutlinerTree.itemObjectRole).toPyObject()
                        self.currentObjectList.append(item)
        self.blockSignals(False)    
    
    
    def selectedGroups(self):
        selectedGroupItems = []
        for selectedItem in self.selectedItems():
            if self.indexOfTopLevelItem(selectedItem) > -1 and selectedItem.data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                selectedGroupItems.append( selectedItem.data(0,OutlinerTree.itemObjectRole).toPyObject() )
  
        return selectedGroupItems
        
    
    def selectMatching(self,item):
        
        matchItems = item
        if not isinstance(item,(list)):
            matchItems = [item]
        
        if not len(matchItems):
            return

        
        
        for index in range(self.invisibleRootItem().childCount()):
            if self.invisibleRootItem().child(index).data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                continue
                
            if self.invisibleRootItem().child(index).text(0) in (item.text(0) for item in matchItems):
                self.invisibleRootItem().child(index).setSelected(True)
        

        
    def updateSelection(self):
        
        matchItems = []
        addGroupNames = []
        self.currentObjectList = []
        self.blockSignals(True)  
        for selectedItem in self.selectedItems():

            if self.indexOfTopLevelItem(selectedItem) == -1 and selectedItem.parent().data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                matchItems.append(selectedItem)
        self.selectMatching(matchItems)        
                
        for selectedItem in self.selectedItems():
            if self.indexOfTopLevelItem(selectedItem) > -1 and selectedItem.data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                matchItems = []
                for index in range(selectedItem.childCount()):
                    selectedItem.child(index).setSelected(True)
                    matchItems.append(selectedItem.child(index))
                self.selectMatching(matchItems)
                
        for selectedItem in self.selectedItems():
            if self.indexOfTopLevelItem(selectedItem) > -1 and selectedItem.data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_ITEM:
                addGroupNames.append(str(selectedItem.text(0)))
                self.currentObjectList.append(selectedItem.data(0,OutlinerTree.itemObjectRole).toPyObject())
                
        for index in range(self.invisibleRootItem().childCount()):
            if self.invisibleRootItem().child(index).data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                groupItem = self.invisibleRootItem().child(index)
                for childIndex in range(groupItem.childCount()):
                    if str(groupItem.child(childIndex).text(0)) in addGroupNames:
                        groupItem.child(childIndex).setSelected(True)
        
        
        
        self.blockSignals(False)
        
        print "ADD",addGroupNames
        Eaglepy.setgroup(addGroupNames)
        Eaglepy.refreshview()
        
    def createGroup(self):

        if len(self.currentObjectList) == 0:
            return
        
        newGroup = Eaglepy.ULGroup()
        
        for objectItem in self.currentObjectList:
            newGroup.append(objectItem)
        
        self.groupSet.append(newGroup) 
        self.populateGroups()
        
        
    
    def createItemWidget(self,item,italic=False):
        typeName = " ".join(re.split("([A-Z][a-z]+)",str(item.__class__.__name__)[2:]))
        newItem = QTreeWidgetItem([item.name(),typeName])
        newItem.setData (0,OutlinerTree.itemObjectRole,item)
        newItem.setData (0,OutlinerTree.itemTypeRole,self.TYPE_ITEM)
        if self.iconMappings.has_key(item.__class__):
            newItem.setIcon(0,self.iconMappings[item.__class__])
        if italic:
            font = QFont()
            font.setItalic(True)
            newItem.setFont(0,font)
            newItem.setFont(1,font)
        return newItem
    
    def populateGroups(self):
    
        groupStatus = {}
        self.blockSignals(True)
        for index in range(self.topLevelItemCount()):
            if self.topLevelItem(0).data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_ITEM:
                break
                
            groupWidgetItem = self.topLevelItem(0)
            groupStatus[str(groupWidgetItem .text(0))] = (groupWidgetItem.isExpanded(),groupWidgetItem.isSelected())
            self.takeTopLevelItem(0)
        
        
        for index,group in enumerate(self.groupSet):
            newGroupWidget= QTreeWidgetItem([group.name(),"Group"])
            newGroupWidget.setIcon(0,self.ICON_GROUP)
            newGroupWidget.setData (0,OutlinerTree.itemTypeRole,self.TYPE_GROUP)
            newGroupWidget.setData (0,OutlinerTree.itemObjectRole,group)
            
            for item in group:
                newGroupWidget.addChild(self.createItemWidget(item))
            
            self.insertTopLevelItem(index,newGroupWidget)
            
            if groupStatus.has_key(group.name()):                
                newGroupWidget.setExpanded(groupStatus[group.name()][0])
                newGroupWidget.setSelected(groupStatus[group.name()][1])
            
            
        self.blockSignals(False)   
        self.emit(SIGNAL("selectionChanged()"))
        
    def populateItems(self):
        self.blockSignals(True)
        itemStatus = {}
        
        offsetIndex = 0
        
        for index in range(self.topLevelItemCount()):
            
            if self.topLevelItem(offsetIndex).data(0,OutlinerTree.itemTypeRole).toPyObject() == self.TYPE_GROUP:
                offsetIndex += 1
                continue
             
            objectWidgetItem = self.topLevelItem(offsetIndex)
            itemStatus[str(objectWidgetItem.text(0))] = objectWidgetItem.isSelected()
             
            self.takeTopLevelItem(offsetIndex);
        
        for item in (item for item in self.allObjects if hasattr(item,"name")):
            print item
            newItem = self.createItemWidget(item)
            self.insertTopLevelItem(self.topLevelItemCount(),newItem)
            if itemStatus.has_key(str(newItem.text(0))):
                newItem.setSelected(itemStatus[str(newItem.text(0))])
            
            
        self.blockSignals(False)
        self.emit(SIGNAL("selectionChanged()"))
                

class OutlinerDialog(QDialog):

    LABEL_WIDTH = 75
    RIGHT_SPACING_WIDTH = 0

    
    def __init__(self):
        QDialog.__init__(self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)

        
        self.setWindowTitle("Outliner")
        self.setWindowIcon(QIcon(QPixmap(":/eagleimages/eaglepy.png")))
        self.setGeometry(0,0,600,500)
        self.setLayout(QHBoxLayout())
        
        self.objectTree = OutlinerTree()
        self.objectTree.initialize()
        self.layout().addWidget(self.objectTree)
     
        #self.newGroupLabel = QLabel("New Group Name : ")
        #self.newGroupEdit  = QLineEdit()
        #self.newGroupLayout = QHBoxLayout()
        
        

        self.centerToWidget()
        

    def centerToWidget(self,target=None):

        if not target:
            rect = QApplication.desktop().availableGeometry(target if target != None else self)
        else:
            rect = target.geometry()

        center = rect.center()
        self.move(center.x() - self.width()  * 0.5, center.y() - self.height() * 0.5);



if __name__ == "__main__":

    Eaglepy.initialize()
    application = QApplication([])


    dialog = OutlinerDialog()
    dialog.show()
    application.exec_()
    Eaglepy.shutdown()



