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
import Eaglepy
import alignment_tool_rsc
from outliner import OutlinerTree

class AlignmentToolDialog(QDialog):
    
    LABEL_WIDTH = 115
    RIGHT_SPACING_WIDTH = 0

    LAYER_ENUMERATION_COMPLETE_EVENT = QEvent.User+1
    
    DIRECTION_UP         = 0
    DIRECTION_DOWN       = 1
    DIRECTION_LEFT       = 2 
    DIRECTION_RIGHT      = 3
    DIRECTION_CENTER_H   = 4
    DIRECTION_CENTER_V   = 5    
    DIRECTION_VERTICAL   = 6
    DIRECTION_HORIZONTAL = 7
    DIRECTION_TOP        = 8
    DIRECTION_BOTTOM     = 9
    DIRECTION_GRID       = 10
    
    DISTRIBUTE_MINMAX    = 1
    DISTRIBUTE_VALUES    = 2
    
    def __init__(self):

        QDialog.__init__(self)
        
        self.setWindowIcon(QIcon(QPixmap(":/eagleimages/eaglepy.png")))
        self.setWindowTitle("Alignment Tool")
        self.setGeometry(0,0,500,300)
        self.setMaximumHeight(300)
        self.centerToWidget()

        self.setLayout(QHBoxLayout())
        
        self.buttonLayout = QHBoxLayout()
        
        def setupButton(button,tooltip,width=50,height=50):
            button.setMaximumWidth(width)
            button.setMinimumWidth(width)
            button.setMaximumHeight(height)
            button.setMinimumHeight(height)
            button.setToolTip(tooltip)
            return button
        
        self.alignmentButtonFrame = QFrame()
        self.alignmentButtonFrame.setMaximumHeight(280)
        self.alignmentButtonFrame.setMaximumWidth(170)
        self.alignmentButtonFrame.setLayout(QGridLayout())
        
        self.nudgeUpButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_move_u.png")),""),"Nudge Up")
        self.nudgeDownButton  = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_move_d.png")),""),"Nudge Down")
        self.nudgeLeftButton  = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_move_l.png")),""),"Nudge Left")
        self.nudgeRightButton = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_move_r.png")),""),"Nudge Right")

        self.alignLeftButton       = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_l.png")),""),"Align Left")
        self.alignRightButton      = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_r.png")),""),"Align Right")
        self.alignCenterVButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_v_c.png")),""),"Align Vertical Center")
        self.alignCenterHButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_h_c.png")),""),"Align Horizontal Center")
        self.alignTopButton        = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_t.png")),""),"Align Top")
        self.alignBottomButton     = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_align_b.png")),"") ,"Align Bottom")
        
        self.distributeHButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_distrib_h.png")),""),"Distrubute Horiztontal")
        self.distributeVButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_distrib_v.png")),""),"Distrubute Vertical")
        self.distributeGButton    = setupButton(QPushButton(QIcon(QPixmap(":/alignmenttool/button_distrib_g.png")),""),"Distrubute Grid")
        
        
        # Nudge Buttons
        self.nudgeSignalMapper = QSignalMapper()
        self.nudgeSignalMapper.setMapping(self.nudgeUpButton,self.DIRECTION_UP)
        self.nudgeSignalMapper.setMapping(self.nudgeDownButton,self.DIRECTION_DOWN)
        self.nudgeSignalMapper.setMapping(self.nudgeLeftButton,self.DIRECTION_LEFT)
        self.nudgeSignalMapper.setMapping(self.nudgeRightButton,self.DIRECTION_RIGHT)
        
        self.nudgeUpButton.clicked.connect(self.nudgeSignalMapper.map)
        self.nudgeDownButton.clicked.connect(self.nudgeSignalMapper.map)
        self.nudgeLeftButton.clicked.connect(self.nudgeSignalMapper.map)
        self.nudgeRightButton.clicked.connect(self.nudgeSignalMapper.map)        
       
        self.nudgeSignalMapper.mapped.connect(self.nudgePressed)
         
        # Align Buttons       
        self.alignSignalMapper = QSignalMapper()
        self.alignSignalMapper.setMapping(self.alignLeftButton,self.DIRECTION_LEFT)
        self.alignSignalMapper.setMapping(self.alignRightButton,self.DIRECTION_RIGHT)        
        self.alignSignalMapper.setMapping(self.alignTopButton,self.DIRECTION_TOP)
        self.alignSignalMapper.setMapping(self.alignBottomButton,self.DIRECTION_BOTTOM)
        self.alignSignalMapper.setMapping(self.alignCenterHButton,self.DIRECTION_CENTER_H)
        self.alignSignalMapper.setMapping(self.alignCenterVButton,self.DIRECTION_CENTER_V)
        
        self.alignLeftButton.clicked.connect(self.alignSignalMapper.map)
        self.alignRightButton.clicked.connect(self.alignSignalMapper.map)
        self.alignCenterHButton.clicked.connect(self.alignSignalMapper.map)
        self.alignCenterVButton.clicked.connect(self.alignSignalMapper.map)           
        self.alignTopButton.clicked.connect(self.alignSignalMapper.map)
        self.alignBottomButton.clicked.connect(self.alignSignalMapper.map)
        
        self.alignSignalMapper.mapped.connect(self.alignPressed)
        
        # Distribute Buttons        

        self.distributeSignalMapper = QSignalMapper()
        self.distributeSignalMapper.setMapping(self.distributeHButton,self.DIRECTION_HORIZONTAL)
        self.distributeSignalMapper.setMapping(self.distributeVButton,self.DIRECTION_VERTICAL)        
        self.distributeSignalMapper.setMapping(self.distributeGButton,self.DIRECTION_GRID) 
        
        self.distributeHButton.clicked.connect(self.distributeSignalMapper.map)
        self.distributeVButton.clicked.connect(self.distributeSignalMapper.map)
        self.distributeGButton.clicked.connect(self.distributeSignalMapper.map)

        self.distributeSignalMapper.mapped.connect(self.distributePressed)


        self.alignmentButtonFrame.layout().addWidget(self.distributeHButton,0,0)
        self.alignmentButtonFrame.layout().addWidget(self.distributeGButton,0,1)
        self.alignmentButtonFrame.layout().addWidget(self.distributeVButton,0,2)
        self.alignmentButtonFrame.layout().addWidget(self.alignLeftButton,1,0)
        self.alignmentButtonFrame.layout().addWidget(self.alignCenterVButton,1,1)
        self.alignmentButtonFrame.layout().addWidget(self.alignRightButton,1,2)
        self.alignmentButtonFrame.layout().addWidget(self.alignTopButton,2,0)
        self.alignmentButtonFrame.layout().addWidget(self.alignCenterHButton,2,1)
        self.alignmentButtonFrame.layout().addWidget(self.alignBottomButton,2,2)
        
        self.alignmentButtonFrame.layout().addWidget(self.nudgeUpButton,3,1)        
        self.alignmentButtonFrame.layout().addWidget(self.nudgeLeftButton,4,0)
        self.alignmentButtonFrame.layout().addWidget(self.nudgeDownButton,4,1)
        self.alignmentButtonFrame.layout().addWidget(self.nudgeRightButton,4,2)
        

      

        self.fileInfoName = QLabel("File Name : ")
        self.fileInfoName.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.fileInfoName.setMaximumWidth(self.LABEL_WIDTH)
        self.fileInfoName.setMinimumWidth(self.LABEL_WIDTH)

        self.activateMarkerLayout = QHBoxLayout()
        self.activateMarkerName = QLabel("Activate Marker : ")
        self.activateMarkerName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.activateMarkerName.setMaximumWidth(self.LABEL_WIDTH)
        self.activateMarkerName.setMinimumWidth(self.LABEL_WIDTH)        
        self.activateMarkerCheckBox = QCheckBox() 
        self.activateMarkerLayout.addWidget(self.activateMarkerName)
        self.activateMarkerLayout.addWidget(self.activateMarkerCheckBox)
        self.activateMarkerCheckBox.toggled.connect(self.markerActivated)
        
        self.currentGridUnitLayout = QHBoxLayout()
        self.currentGridUnitName = QLabel("Current Unit : ")
        self.currentGridUnitName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.currentGridUnitName.setMaximumWidth(self.LABEL_WIDTH)
        self.currentGridUnitName.setMinimumWidth(self.LABEL_WIDTH)        
        self.currentGridUnitCombo = QComboBox()       
        for item in (("mic",Eaglepy.GRID_UNIT_MIC),("mm",Eaglepy.GRID_UNIT_MM),("mil",Eaglepy.GRID_UNIT_MIL),("inch",Eaglepy.GRID_UNIT_INCH)):
            self.currentGridUnitCombo.addItem(item[0],item[1])
        self.currentGridUnitLayout.addWidget(self.currentGridUnitName)
        self.currentGridUnitLayout.addWidget(self.currentGridUnitCombo)

        
        
        self.currentGridValueLayout = QHBoxLayout()
        self.currentGridValueName = QLabel("Current Unit : ")
        self.currentGridValueName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.currentGridValueName.setMaximumWidth(self.LABEL_WIDTH)
        self.currentGridValueName.setMinimumWidth(self.LABEL_WIDTH)        
        self.currentGridValueSpinBox = QDoubleSpinBox()
        self.currentGridValueSpinBox.setDecimals(6)
        self.currentGridValueSpinBox.setMinimum(0.000001)
        self.currentGridValueSpinBox.setMaximum(1000)
        self.currentGridValueSpinBox.setSingleStep(0.000001)
        self.currentGridValueLayout.addWidget(self.currentGridValueName)
        self.currentGridValueLayout.addWidget(self.currentGridValueSpinBox)

        
        self.distributeModeLayout = QHBoxLayout()
        self.distributeModeName = QLabel("Distribute Mode : ")
        self.distributeModeName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.distributeModeName.setMaximumWidth(self.LABEL_WIDTH)
        self.distributeModeName.setMinimumWidth(self.LABEL_WIDTH)        
        self.distributeModeMinMax = QRadioButton("Min/Max")
        self.distributeModeMinMax.setChecked(True)
        self.distributeModeValues = QRadioButton("Values")
        self.distributeModeMinMax.toggled.connect(self.distributeModeChanged)
        
        self.distributeModeLayout.addWidget(self.distributeModeName)
        self.distributeModeLayout.addWidget(self.distributeModeMinMax)
        self.distributeModeLayout.addWidget(self.distributeModeValues)
        
        
        self.distributeValuesHorizontalLayout = QHBoxLayout()
        self.distributeValuesHorizontalName = QLabel("Distribute X Values : ")
        self.distributeValuesHorizontalName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.distributeValuesHorizontalName.setMaximumWidth(self.LABEL_WIDTH)
        self.distributeValuesHorizontalName.setMinimumWidth(self.LABEL_WIDTH) 
        self.distributeValuesHorizontalMinSpinBox = QDoubleSpinBox()
        self.distributeValuesHorizontalMinSpinBox.setDecimals(6)
        self.distributeValuesHorizontalMinSpinBox.setMinimum(-1000)
        self.distributeValuesHorizontalMinSpinBox.setMaximum(1000)
        self.distributeValuesHorizontalMinSpinBox.setSingleStep(0.1)
        self.distributeValuesHorizontalMinSpinBox.setValue(0)
        
        self.distributeValuesHorizontalMaxSpinBox = QDoubleSpinBox()
        self.distributeValuesHorizontalMaxSpinBox.setDecimals(6)
        self.distributeValuesHorizontalMaxSpinBox.setMinimum(-1000)
        self.distributeValuesHorizontalMaxSpinBox.setMaximum(1000)
        self.distributeValuesHorizontalMaxSpinBox.setSingleStep(0.1)
        self.distributeValuesHorizontalMaxSpinBox.setValue(5)
        
        self.distributeValuesHorizontalMinSpinBox.valueChanged.connect(self.distributeValueChanged)
        self.distributeValuesHorizontalMaxSpinBox.valueChanged.connect(self.distributeValueChanged)
        self.distributeValuesHorizontalLayout.addWidget(self.distributeValuesHorizontalName)
        self.distributeValuesHorizontalLayout.addWidget(self.distributeValuesHorizontalMinSpinBox)
        self.distributeValuesHorizontalLayout.addWidget(self.distributeValuesHorizontalMaxSpinBox)
        
        self.distributeValuesVerticalLayout = QHBoxLayout()
        self.distributeValuesVerticalName = QLabel("Distribute Y Values : ")
        self.distributeValuesVerticalName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.distributeValuesVerticalName.setMaximumWidth(self.LABEL_WIDTH)
        self.distributeValuesVerticalName.setMinimumWidth(self.LABEL_WIDTH) 
        self.distributeValuesVerticalMinSpinBox = QDoubleSpinBox()
        self.distributeValuesVerticalMinSpinBox.setDecimals(6)
        self.distributeValuesVerticalMinSpinBox.setMinimum(-1000)
        self.distributeValuesVerticalMinSpinBox.setMaximum(1000)
        self.distributeValuesVerticalMinSpinBox.setSingleStep(0.1)
        self.distributeValuesVerticalMinSpinBox.setValue(0)
        
        self.distributeValuesVerticalMaxSpinBox = QDoubleSpinBox()
        self.distributeValuesVerticalMaxSpinBox.setDecimals(6)
        self.distributeValuesVerticalMaxSpinBox.setMinimum(-1000)
        self.distributeValuesVerticalMaxSpinBox.setMaximum(1000)
        self.distributeValuesVerticalMaxSpinBox.setSingleStep(0.1)
        self.distributeValuesVerticalMaxSpinBox.setValue(5)
        
        self.distributeValuesVerticalMinSpinBox.valueChanged.connect(self.distributeValueChanged)
        self.distributeValuesVerticalMaxSpinBox.valueChanged.connect(self.distributeValueChanged)
        self.distributeValuesVerticalLayout.addWidget(self.distributeValuesVerticalName)
        self.distributeValuesVerticalLayout.addWidget(self.distributeValuesVerticalMinSpinBox)
        self.distributeValuesVerticalLayout.addWidget(self.distributeValuesVerticalMaxSpinBox)
        
        
        self.distributeGridLayout = QHBoxLayout()
        self.distributeGridName = QLabel("Grid Rows/Columns : ")
        self.distributeGridName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.distributeGridName.setMaximumWidth(self.LABEL_WIDTH)
        self.distributeGridName.setMinimumWidth(self.LABEL_WIDTH) 
        self.distributeGridRowsSpinBox = QSpinBox()
        self.distributeGridRowsSpinBox.setMinimum(2)
        self.distributeGridRowsSpinBox.setMaximum(50)
        self.distributeGridColsSpinBox = QSpinBox()
        self.distributeGridColsSpinBox.setMinimum(2)
        self.distributeGridColsSpinBox.setMaximum(50)       
        self.distributeGridLayout.addWidget(self.distributeGridName)
        self.distributeGridLayout.addWidget(self.distributeGridColsSpinBox)
        self.distributeGridLayout.addWidget(self.distributeGridRowsSpinBox)
        
        
        self.currentNudgeValueLayout = QHBoxLayout()
        self.currentNudgeValueName = QLabel("Nudge Value : ")
        self.currentNudgeValueName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.currentNudgeValueName.setMaximumWidth(self.LABEL_WIDTH)
        self.currentNudgeValueName.setMinimumWidth(self.LABEL_WIDTH)        
        self.currentNudgeValueSpinBox = QDoubleSpinBox()
        self.currentNudgeValueSpinBox.setDecimals(6)
        self.currentNudgeValueSpinBox.setMinimum(0.000001)
        self.currentNudgeValueSpinBox.setMaximum(10000)
        self.currentNudgeValueSpinBox.setSingleStep(0.000001)
        self.currentNudgeValueLayout.addWidget(self.currentNudgeValueName)
        self.currentNudgeValueLayout.addWidget(self.currentNudgeValueSpinBox)
        self.currentNudgeValueSpinBox.setValue(0.1)
        
        
        self.valuesLayout = QVBoxLayout()
        self.valuesLayout.addSpacerItem(QSpacerItem(50,10,QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.valuesLayout.addLayout(self.activateMarkerLayout)
        self.valuesLayout.addLayout(self.currentGridUnitLayout)
        self.valuesLayout.addLayout(self.currentGridValueLayout)
        self.valuesLayout.addLayout(self.currentNudgeValueLayout)
        self.valuesLayout.addLayout(self.distributeModeLayout)
        self.valuesLayout.addLayout(self.distributeValuesHorizontalLayout)
        self.valuesLayout.addLayout(self.distributeValuesVerticalLayout)
        self.valuesLayout.addLayout(self.distributeGridLayout)
        
        self.valuesLayout.addSpacerItem(QSpacerItem(1,1,QSizePolicy.Expanding,QSizePolicy.Expanding))
 
        self.outlinerTree = OutlinerTree()
        self.outlinerTree.setMinimumWidth(250)
        self.outlinerTree.setColumnWidth(0,120)
        self.outlinerTree.setVisible(False)
        self.buttonLayout.addWidget(self.alignmentButtonFrame)
        self.buttonLayout.addSpacerItem(QSpacerItem(0,100,QSizePolicy.Expanding,QSizePolicy.Maximum))

        self.extrasButtonLayout = QVBoxLayout()
        self.extraOutlinerButton = setupButton(QPushButton("+"),"Show Outliner",18,18)
        self.extraOutlinerButton.clicked.connect(self.toggleOutliner)
        self.extrasButtonLayout.setAlignment(Qt.AlignHCenter)
        self.extrasButtonLayout.setSpacing(0)
        self.extrasButtonLayout.addSpacerItem(QSpacerItem(0,10,QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.extrasButtonLayout.addWidget(self.extraOutlinerButton)
        self.extrasButtonLayout.addSpacerItem(QSpacerItem(0,500,QSizePolicy.Fixed,QSizePolicy.Expanding))
        
        
        self.outlinerLayout = QVBoxLayout()
        self.outlinerLayout.setSpacing(0)
        self.outlinerLayout.addSpacerItem(QSpacerItem(0,10,QSizePolicy.Fixed,QSizePolicy.Fixed))
        self.outlinerLayout.addWidget(self.outlinerTree)
        
        self.layout().addLayout(self.outlinerLayout)
        self.layout().addLayout(self.extrasButtonLayout)
        self.layout().addLayout(self.buttonLayout)
        self.layout().addLayout(self.valuesLayout)
       
        

        
        self.markerLast = (0,0)
        self.layout().setSpacing(5)
        self.layout().setStretch(0,0)
        self.layout().setStretch(1,0)
        self.layout().setStretch(2,0)
        self.layout().setStretch(3,100)
        print "L"
        self.eaglegrid = Eaglepy.ULContext().grid()
        print "L2"
        currentUnit  = self.eaglegrid.unit(Eaglepy.REFRESH_VALUE)
        currentValue = self.eaglegrid.distance(Eaglepy.REFRESH_VALUE)
        
        self.currentGridUnitCombo.setCurrentIndex(currentUnit)
        self.currentGridValueSpinBox.setValue(currentValue)

        self.updateSelection()

        self.outlinerTree.itemSelectionChanged.connect(self.updateSelection)

        self.currentGridUnitCombo.currentIndexChanged.connect(self.currentGridUnitChanged)
        self.currentGridValueSpinBox.valueChanged.connect(self.currentGridValueChanged)
     
        self.distributeModeChanged()
    
    def toggleOutliner(self):
        self.outlinerTree.initialize()
        self.outlinerTree.setVisible(not self.outlinerTree.isVisible())
        self.extraOutlinerButton.setText("-" if  self.outlinerTree.isVisible() else "+")
        

        
    def updateSelection(self):

        self.selected  = [item for item in Eaglepy.selected() if isinstance(item,(Eaglepy.ULInstance,Eaglepy.ULElement,Eaglepy.ULContact))]
        print "UPDATE,", self.selected
        
    def markerActivated(self,value):
        if self.activateMarkerCheckBox.checkState() == Qt.Unchecked:
            Eaglepy.marker()
        else:
            self.updateMarker(self.markerLast)
    
    def updateMarker(self,value):
        if self.activateMarkerCheckBox.checkState() == Qt.Checked:
            self.markerLast = value
            Eaglepy.marker(self.markerLast)
    
    def distributeModeChanged(self,value=None):
        self.distributeValuesHorizontalMaxSpinBox.setEnabled(not self.distributeModeMinMax.isChecked())
        self.distributeValuesHorizontalMinSpinBox.setEnabled(not self.distributeModeMinMax.isChecked())
        self.distributeValuesVerticalMaxSpinBox.setEnabled(not self.distributeModeMinMax.isChecked())
        self.distributeValuesVerticalMinSpinBox.setEnabled(not self.distributeModeMinMax.isChecked())
        
    def distributeValueChanged(self,value):
        if self.sender() == self.distributeValuesHorizontalMinSpinBox:
            #if self.distributeValuesHorizontalMinSpinBox.value() >= self.distributeValuesHorizontalMaxSpinBox.value():
                #self.distributeValuesHorizontalMinSpinBox.setValue(self.distributeValuesHorizontalMaxSpinBox.value() - self.distributeValuesHorizontalMinSpinBox.singleStep())
            self.updateMarker((self.distributeValuesHorizontalMinSpinBox.value(),self.distributeValuesVerticalMinSpinBox.value() ))
                
        elif self.sender() == self.distributeValuesHorizontalMaxSpinBox:
            #if self.distributeValuesHorizontalMaxSpinBox.value() <= self.distributeValuesHorizontalMinSpinBox.value():
                #self.distributeValuesHorizontalMaxSpinBox.setValue(self.distributeValuesHorizontalMinSpinBox.value() + self.distributeValuesHorizontalMaxSpinBox.singleStep()) 
            self.updateMarker((self.distributeValuesHorizontalMaxSpinBox.value(),self.distributeValuesVerticalMaxSpinBox.value() ))
                
        if self.sender() == self.distributeValuesVerticalMinSpinBox:
            #if self.distributeValuesVerticalMinSpinBox.value() >= self.distributeValuesVerticalMaxSpinBox.value():
                #self.distributeValuesVerticalMinSpinBox.setValue(self.distributeValuesVerticalMaxSpinBox.value() - self.distributeValuesVerticalMinSpinBox.singleStep()) 
            self.updateMarker((self.distributeValuesHorizontalMinSpinBox.value(),self.distributeValuesVerticalMinSpinBox.value()))
                
        elif self.sender() == self.distributeValuesVerticalMaxSpinBox:
            #if self.distributeValuesVerticalMaxSpinBox.value() <= self.distributeValuesVerticalMinSpinBox.value():
                #self.distributeValuesVerticalMaxSpinBox.setValue(self.distributeValuesVerticalMinSpinBox.value() + self.distributeValuesVerticalMaxSpinBox.singleStep()) 
            self.updateMarker((self.distributeValuesHorizontalMaxSpinBox.value(),self.distributeValuesVerticalMaxSpinBox.value()))
     
                
    def currentGridUnitChanged(self,index):
        unitType = self.currentGridUnitCombo.itemData(index).toInt()[0]
        Eaglepy.setGridUnitType(unitType)
        self.currentGridValueSpinBox.blockSignals(True)
        
        distType  = self.eaglegrid.unitdist(Eaglepy.REFRESH_VALUE)
        distValue = self.eaglegrid.distance(Eaglepy.REFRESH_VALUE)
        value = Eaglepy.unitToUnit(distValue,distType,unitType)
        self.currentGridValueSpinBox.setValue(value)
        self.currentGridValueSpinBox.blockSignals(False)
    
    def currentGridValueChanged(self,value):
        Eaglepy.setGridUnitValue(value)

    
    def checkSelected(self):  
        if not len(self.selected):
            messageBox = QMessageBox(
            QMessageBox.Warning,"Nothing Selected",
            "No items selected. Select at least one item to use this tool.",
            QMessageBox.Ok,self)
            messageBox.exec_()
            return False
        return True
        
    def distributePressed(self,direction):
    
        if not self.checkSelected():
            return
    
        if self.distributeModeValues.isChecked()and (self.distributeValuesHorizontalMinSpinBox.value() >= self.distributeValuesHorizontalMaxSpinBox.value() or \
                self.distributeValuesVerticalMinSpinBox.value() >= self.distributeValuesVerticalMaxSpinBox.value()):
            messageBox = QMessageBox(
            QMessageBox.Warning,"Invalid Min/Max values",
            "Minimum values must be less than maximum values for grid distribution",
            QMessageBox.Ok,self)
            messageBox.exec_()
            return

    
        unitType = self.currentGridUnitCombo.itemData(self.currentGridUnitCombo.currentIndex()).toInt()[0]

        distributeValueMode = self.DISTRIBUTE_MINMAX if self.distributeModeMinMax.isChecked() else self.DISTRIBUTE_VALUES
        
        minx=  sys.float_info.max if distributeValueMode == self.DISTRIBUTE_MINMAX else self.distributeValuesHorizontalMinSpinBox.value()
        maxx= -sys.float_info.max if distributeValueMode == self.DISTRIBUTE_MINMAX else self.distributeValuesHorizontalMaxSpinBox.value()
        miny=  sys.float_info.max if distributeValueMode == self.DISTRIBUTE_MINMAX else self.distributeValuesVerticalMinSpinBox.value()
        maxy= -sys.float_info.max if distributeValueMode == self.DISTRIBUTE_MINMAX else self.distributeValuesVerticalMaxSpinBox.value()
        spacingx = 0
        spacingy = 0
        
        itemPositions = []

        for index,selectedItem in enumerate(self.selected):
            itemx = Eaglepy.eagleToConfigured(selectedItem.x(Eaglepy.REFRESH_VALUE),unitType) if direction in [self.DIRECTION_HORIZONTAL,self.DIRECTION_GRID] else 0
            itemy = Eaglepy.eagleToConfigured(selectedItem.y(Eaglepy.REFRESH_VALUE),unitType) if direction in [self.DIRECTION_VERTICAL,  self.DIRECTION_GRID] else 0
            itemPositions.append(((itemx,itemy),index))
            if distributeValueMode == self.DISTRIBUTE_MINMAX:
                minx = itemx if itemx < minx else minx
                maxx = itemx if itemx > maxx else maxx
                miny = itemy if itemy < miny else miny
                maxy = itemy if itemy > maxy else maxy
        

                
        if direction in [self.DIRECTION_HORIZONTAL,self.DIRECTION_VERTICAL]:
            if direction == self.DIRECTION_HORIZONTAL:
                spacingx = abs((float(maxx) - float(minx)) / (len(self.selected)-1)) if self.DIRECTION_HORIZONTAL else 0
                sortedSelected = sorted(self.selected,key=lambda selected:selected.x())
            elif direction == self.DIRECTION_VERTICAL:
                spacingy = abs((float(maxy) - float(miny)) / (len(self.selected)-1)) if self.DIRECTION_VERTICAL   else 0
                sortedSelected = sorted(self.selected,key=lambda selected:selected.y())
                
            script = ""
            currentspacingx = 0
            currentspacingy = 0
            
            for selectedItem in sortedSelected:
                
                itemx = Eaglepy.eagleToConfigured(selectedItem.x(Eaglepy.REFRESH_VALUE),unitType)
                itemy = Eaglepy.eagleToConfigured(selectedItem.y(Eaglepy.REFRESH_VALUE),unitType)
                
                if direction == self.DIRECTION_HORIZONTAL: 
                    script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (minx+currentspacingx,itemy))
                    selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(minx+currentspacingx,unitType)
                    selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemy ,unitType)
                elif direction == self.DIRECTION_VERTICAL:
                    script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (itemx,miny+currentspacingy))
                    selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemx,unitType)
                    selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(miny+currentspacingy ,unitType)
                    
                currentspacingx += spacingx
                currentspacingy += spacingy
                    
                
        elif direction == self.DIRECTION_GRID:
            
            rows = self.distributeGridRowsSpinBox.value()
            columns = self.distributeGridColsSpinBox.value()
            
            
            spacingx = abs((float(maxx) - float(minx)) / (rows-1))
            spacingy = abs((float(maxy) - float(miny)) / (columns-1))
            
            if rows*columns < len(self.selected):
                messageBox = QMessageBox(
                QMessageBox.Warning,"Too many items selected",
                "%d items exceeds the maximum for the current grid size.\nFor %d rows * %d columns the maximum number of selected items is %d" % (len(self.selected),rows,columns,rows*columns),
                QMessageBox.Ok,self)
                
                return messageBox.exec_()
            
            distance = lambda p1,p2: abs(math.sqrt(math.pow(p2[0]-p1[0],2) + math.pow(p2[1]-p1[1],2)))
            script = ""    
            

            complete = False
            for rowIndex in range(rows):
                for colIndex in range(columns):
                    if (rowIndex*columns)+colIndex == len(self.selected):
                        complete = True 
                        break
                
                    newx = minx+rowIndex*spacingx
                    newy = miny+colIndex*spacingy

                    closestItem = min(itemPositions,key=lambda item:distance(item[0],(newx,newy)))
                    itemPositions.remove(closestItem)
                    script += ("MOVE %s" % self.selected[closestItem[1]].name()) + (" (%f %f);" % (newx,newy))
                    self.selected[closestItem[1]].x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(newx, unitType)
                    self.selected[closestItem[1]].y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(newy ,unitType)
                    
                if complete:
                    break

        

        Eaglepy.executescr(script)
            
    def alignPressed(self,direction):
        unitType = self.currentGridUnitCombo.itemData(self.currentGridUnitCombo.currentIndex()).toInt()[0]
        
        minx=sys.float_info.max
        maxx=-sys.float_info.max
        miny=sys.float_info.max
        maxy=-sys.float_info.max

        for selectedItem in self.selected:
            itemx = Eaglepy.eagleToConfigured(selectedItem.x(Eaglepy.REFRESH_VALUE),unitType) if direction in [self.DIRECTION_LEFT,self.DIRECTION_RIGHT,self.DIRECTION_CENTER_V] else 0
            itemy = Eaglepy.eagleToConfigured(selectedItem.y(Eaglepy.REFRESH_VALUE),unitType) if direction in [self.DIRECTION_TOP,self.DIRECTION_BOTTOM,self.DIRECTION_CENTER_H] else 0
            
            minx = itemx if itemx < minx else minx
            maxx = itemx if itemx > maxx else maxx
            miny = itemy if itemy < miny else miny
            maxy = itemy if itemy > maxy else maxy
        
        centerx = minx + ((maxx - minx)/2)
        centery = miny + ((maxy - miny)/2)
        
        script = ""
        for selectedItem in self.selected:
            itemx = Eaglepy.eagleToConfigured(selectedItem.x(Eaglepy.REFRESH_VALUE),unitType)
            itemy = Eaglepy.eagleToConfigured(selectedItem.y(Eaglepy.REFRESH_VALUE),unitType)
            
            if direction == self.DIRECTION_LEFT: 
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (minx,itemy))
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(minx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemy ,unitType)
            elif direction == self.DIRECTION_RIGHT:
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (maxx,itemy))
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(maxx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemy ,unitType)
            elif direction == self.DIRECTION_CENTER_V:
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (centerx,itemy))
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(centerx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemy ,unitType)
            elif direction == self.DIRECTION_TOP:
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (itemx,maxy))  
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(maxy ,unitType)
            elif direction == self.DIRECTION_BOTTOM:
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (itemx,miny))
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(miny ,unitType)
            elif direction == self.DIRECTION_CENTER_H:
                script += ("MOVE %s" % selectedItem.name()) + (" (%f %f);" % (itemx,centery))
                selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemx,unitType)
                selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(centery ,unitType)
                
        Eaglepy.executescr(script)
            
        
    def nudgePressed(self,direction):
        
        unitType = self.currentGridUnitCombo.itemData(self.currentGridUnitCombo.currentIndex()).toInt()[0]
         
        offsetx = 0.0
        offsety = 0.0
        
        nudgeValue = self.currentNudgeValueSpinBox.value()
        
        if direction == self.DIRECTION_UP:
            offsety = nudgeValue
        elif direction == self.DIRECTION_DOWN:
            offsety = -nudgeValue
        elif direction == self.DIRECTION_RIGHT:
            offsetx = nudgeValue
        elif direction == self.DIRECTION_LEFT:
            offsetx = -nudgeValue

        
        script = ""
        

        for selectedItem in self.selected:
            itemx = Eaglepy.eagleToConfigured(selectedItem.x(),unitType) + offsetx
            itemy = Eaglepy.eagleToConfigured(selectedItem.y(),unitType) + offsety
            ## Quick Hack to considerable speed this up on multiple calls.. ideally should be a batching option on the server..
            selectedItem.x.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemx,unitType)
            selectedItem.y.__dict__["cachedValue"] = Eaglepy.configuredToEagle(itemy ,unitType)
            script += "MOVE " + selectedItem.name() + " (%f %f);" % (itemx,itemy)
            
        Eaglepy.executescr(script)
            
    
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

    dialog = AlignmentToolDialog()
    dialog.show()

    application.exec_()
    Eaglepy.shutdown()



