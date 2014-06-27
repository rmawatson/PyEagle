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

import os,sys,time,json,re,platform
import weakref

from types import ListType

from urlparse import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from threading import Thread,Condition,Timer,Lock
from uuid import uuid4
from types import ListType
from xml.dom.minidom import parseString

if platform.system() == "Windows" and "pythonw.exe" in sys.executable.lower():
    class NullOutput(object):
        def write(self, text): pass
        
    sys.stdout = NullOutput()    
    sys.stderr = NullOutput()     


""" REMOTE MESSAGE TYPES """
POLLING_TYPE_NAME = "polling"
EXECREPLY_TYPE_NAME = "execreply"

""" LOCAL MESSAGE TYPES """
POLLING_TYPE_CODE = 0
EXEC_TYPE_CODE    = 1

""" POLLING MESSAGE RESPONSE TYPES """
POLLING_REPONSE_NOP = 0
POLLING_REPONSE_EXIT = 1

""" EXECUTION ERROR VALUES """

ERROR_VALUES = [
"ERROR_INVALID_CONTEXT",
"ERROR_WIRE_HANDLER",
"ERROR_GRID_HANDLER",
"ERROR_AREA_HANDLER",
"ERROR_ARC_HANDLER",
"ERROR_ATTRIBUTE_HANDLER",
"ERROR_CIRCLE_HANDLER",
"ERROR_CLASS_HANDLER",
"ERROR_DIMENSION_HANDLER",
"ERROR_ELEMENT_HANDLER",
"ERROR_PACKAGE_HANDLER",
"ERROR_TEXT_HANDLER",
"ERROR_CONTACT_HANDLER",
"ERROR_POLYGON_HANDLER",
"ERROR_FRAME_HANDLER",
"ERROR_RECTANGLE_HANDLER",
"ERROR_HOLE_HANDLER",
"ERROR_LAYER_HANDLER",
"ERROR_LIBRARY_HANDLER",
"ERROR_DEVICE_HANDLER",
"ERROR_DEVICESET_HANDLER",
"ERROR_SYMBOL_HANDLER",
"ERROR_GATE_HANDLER",
"ERROR_PIN_HANDLER",
"ERROR_PAD_HANDLER",
"ERROR_PINREF_HANDLER",
"ERROR_SIGNAL_HANDLER",
"ERROR_VIA_HANDLER",
"ERROR_VARIANTDEF_HANDLER",
"ERROR_VARIANT_HANDLER",
"ERROR_PART_HANDLER",
"ERROR_INSTANCE_HANDLER",
"ERROR_JUNCTION_HANDLER",	
"ERROR_SEGMENT_HANDLER",
"ERROR_LABEL_HANDLER",
"ERROR_NET_HANDLER",
"ERROR_BUS_HANDLER",
"ERROR_CONTACTREF_HANDLER",
"ERROR_BOARD_HANDLER",
"ERROR_SCHEMATIC_HANDLER",
"ERROR_SHEET_HANDLER",
"ERROR_MAX_DEPTH",
"ERROR_BASE_HANDLER"]



class EaglepyException(Exception):pass

class EagleRemoteHandler(BaseHTTPRequestHandler):
 
    def __init__(self,request,client_address,server):  
        BaseHTTPRequestHandler.__init__(self,request,client_address,server)

    
    def log_message(self, format, *args):
        return
 
    def do_POST(self):
        print "POST"
        params  = urlparse(self.path)
                 
        requestType = params.path[1:].split("?")[0] if len(params.path) > 0 else None
        requestData = params.path[1:].split("?")[0] if len(params.path) > 1 else None
         
        length = int(self.headers['Content-Length'])
        postData = self.rfile.read(length)

        
        if requestType == POLLING_TYPE_NAME:
            self.pollingHandler(requestData)
        if requestType == EXECREPLY_TYPE_NAME:
            self.execReplyHandler(postData)

    def execReplyHandler(self,postData):
        

        splitReplies = [item for item in postData.split(";") if item != ""]
        
        self.server.commandQueueLock.acquire()
        
        commandConditions = dict(self.server.commandCondition)
        for reply in splitReplies:
            
            splitReplyItem = reply.split("|")
            cmdid = str(splitReplyItem[0])
            
            cmddata = None
            if len(splitReplyItem) > 1:
                cmddata = str(splitReplyItem[1])
                
            commandConditions[cmdid][0].acquire()
            commandConditions[cmdid][1] = cmddata
            commandConditions[cmdid][0].notifyAll()
            commandConditions[cmdid][0].release()
            
            cond = commandConditions[cmdid][0]
            cond.acquire()
            del commandConditions[cmdid]
            cond.release()
            
        self.server.commandQueueLock.release()
        self.postResponse({str(POLLING_TYPE_CODE):str(POLLING_REPONSE_NOP)})
        
    def pollingHandler(self,data):
        time.sleep(0.005)
        self.server.commandQueueLock.acquire()
  
        if self.server.shuttingDown:
            self.postResponse({str(POLLING_TYPE_CODE):str(POLLING_REPONSE_EXIT)})
            self.server.shutdownCondition.acquire()
            self.server.shutdownCondition.notifyAll()
            self.server.shutdownCondition.release()

        if len(self.server.commandQueue):
            commandItem = self.server.commandQueue.pop()
            commandData = str(commandItem[0]) + "|" + str(commandItem[1]) + "|"  + "?".join(str(item) for item in commandItem[2])
            self.postResponse({str(EXEC_TYPE_CODE):commandData})
        else:
            self.postResponse({str(POLLING_TYPE_CODE):str(POLLING_REPONSE_NOP)})

    
        
        self.server.commandQueueLock.release()
 
    def postResponse(self,keyvalues):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(keyvalues))

        
        
 
class EagleRemoteServer(HTTPServer):
     
    TIMEOUT = 3.0
    def __init__(self):
        
        self.connectData = None
        self.queuedRequests       = []
        self.sessionID            = None
        self.serverThread         = None
    
        self.commandQueueLock = Lock() 
        self.commandQueue = []
        
        self.shuttingDown = False 
        self.shutdownCondition = Condition()
        self.commandCondition = {}
        
        HTTPServer.__init__(self,("127.0.0.1",7697),EagleRemoteHandler )

        
    def startup(self):
    

        self.serverThread= Thread(target=self.serve_forever)
        self.serverThread.start()
 
    def shutdown(self):
        self.shuttingDown = True
        
        self.shutdownCondition.acquire()
        self.shutdownCondition.wait()
        self.shutdownCondition.release()
        
        HTTPServer.shutdown(self)
        self.serverThread.join()
        
    def executeCommand(self,cmdtype,args=[]):
        
        cmdid = str(uuid4().hex)
        
        self.commandQueueLock.acquire()
        self.commandCondition[cmdid] = [Condition(),None]
        self.commandQueue.append([cmdid,cmdtype,args])
        self.commandCondition[cmdid][0].acquire()
        self.commandQueueLock.release()
        
        self.commandCondition[cmdid][0].wait()

        condition = self.commandCondition[cmdid][0]
        result    = self.commandCondition[cmdid][1]
        
        condition.release()
        return result;
    
global EALGE_SERVER_INSTANCE
EALGE_SERVER_INSTANCE = None

def initialize():

    global EALGE_SERVER_INSTANCE 
    EALGE_SERVER_INSTANCE = EagleRemoteServer()
    EALGE_SERVER_INSTANCE.startup()

def shutdown():
    instance().shutdown()

def instance():
    global EALGE_SERVER_INSTANCE 
    return EALGE_SERVER_INSTANCE

    
""" EAGLE OBJECTS """
from types import *
import weakref


def splitEscapedString(unescaped,splitchar):
    skipNext = False
    currentString = ""
    result = []
    for index,char in enumerate(unescaped):
        if skipNext:
            skipNext = False
            continue
        
        if char == "\\":
            if index+1 < len(unescaped) and unescaped[index+1] == splitchar:
                currentString += splitchar
                skipNext = True
                continue
            else:
                currentString += "\\"
                continue


        if char == splitchar:
            result.append(currentString)
            currentString = ""
            continue
        currentString += char
    result.append(currentString)
    return result
    


class ULBaseAttribute(object):

    def __init__(self,owner,ul_name,datatype):
        self.parent      = owner
        self.ul_name       = ul_name
        self.datatype = datatype   

    def cleanString(self,string):
        
        return string.replace("uF","")
    

    
class ULMethodAttribute(ULBaseAttribute):

    def __init__(self,owner,ul_name,datatype):
        ULBaseAttribute.__init__(self,owner,ul_name,datatype)
 

    def __call__(self,cacheAhead=True):
        result = []
        path = self.parent.path() + "@" + self.ul_name
        resultString = instance().executeCommand(COMMAND_getattribute,[path,int(cacheAhead)])
        
        if not resultString:
            return result
        
        handleReplyError(resultString)
            
        if cacheAhead:
          
            splitResult = splitEscapedString(resultString[1:],":")
            for index,cachedItem in enumerate(splitResult):
                result.append(self.datatype(self).setIndex(index))                
                cachedItem = cachedItem[:-1]
                splitCached = splitEscapedString(cachedItem,"?")
                for attrIndex,value in enumerate(splitCached):
        
                    try:
                        result[-1].simplePropertyList[attrIndex].cachedValue = result[-1].simplePropertyList[attrIndex].datatype(self.cleanString(value))
                    except:
                        #print "ERROR: Unable to convert value to native type with value='%s' and type=%s" % (value,result[-1].simplePropertyList[attrIndex].datatype.__name__)
                        result[-1].simplePropertyList[attrIndex].cachedValue  = result[-1].simplePropertyList[attrIndex].datatype()
                    
                    
            
            return result 
        else:  
            return [self.datatype(self).setIndex(index) for index in range(int(resultString))]
               
        
class ULPropertyAttribute(ULBaseAttribute):

    def __init__(self,owner,ul_name,datatype):
        ULBaseAttribute.__init__(self,owner,ul_name,datatype)
        self.cachedValue = None
        
    def __call__(self,cached=True):
        return self.get(cached)
        
    def get(self,cached=True):
        if self.parent and self not in self.parent.simplePropertyList:
            return self
        if not cached or not self.cachedValue:
            path = self.path()
            self.cachedValue =  self.datatype(instance().executeCommand(COMMAND_getattribute,[path]))

        return self.cachedValue 

    def set(self,value):
        pass
        #path = self.path()
        #return self.datatype(instance().executeCommand(COMMAND_setattribute,[path + "?" + str(value)]))
       
    def __getattr__(self,attr):
        if attr == "value":
            if issubclass(self.__dict__["datatype"],ULObject):
                return self.__dict__["datatype"](self)
                
            else:
                return self.__dict__["datatype"]()
        elif attr == "__dict__":
            return self.__dict__
        elif attr == "path":
            if not issubclass(self.__dict__["datatype"],ULObject):

                def simplePropertyPath():
                    parent = self.__dict__["parent"];
                    pathList = parent.path()
                    pathList += "@" + self.__dict__["ul_name"] + "@" + str(self.__dict__["datatype"].__name__)
                    return pathList
                return simplePropertyPath
            return getattr(self.value,attr)
        elif attr == "index":
            return getattr(self.value,attr)


        return getattr(self.value,attr)
    

class ULObject(object):

    def __init__(self,parent=None):
        self.ul_name   = str(self.__class__.__name__)
        self.parent = parent
        self.simplePropertyList = []
        self.index  = -1
        self.args   = None
    def createAttribute(self,ul_name,datatype,writeable=False,readable=True,args=None):    
        self.args = args
        if isinstance(datatype,ListType):            
            self.__dict__[ul_name] = ULMethodAttribute(self,ul_name,datatype[0])
        else:
            self.__dict__[ul_name] = ULPropertyAttribute(self,ul_name,datatype)
            if issubclass(datatype,(str,int,float)) and not self.args:
                self.simplePropertyList.append(self.__dict__[ul_name])
        
       
        if ul_name == "name" and datatype == str:
            def rename_func(newname):
                
                globals()["rename"](self.name(),newname)
            
            self.rename = rename_func

        elif ul_name == "x":
            def move_func(unitx,unity,currentUnits=None):

                eaglex = configuredToEagle(unitx,currentUnits)
                eagley = configuredToEagle(unity,currentUnits)
                self.x.__dict__["cachedValue"] = eaglex 
                self.y.__dict__["cachedValue"] = eagley
                globals()["move"](self.name(),unitx,unity)
                
            self.move = move_func
                
    def setIndex(self,index):
        self.__dict__["index"] = index
        return self
    
    def path(self):

        pathList = []
        parent = self
        while parent:
            
            if hasattr(parent,"index") and parent.index >= 0:
                pathList.append(str(parent.index))
                pathList.append("^")
            pathList.append(parent.ul_name)
            pathList.append("@")
            parent = parent.parent
        pathList.reverse()
        return "".join(pathList)
        

class ULClass(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("clearance",int,args=[(None),(int)])
        self.createAttribute("drill",int)
        self.createAttribute("name",str)
        self.createAttribute("number",int)
        self.createAttribute("width",int)
        
class ULGate(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("addlevel",int)
        self.createAttribute("name",str)
        self.createAttribute("swaplevel",int)
        self.createAttribute("symbol",ULSymbol)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        
class ULPinRef(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("contact",ULPart)
        self.createAttribute("direction",ULPin)

class ULPin(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("direction",int)
        self.createAttribute("function",int)
        self.createAttribute("length",int)
        self.createAttribute("name",str)
        self.createAttribute("net",str)
        self.createAttribute("route",int)
        self.createAttribute("swaplevel",int)
        self.createAttribute("visible",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("contacts",[ULContact])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])


        
class ULNet(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("class",ULClass)
        self.createAttribute("column",str)
        self.createAttribute("name",str)
        self.createAttribute("row",str)
        self.createAttribute("pinrefs",[ULPinRef])
        self.createAttribute("segments",[ULSegment])
        
class ULLabel(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("layer",int)
        self.createAttribute("mirror",int)
        self.createAttribute("spin",int)
        self.createAttribute("text",ULText)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("xref",int)
        self.createAttribute("wires",[ULWire])
        
class ULSegment(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("junctions",[ULJunction])
        self.createAttribute("labels",[ULLabel])
        self.createAttribute("pinrefs",[ULPinRef])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])
        
class ULPart(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("attribute",str,args=[(int)])
        self.createAttribute("device",ULDevice)
        self.createAttribute("deviceset",[ULDeviceSet])
        self.createAttribute("name",str)
        self.createAttribute("populate",int)
        self.createAttribute("value",str)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("variants",[ULVariant])
        self.createAttribute("instances",[ULInstance])
        
class ULSignal(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("airwireshidden",int)
        self.createAttribute("class",ULClass)
        self.createAttribute("name",str)
        self.createAttribute("contactrefs",[ULContactRef])
        self.createAttribute("polygons",[ULPolygon])
        self.createAttribute("vias",[ULVia])
        self.createAttribute("wires",[ULWire])

class ULSymbol(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("area",[ULArea])
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("library",str)
        self.createAttribute("name",str)
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("dimensions",[ULDimension])
        self.createAttribute("frames",[ULFrame])
        self.createAttribute("rectangles",[ULRectangle])
        self.createAttribute("pins",[ULPin])
        self.createAttribute("polygons",[ULPolygon])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])
        
class ULDeviceSet(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("activedevice",ULDevice)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("library",str)
        self.createAttribute("name",str)
        self.createAttribute("prefix",str)
        self.createAttribute("value",str)
        self.createAttribute("devices",[ULDevice])
        self.createAttribute("gates",[ULGate])
        
class ULDevice(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("activetechnology",str)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("library",str)
        self.createAttribute("name",str)
        self.createAttribute("package",ULPackage)
        self.createAttribute("prefix",str)
        self.createAttribute("technologies",str)
        self.createAttribute("value",str)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("gates",[ULGate])

        
class ULLibrary(ULObject):
    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("description",str)
        self.createAttribute("grid",ULGrid)
        self.createAttribute("headline",str)
        self.createAttribute("name",str)
        self.createAttribute("devices",[ULDevice])
        self.createAttribute("devicesets",[ULDeviceSet])
        self.createAttribute("layers",[ULLayer])
        self.createAttribute("packages",[ULPackage])
        self.createAttribute("symbols",[ULSymbol])
 
class ULPackage(ULObject):
    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("library",str)
        self.createAttribute("name",str)
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("contacts",[ULContact])
        self.createAttribute("dimensions",[ULDimension])
        self.createAttribute("frames",[ULFrame])
        self.createAttribute("holes",[ULHole])
        self.createAttribute("rectangles",[ULRectangle])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])
        
class ULContactRef(ULObject):
    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        
        self.createAttribute("contact",ULContact)
        self.createAttribute("element",ULElement)
        self.createAttribute("route",int)
        self.createAttribute("routetag",str)
        
        
class ULVia(ULObject):
    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        
        self.createAttribute("drill",int)
        self.createAttribute("drillsymbol",int)
        self.createAttribute("end",int)
        self.createAttribute("flags",int)
        self.createAttribute("shape",int,args=[(int)])
        self.createAttribute("start",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        
class ULBus(ULObject):
    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("name",str)
        self.createAttribute("segments",[ULSegment])

class ULJunction(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("diameter",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)

class ULVariantDef(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("name",str)
        
class ULVariant(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("populate",int)
        self.createAttribute("value",str)
        self.createAttribute("technology",str)
        self.createAttribute("variantdef",str)
        
class ULRectangle(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("layer",int)
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)
        
class ULHole(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("diameter",int,args=[(int)])
        self.createAttribute("drill",int)
        self.createAttribute("drillsymbol",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)

class ULFrame(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("columns",int)
        self.createAttribute("rows",int)
        self.createAttribute("border",int)
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)
        self.createAttribute("texts",[ULText])
        self.createAttribute("fillings",[ULWire])
        
class ULPolygon(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("isolate",int)
        self.createAttribute("layer",int)
        self.createAttribute("orphans",int)
        self.createAttribute("pour",int)
        self.createAttribute("rank",int)
        self.createAttribute("spacing",int)
        self.createAttribute("thermals",int)
        self.createAttribute("width",int)
        self.createAttribute("contours",[ULWire])
        self.createAttribute("fillings",[ULWire])
        self.createAttribute("wires",[ULWire])
        
        
class ULContact(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)   
        self.createAttribute("name",str)
        self.createAttribute("pad",ULPad)
        self.createAttribute("signal",str)
        self.createAttribute("smd",ULSmd)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("polygons",[ULPolygon])
        self.createAttribute("wires",[ULWire])

class ULSmd(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("dx",float,args=[(int)])
        self.createAttribute("dy",float,args=[(int)])
        self.createAttribute("flags",int)
        self.createAttribute("layer",int)
        self.createAttribute("name",str)
        self.createAttribute("roundness",str)
        self.createAttribute("signal",str)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        
class ULPad(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)     
        self.createAttribute("angle",float)
        self.createAttribute("diameter",int,args=[(int)])
        self.createAttribute("drill",int)
        self.createAttribute("drillsymbol",int)
        self.createAttribute("elongation",int)
        self.createAttribute("flags",int)
        self.createAttribute("name",str)
        self.createAttribute("shape",int,args=[(int)])
        self.createAttribute("signal",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        
class ULArc(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle1",float)
        self.createAttribute("angle2",float)
        self.createAttribute("cap",int)
        self.createAttribute("layer",int)
        self.createAttribute("radius",int)
        self.createAttribute("width",int)
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("xc",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)
        self.createAttribute("yc",int)
        
class ULWire(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)        
        self.createAttribute("arc",ULArc)
        self.createAttribute("cap",int)
        self.createAttribute("curve",float)
        self.createAttribute("layer",int)
        self.createAttribute("style",int)
        self.createAttribute("width",int)
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)
        self.createAttribute("pieces",[ULWire])
        
class ULText(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("align",int)
        self.createAttribute("angle",float)
        self.createAttribute("font",int)
        self.createAttribute("layer",int)
        self.createAttribute("mirror",int)
        self.createAttribute("ratio",int)
        self.createAttribute("size",int)
        self.createAttribute("spin",int)
        self.createAttribute("value",str)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("wires",[ULWire])


        
class ULPackage(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("library",str)
        self.createAttribute("name",str)
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("contacts",[ULContact])
        self.createAttribute("dimensions",[ULDimension])
        self.createAttribute("frames",[ULFrame])
        self.createAttribute("holes",[ULHole])
        self.createAttribute("polygons",[ULPolygon])
        self.createAttribute("rectangles",[ULRectangle])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])
    
    def grid(self):
        return ULLibrary().grid
    
    def groups(self):
        if ULContext() != ULPackage:
            return []
            
        return ULGroupSet(ULPackage)
        

class ULElement(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("attribute",str,args=[(str)])
        self.createAttribute("column",str)
        self.createAttribute("locked",int)
        self.createAttribute("mirror",int)
        self.createAttribute("name",str)
        self.createAttribute("package",ULPackage)
        self.createAttribute("populate",int)
        self.createAttribute("row",str)
        self.createAttribute("smashed",int)
        self.createAttribute("spin",int)
        self.createAttribute("value",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("texts",[ULText])
        self.createAttribute("variants",[ULVariant])


        
class ULDimension(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)        
        self.createAttribute("dtype",int)
        self.createAttribute("layer",int)
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("x3",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)
        self.createAttribute("y3",int)        
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWires])

class ULLayer(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("color",int)
        self.createAttribute("fill",int)
        self.createAttribute("name",str)
        self.createAttribute("number",int)
        self.createAttribute("used",int)
        self.createAttribute("visible",int)
        
class ULCircle(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("layer",int)
        self.createAttribute("radius",int)
        self.createAttribute("width",int)
        self.createAttribute("x",int)
        self.createAttribute("y",int)   

class ULAttribute(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("constant",int)
        self.createAttribute("defaultvalue",str)
        self.createAttribute("display",int)
        self.createAttribute("name",str)
        self.createAttribute("text",ULText)
        self.createAttribute("value",str)

        
class ULArea(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)        
        self.createAttribute("x1",int)
        self.createAttribute("x2",int)
        self.createAttribute("y1",int)
        self.createAttribute("y2",int)

        
     
class ULGrid(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("distance",float)
        self.createAttribute("dots",int)
        self.createAttribute("multiple",int)
        self.createAttribute("on",int)
        self.createAttribute("unit",int)
        self.createAttribute("unitdist",int)

class ULInstance(ULObject):    
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("angle",float)
        self.createAttribute("column",str)
        self.createAttribute("gate",ULGate)
        self.createAttribute("mirror",int)
        self.createAttribute("name",str)
        #self.createAttribute("part",ULPart)
        self.createAttribute("row",str)
        self.createAttribute("sheet",int)
        self.createAttribute("smashed",int)
        self.createAttribute("value",str)
        self.createAttribute("x",int)
        self.createAttribute("y",int)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("texts",[ULText])
        self.createAttribute("xrefs",[ULGate])
        
class ULBoard(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("grid",ULGrid)
        self.createAttribute("headline",str)
        self.createAttribute("name",str)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("classes",[ULClass])
        self.createAttribute("dimensions",[ULDimension])
        self.createAttribute("elements",[ULElement])
        self.createAttribute("frames",[ULFrame])
        self.createAttribute("holes",[ULHole])
        self.createAttribute("layers",[ULLayer])
        self.createAttribute("libraries",[ULLibrary])
        self.createAttribute("polygons",[ULPolygon])
        self.createAttribute("rectangles",[ULRectangle])
        self.createAttribute("signals",[ULSignal])          
        self.createAttribute("texts",[ULText])
        self.createAttribute("variantdefs",[ULVariantDef])
        self.createAttribute("wires",[ULWire])
      
    def groups(self):
        return ULGroupSet(ULBoard)
      
class ULSchematic(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("alwaysvectorfont",int)
        self.createAttribute("description",str)
        self.createAttribute("grid",ULGrid)
        self.createAttribute("headline",str)
        self.createAttribute("name",str)
        self.createAttribute("verticaltext",int)
        self.createAttribute("xreflabel",str)
        self.createAttribute("attributes",[ULAttribute])
        self.createAttribute("classes",[ULClass])
        self.createAttribute("layers",[ULLayer])
        self.createAttribute("libraries",[ULLibrary])
        self.createAttribute("nets",[ULNet])
        self.createAttribute("parts",[ULPart])          
        self.createAttribute("sheets",[ULSheet])
        self.createAttribute("instances",[ULInstance])
        self.createAttribute("variantdefs",[ULVariantDef])
        
    def groups(self):
        return ULGroupSet(ULSchematic)
        
class ULSheet(ULObject):
    def __init__(self,parent=None):
        ULObject.__init__(self,parent)
        self.createAttribute("area",ULArea)
        self.createAttribute("description",str)
        self.createAttribute("headline",str)
        self.createAttribute("number",int)
        self.createAttribute("busses",[ULBus])
        self.createAttribute("circles",[ULCircle])
        self.createAttribute("dimensions",[ULDimension])
        self.createAttribute("frames",[ULFrame])
        self.createAttribute("nets",[ULNet])
        self.createAttribute("polygons",[ULPolygon])          
        self.createAttribute("rectangles",[ULRectangle])
        self.createAttribute("texts",[ULText])
        self.createAttribute("wires",[ULWire])
        self.createAttribute("instances",[ULInstance])
    def groups(self):
        return ULGroupSet(ULSheet)
        
class ULGroupSet(list):

    GROUP_FILE_LOCK = Lock()
    def __init__(self,contextObject):
        list.__init__(self)
        self.contextObject = contextObject
        self.groupsFilePath = None
        self._enabledupdates = True
        
        if not self.contextObject in [ULBoard,ULSchematic]:
            raise EaglepyException("Invalid context object")
       
        matches = re.match("(.+)\.[\w\d]+",self.contextObject().name())
        if not matches or len(matches.groups()) < 1:
            return
         
        self.groupsFilePath = matches.groups()[0] + ".epy"
        
        self._loadfromxml()
        
    def enableupdates(self,value):
        self._enabledupdates = value
        
    def append(self,group):

        if not isinstance(group,ULGroup):
            raise EaglepyException("Only ULGroup objects can be appended")
        
        group._parentset = self
        
        list.append(self,group) # Circular Reference Here.. weakref.proxy(group))
 
        self._updatexml()

    def remove(self,group):
    
        if not isinstance(group,ULGroup):
            raise EaglepyException("Only ULGroup objects can be removed")
        
        list.remove(self,group) 
        group._parentset = None
        self._updatexml()
    
    def _loadfromxml(self):
    
        self.GROUP_FILE_LOCK.acquire()
        groupsData = "<?xml version=\"1.0\" ?><Eaglepy></Eaglepy>"
        if self.groupsFilePath and os.path.exists(self.groupsFilePath):
            groupsFile = file(self.groupsFilePath,"r")
            groupsData = groupsFile.read()
            groupsFile.close()
        self.GROUP_FILE_LOCK.release()
        eaglepyDom = parseString(groupsData)
        
        def getSingleElement(parent,name):
            elements = parent.getElementsByTagName(name)
            if not len(elements):
                return None
            return elements[0]
            
        eaglePyElement   = getSingleElement(eaglepyDom,"Eaglepy")
        boardElement     = getSingleElement(eaglePyElement,"BoardContext")
        schematicElement = getSingleElement(eaglePyElement,"SchematicContext")
        packageElement   = getSingleElement(eaglePyElement,"PackageContext")
        
        if self.contextObject == ULBoard:
            contextElement   = boardElement
        elif self.contextObject == ULSchematic:
            contextElement   = scehematicElement
        elif self.cojntextObject == ULPackage:
            contextElement   = packageElement
        
        if not contextElement:   return

        contextGroupList = getSingleElement(contextElement,"GroupList")
        if not contextGroupList: return
        
        allObjectsList = allobjects()
        
        for groupItem in contextGroupList.childNodes:
            groupName = groupItem.getAttribute("name")
            loadedGroup = ULGroup()
            loadedGroup._name = groupName
            for groupMember in groupItem.childNodes:
                
                elementNameString  = groupMember.getAttribute("name")
                elementClassString = groupMember.getAttribute("class")
                elementPath        = groupMember.getAttribute("path")
                
                foundElement = False
                for element in allObjectsList:
                    if hasattr(element,"name") and element.name() == elementNameString:
                        foundElement = True
                        break
                
                if foundElement:
                    loadedGroup.append(element)
            if len(loadedGroup):
                
                loadedGroup._parentset = self
                list.append(self,loadedGroup)   
    
    def update(self):
        if self._enabledupdates:
            
            self._updatexml()
            
    def _updatexml(self):
        
        if not self._enabledupdates:
            return
        
        self.GROUP_FILE_LOCK.acquire()
        groupsData = "<?xml version=\"1.0\" ?><Eaglepy></Eaglepy>"
        if self.groupsFilePath and os.path.exists(self.groupsFilePath):
            groupsFile = file(self.groupsFilePath,"r")
            groupsData = groupsFile.read()
            groupsFile.close()
        self.GROUP_FILE_LOCK.release()
        
        
        eaglepyDom = parseString(groupsData)
        def getOrCreateElement(parent,name):
            elements = parent.getElementsByTagName(name)
            if not len(elements):
                element = eaglepyDom.createElement(name)
                parent.appendChild(element)
                return element
            return elements[0]
        
        def createElement(parent,name):
            element = eaglepyDom.createElement(name)
            parent.appendChild(element)
            return element
        
        eaglePyElement   = getOrCreateElement(eaglepyDom,"Eaglepy")
        boardElement     = getOrCreateElement(eaglePyElement,"BoardContext")
        schematicElement = getOrCreateElement(eaglePyElement,"SchematicContext")
        packageElement   = getOrCreateElement(eaglePyElement,"PackageContext")
        
        if self.contextObject == ULBoard:
            contextElement   = boardElement
        elif self.contextObject == ULSchematic:
            contextElement   = scehematicElement
        elif self.cojntextObject == ULPackage:
            contextElement   = packageElement
            


        contextGroupList = getOrCreateElement(contextElement,"GroupList")
        
        for child in list(contextGroupList.childNodes):
            contextGroupList.removeChild(child)
        
        currentGroupCount = len(self)

        for group in self:
            groupName = group.name()
            if not groupName:
                index = 0
                while True:
                    newGroupName = "Group" + str(currentGroupCount+index)
                    if not len([item for item in self if item.name() == newGroupName]):
                        groupName = newGroupName
                        break
                    index +=1
                            
                group._name = groupName
            
            newGroup = createElement(contextGroupList,"Group")
            newGroup.setAttribute("name",group.name())
       
            for ulobject in group:

                newobject = createElement(newGroup,"object")
                newobject.setAttribute("name",ulobject.name())
                newobject.setAttribute("class",ulobject.__class__.__name__)
                newobject.setAttribute("path",ulobject.path())    
        
        self.GROUP_FILE_LOCK.acquire()
        groupsData = eaglepyDom.toxml()
        groupsFile = file(self.groupsFilePath,"w")
        groupsFile.write(groupsData)
        groupsFile.close()
        self.GROUP_FILE_LOCK.release()
        
         
        
class ULGroup(list):
    def __init__(self,name=None):
        self._name = name
        self._parentset = None
        self._enabledupdates = True
        list.__init__(self)
    
    
    def enableupdates(self,value):
        self._enabledupdates = value
    
    def update(self):
        if self._enabledupdates:
            self._parentset._updatexml()
        
    def name(self):
        return self._name
    
    def rename(self,newname):
        self._name = newname
        if self._enabledupdates and self._parentset:
            self._parentset._updatexml()
    
    def remove(self,item):

        if not isinstance(item,ULObject):
            raise EaglepyException("Only ULObject objects can be removed")
            
        list.remove(self,item)
               
        if self._enabledupdates and self._parentset:
            self._parentset._updatexml()
            
    def parentset(self):
        return self._parentset
            
    def append(self,item):

        if not isinstance(item,ULObject):
            raise EaglepyException("Only ULObject objects can be appended") 
          
        list.append(self,item)
          
        if self._enabledupdates and self._parentset:
            self._parentset._updatexml()
            
        
        
        
""" CONTEXT """

CONTEXT_BOARD = 0
CONTEXT_SCHEMATIC = 1
CONTEXT_SHEET = 2
CONTEXT_PACKAGE = 3
CONTEXT_LIBRARY = 4

""" EAGLE COMMANDS """

COMMAND_dlgMessageBox  = 100
COMMAND_ingroup        = 101
COMMAND_clrgroupall    = 102
COMMAND_allobjects     = 103
COMMAND_setgroup       = 104
COMMAND_executescr     = 105
COMMAND_getcontext     = 106
COMMAND_getattribute   = 107
COMMAND_setattribute   = 108
COMMAND_palette        = 109
COMMAND_paletteall     = 110
COMMAND_getselected    = 111
COMMAND_status         = 112

PALETTE_DEFAULT = -1
PALETTE_BLACK   = 0
PALETTE_WHITE   = 1
PALETTE_COLORED = 2
PALETTE_TYPES   = 3
PALETTE_ENTRIES = 64

GRID_UNIT_MIC  = 0
GRID_UNIT_MM   = 1
GRID_UNIT_MIL  = 2
GRID_UNIT_INCH = 3

GRID_VALUE_LAST    = -1
GRID_VALUE_FINEST  = -2
GRID_VALUE_DEFAULT = -3

REFRESH_VALUE=False
CACHED_VALUE=True

def handleReplyError(resultString):
    errors = re.search("ERROR:(\d+)",resultString)
    if errors:
        value = int(errors.group(1))
        raise EaglepyException(ERROR_VALUES[value-1] + " id:"+str(value))
    
    return resultString

def marker(value=None,relative=False):
    if value and len(value) != 2:
        raise EaglepyException("marker value must be a tuple of numeric values")
    if not value:
        executescr("Mark;")
    else:
        relativeValue = "R" if relative else ""
        executescr("Mark (%s%f %s%f);" % (relativeValue,value[0],relativeValue,value[1]))
    
def dlgMessageBox(message):
    return handleReplyError(instance().executeCommand(COMMAND_dlgMessageBox,[message]))

    
def executescr(script):
    result = handleReplyError(instance().executeCommand(COMMAND_executescr,[script]))


def _objectsFromIndicies(result):
    splitResult = result.split(":")

    context = int(splitResult[0])
    
    resultList = []

    netIndicies         = []
    elementIndicies     = []
    instanceIndicies    = []
    circleIndicies      = []
    framesIndicies      = []
    polygonsIndicies    = []
    rectanglesIndicies  = []
    textsIndicies       = []
    wiresIndicies       = []
    holesIndicies       = []
    signalsIndicies     = []
    contactIndicies     = []


    netList             = []
    elementList         = []
    instanceList        = []
    circleList          = []
    framesList          = []
    polygonsList        = []
    rectanglesList      = []
    textsList           = []     
    wiresList           = []
    holesList           = []
    signalsList         = []
    contactList         = []
    
    if context == CONTEXT_SHEET:
    
        netIndicies         = [int(i) for i in splitResult[1].split("#") if i]
        instanceIndicies    = [int(i) for i in splitResult[2].split("#") if i]
        circleIndicies      = [int(i) for i in splitResult[3].split("#") if i]
        framesIndicies      = [int(i) for i in splitResult[4].split("#") if i]
        polygonsIndicies    = [int(i) for i in splitResult[5].split("#") if i]
        rectanglesIndicies  = [int(i) for i in splitResult[6].split("#") if i]
        textsIndicies       = [int(i) for i in splitResult[7].split("#") if i]
        wiresIndicies       = [int(i) for i in splitResult[8].split("#") if i]

        
        netList             = ULSheet().nets()
        instanceList        = ULSheet().instances()   
        circleList          = ULSheet().circles()
        framesList          = ULSheet().frames()
        polygonsList        = ULSheet().polygons()
        rectanglesList      = ULSheet().rectangles()
        textsList           = ULSheet().texts()        
        wiresList           = ULSheet().wires()
        
       
          
    elif context == CONTEXT_BOARD:
    
        circleIndicies      = [int(i) for i in splitResult[1].split("#") if i]
        elementIndicies     = [int(i) for i in splitResult[2].split("#") if i]
        framesIndicies      = [int(i) for i in splitResult[3].split("#") if i]
        holesIndicies       = [int(i) for i in splitResult[4].split("#") if i]
        polygonsIndicies    = [int(i) for i in splitResult[5].split("#") if i]
        rectanglesIndicies  = [int(i) for i in splitResult[6].split("#") if i]
        signalsIndicies     = [int(i) for i in splitResult[7].split("#") if i]
        textsIndicies       = [int(i) for i in splitResult[8].split("#") if i]
        wiresIndicies       = [int(i) for i in splitResult[9].split("#") if i]

        
        circleList          = ULBoard().circles()
        elementList         = ULBoard().elements()   
        framesList          = ULBoard().frames()
        holesList           = ULBoard().holes()
        polygonsList        = ULBoard().polygons()
        rectanglesList      = ULBoard().rectangles()
        signalsList         = ULBoard().signals()
        textsList           = ULBoard().texts()        
        wiresList           = ULBoard().wires()  

    elif context == CONTEXT_PACKAGE:
        circleIndicies      = [int(i) for i in splitResult[1].split("#") if i]
        contactIndicies     = [int(i) for i in splitResult[2].split("#") if i]
        

        
        circleList          = ULPackage().circles()
        contactList         = ULPackage().contacts()
        print contactIndicies
        print contactList
        
        
        
        
    for index in netIndicies:
        resultList.append(netList[index])
    for index in elementIndicies:
        resultList.append(elementList[index])
    for index in instanceIndicies:
        resultList.append(instanceList[index])
    for index in circleIndicies:
        resultList.append(circleList[index])
    for index in framesIndicies:
        resultList.append(framesList[index])
    for index in polygonsIndicies:
        resultList.append(polygonsList[index])
    for index in rectanglesIndicies:
        resultList.append(rectanglesList[index]) 
    for index in textsIndicies:
        resultList.append(textsList[index])
    for index in wiresIndicies:
        resultList.append(wiresList[index])
    for index in holesIndicies:
        resultList.append(holesList[index])
    for index in signalsIndicies:
        resultList.append(signalsList[index])
    for index in contactIndicies:
        resultList.append(contactList[index])
        
    return resultList
    
__allobjects_cached_list = []
def allobjects():
    for index in range(len(__allobjects_cached_list)):
        __allobjects_cached_list.pop(0)
    for item in _objectsFromIndicies(handleReplyError(instance().executeCommand(COMMAND_allobjects))):
        __allobjects_cached_list.append(item)
    return __allobjects_cached_list
    
def selected():
    return _objectsFromIndicies(handleReplyError(instance().executeCommand(COMMAND_getselected)))
    
    

def move(objectname,unitx,unity):
    executescr("MOVE %s (%f %f);" % (objectname,unitx,unity))
    
def rename(oldname,newname):
    executescr("NAME %s %s;" % (oldname,newname))
    
def ingroup(objects):
    
    multi = False
    if isinstance(objects, ListType):
        multi = True
    
    objectsArg = objects if not multi else ";".join(objects)
        
    result = instance().executeCommand(COMMAND_ingroup,[objectsArg])
    

def palette(index,type=PALETTE_DEFAULT):
    if index < 0 or index > PALETTE_ENTRIES-1:
        raise EaglepyException("Invalid index %d. 0<index<%d" % (index,PALETTE_ENTRIES))
    if type < PALETTE_DEFAULT or type > 2:
        raise EaglepyException("Invalie type index %d" % type)
        
    result = instance().executeCommand(COMMAND_palette,[index,type])
    result = int(result)
    color = (result >> 16 & 255,result >> 8 & 255,result & 255,result >> 24 & 255)
    return color   

def paletteall(type=PALETTE_DEFAULT):
    if type < PALETTE_DEFAULT or type > 2:
        raise EaglepyException("Invalie type index %d" % type)
        
    result = instance().executeCommand(COMMAND_paletteall,[type])
    entries = []
    for colorstr in  result[1:].split(":"):
        color = int(colorstr)
        entries.append((color >> 16 & 255,color >> 8 & 255,color & 255,color >> 24 & 255))

    return entries
 
def executescr(script):
    instance().executeCommand(COMMAND_executescr,[script])

def status(message):
    instance().executeCommand(COMMAND_status,[message])
    
def moveobjects(objects,x,y):
    moveObjects = [objects]
    if isinstance(objects,ListType):    
        moveObjects = objects
    
    script = ""
    for object in moveObjects:
        script += "MOVE " + object + (" (%f %f);" % (x,y))
    instance().executeCommand(COMMAND_executescr,[script])
    
def clrgroup(objects):
    pass

def refreshview(): window()
def window():
    instance().executeCommand(COMMAND_executescr,["Window;"])
    
def clrgroupall():
    result = instance().executeCommand(COMMAND_clrgroupall)
    

def addgroup(objects):
    pass

def setgroup(objects):
    
    multi = False
    if isinstance(objects, ListType):
        multi = True
    
    objectsArg = objects if not multi else ";".join(objects)
    clrgroupall()
    result = instance().executeCommand(COMMAND_setgroup,[objectsArg])
   
   
def eagleToConfigured(value,configuredUnits=None):
    if configuredUnits is None:
        configuredUnits = ULContext().grid().unit()
    if configuredUnits == GRID_UNIT_MIC:
        return eagleToMic(value)
    elif configuredUnits == GRID_UNIT_MM:
        return eagleToMM(value)
    elif configuredUnits == GRID_UNIT_MIL:
        return eagleToMil(value)
    elif configuredUnits == GRID_UNIT_INCH:
        return eagleToInch(value)

def configuredToEagle(value,configuredUnits=None):  
    if configuredUnits is None:
        configuredUnits = ULContext().grid().unit()
    if configuredUnits == GRID_UNIT_MIC:
        return micToEage(value)
    elif configuredUnits == GRID_UNIT_MM:
        return mmToEagle(value)
    elif configuredUnits == GRID_UNIT_MIL:
        return milToEagle(value)
    elif configuredUnits == GRID_UNIT_INCH:
        return inchToEagle(value)

        
def unitToUnit(value,firstType,secondType):
    return eagleToConfigured(configuredToEagle(value,firstType),secondType)
 
def eagleToMic(value):
    return value * 0.003125
def eagleToMM(value):
    return value * 0.000003125
def eagleToMil(value):
    return value * 0.0001230314959375
def eagleToInch(value):
    return value * 0.0000001230314959375

def micToEage(value):
    return value / 0.003125
def mmToEagle(value):
    return value / 0.000003125
def milToEagle(value):
    return value / 0.0001230314959375
def inchToEagle(value):
    return value / 0.0000001230314959375    
    
    
def setGridUnitType(value):

    script = "GRID "
    if value == GRID_UNIT_MIC:
        script += "MIC;"
    elif value == GRID_UNIT_MM:
        script += "MM;"
    elif value == GRID_UNIT_MIL:
        script += "MIL;"
    elif value == GRID_UNIT_INCH:
        script += "INCH;"
    else:
        raise EaglepyException("Invalid unit type %s." % value)
    
    instance().executeCommand(COMMAND_executescr,[script])
 
 
def setGridUnitValue(value=-1):
 
    script = "GRID "
    if value == GRID_VALUE_FINEST:
        script += "FINEST;"
    elif value == GRID_VALUE_LAST:
        script += "LAST;"
    elif value == GRID_VALUE_DEFAULT or value == 0:
        script += "DEFAULT;"   
    else:
        script += str(value)    
    
    instance().executeCommand(COMMAND_executescr,[script])
    
    
def getcontext():
    return int(instance().executeCommand(COMMAND_getcontext))

def ULContext():
	
    context = int(instance().executeCommand(COMMAND_getcontext))
    if context == CONTEXT_BOARD:
        return ULBoard()
    elif context == CONTEXT_SCHEMATIC:
        return ULSchematic()
    elif context == CONTEXT_SHEET:
        return ULSheet()
    elif context == CONTEXT_PACKAGE:
        return ULPackage()

qt_imported = True 
try:
    from PyQt4 import QtCore
    from PyQt4 import QtGui
except:
    qt_imported = False


#RESOURCES
qt_resource_data = "\
\x00\x00\x21\x88\
\x89\
\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\
\x00\x00\x40\x00\x00\x00\x40\x08\x06\x00\x00\x00\xaa\x69\x71\xde\
\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0b\x13\x00\x00\x0b\x13\
\x01\x00\x9a\x9c\x18\x00\x00\x0a\x4f\x69\x43\x43\x50\x50\x68\x6f\
\x74\x6f\x73\x68\x6f\x70\x20\x49\x43\x43\x20\x70\x72\x6f\x66\x69\
\x6c\x65\x00\x00\x78\xda\x9d\x53\x67\x54\x53\xe9\x16\x3d\xf7\xde\
\xf4\x42\x4b\x88\x80\x94\x4b\x6f\x52\x15\x08\x20\x52\x42\x8b\x80\
\x14\x91\x26\x2a\x21\x09\x10\x4a\x88\x21\xa1\xd9\x15\x51\xc1\x11\
\x45\x45\x04\x1b\xc8\xa0\x88\x03\x8e\x8e\x80\x8c\x15\x51\x2c\x0c\
\x8a\x0a\xd8\x07\xe4\x21\xa2\x8e\x83\xa3\x88\x8a\xca\xfb\xe1\x7b\
\xa3\x6b\xd6\xbc\xf7\xe6\xcd\xfe\xb5\xd7\x3e\xe7\xac\xf3\x9d\xb3\
\xcf\x07\xc0\x08\x0c\x96\x48\x33\x51\x35\x80\x0c\xa9\x42\x1e\x11\
\xe0\x83\xc7\xc4\xc6\xe1\xe4\x2e\x40\x81\x0a\x24\x70\x00\x10\x08\
\xb3\x64\x21\x73\xfd\x23\x01\x00\xf8\x7e\x3c\x3c\x2b\x22\xc0\x07\
\xbe\x00\x01\x78\xd3\x0b\x08\x00\xc0\x4d\x9b\xc0\x30\x1c\x87\xff\
\x0f\xea\x42\x99\x5c\x01\x80\x84\x01\xc0\x74\x91\x38\x4b\x08\x80\
\x14\x00\x40\x7a\x8e\x42\xa6\x00\x40\x46\x01\x80\x9d\x98\x26\x53\
\x00\xa0\x04\x00\x60\xcb\x63\x62\xe3\x00\x50\x2d\x00\x60\x27\x7f\
\xe6\xd3\x00\x80\x9d\xf8\x99\x7b\x01\x00\x5b\x94\x21\x15\x01\xa0\
\x91\x00\x20\x13\x65\x88\x44\x00\x68\x3b\x00\xac\xcf\x56\x8a\x45\
\x00\x58\x30\x00\x14\x66\x4b\xc4\x39\x00\xd8\x2d\x00\x30\x49\x57\
\x66\x48\x00\xb0\xb7\x00\xc0\xce\x10\x0b\xb2\x00\x08\x0c\x00\x30\
\x51\x88\x85\x29\x00\x04\x7b\x00\x60\xc8\x23\x23\x78\x00\x84\x99\
\x00\x14\x46\xf2\x57\x3c\xf1\x2b\xae\x10\xe7\x2a\x00\x00\x78\x99\
\xb2\x3c\xb9\x24\x39\x45\x81\x5b\x08\x2d\x71\x07\x57\x57\x2e\x1e\
\x28\xce\x49\x17\x2b\x14\x36\x61\x02\x61\x9a\x40\x2e\xc2\x79\x99\
\x19\x32\x81\x34\x0f\xe0\xf3\xcc\x00\x00\xa0\x91\x15\x11\xe0\x83\
\xf3\xfd\x78\xce\x0e\xae\xce\xce\x36\x8e\xb6\x0e\x5f\x2d\xea\xbf\
\x06\xff\x22\x62\x62\xe3\xfe\xe5\xcf\xab\x70\x40\x00\x00\xe1\x74\
\x7e\xd1\xfe\x2c\x2f\xb3\x1a\x80\x3b\x06\x80\x6d\xfe\xa2\x25\xee\
\x04\x68\x5e\x0b\xa0\x75\xf7\x8b\x66\xb2\x0f\x40\xb5\x00\xa0\xe9\
\xda\x57\xf3\x70\xf8\x7e\x3c\x3c\x45\xa1\x90\xb9\xd9\xd9\xe5\xe4\
\xe4\xd8\x4a\xc4\x42\x5b\x61\xca\x57\x7d\xfe\x67\xc2\x5f\xc0\x57\
\xfd\x6c\xf9\x7e\x3c\xfc\xf7\xf5\xe0\xbe\xe2\x24\x81\x32\x5d\x81\
\x47\x04\xf8\xe0\xc2\xcc\xf4\x4c\xa5\x1c\xcf\x92\x09\x84\x62\xdc\
\xe6\x8f\x47\xfc\xb7\x0b\xff\xfc\x1d\xd3\x22\xc4\x49\x62\xb9\x58\
\x2a\x14\xe3\x51\x12\x71\x8e\x44\x9a\x8c\xf3\x32\xa5\x22\x89\x42\
\x92\x29\xc5\x25\xd2\xff\x64\xe2\xdf\x2c\xfb\x03\x3e\xdf\x35\x00\
\xb0\x6a\x3e\x01\x7b\x91\x2d\xa8\x5d\x63\x03\xf6\x4b\x27\x10\x58\
\x74\xc0\xe2\xf7\x00\x00\xf2\xbb\x6f\xc1\xd4\x28\x08\x03\x80\x68\
\x83\xe1\xcf\x77\xff\xef\x3f\xfd\x47\xa0\x25\x00\x80\x66\x49\x92\
\x71\x00\x00\x5e\x44\x24\x2e\x54\xca\xb3\x3f\xc7\x08\x00\x00\x44\
\xa0\x81\x2a\xb0\x41\x1b\xf4\xc1\x18\x2c\xc0\x06\x1c\xc1\x05\xdc\
\xc1\x0b\xfc\x60\x36\x84\x42\x24\xc4\xc2\x42\x10\x42\x0a\x64\x80\
\x1c\x72\x60\x29\xac\x82\x42\x28\x86\xcd\xb0\x1d\x2a\x60\x2f\xd4\
\x40\x1d\x34\xc0\x51\x68\x86\x93\x70\x0e\x2e\xc2\x55\xb8\x0e\x3d\
\x70\x0f\xfa\x61\x08\x9e\xc1\x28\xbc\x81\x09\x04\x41\xc8\x08\x13\
\x61\x21\xda\x88\x01\x62\x8a\x58\x23\x8e\x08\x17\x99\x85\xf8\x21\
\xc1\x48\x04\x12\x8b\x24\x20\xc9\x88\x14\x51\x22\x4b\x91\x35\x48\
\x31\x52\x8a\x54\x20\x55\x48\x1d\xf2\x3d\x72\x02\x39\x87\x5c\x46\
\xba\x91\x3b\xc8\x00\x32\x82\xfc\x86\xbc\x47\x31\x94\x81\xb2\x51\
\x3d\xd4\x0c\xb5\x43\xb9\xa8\x37\x1a\x84\x46\xa2\x0b\xd0\x64\x74\
\x31\x9a\x8f\x16\xa0\x9b\xd0\x72\xb4\x1a\x3d\x8c\x36\xa1\xe7\xd0\
\xab\x68\x0f\xda\x8f\x3e\x43\xc7\x30\xc0\xe8\x18\x07\x33\xc4\x6c\
\x30\x2e\xc6\xc3\x42\xb1\x38\x2c\x09\x93\x63\xcb\xb1\x22\xac\x0c\
\xab\xc6\x1a\xb0\x56\xac\x03\xbb\x89\xf5\x63\xcf\xb1\x77\x04\x12\
\x81\x45\xc0\x09\x36\x04\x77\x42\x20\x61\x1e\x41\x48\x58\x4c\x58\
\x4e\xd8\x48\xa8\x20\x1c\x24\x34\x11\xda\x09\x37\x09\x03\x84\x51\
\xc2\x27\x22\x93\xa8\x4b\xb4\x26\xba\x11\xf9\xc4\x18\x62\x32\x31\
\x87\x58\x48\x2c\x23\xd6\x12\x8f\x13\x2f\x10\x7b\x88\x43\xc4\x37\
\x24\x12\x89\x43\x32\x27\xb9\x90\x02\x49\xb1\xa4\x54\xd2\x12\xd2\
\x46\xd2\x6e\x52\x23\xe9\x2c\xa9\x9b\x34\x48\x1a\x23\x93\xc9\xda\
\x64\x6b\xb2\x07\x39\x94\x2c\x20\x2b\xc8\x85\xe4\x9d\xe4\xc3\xe4\
\x33\xe4\x1b\xe4\x21\xf2\x5b\x0a\x9d\x62\x40\x71\xa4\xf8\x53\xe2\
\x28\x52\xca\x6a\x4a\x19\xe5\x10\xe5\x34\xe5\x06\x65\x98\x32\x41\
\x55\xa3\x9a\x52\xdd\xa8\xa1\x54\x11\x35\x8f\x5a\x42\xad\xa1\xb6\
\x52\xaf\x51\x87\xa8\x13\x34\x75\x9a\x39\xcd\x83\x16\x49\x4b\xa5\
\xad\xa2\x95\xd3\x1a\x68\x17\x68\xf7\x69\xaf\xe8\x74\xba\x11\xdd\
\x95\x1e\x4e\x97\xd0\x57\xd2\xcb\xe9\x47\xe8\x97\xe8\x03\xf4\x77\
\x0c\x0d\x86\x15\x83\xc7\x88\x67\x28\x19\x9b\x18\x07\x18\x67\x19\
\x77\x18\xaf\x98\x4c\xa6\x19\xd3\x8b\x19\xc7\x54\x30\x37\x31\xeb\
\x98\xe7\x99\x0f\x99\x6f\x55\x58\x2a\xb6\x2a\x7c\x15\x91\xca\x0a\
\x95\x4a\x95\x26\x95\x1b\x2a\x2f\x54\xa9\xaa\xa6\xaa\xde\xaa\x0b\
\x55\xf3\x55\xcb\x54\x8f\xa9\x5e\x53\x7d\xae\x46\x55\x33\x53\xe3\
\xa9\x09\xd4\x96\xab\x55\xaa\x9d\x50\xeb\x53\x1b\x53\x67\xa9\x3b\
\xa8\x87\xaa\x67\xa8\x6f\x54\x3f\xa4\x7e\x59\xfd\x89\x06\x59\xc3\
\x4c\xc3\x4f\x43\xa4\x51\xa0\xb1\x5f\xe3\xbc\xc6\x20\x0b\x63\x19\
\xb3\x78\x2c\x21\x6b\x0d\xab\x86\x75\x81\x35\xc4\x26\xb1\xcd\xd9\
\x7c\x76\x2a\xbb\x98\xfd\x1d\xbb\x8b\x3d\xaa\xa9\xa1\x39\x43\x33\
\x4a\x33\x57\xb3\x52\xf3\x94\x66\x3f\x07\xe3\x98\x71\xf8\x9c\x74\
\x4e\x09\xe7\x28\xa7\x97\xf3\x7e\x8a\xde\x14\xef\x29\xe2\x29\x1b\
\xa6\x34\x4c\xb9\x31\x65\x5c\x6b\xaa\x96\x97\x96\x58\xab\x48\xab\
\x51\xab\x47\xeb\xbd\x36\xae\xed\xa7\x9d\xa6\xbd\x45\xbb\x59\xfb\
\x81\x0e\x41\xc7\x4a\x27\x5c\x27\x47\x67\x8f\xce\x05\x9d\xe7\x53\
\xd9\x53\xdd\xa7\x0a\xa7\x16\x4d\x3d\x3a\xf5\xae\x2e\xaa\x6b\xa5\
\x1b\xa1\xbb\x44\x77\xbf\x6e\xa7\xee\x98\x9e\xbe\x5e\x80\x9e\x4c\
\x6f\xa7\xde\x79\xbd\xe7\xfa\x1c\x7d\x2f\xfd\x54\xfd\x6d\xfa\xa7\
\xf5\x47\x0c\x58\x06\xb3\x0c\x24\x06\xdb\x0c\xce\x18\x3c\xc5\x35\
\x71\x6f\x3c\x1d\x2f\xc7\xdb\xf1\x51\x43\x5d\xc3\x40\x43\xa5\x61\
\x95\x61\x97\xe1\x84\x91\xb9\xd1\x3c\xa3\xd5\x46\x8d\x46\x0f\x8c\
\x69\xc6\x5c\xe3\x24\xe3\x6d\xc6\x6d\xc6\xa3\x26\x06\x26\x21\x26\
\x4b\x4d\xea\x4d\xee\x9a\x52\x4d\xb9\xa6\x29\xa6\x3b\x4c\x3b\x4c\
\xc7\xcd\xcc\xcd\xa2\xcd\xd6\x99\x35\x9b\x3d\x31\xd7\x32\xe7\x9b\
\xe7\x9b\xd7\x9b\xdf\xb7\x60\x5a\x78\x5a\x2c\xb6\xa8\xb6\xb8\x65\
\x49\xb2\xe4\x5a\xa6\x59\xee\xb6\xbc\x6e\x85\x5a\x39\x59\xa5\x58\
\x55\x5a\x5d\xb3\x46\xad\x9d\xad\x25\xd6\xbb\xad\xbb\xa7\x11\xa7\
\xb9\x4e\x93\x4e\xab\x9e\xd6\x67\xc3\xb0\xf1\xb6\xc9\xb6\xa9\xb7\
\x19\xb0\xe5\xd8\x06\xdb\xae\xb6\x6d\xb6\x7d\x61\x67\x62\x17\x67\
\xb7\xc5\xae\xc3\xee\x93\xbd\x93\x7d\xba\x7d\x8d\xfd\x3d\x07\x0d\
\x87\xd9\x0e\xab\x1d\x5a\x1d\x7e\x73\xb4\x72\x14\x3a\x56\x3a\xde\
\x9a\xce\x9c\xee\x3f\x7d\xc5\xf4\x96\xe9\x2f\x67\x58\xcf\x10\xcf\
\xd8\x33\xe3\xb6\x13\xcb\x29\xc4\x69\x9d\x53\x9b\xd3\x47\x67\x17\
\x67\xb9\x73\x83\xf3\x88\x8b\x89\x4b\x82\xcb\x2e\x97\x3e\x2e\x9b\
\x1b\xc6\xdd\xc8\xbd\xe4\x4a\x74\xf5\x71\x5d\xe1\x7a\xd2\xf5\x9d\
\x9b\xb3\x9b\xc2\xed\xa8\xdb\xaf\xee\x36\xee\x69\xee\x87\xdc\x9f\
\xcc\x34\x9f\x29\x9e\x59\x33\x73\xd0\xc3\xc8\x43\xe0\x51\xe5\xd1\
\x3f\x0b\x9f\x95\x30\x6b\xdf\xac\x7e\x4f\x43\x4f\x81\x67\xb5\xe7\
\x23\x2f\x63\x2f\x91\x57\xad\xd7\xb0\xb7\xa5\x77\xaa\xf7\x61\xef\
\x17\x3e\xf6\x3e\x72\x9f\xe3\x3e\xe3\x3c\x37\xde\x32\xde\x59\x5f\
\xcc\x37\xc0\xb7\xc8\xb7\xcb\x4f\xc3\x6f\x9e\x5f\x85\xdf\x43\x7f\
\x23\xff\x64\xff\x7a\xff\xd1\x00\xa7\x80\x25\x01\x67\x03\x89\x81\
\x41\x81\x5b\x02\xfb\xf8\x7a\x7c\x21\xbf\x8e\x3f\x3a\xdb\x65\xf6\
\xb2\xd9\xed\x41\x8c\xa0\xb9\x41\x15\x41\x8f\x82\xad\x82\xe5\xc1\
\xad\x21\x68\xc8\xec\x90\xad\x21\xf7\xe7\x98\xce\x91\xce\x69\x0e\
\x85\x50\x7e\xe8\xd6\xd0\x07\x61\xe6\x61\x8b\xc3\x7e\x0c\x27\x85\
\x87\x85\x57\x86\x3f\x8e\x70\x88\x58\x1a\xd1\x31\x97\x35\x77\xd1\
\xdc\x43\x73\xdf\x44\xfa\x44\x96\x44\xde\x9b\x67\x31\x4f\x39\xaf\
\x2d\x4a\x35\x2a\x3e\xaa\x2e\x6a\x3c\xda\x37\xba\x34\xba\x3f\xc6\
\x2e\x66\x59\xcc\xd5\x58\x9d\x58\x49\x6c\x4b\x1c\x39\x2e\x2a\xae\
\x36\x6e\x6c\xbe\xdf\xfc\xed\xf3\x87\xe2\x9d\xe2\x0b\xe3\x7b\x17\
\x98\x2f\xc8\x5d\x70\x79\xa1\xce\xc2\xf4\x85\xa7\x16\xa9\x2e\x12\
\x2c\x3a\x96\x40\x4c\x88\x4e\x38\x94\xf0\x41\x10\x2a\xa8\x16\x8c\
\x25\xf2\x13\x77\x25\x8e\x0a\x79\xc2\x1d\xc2\x67\x22\x2f\xd1\x36\
\xd1\x88\xd8\x43\x5c\x2a\x1e\x4e\xf2\x48\x2a\x4d\x7a\x92\xec\x91\
\xbc\x35\x79\x24\xc5\x33\xa5\x2c\xe5\xb9\x84\x27\xa9\x90\xbc\x4c\
\x0d\x4c\xdd\x9b\x3a\x9e\x16\x9a\x76\x20\x6d\x32\x3d\x3a\xbd\x31\
\x83\x92\x91\x90\x71\x42\xaa\x21\x4d\x93\xb6\x67\xea\x67\xe6\x66\
\x76\xcb\xac\x65\x85\xb2\xfe\xc5\x6e\x8b\xb7\x2f\x1e\x95\x07\xc9\
\x6b\xb3\x90\xac\x05\x59\x2d\x0a\xb6\x42\xa6\xe8\x54\x5a\x28\xd7\
\x2a\x07\xb2\x67\x65\x57\x66\xbf\xcd\x89\xca\x39\x96\xab\x9e\x2b\
\xcd\xed\xcc\xb3\xca\xdb\x90\x37\x9c\xef\x9f\xff\xed\x12\xc2\x12\
\xe1\x92\xb6\xa5\x86\x4b\x57\x2d\x1d\x58\xe6\xbd\xac\x6a\x39\xb2\
\x3c\x71\x79\xdb\x0a\xe3\x15\x05\x2b\x86\x56\x06\xac\x3c\xb8\x8a\
\xb6\x2a\x6d\xd5\x4f\xab\xed\x57\x97\xae\x7e\xbd\x26\x7a\x4d\x6b\
\x81\x5e\xc1\xca\x82\xc1\xb5\x01\x6b\xeb\x0b\x55\x0a\xe5\x85\x7d\
\xeb\xdc\xd7\xed\x5d\x4f\x58\x2f\x59\xdf\xb5\x61\xfa\x86\x9d\x1b\
\x3e\x15\x89\x8a\xae\x14\xdb\x17\x97\x15\x7f\xd8\x28\xdc\x78\xe5\
\x1b\x87\x6f\xca\xbf\x99\xdc\x94\xb4\xa9\xab\xc4\xb9\x64\xcf\x66\
\xd2\x66\xe9\xe6\xde\x2d\x9e\x5b\x0e\x96\xaa\x97\xe6\x97\x0e\x6e\
\x0d\xd9\xda\xb4\x0d\xdf\x56\xb4\xed\xf5\xf6\x45\xdb\x2f\x97\xcd\
\x28\xdb\xbb\x83\xb6\x43\xb9\xa3\xbf\x3c\xb8\xbc\x65\xa7\xc9\xce\
\xcd\x3b\x3f\x54\xa4\x54\xf4\x54\xfa\x54\x36\xee\xd2\xdd\xb5\x61\
\xd7\xf8\x6e\xd1\xee\x1b\x7b\xbc\xf6\x34\xec\xd5\xdb\x5b\xbc\xf7\
\xfd\x3e\xc9\xbe\xdb\x55\x01\x55\x4d\xd5\x66\xd5\x65\xfb\x49\xfb\
\xb3\xf7\x3f\xae\x89\xaa\xe9\xf8\x96\xfb\x6d\x5d\xad\x4e\x6d\x71\
\xed\xc7\x03\xd2\x03\xfd\x07\x23\x0e\xb6\xd7\xb9\xd4\xd5\x1d\xd2\
\x3d\x54\x52\x8f\xd6\x2b\xeb\x47\x0e\xc7\x1f\xbe\xfe\x9d\xef\x77\
\x2d\x0d\x36\x0d\x55\x8d\x9c\xc6\xe2\x23\x70\x44\x79\xe4\xe9\xf7\
\x09\xdf\xf7\x1e\x0d\x3a\xda\x76\x8c\x7b\xac\xe1\x07\xd3\x1f\x76\
\x1d\x67\x1d\x2f\x6a\x42\x9a\xf2\x9a\x46\x9b\x53\x9a\xfb\x5b\x62\
\x5b\xba\x4f\xcc\x3e\xd1\xd6\xea\xde\x7a\xfc\x47\xdb\x1f\x0f\x9c\
\x34\x3c\x59\x79\x4a\xf3\x54\xc9\x69\xda\xe9\x82\xd3\x93\x67\xf2\
\xcf\x8c\x9d\x95\x9d\x7d\x7e\x2e\xf9\xdc\x60\xdb\xa2\xb6\x7b\xe7\
\x63\xce\xdf\x6a\x0f\x6f\xef\xba\x10\x74\xe1\xd2\x45\xff\x8b\xe7\
\x3b\xbc\x3b\xce\x5c\xf2\xb8\x74\xf2\xb2\xdb\xe5\x13\x57\xb8\x57\
\x9a\xaf\x3a\x5f\x6d\xea\x74\xea\x3c\xfe\x93\xd3\x4f\xc7\xbb\x9c\
\xbb\x9a\xae\xb9\x5c\x6b\xb9\xee\x7a\xbd\xb5\x7b\x66\xf7\xe9\x1b\
\x9e\x37\xce\xdd\xf4\xbd\x79\xf1\x16\xff\xd6\xd5\x9e\x39\x3d\xdd\
\xbd\xf3\x7a\x6f\xf7\xc5\xf7\xf5\xdf\x16\xdd\x7e\x72\x27\xfd\xce\
\xcb\xbb\xd9\x77\x27\xee\xad\xbc\x4f\xbc\x5f\xf4\x40\xed\x41\xd9\
\x43\xdd\x87\xd5\x3f\x5b\xfe\xdc\xd8\xef\xdc\x7f\x6a\xc0\x77\xa0\
\xf3\xd1\xdc\x47\xf7\x06\x85\x83\xcf\xfe\x91\xf5\x8f\x0f\x43\x05\
\x8f\x99\x8f\xcb\x86\x0d\x86\xeb\x9e\x38\x3e\x39\x39\xe2\x3f\x72\
\xfd\xe9\xfc\xa7\x43\xcf\x64\xcf\x26\x9e\x17\xfe\xa2\xfe\xcb\xae\
\x17\x16\x2f\x7e\xf8\xd5\xeb\xd7\xce\xd1\x98\xd1\xa1\x97\xf2\x97\
\x93\xbf\x6d\x7c\xa5\xfd\xea\xc0\xeb\x19\xaf\xdb\xc6\xc2\xc6\x1e\
\xbe\xc9\x78\x33\x31\x5e\xf4\x56\xfb\xed\xc1\x77\xdc\x77\x1d\xef\
\xa3\xdf\x0f\x4f\xe4\x7c\x20\x7f\x28\xff\x68\xf9\xb1\xf5\x53\xd0\
\xa7\xfb\x93\x19\x93\x93\xff\x04\x03\x98\xf3\xfc\x63\x33\x2d\xdb\
\x00\x00\x00\x20\x63\x48\x52\x4d\x00\x00\x7a\x25\x00\x00\x80\x83\
\x00\x00\xf9\xff\x00\x00\x80\xe9\x00\x00\x75\x30\x00\x00\xea\x60\
\x00\x00\x3a\x98\x00\x00\x17\x6f\x92\x5f\xc5\x46\x00\x00\x16\xb3\
\x49\x44\x41\x54\x78\xda\xec\x7b\x69\x70\x1d\xd7\x75\xe6\x77\xee\
\xed\xe5\xed\xc0\xc3\x4e\x00\x5c\x41\x71\x11\x17\x59\x6b\xa8\xc5\
\xb1\xb6\x58\x16\x3d\x71\x42\xcb\x72\x6c\x57\xec\x59\x9c\xd4\x8c\
\x2b\x1a\x57\xa6\x32\x99\x99\x9a\x89\x67\xaa\x3c\x55\x29\xc7\x33\
\x3f\x92\x1a\x8f\x26\x95\x9a\xf2\x92\x72\x92\x4a\xc5\x8a\x2b\x29\
\x5b\xb2\xb5\x38\xa6\xa8\x88\x92\x22\x91\x22\x45\x71\x05\x49\x80\
\x04\x08\x82\x00\xde\xc3\xdb\x5f\x77\xdf\x7b\xce\xfc\xe8\x7e\x20\
\x28\x53\x12\x29\x89\xf3\x47\xec\xaa\x57\x8d\x87\xd7\x00\xfa\x7c\
\xf7\x9c\xef\x7c\xe7\xbb\x0d\x12\x11\x7c\x98\x0f\x85\x0f\xf9\x71\
\x1d\x80\xeb\x00\x5c\x07\xe0\x3a\x00\xd7\x01\xb8\x0e\xc0\x87\xf8\
\x70\x2e\xf7\x4d\x22\xba\xfa\x5f\xa4\x35\x36\x6e\xbb\x05\xb9\xae\
\x5e\x9c\x38\xfc\xba\x02\x90\xbd\xef\x91\x7f\x39\x78\xc3\xd6\x9b\
\x87\x89\x64\xa4\x69\x78\x45\xd3\xe8\x62\x14\x4a\x9e\x18\x2e\x69\
\xb2\x9e\xef\xb7\x3d\x57\x6a\x59\xd7\x9e\xcf\xa7\xdd\x69\x97\x68\
\x5a\xe9\xf4\x99\xd9\x85\x85\x45\xdf\xf3\x64\xeb\xc6\x4d\x18\x3f\
\xf4\x2a\xfe\xcb\x63\x5f\x04\x00\x64\x3d\x0f\x0f\x6f\xd8\x80\x4f\
\xdf\xb4\x0d\x3d\x99\x2c\x52\x9e\x8b\x6f\x3c\xf7\x33\xfc\xe4\xe8\
\x31\xac\xe9\xe9\xc1\xe3\x8f\x3e\x8a\x5a\x18\x62\x7a\x71\x11\x8e\
\x52\xb8\x5c\x14\x8f\xfd\xe0\x07\xef\x0e\xc0\x7b\x3d\x44\x04\x51\
\x18\xa6\xb7\xde\xf9\xc0\xcd\xbd\x2b\xd7\xdf\x45\x85\xa1\xad\xc7\
\x66\xcd\xea\xc8\x72\x7f\x60\x39\x6b\x38\xf2\x89\xd9\x15\x6b\x15\
\x08\xa2\x74\x3d\x52\xc2\xc6\x73\xa4\x99\xf6\x68\x31\xeb\x3a\x33\
\xbd\x5d\xb9\x57\xd9\xda\xa7\x0d\x9b\xfd\x8a\x10\x5d\x6e\x7d\x00\
\xf8\x96\xd9\xad\x05\x41\x2b\xb2\xd6\x74\xfe\x36\x00\x45\x44\x9e\
\x61\x16\xcb\x1c\xca\x15\xc8\xdc\x0f\x0c\x00\x22\x22\x08\x8f\xac\
\xbc\xf1\x8e\x7f\xa1\x56\x6c\x7d\xb4\x42\xb9\xf5\xd5\x46\x90\x09\
\x6a\x21\x18\x80\x16\x86\x87\x08\x10\x82\x05\x01\x02\x08\x31\x60\
\x2d\x48\x04\x4c\x02\x12\x0b\xff\x7c\xeb\xe3\xfd\x59\xda\x75\xc3\
\x68\xef\x77\x58\xe4\x7b\x5a\xeb\x9a\x52\x1a\xcc\xd6\x11\x11\xa3\
\x15\x8d\xf8\xda\xd9\xf5\xe2\xc4\xc4\xf9\x3f\x79\xe1\x85\x1f\xd7\
\x83\xd0\x00\x40\xda\xf3\x3c\x57\xa9\x8f\x01\x78\xe0\xa9\xc3\x87\
\x9f\x00\xf0\xea\x64\xa9\x84\xb6\x31\x97\x64\xc2\xef\x5f\x2b\x0e\
\xc8\xe5\xf3\x83\xeb\x6f\xf9\xe8\x6f\xd3\xe8\xed\xbf\x77\xba\xa2\
\xb6\x37\x4a\x0b\x4e\x3e\x38\xbf\xd0\xa3\x16\x6b\xbe\x63\x99\x7c\
\x17\xe4\x79\xd0\xae\x82\xe7\x3a\xf0\x3c\x07\xbe\xeb\x22\xe5\x3b\
\xf0\x3d\x05\xdf\x75\xa0\x34\x21\x30\x9c\x3e\x5b\x0e\x6e\x79\x7d\
\x62\xe1\x6b\x93\xe7\xe6\x7e\xab\xd8\xd3\xef\x0d\xac\x18\x01\x80\
\x94\x88\xe4\xb7\x0d\xad\xb8\xb7\x2f\x93\xfe\xe7\x4f\x1d\x3b\x36\
\x50\x0f\xc2\x16\x00\xac\x28\x14\x06\x1e\xbb\xfb\xee\x2f\xa7\x5d\
\xf7\xbf\x7f\x67\xef\xde\xe2\xf8\xfc\xfc\xcc\xef\xdf\x7f\xbf\xb7\
\xb2\xbb\xdb\xd1\x44\xf0\xb4\x5e\x7a\x5d\x93\x0c\x20\xc0\x2f\x0e\
\x8c\xdc\x11\x64\x06\x77\x2d\x36\xa4\x3b\x2d\x8d\x59\x4c\x3c\xff\
\xd4\xf8\xe1\xbd\x93\x99\x62\xff\xd8\xe8\x6d\x3b\x3f\x5a\x4b\xaf\
\x5c\xc5\x50\x31\xbb\xb0\x59\xc2\x5f\x88\x01\x12\x10\x04\xae\x16\
\x90\xa3\x10\x1a\x17\x33\x95\x60\xe0\x95\xe3\x53\xff\x7a\x63\x0f\
\xbd\xaa\x20\x2f\x00\x70\xd6\xf5\x14\x37\x3e\x38\xb6\xf6\xd1\x73\
\xb5\x5a\xfa\x4c\xb9\x7c\x10\x80\xac\xef\xed\x1d\xfb\xfa\x43\x0f\
\x3d\xb6\x65\x78\xc5\x23\xff\xf1\xc7\x4f\xfe\x7c\xcf\xc9\x93\x7f\
\xf4\x3f\x3e\xf5\xa9\x4c\xd6\x75\x3f\x5d\x0f\x82\x97\x0c\xf3\x84\
\x00\xf2\xde\x4b\x80\x08\xae\xeb\x42\x44\x60\xa2\xe8\xf2\xad\x44\
\xa9\x1e\xb7\xd0\xbb\xb9\xa9\x0b\x83\xae\xef\x22\x55\x9b\xdb\x73\
\x70\xdf\xcf\x1e\xbf\x30\x33\x5d\x77\x26\xc6\x6f\xeb\x1b\x18\xce\
\x79\x63\xc5\x81\x50\x65\xd3\x80\x80\x40\x49\x29\x0b\x58\x14\x20\
\x04\x82\x00\x22\x60\x00\xbe\xb2\x80\xe7\x60\x66\xb1\x35\x92\x0e\
\xea\xf7\x07\x51\xf8\x86\x22\xf8\x77\x8c\x8e\xde\xd2\xe5\x79\x77\
\x7c\xfb\xd8\xb1\xe7\xe7\x1b\xcd\xe3\x77\x8c\x8e\x6e\xf9\xda\x03\
\xf7\xff\xc1\x48\x77\xd7\x43\xdf\xda\xf3\xfc\x1e\xb1\xe6\x6f\xbf\
\xfb\xb9\xdf\xd8\xf9\x91\xd1\xd1\x47\xfe\xf0\xd9\xe7\x0e\x1d\x98\
\x99\xd9\x6b\xac\x15\x22\x7a\x5b\x04\xde\x15\x00\xa5\x14\x7a\x87\
\x46\x10\x05\x01\x16\x66\xcf\x5d\xbe\x95\x12\x15\x18\xaa\x87\xa1\
\x5c\xa5\x1d\x68\xcf\x9f\xcf\x16\x8a\x47\x53\x8b\xa5\x1a\x89\xf4\
\xb3\x70\x5d\x81\x61\x88\xa0\x45\x43\x43\x40\x44\x10\x01\x48\x24\
\xa9\xd1\x4b\x6f\x52\x11\x20\xcc\x6e\xa3\x5e\x5f\x1d\x5a\x5b\xec\
\xf5\xbc\xdc\xe7\xb6\x6c\xbe\x2f\x30\xa1\x7e\xf9\xcc\xd4\x3f\x3d\
\x74\xc3\xfa\xdb\xbf\xb9\xf3\xe1\x7f\xe7\x39\xce\x3d\xff\xf3\xf9\
\xe7\x9f\xc9\xba\xde\x81\xff\xfd\xe8\x67\xfe\xcd\x58\xb1\xf8\xc0\
\x7f\xfb\xc9\x4f\xdf\xfc\xce\x2b\xaf\x3c\xb1\x65\x70\xf0\xac\x56\
\x0a\x56\xf8\xfd\x91\xa0\x35\x06\xda\xf5\x30\xb4\x76\x23\x9a\x95\
\x05\x54\x4b\xf3\x97\x02\x20\xe2\x8a\x35\xae\x03\x2b\xad\x76\x1b\
\xf9\xae\xd1\x7b\x7e\x79\xd7\x97\x1e\x9e\x38\xf4\xea\x6b\x61\x18\
\x6e\xee\x5a\xb3\x7d\x5b\x45\xfb\x29\x52\x2a\x0e\x98\xdf\x89\x9c\
\x05\x02\x40\x88\x00\x11\x98\x30\xf4\x00\xe4\xd6\x17\x8b\xeb\x6f\
\xea\xef\xbb\x6b\xb2\x5a\x8b\x76\xac\x1c\x5e\xf7\xdb\x3b\x76\x3c\
\xb2\x7d\x74\x78\xc7\x5f\xbf\xba\xef\xfc\x86\x62\x0f\x7d\xf1\xce\
\x1d\x9f\x59\x51\x2c\x6e\xfe\xe6\xd3\xcf\x1c\xf9\xab\x03\x07\xfe\
\xfd\x86\xbe\xbe\x9f\x7f\xef\x37\x3e\x8b\x52\xbb\x49\x8d\x30\x14\
\x7a\x3f\x00\x08\x33\x0a\xbd\x43\xd8\xf1\xa9\xdf\xc4\xd9\x83\x2f\
\xe2\xa5\x67\x7f\x84\xb0\xd5\x58\x5e\x27\x0a\xa4\x35\x69\xa5\xd8\
\x32\xe6\x02\xb5\x35\xd3\xb7\xe9\x0f\xfb\x6e\x1d\x9c\xac\xd7\x5b\
\xa3\x35\xeb\xae\x8f\xd8\x21\x02\x81\x98\xc1\x02\x10\x01\x20\x81\
\x2c\x65\xc0\x5b\x79\x85\x20\xc2\xa8\xb5\x9a\x48\x0b\xfa\x3f\x39\
\xb6\xe6\x9e\x62\x26\x35\xa8\x48\x99\xff\x70\xf7\x5d\x9f\x5d\xd7\
\xd7\xd7\x3b\xb7\x50\x92\x75\x85\x7c\xea\x57\xb7\x6e\x79\x20\x93\
\xcf\xfa\xdf\xde\xb3\x67\xfc\xbf\x3e\xfd\xcc\x1f\x7c\x64\x78\xf8\
\xd9\x2f\x6c\xdf\x36\xe8\x2a\x5a\x33\x51\x2a\xd7\x9b\x51\x74\x94\
\x00\xfb\xbe\xda\x20\xb3\x45\xb3\xba\x08\x52\x0e\x46\x37\x6c\x47\
\x26\x9d\x46\x65\x7e\x06\x67\xc7\x8f\xc4\xeb\xa5\x5d\x87\xbc\xb4\
\xe3\x78\x3e\x5a\xad\x36\x8e\xcf\x54\xc7\x3c\xd7\x1b\x23\xa4\x20\
\x4a\x40\x9a\xa0\x20\x70\x00\x58\x58\x18\x00\x5a\x2c\x88\x18\x10\
\x7d\x29\xa5\xc6\x5d\x12\xa1\x8d\x28\x6c\x34\xf4\x9a\x7c\x6e\xfd\
\xce\x75\x6b\xee\xf5\x5c\xdf\xe9\x87\x76\xfa\xdd\x7c\x0a\x51\x84\
\x82\x56\x72\xeb\xc8\x70\x77\x53\x18\x7f\xf9\xe2\x4b\xe3\xdf\xdc\
\xfd\xfc\x9f\x0c\x64\x33\xfb\x7f\x6d\xf3\xc6\x47\xb6\x0d\x0d\xfe\
\xe6\x99\x72\xb9\xef\xef\x0f\x1d\xfe\x3f\xb5\x20\x38\x4e\x44\x16\
\x00\xbe\xfa\x7e\xbb\x40\x14\x06\x28\xf4\xf4\x63\xe7\x17\xbe\x82\
\xa0\x51\xc1\x5f\x7f\xeb\xeb\x66\x6a\xfc\x70\xa5\x3e\x3b\x71\x3a\
\x98\xd8\xf7\x9a\x93\xed\xed\xcd\x98\x30\x24\x22\x89\x0c\x2b\x22\
\x90\x4b\xc4\x22\x42\x10\x16\x21\x56\x7e\xb6\xd8\x4d\xa9\xfe\x11\
\x23\xae\xab\x84\x71\x09\x49\x0b\xc5\x4a\x54\x0c\xea\xad\x86\x1d\
\x62\xdb\xf3\xf9\xad\x9b\x1e\xdc\x50\x2c\xde\x80\x30\x84\x35\x06\
\x30\x11\xa0\x14\x7c\xcf\x53\xf5\x28\x92\xef\xef\x3f\x70\xea\x89\
\xc3\x47\x7e\xf8\xeb\x9b\x37\x3a\xbf\xba\x65\xcb\x1f\xdd\xbd\x72\
\xe5\x83\xaf\x4d\x9f\x4b\x7f\x63\xf7\xf3\xdf\x7d\x76\xfc\xe4\x3e\
\x16\xb1\x1f\x8c\x10\x12\x01\x47\x6d\x27\x6a\xd6\xd3\x95\xb9\x73\
\xee\xd8\xe6\x6d\xb8\xf7\xd3\x5f\xa4\xdd\x4f\x7c\xd7\x0f\x9b\xb5\
\x13\xd3\xaf\x3d\xfd\x03\xc7\xf3\x5d\x16\x66\x12\x02\xe8\x62\x86\
\x13\x20\xc6\x1a\x52\x24\xf9\xd1\x0d\x37\xdd\xea\xaf\xde\xd1\xd7\
\x56\x03\xae\x82\xc0\x43\x90\x54\x7e\xdc\x1b\x48\x18\x91\x09\x11\
\xd4\x2b\xb8\xc3\xe3\xb5\x9f\x5f\xb5\xb6\x2f\xeb\x7b\x79\x0e\xdb\
\xb1\x74\x21\x82\x22\x05\x13\x84\x38\x31\x77\xa1\x49\x2c\xd5\xdf\
\xbd\xe7\xae\x1d\x9f\xdc\xb2\x69\x43\x10\xd9\xc1\xaf\x3d\xf3\xdc\
\xc4\xb7\x5f\xdb\xf7\xf5\x73\xb5\xda\xf7\xb6\x0f\x0e\x96\x73\x9e\
\x8b\xb7\xd3\x84\x57\xc6\x01\xc2\x88\x5a\x75\xd7\x71\x9d\xcd\xc3\
\x5b\xee\xbc\xbb\xda\x8a\xc6\x2a\x9c\xce\x1c\x3d\x3d\x0d\x53\x58\
\x89\x9b\x76\x3d\xe6\xb5\x4a\x33\x6e\xab\x1d\xc0\x0a\x18\x04\x08\
\x83\x14\x04\xd4\xa1\x1f\x82\xb0\x35\x4a\x45\x61\xc6\xed\xea\x59\
\x13\xaa\x94\xab\x54\x04\x25\x17\x13\x40\x88\x40\x02\x84\x96\xd1\
\x6a\xd5\xb1\x2a\xaa\x78\x8f\x14\x64\x55\xc1\x51\x3e\x1b\x1b\x5f\
\x46\x0c\x28\x0d\x58\x0b\x11\xc1\x8a\x6c\x56\x3f\x7a\xe3\xc6\x0d\
\xe2\x79\xde\xd3\x47\x8e\xcf\x7d\x6b\xef\xcb\xdf\x67\xd0\xe3\xeb\
\x8b\xdd\x7b\x87\x73\x39\xdc\x3e\x32\x8c\xb4\xe3\xe0\xed\x54\xf1\
\xbb\x02\xc0\xd6\x42\x11\x15\xd7\xdc\xfc\xcb\x9f\x89\xba\xd6\x7e\
\xa9\xed\x74\x6d\x34\x11\x15\x8f\x57\x1a\x9a\xe7\xeb\x50\x9e\x27\
\x8e\x3f\x2a\xee\xc8\x28\xbb\x44\xe2\x48\xcc\xe3\x9d\x16\xa7\x93\
\xcc\x11\x91\xb8\xf1\x5b\xa6\x76\x14\x3a\x46\x2c\x39\x1c\x81\x84\
\x21\x50\xb0\xa4\x93\x8f\x2d\xb8\x55\x47\xa1\x36\x8b\xcf\xa7\x5a\
\xfa\xd6\x8c\xab\x61\x0c\x04\x0a\x50\x0a\x90\x44\x2f\x28\x86\x56\
\x1a\x43\x85\x7c\x6a\xba\x52\x91\x3f\xde\xfb\xf2\xab\x3f\x19\x3f\
\xf5\xa3\x76\x64\x76\xff\xa7\x7b\xee\x9c\xae\x06\xc1\x9a\x13\xa5\
\x45\xab\x88\x4a\xa1\xb5\x4d\xbc\x8d\x18\x7a\x37\x00\x28\x9b\xcb\
\xf7\x6e\xb8\xeb\xe1\x2f\x77\xdd\xf4\x89\xaf\xce\xb4\x9c\xe1\xa0\
\xda\x4c\x6e\x1a\x50\xca\x85\x8d\x2c\x85\x51\x0b\x00\x69\x82\x85\
\x58\xc6\xc5\xe1\x44\xa0\x09\x80\xf0\xc5\x14\x14\x40\x13\xc1\x51\
\x2a\x51\x82\xb1\x2c\x12\x36\x48\x85\x75\xb4\x23\xc6\xea\xea\x19\
\x6c\x0e\xcf\x63\x57\x6f\x16\x0e\xb9\xb0\x96\x21\x14\x07\x4e\xcb\
\x40\x10\x11\xd8\x50\x90\x02\xe4\xe1\x35\xab\x46\x6e\x1f\x18\x78\
\x68\x20\x9b\xbd\x6f\x28\x9f\xcb\xd7\xa3\xc8\xeb\xcf\x64\xdf\x7c\
\x6e\x62\xf2\xff\x06\xc6\xec\x26\x82\xb9\x5a\x00\xc8\x75\x9c\xae\
\x9b\xef\x79\xf0\x9f\x65\xb7\xfc\xca\x57\xa6\xdb\xfe\xb0\x63\x9a\
\x48\xbb\x3a\xce\x71\x96\x44\xbd\xd1\xb2\xea\x55\xe8\xf4\xb4\xe5\
\x00\x24\xf7\x1b\x5f\xc5\x02\x92\x18\x09\x66\x05\xcb\x21\x34\x1b\
\xac\x6b\xcd\xa1\xb9\x70\x16\x69\xc7\xc5\x4d\x8d\xb3\xd8\xd5\xe3\
\x61\xd0\xd1\xb0\x9d\xd4\x57\x6a\xa9\x6d\x22\xd1\x13\x1d\x10\x7a\
\x7d\x4f\xdd\xbf\x7e\xdd\x30\x0c\x0f\x1f\x9d\x9b\xc7\x9b\xf3\x17\
\xe6\x0f\x5e\x98\x3f\xf4\xd2\xf4\xcc\xe1\x43\x73\xf3\xe5\xc8\x5a\
\x26\xd0\xd5\x95\x00\x01\x7e\xae\xd8\xb7\xbe\x30\x76\xdb\x23\x0b\
\x92\x5e\x6d\x4d\x84\xb4\xe3\x00\x1c\x2b\x6b\xb9\x44\xba\xe0\x17\
\x32\x6c\xd9\x82\x43\x2e\xf3\xa9\x80\xc0\x26\x84\x5f\x99\x06\x69\
\x8d\x9d\xd1\x24\xf6\x94\xcf\xe2\xae\xae\x14\x36\x65\x04\x63\x19\
\x3f\xbe\xce\xda\x44\x34\x74\xe4\xa1\xc4\x19\xa5\x62\x09\xad\x04\
\x30\xc2\x68\xd6\x02\x84\x22\xb6\xd4\x6e\x96\x9f\x3e\x79\xfa\x47\
\x7f\x75\xf8\xd8\x1f\xd7\xc2\x70\x1c\x40\x00\x80\xaf\xb6\x0b\x10\
\x29\x95\x1f\x58\xb9\x66\x5b\xc3\xeb\xdd\x6e\x2c\xe0\x83\x21\x42\
\x1f\xc8\xe4\xc4\x6c\x41\x36\x42\xb1\x39\x87\xf4\xc2\x09\x74\xa5\
\x73\x58\x8b\x39\xb4\x9c\x08\x77\xa5\x7d\xac\xcd\x66\xa0\x01\x58\
\x13\x01\xa4\x63\x00\x44\x62\xbd\x40\x1d\x15\x25\x00\x69\x28\x02\
\x5a\x61\x88\xc3\xad\x05\x1c\xa8\x57\x2e\xec\x3e\x3c\xfd\x37\x2f\
\x4e\xce\xfc\xb0\x16\x86\x87\xf0\x36\xe2\xe7\x4a\x00\x70\x94\x52\
\xc5\x9e\x81\xd1\x4d\xd0\xa9\x5e\x81\x02\xc8\x01\x49\x3c\x0c\xf1\
\xfb\x89\x5e\x0c\xc2\x28\x40\xc6\xb4\x70\x5f\x73\x02\xaf\xd4\x4b\
\xf8\x98\xdb\xc0\x74\xb3\x82\x7b\x8b\x39\x8c\xa5\x7d\x68\x10\x2c\
\x33\x84\xe3\xf8\xe3\x80\x55\x67\x38\x59\xca\x42\x28\xc0\x0a\xc3\
\x05\x61\x63\xaa\x1b\x2b\xdc\x7c\xcf\x47\xb6\xf5\xae\x19\xcb\xe5\
\xdb\xff\x6b\xff\x41\x54\x82\x10\xef\x15\x00\x0f\xa4\xba\xfc\xae\
\x81\xd5\x56\xa7\x7c\x61\x8e\x09\x98\x71\x49\x25\x5d\xfd\xae\x22\
\xc3\xda\x10\x61\xd0\xc0\x60\x7b\x01\xb7\xb6\x66\x30\x6e\x5b\xb8\
\x99\x18\x26\xe5\x62\xd4\x77\xe0\x08\xc3\xd8\x24\xe8\xce\x14\xa7\
\x54\x32\x2a\x49\x72\x13\x2a\x5e\x5b\x89\x5b\xa7\x22\x85\x6e\x72\
\x50\xcc\x64\xfc\xd5\xf9\xee\x9d\xe3\x8b\x8b\xe2\x2a\xfd\x6f\x01\
\x9c\x7d\xaf\x00\xf8\x00\x75\x49\xaa\x38\x68\x9c\x8c\x43\x91\x81\
\x12\xb5\x34\xc2\x5e\x91\x76\x00\x81\x99\x10\xeb\x21\xc0\x0a\x00\
\x66\xb4\x03\x03\xdd\x6a\xe0\xb6\xe6\x34\x66\xaa\x65\x7c\x3c\xeb\
\x62\xa5\xa3\x90\x4b\x39\xd0\x10\x18\x6b\x93\x34\x4f\xd2\xbd\x43\
\x76\x49\xda\x13\x03\xd0\x49\x59\x58\x59\x22\x47\x72\x1c\x34\x5a\
\x2d\xfc\x7c\x7a\xa6\xf4\xf7\x27\x4f\x9d\x6e\x44\x51\xe3\x3d\x9b\
\xa2\x00\x5c\x10\xb2\x46\xfb\x5d\x4c\x1a\x0a\x11\x00\x06\x83\xa0\
\x92\xc1\x55\x2e\x1b\x34\x60\x95\x01\x58\x41\xb1\x0b\x31\x16\x21\
\x2c\x08\x0c\x21\xc0\x46\x01\x1a\x8d\xba\xf4\x37\x17\x71\x6f\x34\
\x4f\x47\xda\x01\x1e\xe8\x4a\xa3\x5b\x5f\xd4\x1c\x94\x04\xb4\x54\
\xeb\x9d\xfa\x4f\xce\xa2\x14\x60\x4c\x72\x9d\x02\x98\x63\x10\x5c\
\x17\x73\x8d\x46\xe3\xcf\xde\x78\xf3\xcf\x7e\x7a\x66\xea\xf1\x90\
\xb9\x4c\xef\x03\x00\x07\x02\x5f\x84\x7d\x4d\x1c\x87\x2e\x04\x21\
\x15\x87\xce\xcb\x79\x3f\x56\x6f\x4c\x0a\x36\xb9\x6f\x15\xd4\x2b\
\x6e\x6b\xea\x4c\xbf\x94\xe6\x7c\x1d\x44\x49\xdb\x50\x95\x7a\xc3\
\xc9\x2e\xce\x67\x1f\x8c\x9a\xc3\xdb\x53\x66\xc5\x8d\x3d\x19\xdd\
\xab\x00\xb1\x36\x71\x86\x12\xed\xbc\x04\x02\xc5\x41\x92\xc4\xe7\
\x4e\x3f\xed\x80\xa2\xe4\x62\x26\x44\x11\x46\xd3\xa9\xcc\xc7\x56\
\x0c\xad\x78\x61\x66\x36\x0c\x82\x40\xf4\x15\xb8\xdb\xce\x3b\xec\
\x17\xb8\x60\xa8\xb8\x81\xd3\xa5\xc9\x9f\xdc\x80\x12\x01\x13\xc1\
\x40\x81\x59\x90\x62\x6b\xba\x82\xd9\x57\x1b\x27\x77\xff\x74\xf2\
\xe8\x6b\x13\x18\x29\xb8\xeb\xd6\x0d\x65\x48\x20\xed\x76\xe8\xb6\
\xe6\x2b\x59\x5d\x6f\xac\xbc\x3f\xd7\x35\xdc\x2d\x59\xa5\x5d\x05\
\xcb\x76\xa9\xb7\xc7\x01\x77\x7a\x3d\x81\x3a\xc1\x2b\xd5\x29\xf8\
\x24\x70\xb5\xe4\x17\x2c\xfd\x9c\x30\xea\x41\x40\x67\x6a\xf5\x6c\
\x68\xad\x77\xa5\xfd\xea\x9d\x95\xa0\x12\x4b\xa4\xa0\xe8\x2d\x7e\
\xcd\x32\xed\xce\x12\xaf\x60\x8f\x6b\xdb\x66\x6a\xff\xdf\x8d\xef\
\x7b\xea\xfb\x0f\xdf\x39\x92\xf9\xc6\x57\x76\x7e\x72\x64\xa0\x7d\
\xbb\xaf\x6d\x1a\x0c\x5b\x5e\x0c\xe8\xe8\x54\xda\x59\x98\xac\xf9\
\x9b\xf7\x73\x2f\x45\x4c\x16\x72\x71\x85\x25\x49\xe5\xa5\xf7\x84\
\x98\x76\x28\x16\x3d\xaa\x23\x85\x6d\x9c\x81\x4a\x25\x02\x23\xce\
\x02\x89\x42\x14\x1c\x8d\xbb\x07\x7a\x6f\xda\x73\xbe\xb0\x69\xae\
\x1d\x9c\x77\x88\xde\xb3\x2d\x2e\x00\xac\x16\x1b\x18\xb6\x89\x81\
\x41\x97\x71\x6e\x08\x86\x19\x05\x07\xac\xe6\x8e\x3f\x65\xa6\x5f\
\xfe\xfe\xef\x7d\x79\xeb\xb6\xcf\x3d\x9c\xff\x57\xc5\xf4\xb9\x31\
\x40\x53\xdc\x89\x2d\xb2\x14\xa2\x54\x6b\x40\x15\xda\x31\xc1\x59\
\x8a\x65\xb0\xea\x80\xb0\x3c\xad\xd5\x45\xf1\x43\xb4\xb4\xda\x4b\
\x40\x88\x4d\x9a\x71\x9c\x19\x4a\x69\xc0\x32\xa6\x83\xba\x1c\x2c\
\x97\xa7\xce\x34\x1a\xe7\xcb\x41\xec\x02\x51\xe2\x2f\x74\xb4\xea\
\x95\x02\x60\x01\x09\x75\x58\xad\x58\x0e\xc4\x2a\x87\x14\x31\x88\
\x39\x76\x6a\x90\xa0\x0e\x8b\x94\x97\x42\x34\x37\x7d\x3c\x3a\x73\
\xe0\xef\x3e\xff\x89\x35\x37\x7e\xe9\xd7\xbb\xbe\x9a\xf5\xa6\x86\
\xd0\x0a\x21\xec\x80\xe0\x00\x42\x30\x86\x80\x08\x08\x95\xc2\xc9\
\x3e\x8b\xdc\x59\x42\x26\x52\xb0\x4e\x4c\x1c\xa4\xe8\x62\x9d\x77\
\x6a\x5b\x12\xf5\xb7\xac\x34\x96\x40\x60\x59\x5a\x04\x4d\x0a\x00\
\xe3\x1f\xe7\x2e\x9c\xff\xcb\xf1\xd3\x7f\x3a\xdf\x0a\x4e\x00\x40\
\x97\xeb\xc2\x08\x77\x28\x0b\x6d\x6b\xaf\x18\x00\x03\x91\x46\x58\
\x9b\x9b\x23\x1b\x44\xa2\x52\x1e\x49\xb0\x0c\x42\x02\x60\x61\x84\
\x91\xd6\x0e\x47\x51\x75\x5f\x75\xee\x64\x63\x75\xcf\x86\xfb\xb2\
\x19\x77\x08\x55\x0b\x46\x1a\x04\x9b\x94\x8b\x82\xef\x6b\x14\x73\
\x3e\x2a\x79\x83\xa9\xb1\x00\x7e\x33\xc0\x0d\x0b\x2e\x32\x46\x01\
\x4a\x20\x12\x9f\x69\x09\x84\x64\xae\x10\x4a\x40\x58\x36\x0b\x08\
\x27\xfc\xa0\x62\x2c\x8c\x45\x09\x11\x0e\x53\x75\x1e\x39\x7d\xb0\
\xdf\xf8\x06\x2c\x78\xf2\xfe\xbb\xf1\xdc\xcc\x05\x2c\x04\x21\x34\
\x11\xfe\xf4\xc4\xe9\x2b\x06\x20\x14\xe1\x7a\xe5\xc2\xd4\x6c\xcf\
\x0d\xed\xb6\x4a\x15\x3d\x6b\x09\x8a\x3a\xfe\x5d\x4c\x8c\xcc\x0e\
\xc2\xb0\x55\xee\xf6\x82\x53\x6b\x6f\xe8\x1e\x58\xd1\x13\xae\x87\
\xad\x27\xa9\xa9\x97\x4c\x14\x90\x20\xe5\x2b\x0c\xf5\xfa\x88\x8c\
\x01\x48\x70\x4c\x05\x98\x3c\xd1\xc6\x47\xa7\x3c\xf4\x5a\x0d\x16\
\x01\x44\x41\x92\xd5\x27\xc1\xb2\x4c\xa0\xe4\x6b\x0d\x90\x8d\x8d\
\xe8\x0e\x3f\x92\xc6\xa9\x4a\x19\x27\xd7\x18\x64\x86\xfa\x16\x3e\
\xb1\x2a\x1d\xfd\xda\x6c\x0a\x5c\x17\x74\xb9\x2e\x5a\xd6\x22\x64\
\x86\x7e\x1b\x6b\xfc\x6d\x01\x60\xe6\xea\x85\xa9\xc9\x99\xbe\x76\
\x79\x81\xd2\x43\x05\xcb\x02\x57\x31\x04\x71\x3a\x02\x04\xad\x14\
\xc0\xcd\xc8\x57\x81\x5d\x33\x52\x18\xe8\xe9\x73\xf2\x80\x49\x8c\
\x0b\x42\xcc\x62\x71\x16\x68\x4d\xe8\xce\x3b\x20\x95\x81\x76\x62\
\x65\xd1\x8c\x08\x95\x92\x41\xb1\x92\x68\x0b\x49\x98\x9e\x14\x24\
\x59\x7d\x52\x89\x00\x4b\x4a\x83\x48\x01\x0c\x04\x62\x41\xe4\xe0\
\x42\xab\x8d\xbd\xee\x19\x8c\xdd\xbb\x92\xb7\x64\x6f\x7c\xe3\xc4\
\x7f\x7e\x6e\x71\xd1\x33\x1e\xa5\xfd\x14\x8b\x68\x45\x14\x2a\xa2\
\xa6\x5c\xa5\x1f\x60\x44\xa4\xba\x38\x77\x61\x4a\xe6\x27\x4f\xb9\
\x85\x35\xab\x5a\xca\xd3\x56\x45\x20\x30\xd8\x12\x44\x34\x94\x10\
\x94\x08\x59\x13\xa4\x94\x66\x47\x7b\xae\x03\xc4\x7b\x7c\x4b\xa4\
\xb5\x8c\x56\x95\x43\xf0\x7c\x17\xb9\x30\xc4\xf0\xd9\x08\xfe\x69\
\x8b\x9e\xba\x2c\xb9\x3b\x50\x71\x16\xc4\x93\x35\xc7\x19\x21\x09\
\x3f\x30\xc5\x03\x12\x04\x13\xa6\x89\x09\x15\x80\xd2\x82\x66\x3e\
\x80\xe9\x31\x80\x57\x3c\xdf\x3c\xe7\x1d\xe9\xd2\xa9\xb5\x9e\xa3\
\x6f\x49\xbb\xee\x46\x02\xb2\x95\x28\xda\x5d\x0e\xa3\x1f\x0e\xa5\
\xfc\xab\xf2\x03\x0c\x80\xaa\x8d\xc2\xa9\xa9\x83\x2f\xbc\xbe\xb6\
\x67\xf5\xc6\xa8\x6f\xcb\x68\x33\xd2\x48\x89\x89\xc7\x51\x08\x22\
\xa5\x01\xeb\xa1\x1d\x5a\x15\x85\xa1\x13\xeb\x73\x4a\x76\x7a\x96\
\xd1\x05\x03\xa1\x15\x54\x9a\x11\x1a\x87\xab\x70\x9f\xae\x60\xd3\
\xb4\x85\x17\x12\x48\xab\x38\x58\xc6\x45\xe9\x4b\x7c\xd1\x5b\x10\
\x81\x48\x7c\x1d\x09\x61\xa2\x19\xe0\x49\xa7\x04\x67\xbd\x60\xd3\
\x2a\x17\xab\x73\x11\xd6\x39\xfd\xd2\x7e\x5d\x95\x36\x1c\x3a\xbe\
\xf3\xc6\xfe\xc2\xef\x90\x52\x2b\xd6\xe4\x73\x5d\x0b\x61\xc4\x67\
\x1a\xad\xf0\xc0\x62\xe5\xa7\xbf\x33\xb6\xb6\xaa\x2e\x23\x8c\xde\
\xa9\x0d\x36\x58\x78\xea\xec\xa9\xc3\xaf\x77\xf7\x3d\xb7\xba\x7b\
\x47\xd7\x03\x6d\x6f\xa4\xc8\xa1\x86\x25\x80\x15\x83\x85\x60\x45\
\x79\x4a\x39\x8e\x88\x12\xbe\xdc\x98\x28\x84\xb6\xb1\x98\xa9\x84\
\xa8\xee\x5f\xc4\xc0\x53\x25\x74\x4d\x1b\xb8\x5a\x03\xae\x02\x93\
\xc4\x76\x17\x49\x2c\xb4\x97\xc6\xdd\x8e\x43\x1a\xaf\xbe\x02\xd0\
\x8a\x18\x25\x13\x60\x7d\xda\xc7\xda\x86\x87\x81\x71\x0f\xae\x21\
\xf8\x26\x0d\x5b\xab\x8d\x79\x81\xd9\xe2\xe5\x33\x14\x29\x0d\x57\
\x11\x9a\x44\xfa\xe1\xc1\xbe\xfb\x32\x4a\x3d\xef\x2a\xda\x03\xa0\
\xfc\xd6\x61\xf6\x9d\x84\x50\x08\x60\x36\x0a\xa3\xc3\x47\x5e\xdb\
\x9d\x59\x6b\x82\x60\x68\xeb\xbd\xb7\x49\x7e\x78\x30\x22\xcf\x65\
\x56\x92\xd6\x9e\xf8\x4e\x7b\x96\x4c\xab\x61\xad\xcd\x81\xd4\xa5\
\xc3\x12\x11\xc2\xc8\x62\xb6\x12\x62\xf6\x60\x05\xfd\x3f\x5e\x40\
\xf7\xd9\x00\xda\x77\x60\xdd\x78\x3e\xa0\xa4\x9d\x81\xd4\x32\x19\
\x9c\xb4\x40\xe2\x25\xa5\xc7\x56\xa0\x84\xb0\xc9\xf7\xe1\x73\x06\
\xde\x8c\x86\x58\x05\x8e\x1f\x35\x20\xdf\x0f\xd3\xf0\x1c\x18\x16\
\x68\x30\xac\x08\x7a\x1c\x85\xcf\xae\x5c\xb1\xe5\x63\x03\xbd\xbf\
\xfb\xe7\x13\x53\xd9\x88\xf9\x09\x00\xed\xab\xf1\x04\xeb\x00\x4e\
\xb5\x5a\xed\xe8\xf8\x2b\xbb\xe7\xe7\x26\xc7\x0f\xf6\xae\x5c\x3b\
\x9a\x2f\x14\x73\xcc\x24\x5e\x36\xdf\x08\xb4\x7b\x7c\x66\xe2\xcd\
\xa9\x75\xdb\xf4\xfd\x9e\xe7\x6b\x70\x7b\x49\x4c\x73\xc4\x28\x35\
\x0c\x66\xa6\x5a\x70\xf6\x57\xd0\x3f\xdb\x42\x5a\x03\xb0\x36\x2e\
\x32\xad\x10\xb9\x0a\x76\x59\xef\x5f\xb2\xbc\x68\xb9\xe6\x8f\xc1\
\xd1\x4a\xa1\x20\x0a\x30\x02\x45\x0c\xb8\x00\xfc\x44\x38\x69\x0d\
\x10\xa0\x3a\xaa\x12\x0a\x50\x40\x46\x69\x57\x8b\xdc\xbd\x67\x6e\
\xe1\x67\x2d\x63\xf4\xd5\x9a\xa2\x0c\xa0\x02\x20\x34\x2c\xf3\x73\
\x33\x53\x6f\x96\x67\xa7\x32\x9e\xe7\x3a\x10\x08\x39\x4e\x5d\xa0\
\xcb\xc6\x98\x91\x3b\x37\x6f\xf7\x1c\x57\xc7\xfa\x34\x49\xe1\x76\
\xc0\x98\x29\x05\xb8\x70\xa1\x8d\x2d\xad\x00\x05\x3f\xc2\x7c\x49\
\xb0\xa0\x34\x82\xb4\x46\xce\x21\x0c\x85\x0c\xcf\x11\x18\xb9\x38\
\xda\xc6\x53\x5f\xdc\x0d\xa8\xc3\x0b\x2a\x1e\xc4\x22\x30\x98\x08\
\x2d\x01\x82\x08\x28\x78\x0e\x04\x0a\x27\xdb\x51\xb3\x62\x4d\xdd\
\x02\xd2\xb2\x6c\x1b\x2c\xa6\xc1\x12\x2e\x46\xa6\x76\xa6\xd9\x3a\
\xb9\x18\x44\xe3\x97\xeb\x84\xce\x15\x8d\xf6\x40\x13\x40\x0b\xc0\
\x9c\x61\x90\x69\x27\xdb\xe4\x41\x64\x01\x68\x52\xce\x70\xac\xe2\
\x2e\x85\xae\x19\x58\x94\xab\x11\xb8\x1c\x20\x33\xd3\xc0\xc9\xc5\
\x10\xfb\x7a\x53\x98\x1e\xf1\xd0\xea\x75\x51\xb0\x0e\x7e\x69\x32\
\xc0\xa6\x0b\x16\xbe\x62\x58\x47\x5d\x14\x3d\x12\xaf\xa0\x10\xc5\
\xa5\x20\x0a\x60\x82\xab\x35\x14\x69\x1c\xa8\x37\x16\x9f\x2c\x55\
\xf7\xa7\xb4\xb6\x2d\x2b\x99\x67\x16\x2a\x07\x67\xa3\x68\x42\x80\
\x90\x45\x22\x03\xb4\xac\xc8\x62\x9b\xf9\xfc\x50\xca\x3b\x1b\xb1\
\x54\x01\x6a\xbf\x9f\x9d\x21\x49\xba\xc3\x65\x76\xd0\xd5\xf2\x0d\
\x90\xc4\xf1\x15\xb4\x0d\xc3\x5a\x46\x57\x39\x44\xe5\x54\x13\x2f\
\xad\xce\xa2\xb8\x6b\x04\xb7\xae\x4a\xa1\xda\x0e\x51\x2a\x87\x38\
\x3a\x08\x44\x07\x5a\xd8\x3a\x63\xe1\xd9\x64\x07\x65\xe9\xf1\x81\
\xa4\x2c\x94\x82\xa3\x00\x57\x3b\x00\xc5\xbb\xd5\x62\x39\x3a\x5c\
\x6f\xfc\xd3\xcf\x17\x1b\xcf\xb4\x2c\x9b\x26\x73\x90\x90\x5c\x23\
\xa9\xf3\x20\x39\x87\x9e\x22\x14\x1c\xe7\x1a\x3e\x23\x24\x02\xcb\
\x2c\xcc\x76\xa9\x85\x31\x18\x96\x23\xa4\x3d\x82\x1a\xf0\x31\xb3\
\xb1\x80\x15\x9f\x18\xc2\x6d\xf7\xf5\xa1\xdb\xd5\x28\x97\x0c\x26\
\xfc\x06\x4e\x7b\xc0\x29\x47\xa1\xf7\xd9\x06\xaf\xaa\x5a\x22\x51\
\xb1\xd5\xdb\xe1\x04\x22\xb8\x04\x08\x0b\xc6\x1b\x91\x5d\xb4\x6c\
\x4f\xb7\xc3\xe6\xd1\x76\xb4\x50\x37\xbc\xa2\x6a\x4c\x2a\x12\x4c\
\x00\x48\xc7\x4e\x16\x5a\x9d\x61\xae\xc3\xf8\xf3\x41\x84\x2e\xc7\
\xbd\x76\x00\x10\x29\xb8\xae\x22\xa5\x39\xfe\xbb\x4a\x43\x98\xe0\
\xbb\x0a\x03\x79\x0f\x74\x73\x0f\xcc\xa6\x2e\x0c\x8e\x66\xd0\xe3\
\x6b\x00\x84\x9e\x1e\x0d\xc3\x8c\x6a\x33\xc2\x6c\x57\x8e\x43\xd3\
\x0c\xc4\x98\x14\x91\x8e\xdd\x67\x01\x54\xb2\x81\xe2\x10\x63\x4f\
\x3d\x68\x7d\x7d\x66\xe1\xc4\xbc\xe1\x92\x15\x69\x9e\x8f\xec\xe9\
\x90\xa5\x24\xc0\x18\x80\x3c\x80\x2a\x80\x5a\xa2\xc3\x53\x09\x81\
\x57\x93\xb3\xcc\x06\xc1\x35\x03\x80\xac\x65\x04\x11\x59\x86\x0f\
\xa0\x01\x11\x03\xa5\x7d\x14\x72\x19\x64\xdc\x08\x8e\x4b\x70\xd2\
\x1a\x5e\xe2\x0b\x82\x04\x26\x12\x34\xeb\x06\xd5\x45\xc1\x62\x49\
\xd9\x54\x3b\x84\xe2\x28\x0e\x9e\x63\x0f\xc0\x87\x02\x5c\xc1\xf9\
\x76\x84\xc7\x67\xcb\x67\x9e\xad\x34\xf7\x02\x98\x5d\xc6\x4b\x11\
\xe2\x5e\x30\x08\x20\x03\x20\x97\x14\x4f\x2d\x29\x01\xdb\xe9\xcb\
\x75\x63\xaf\x6a\x1c\xbe\xca\x0a\x30\xc1\xa1\x13\xe5\xd9\x89\x29\
\xbf\x3c\x32\x94\x2f\x10\xcd\x01\x70\x90\xf2\x1c\x90\x93\x6c\x69\
\xd9\x78\x7e\x10\x01\x4a\x8b\x21\x8e\x9e\x6d\xe2\xc8\x54\x13\x27\
\x66\x5b\x68\x9f\xab\xe8\x87\xa2\x48\x69\x66\x32\x6c\xa0\x48\xc3\
\x12\xe1\x65\x58\x2c\x34\xd1\x7e\xb1\xd2\x9a\xfd\x87\x5a\x6b\x7f\
\xe2\xf2\xda\x64\xd2\x4a\x25\x29\xcf\x00\xbc\x04\x08\x93\xf0\xc0\
\x54\x02\x80\xe0\x5d\x5c\xec\x0f\x02\x00\x0b\x48\xed\xcd\x23\x67\
\xc6\xff\xe6\xc9\x89\x37\x36\xae\xdd\x30\xd0\xd7\xd7\x4e\xeb\x46\
\x09\x62\x7d\x10\x39\x31\xb3\x2b\x02\x8c\x41\xb5\x1e\xe1\xf4\xb9\
\x36\xce\x9c\x6d\xa0\x31\xd9\x44\x6e\xa6\x8e\x8d\xb3\x81\xea\x32\
\x11\x1c\x06\x9c\xd0\x00\x9a\x71\x5c\x6b\x7c\xd3\xd1\xb5\x97\x2f\
\x34\xfe\xb1\xbe\x58\x3f\x59\xb3\x3c\x97\x04\xaf\x92\x40\xa3\x65\
\x71\x85\x49\xe0\x67\x93\xb3\x06\x90\x5d\xf6\x59\x74\x2d\x1f\x94\
\x64\x00\xe5\xa0\xd5\x38\xf1\x17\x7f\xfb\xf2\x3f\xa4\xb3\xbe\xff\
\x5b\x9f\xe9\xbf\x7d\x6c\x84\xba\xc9\x8d\x00\x63\x00\x11\xd4\xca\
\x21\x16\xca\x6d\xcc\x56\x22\x4c\xcf\x85\xc8\x9c\xaa\xe1\xa1\x37\
\xca\xe8\x9d\x6a\x22\xb4\x80\x4f\x84\x53\x4a\x41\x79\x1a\x21\x0b\
\xfe\xbc\x6d\x1a\x2f\x19\xde\x77\xae\xd2\xdc\x07\xcb\xf5\x64\x85\
\xd3\x49\xf0\xed\x84\xec\xa2\x04\x94\x06\x80\x85\xe4\x7b\xa3\x00\
\x56\x27\x40\x05\x00\xe6\x00\xcc\x27\xd7\xfc\x82\x23\x42\x97\xdb\
\x37\x7f\x0f\xcf\x0a\x2b\x00\xbd\x00\x36\x64\xb3\x99\x9b\x3e\x7e\
\xef\xf6\x3b\xbe\xb0\x6b\xeb\xad\xbf\xb4\x5d\xaf\xee\xce\xd4\x73\
\xf5\x4a\x9d\x4e\x9d\x2e\x63\xa1\xd2\x46\xa3\x69\xa0\xa6\xeb\x18\
\xd9\x7d\x1e\xdb\x66\x5b\x08\x3d\x07\xa7\x84\x30\xaf\x1d\xfc\xcc\
\xd1\x28\xe7\xfc\xb0\x31\x17\x2c\xee\x2e\x07\x07\xe7\x5b\xc1\x3e\
\x6b\x6d\x65\x99\x34\x6f\x27\x80\x9b\x24\xa0\xc5\x24\x48\xb3\xec\
\xac\x96\x0d\x74\x61\x02\x4a\x35\xc9\x8c\xe8\xad\xf1\x7e\x50\x00\
\x74\x40\xe8\x06\x30\xea\x38\xce\xba\xfe\xfe\xe2\xfa\x8f\xee\xd8\
\xb0\x61\xc3\x58\xff\xea\x66\xbd\x34\xaa\xb8\x51\xd4\x2a\xf0\x82\
\x72\xc3\x19\x1a\x2f\xbb\xa3\x93\xb5\xd4\x94\x52\xd1\xe4\x60\x36\
\x5c\xdb\xb0\xf4\x22\xfc\xe0\x58\x48\xd3\xf3\x41\x78\x74\xb1\x54\
\x9f\x8c\x98\xcf\x41\xe4\xfc\xb2\x14\x5e\x48\x82\xb0\xcb\x02\x0e\
\x93\x97\x2c\xb3\xfc\x3a\x7b\xb1\x1d\xa0\xec\xb2\xf7\x72\x2d\x01\
\xe8\xc8\xa0\x14\x80\x22\x80\x3e\xc7\x71\xfa\x1c\x47\xf7\x88\x70\
\x97\x22\xe4\x88\xa4\x8b\x58\x8a\x64\x38\xd7\x03\xe9\x59\x10\x6a\
\x44\x8a\x4a\x59\x11\x2b\xa0\x56\x55\xf0\xa6\x88\x4c\x89\x48\x25\
\x59\xb5\x46\x12\xc4\x5b\x03\xe1\xcb\x6e\x3a\xff\xa2\x70\xfb\x85\
\x6b\xae\x35\x00\x9d\x43\x27\x35\xeb\x27\x2f\x2f\x79\xe5\x93\x3a\
\x96\x65\x41\xd8\xa4\x57\x37\x92\xd6\x16\x2e\x13\x31\xcb\xaf\x7b\
\x6f\xdb\x91\x97\x79\xa2\xfd\xff\x07\x00\x97\xcb\x0c\x95\x90\xae\
\x5e\xb6\x8a\x1d\xd1\x6b\x96\x11\xd4\x35\xfd\x4f\xce\x2b\x02\xe0\
\xc3\x74\x5c\xff\x9f\xa1\xeb\x00\x5c\x07\xe0\x3a\x00\x1f\xea\xe3\
\xff\x0d\x00\x93\xa3\x64\x7b\xa8\xd9\x2b\xdb\x00\x00\x00\x00\x49\
\x45\x4e\x44\xae\x42\x60\x82\
"

qt_resource_name = "\
\x00\x0b\
\x0b\x55\x81\x83\
\x00\x65\
\x00\x61\x00\x67\x00\x6c\x00\x65\x00\x69\x00\x6d\x00\x61\x00\x67\x00\x65\x00\x73\
\x00\x0b\
\x0c\xae\xab\x07\
\x00\x65\
\x00\x61\x00\x67\x00\x6c\x00\x65\x00\x70\x00\x79\x00\x2e\x00\x70\x00\x6e\x00\x67\
"

qt_resource_struct = "\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02\
\x00\x00\x00\x1c\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

if qt_imported:
    qInitResources()

    
