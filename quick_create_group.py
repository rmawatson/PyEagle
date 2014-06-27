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

import Eaglepy
Eaglepy.initialize()
selectedObjects = Eaglepy.selected()
newGroup = Eaglepy.ULGroup()

for objectItem in selectedObjects:
	newGroup.append(objectItem)

Eaglepy.ULContext().groups().append(newGroup)

Eaglepy.status("New Group %s created" % newGroup.name())
Eaglepy.shutdown()
