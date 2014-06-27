/*
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
*/


#pragma comment(linker, "/SUBSYSTEM:windows /ENTRY:mainCRTStartup")

#include <Windows.h>
#include <string>
#include <vector>
#include <iostream>

void main(int argc,char* argv[])
{
	if (argc < 2) return;

	STARTUPINFO startupInfo;
    PROCESS_INFORMATION processInfo;
    ZeroMemory(&startupInfo, sizeof(STARTUPINFO));
    ZeroMemory(&processInfo, sizeof(PROCESS_INFORMATION));
    startupInfo.cb = sizeof(startupInfo); 

	BOOL result = CreateProcess(NULL,
		argv[1],
		NULL,
		NULL,
		false,
		NORMAL_PRIORITY_CLASS,
		NULL,
		NULL,
		&startupInfo,
		&processInfo);


	CloseHandle( processInfo.hProcess );
    CloseHandle( processInfo.hThread );










}
