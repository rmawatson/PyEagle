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
import Eaglepy

class GroupManagerDialog(QDialog):
	
	LABEL_WIDTH = 75
	RIGHT_SPACING_WIDTH = 0

	def __init__(self):
		
		QDialog.__init__(self)
		self.setWindowTitle("Group Mananger")
		self.setWindowIcon(QIcon(QPixmap(":/eagleimages/eaglepy.png")))
		self.setGeometry(0,0,600,500)
		
		
		self.newGroupLabel = QLabel("New Group Name : ")
		self.newGroupEdit  = QLineEdit()
		self.newGroupLayout = QHBoxLayout()
		
		self.newGroupFromSelectedButton = QPushButton ("Create From Selected")
		self.newGroupEmptyButton = QPushButton ("Create Empty Group")
		
		self.newGroupFromSelectedButton.clicked.connect(self.createFromSelected)
		
		self.newGroupLayout.addWidget(self.newGroupLabel)
		self.newGroupLayout.addWidget(self.newGroupEdit)
		self.newGroupLayout.addWidget(self.newGroupFromSelectedButton)
		self.newGroupLayout.addWidget(self.newGroupEmptyButton)
		
		
		
		self.groupListName = QLabel("Group List : ")
		self.groupListName.setAlignment(Qt.AlignLeft)
		self.groupListName.setMaximumWidth(self.LABEL_WIDTH)
		self.groupListName.setMinimumWidth(self.LABEL_WIDTH)
		
		self.groupListTable = QTableWidget()
		self.groupListTable.setColumnCount(2)
		self.groupListTable.verticalHeader().hide()
		self.groupListTable.setHorizontalHeaderLabels(["Group Name","Member Count"])
		self.groupListTable.horizontalHeader().setClickable(False)
		self.groupListTable.setColumnWidth(0,150)
		self.groupListTable.setColumnWidth(1,150)
		self.groupListTable.horizontalHeader().setStretchLastSection(True)
		self.groupListTable.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.groupListLayout =QVBoxLayout()
		self.groupListLayout.addWidget(self.groupListName)
		self.groupListLayout.addWidget(self.groupListTable)
		
			
		self.memberListName = QLabel("Member List : ")
		self.memberListName.setAlignment(Qt.AlignLeft)
		self.memberListName.setMaximumWidth(self.LABEL_WIDTH)
		self.memberListName.setMinimumWidth(self.LABEL_WIDTH)
		
		self.memberListTable = QTableWidget()
		self.memberListTable.setColumnCount(2)
		self.memberListTable.verticalHeader().hide()
		self.memberListTable.setHorizontalHeaderLabels(["Member Name","Member Type"])
		self.memberListTable.horizontalHeader().setClickable(False)
		self.memberListTable.setColumnWidth(0,150)
		self.memberListTable.setColumnWidth(1,150)
		self.memberListTable.horizontalHeader().setStretchLastSection(True)
		self.memberListTable.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.memberListLayout =QVBoxLayout()
		self.memberListLayout.addWidget(self.memberListName)
		self.memberListLayout.addWidget(self.memberListTable)
		
		
		self.tableLayout = QHBoxLayout()
		
		self.centerToWidget()
		self.setLayout(QVBoxLayout())
		
		self.tableLayout.addLayout(self.groupListLayout)
		self.tableLayout.addLayout(self.memberListLayout)
		
		
		
		self.hline = QFrame()
		self.hline.setGeometry(QRect(320, 150, 118, 3));
		self.hline.setFrameShape(QFrame.HLine)
		self.hline.setFrameShadow(QFrame.Sunken)
		
		spacing = 10
		self.layout().addLayout(self.newGroupLayout)
		self.layout().addSpacerItem(QSpacerItem(1,spacing,QSizePolicy.Fixed,QSizePolicy.Fixed))
		self.layout().addWidget(self.hline)
		self.layout().addSpacerItem(QSpacerItem(1,spacing,QSizePolicy.Fixed,QSizePolicy.Fixed))
		self.layout().addLayout(self.tableLayout)
	
	
	def createFromSelected(self):
			
		Eaglepy.
	
	def loadItems(self):
		
		
		
		
		
		
		return
		
	def centerToWidget(self,target=None):

		if not target:
			rect = QApplication.desktop().availableGeometry(target if target != None else self)
		else:
			rect = target.geometry()   
		
		center = rect.center()
		self.move(center.x() - self.width()  * 0.5, center.y() - self.height() * 0.5);
      




Eaglepy.initialize()
application = QApplication([])


dialog = GroupManagerDialog()
dialog.show()
application.exec_()
Eaglepy.shutdown()



