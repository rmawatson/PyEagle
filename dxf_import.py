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
from dxfgrabber import *
from dxfgrabber.entities import *
import threading
import Eaglepy


class Line(object):
    def __init__(self,p1,p2):
        self.points = [p1,p2]

    def draw(self,color=(1.0,1.0,1.0,1.0)):

        glBegin(GL_LINES)
        glColor4f(*color)
        glVertex2f(self.points[0].x,self.points[0].y)
        glVertex2f(self.points[1].x,self.points[1].y)
        glEnd()

    def normalized(self):
        return Line(self.points[0],self.points[0] + (self.points[1] - self.points[0]).normalized())

    def toLength(self,value):
        line = self.normalized()
        line.points[0] -= self.points[0]
        line.points[1] -= self.points[0]
        
        line *= value
        
        return Line(self.points[0],line.points[1] + self.points[0])

    def rotate(self,theta):
        return Line(self.points[0],self.points[0] + Point(
                  (self.points[1] - self.points[0]).x * math.cos(theta) - (self.points[1] - self.points[0]).y * math.sin(theta),
                  (self.points[1] - self.points[0]).x * math.sin(theta) + (self.points[1] - self.points[0]).y * math.cos(theta)
                    ))
                    
    
    def asScr(self,wirewidth):
    
        point1Str = str(self.points[0].x) + " " + str(self.points[0].y)
        point2Str = str(self.points[1].x) + " " + str(self.points[1].y)
        
        return "WIRE " + str(wirewidth) + " (" + point1Str + ") (" + point2Str + ");"
    
    def __mul__(self, value):
            return Line(self.points[0]*value,self.points[1]*value)

class Point(object):
    def __init__(self,x,y):
        self.x = x
        self.y = y
        
    def draw( self,color=(1.0,1.0,1.0,1.0) ):
        glPointSize(6)
        glBegin(GL_POINTS)
        glColor4f(*color)
        glVertex2f(self.x, self.y)
        glEnd()
        
        
    def __eq__(self,other):
        return (self.x == other.x) & (self.y == other.y)

    def __mul__(self, value):
            return Point(self.x*value,self.y*value)
            
    def __rmul__(self, value):
            return self.__mul__(value)

    def __add__(self,other):
            return Point(self.x+other.x,self.y+other.y)

    def __sub__(self,other):
            return Point(self.x-other.x,self.y-other.y)

    def __div__(self,value):
            return Point(self.x/value,self.y/value)

    def interpolate(self,other,value):
            p = Point(self.x,self.y)
            return p + value*(other-self)
            
    def distance(self,other):
            return abs(math.sqrt(math.pow(other.x - self.x,2) + math.pow(other.y - self.y,2)))


        

    def length(self):
            return abs(sqrt(self.x*self.x + self.y*self.y))


    def normalized(self):
            length = self.length()
            return Point(self.x/length,self.y/length)
            
    def __repr__(self):
        return str(self)
        
    def __str__(self):
        
        return "(" + str(self.x) + ", " + str(self.y) + ")"
            
    def rotate(self,theta,around=None):

            if not around:
                around = Point(0,0)

            return Point(
                      (self - around).x * math.cos(theta) - (self - around).y * math.sin(theta),
                      (self - around).x * math.sin(theta) + (self - around).y * math.cos(theta)
                        )
                    
class BezierCurve(object):


    def solveQuadratic(self,a,b,c):

            result =  math.pow(b,2)- 4*a*c
            if result < 0+sys.float_info.epsilon:
                    return ()
            
            sqroot = math.sqrt(   math.pow(b,2) - 4*a*c)
            return (
                    (-b-sqroot)/(2*a),
                    (-b+sqroot)/(2*a)
                    )

    @classmethod
    def Construct(cls,p1,p2,p3,p4):
        
        
        COLINEAR_VALUE = 0.0001
        #Check for colinear

        if  (p1 == p2 and p3 == p4) or (abs((p1.x*(p2.y-p4.y) + p2.x *(p4.y-p1.y) + p4.x*(p1.y-p2.y))) < COLINEAR_VALUE and \
            abs((p1.x*(p3.y-p4.y) + p3.x *(p4.y-p1.y) + p4.x*(p1.y-p3.y))) < COLINEAR_VALUE):
            return Line(p1,p4)
        elif p1 == p2:
            return QuadraticBezierCurve(p2,p3,p4)
        elif p3 == p4:
            return QuadraticBezierCurve(p1,p2,p3)
        else:
            return CubicBezierCurve(p1,p2,p3,p4)
    
    
    def draw(self,color=(1.0,1.0,1.0,1.0)):
    
            glBegin(GL_LINE_STRIP)
            for i in range(101):
                glColor4f(*color)
                point = self.evaluate(i/100.0)
                glVertex2f(point.x, point.y)
            glEnd()
    
    

        
    

                
class QuadraticBezierCurve(BezierCurve):


        def __init__(self,p1,p2,p3):
                self.points = [p1,p2,p3]


        def evaluate(self,value):
                return (1-value)*((1-value)*self.points[0] +\
                    value*self.points[1]) + \
                    value*((1-value)*self.points[1]+ value*self.points[2])
                    
        def inflection(self):    
            return []
        


        def moveTo(self,point):
        
            moveBy = (self.points[0] - point )
            
            
            transformedPoints = []
            for point in self.points:
                transformedPoints.append(point - moveBy)
            
            return QuadraticBezierCurve(*transformedPoints)
        
    
        def rotate(self,theta,around=None):
    
            if not around:
                around = self.points[0]
                
            rotatedPoints = []
            for point in self.points:
                rotatedPoints.append(point.rotate(theta,around))
            
            
            return QuadraticBezierCurve(*rotatedPoints)
            
            
        def split(self,value):
            
                p1,p2,p3 = self.points
                
                
                r1 = p1
                r2 = p1+value*(p2-p1)
                r3 = self.evaluate(value)

                s1 = r3
                s3 = p3
                s2 = p3 + (1-value)*(p2-p3)
                    
                return (BezierCurve.Construct(r1,r2,r3,r3),BezierCurve.Construct(s1,s2,s3,s3))

        
        def findRoots(self,a,b,c):

            result = self.solveQuadratic((a-2*b+c),(2*b-2*a),a)
            if not result:
                return []
            return [root for root in result if root >= 0 and root <= 1]
        
        def intersect(self,line,onLine=False):

            
            theta  = -((math.pi/2)-atan2(
            (line.points[1] - line.points[0]).x,
            (line.points[1] - line.points[0]).y
            ))

            rotatedLine = Line(Point(0,0),line.points[1].rotate(theta,line.points[0]) )

            rotatedBezier = QuadraticBezierCurve( self.points[0].rotate(theta,line.points[0]),
                                                  self.points[1].rotate(theta,line.points[0]),
                                                  self.points[2].rotate(theta,line.points[0]) )

            
            
            roots = rotatedBezier.findRoots(*[p.y for p in rotatedBezier.points])
    
            if (onLine):
                for root in list(roots):
                    point = rotatedBezier.evaluate(root)
                    
                    if min(rotatedLine.points[0].x-sys.float_info.epsilon,rotatedLine.points[1].x-sys.float_info.epsilon) > point.x or max(rotatedLine.points[0].x+sys.float_info.epsilon,rotatedLine.points[1].x+sys.float_info.epsilon) < point.x:
                        roots.remove(root)
                        
                    elif min(rotatedLine.points[0].y-sys.float_info.epsilon,rotatedLine.points[1].y-sys.float_info.epsilon) > point.y or max(rotatedLine.points[0].y+sys.float_info.epsilon,rotatedLine.points[1].y+sys.float_info.epsilon) < point.y:
                        roots.remove(root)
                
                
            result = []
            for root in roots:
                result.append((root,self.evaluate(root),rotatedBezier.evaluate(root)))
                
            result.sort(key=lambda item:item[2].x)
            result.reverse()
            
            return result
                            
        def draw(self,color=(1.0,1.0,1.0,1.0)):

        
            self.points[0].draw(RED)
            self.points[2].draw(RED)
            
            
            BezierCurve.draw(self,color)
                
class CubicBezierCurve(BezierCurve):


        def __init__(self,p1,p2,p3,p4):
                self.points = [p1,p2,p3,p4]

                self.inflectionpnt = None
        
        def moveTo(self,point):
            
            moveBy = (self.points[0] - point )

            transformedPoints = []
            for point in self.points:
                transformedPoints.append(point - moveBy)
            
            return CubicBezierCurve(*transformedPoints)
        
    
        def rotate(self,theta,around=None):
    
            if not around:
                around = self.points[0]
                
            rotatedPoints = []
            for point in self.points:
                rotatedPoints.append(point.rotate(theta,around))
            
            
            return CubicBezierCurve(*rotatedPoints)
            
        def findRoots(self,a,b,c,d):

                #First derivative roots (starting points for the Cubic Root Solver.

                interestValues = [0.0,1.0]
                quadraticRoots = self.solveQuadratic( (3*d-9*c-3*a+9*b),(6*a-12*b+6*c),(3*b-3*a) )
                result = []
                
                if quadraticRoots:
                    result = [root for root in quadraticRoots if root >= 0 and root <= 1]

                interestValues += result
                interestValues.append((2*b-a-c)/(3*b-3*c-a+d))

                extraValues = []
                for index,value in enumerate(interestValues):
                        slope = math.pow((1-value ),3)*a + 3*math.pow((1-value ),2)*value*b + 3*(1-value )*math.pow(value ,2)*c+math.pow(value ,3)*d
                        if slope == 0:
                                interestValues[index] = value - sys.float_info.epsilon                  
                                extraValues.append( value + sys.float_info.epsilon)
                                
                interestValues += extraValues

                roots = []
                for startValue in interestValues:
                        
                        value = startValue
                        for index in range(10):
                                
                                nm = math.pow((1-value),3)*a + 3*math.pow((1-value),2)*value*b + 3*(1-value)*math.pow(value,2)*c+math.pow(value,3)*d
                                dn = (3*d-9*c-3*a+9*b)*math.pow(value,2) + (6*a-12*b+6*c)*value + (3*b-3*a)

                                if dn == 0: continue

                                nextValue = value - nm/dn


                                if abs(value - nextValue) < sys.float_info.epsilon:
                                        exists = False
                                        for existingValue in roots:
                                                if abs(existingValue - nextValue) < sys.float_info.epsilon:
                                                        exists = True
                                                        break
                                        if not exists:
                                                roots.append(nextValue)
                                                break
                                        
                                value = nextValue

                return roots



        def intersect(self,line,onLine=False):


            theta  = -((math.pi/2)-atan2(
            (line.points[1] - line.points[0]).x,
            (line.points[1] - line.points[0]).y
            ))

            rotatedLine = Line(Point(0,0),line.points[1].rotate(theta,line.points[0]) )
            rotatedBezier = CubicBezierCurve( self.points[0].rotate(theta,line.points[0]),
                                  self.points[1].rotate(theta,line.points[0]),
                                  self.points[2].rotate(theta,line.points[0]),
                                  self.points[3].rotate(theta,line.points[0]))

            roots = rotatedBezier.findRoots(*[p.y for p in rotatedBezier.points])
            self.lastRotBez = rotatedBezier
            self.lastRotLine = rotatedLine
            if (onLine):
                for root in list(roots):
                    point = rotatedBezier.evaluate(root)
                    
                    if min(rotatedLine.points[0].x-sys.float_info.epsilon,rotatedLine.points[1].x-sys.float_info.epsilon) > point.x or max(rotatedLine.points[0].x+sys.float_info.epsilon,rotatedLine.points[1].x+sys.float_info.epsilon) < point.x:
                        roots.remove(root)
                    elif min(rotatedLine.points[0].y-sys.float_info.epsilon,rotatedLine.points[1].y-sys.float_info.epsilon) > point.y or max(rotatedLine.points[0].y+sys.float_info.epsilon,rotatedLine.points[1].y+sys.float_info.epsilon) < point.y:
                        roots.remove(root)
                
                
            result = []
            for root in roots:
                if (root > 0 and root < 1):
                    result.append((root,self.evaluate(root),rotatedBezier.evaluate(root)))
            
            result.sort(key=lambda item:item[2].x)
            result.reverse()
            
            return result
                                    

        def evaluate(self,value):

                return ( math.pow((1.0-value),3) * self.points[0])  + \
                       (3*math.pow((1-value),2)*value * self.points[1]) + \
                       (3*(1-value)*math.pow(value,2) * self.points[2]) + \
                       (math.pow(value,3) * self.points[3])
                        

        def inflection(self):
                P1,C1,C2,P2 = self.points
                
                a = C1 - P1
                b = C2 - C1 - a
                c = P2 - C2 - a -2.0*b

                a1 = b.x*c.y - b.y*c.x
                b1 = a.x*c.y - a.y*c.x
                c1 = a.x*b.y - a.y*b.x

                value =  math.pow(b1,2) - (4*a1*c1)
                self.inflectionpnts = []
                
                if value >0+sys.float_info.epsilon:
                        ta = ( -b1 - math.sqrt(   math.pow(b1,2.0) - 4.0*a1*c1  ) )/(2.0*a1)
                        tb = ( -b1 + math.sqrt(   math.pow(b1,2.0) - 4.0*a1*c1  ) )/(2.0*a1)

                        if ta < 1.0 and ta > 0.0:
                                self.inflectionpnts.append(ta)
                        elif tb < 1.0 and tb > 0.0:
                                self.inflectionpnts.append(tb)

                for index,inflpnt in enumerate(list(self.inflectionpnts)):
                    if inflpnt > (1-0.0000000000001):
                        self.inflectionpnts.remove(inflpnt)
                    elif inflpnt <  0.0000000000001:
                        self.inflectionpnts.remove(inflpnt)
 
                return self.inflectionpnts



        def draw(self,color=(1.0,1.0,1.0,1.0)):

        
            self.points[0].draw(RED)
            self.points[3].draw(RED)
            
            Line(self.points[0],self.points[1]).draw(GREEN)
            Line(self.points[2],self.points[3]).draw(GREEN)
            
            if self.inflectionpnt:
                self.evaluate(self.inflectionpnt).draw()
            BezierCurve.draw(self,color)



        def split(self,value):
            p1,p2,p3,p4 = self.points
            
            
            r1 = p1
            r2 = p1+value*(p2-p1)
            r3 = r2 + value*( (p2 + value*(p3-p2) ) -r2)
            r4 = self.evaluate(value)
            
            
            s1 = r4
            s4 = p4
            s3 = p3 + value*(p4-p3)
            s2 =  (s3+((1-value)*((p2 + value*(p3-p2))-s3)))

            return (CubicBezierCurve(r1,r2,r3,r4),CubicBezierCurve(s1,s2,s3,s4))

class Arc(object):


    def asScr(self,wireWidth):
        
        angleStr  = str(-(self.angle * 180/math.pi))
        angleStr = ("+" + angleStr) if not angleStr.startswith("-") else angleStr
        point1Str = str(self.points[0].x) + " " + str(self.points[0].y)
        point2Str = str(self.points[1].x) + " " + str(self.points[1].y)
        
        
        return "WIRE " + str(wireWidth) + " (" + point1Str + ") " + angleStr + " (" + point2Str + ");"
    

    def values(self):
        return (self.points[0],self.points[1],self.angle)


    def moveTo(self,point):
        
        moveBy = (self.points[0] - point )
        transformedPoints = []
        for point in self.points:
            transformedPoints.append(point - moveBy)
        
        return Arc(*transformedPoints,angle=self.angle)

        


    def rotate(self,theta,around=None):

        if not around:
            around = self.points[0]
            
        rotatedPoints = []
        for point in self.points:
            rotatedPoints.append(point.rotate(theta,around))
        
        
        return Arc(*rotatedPoints,angle=self.angle)
        
    def dot(self,p1,p2):
            return (p1.x*p2.x) + (p1.y*p2.y)

    def __init__(self,p1=None,p2=None,angle=None,tangent=None):

        if not p1 or not p2:
            return
        
        
    
        self.points  = [p1,p2]
        self.angle   = angle
        self.tangent = tangent
        self.chord   = p2- p1
        
        self.recalculate()
        
    def recalculate(self):

        p1,p2 = self.points
        tangentangle = None

        if not self.tangent:
                self.tangent = Point(
                        self.chord.x*cos(self.angle/2) - self.chord.y*sin(self.angle/2),
                        self.chord.x*sin(self.angle/2) + self.chord.y*cos(self.angle/2)
                        )
            
        self.tangent = self.tangent.normalized()


        dotprod = self.dot(self.tangent,self.chord)
        dotprod = min(max(dotprod,-0.9999999),0.9999999)

        tangentangle = acos(dotprod)
        if tangentangle > math.pi/2:
                self.chord = p1 -p2



        self.center  = None
        self.radius  = None


        dot = lambda p1,p2: (p1.x*p2.x) + (p1.y*p2.y)


        if (self.angle):                        
                self.halfangle  = self.angle/2
        elif(self.tangent):
                self.halfangle = math.acos(dot(self.tangent,self.chord) / (self.tangent.length() * self.chord.length()))
                self.angle = self.halfangle*2
        else:
                raise Exception("Angle or Tangent required")


        halfChord   = self.chord.length()/2
        self.radius = halfChord/math.sin(self.halfangle)



        if tangentangle < math.pi/2:
                self.center  = (Point(self.tangent.y , -self.tangent.x ) * self.radius)
        else:
                self.center  = (Point(-self.tangent.y , self.tangent.x ) * self.radius)


        self.center += self.points[1] if tangentangle > math.pi/2 else self.points[0]

        #self.center.draw(GREEN)
    
        self.offsetLine = self.points[0] - self.center
        
        self.offsetAngle = math.pi/2 - math.atan2(self.offsetLine.x,self.offsetLine.y) 

          
    def draw(self,color=(1.0,1.0,1.0,1.0)):

            degtorad = lambda deg: deg*(math.pi/180)
            radtodeg  = lambda rad: rad*(180/math.pi)
            glPointSize(5.0);
            self.points[0].draw(BLUE)
            self.points[1].draw(BLUE)
           
            glBegin(GL_LINE_STRIP)
            glColor4f(*color)
            
            

            
            for i in range( int(radtodeg(self.angle*10)) ):
                    
                    glVertex2f((cos(self.offsetAngle-degtorad((float(i)/10)) )*self.radius)+self.center.x,(sin( self.offsetAngle-degtorad( (float(i)/10)  ))*self.radius)+self.center.y);

            glEnd()
    
    def incenterIntersect(self,bezier):
    
    
        intersectLine = Line(self.center,self.offsetLine+self.center)
        intersectLine = intersectLine.toLength(self.radius)
        intersectLine = intersectLine.rotate(-self.angle)
        intersection  = bezier.intersect(intersectLine)
        
        return intersection[0]
    
    def deviation(self,bezier):
        
        DEVIATION_INCREMENT = 50.0
        
        intersectLine = Line(self.center,self.offsetLine+self.center)
        intersectLine = intersectLine.toLength(self.radius)
        
        lastRotBez = None
        lastRotLine = None
        
        maxAngle = self.angle
        newLine = intersectLine
        
        maxDeviation = (0,(None,None,None))

        for angle in range(0,-int(maxAngle*DEVIATION_INCREMENT)+1,-1):
            currentAngle = angle/DEVIATION_INCREMENT
            
            
            intersection = bezier.intersect(newLine)

            if intersection:
                
                deviation = newLine.points[1].distance(intersection[0][1])
                #newLine.draw()
                if deviation > maxDeviation[0] and intersection[0][0] > 0+0.001 and intersection[0][0] < 1-0.001:

                    lastRotBez = bezier.lastRotBez if hasattr(bezier,"lastRotBez") else None
                    lastRotLine = bezier.lastRotLine if hasattr(bezier,"lastRotLine") else None

                    maxDeviation = (deviation,(currentAngle,intersection[0][1],intersection[0][0]))
                
                newLine = intersectLine.rotate(currentAngle)
            else:
                continue
        """    
        if lastRotBez: lastRotBez.draw()
            
        if lastRotLine: lastRotLine.draw()

        if (lastRotBez):
            for point in lastRotBez.points:
                point.draw(GREEN)

            print "ROOTS",lastRotBez.findRoots(*[point.y for point in lastRotBez.points])

            lastRotBez.evaluate(0.9287).draw()
        """
        #print "MAX ANGLE",maxDeviation[1][0]
        #print "VALUE",maxDeviation[1][2]
        #maxDeviation[1][1].draw()
        return maxDeviation
                


class Biarc(object):
        def __init__(self,bezier):

        
            self.bezier = bezier
            self.calcBezier = bezier.moveTo(Point(0,0))
            self.offsetAngle =  -atan2(self.calcBezier.points[-1].y,self.calcBezier.points[-1].x)
            
        
            self.calcBezier = self.calcBezier.rotate(self.offsetAngle)
            
            self.orderReversed = False
            if self.calcBezier.points[1].y < 0 :    
                self.orderReversed = True
                self.calcBezier.points = list(reversed(self.calcBezier.points))
                
            
            if self.calcBezier.points[1].y < 0:
                self.offsetAngle  -= math.pi
                self.calcBezier = self.calcBezier.rotate(math.pi)
            

            
            if len(self.bezier.points) == 3:
                self.isCubic = False
            
                self.intersection = self.bezier.points[1]
                
            else:
                self.intersection = None
                self.calcTangentIntersection()
            
            
            
            
            self.calcIncenter()
            self.calculateArcs()
                
        def calcTangentIntersection(self):

                p1,p2,p3,p4 = self.calcBezier.points

                xn = (p1.x*p2.y - p1.y*p2.x)*(p3.x - p4.x) - (p1.x - p2.x)*(p3.x*p4.y - p3.y*p4.x)
                yn = (p1.x*p2.y - p1.y*p2.x)*(p3.y - p4.y) - (p1.y - p2.y)*(p3.x*p4.y - p3.y*p4.x)
                dn  = (p1.x - p2.x)*(p3.y - p4.y) - (p1.y - p2.y)*(p3.x - p4.x)

                if not dn:
                        self.intersection = None
                        return

                self.intersection = Point(xn/dn,yn/dn)

            
        def incenterIntersect(self):
            
            return self.arc1.incenterIntersect(self.calcBezier)
            
        
        
        def deviation(self):
            if not self.arc1 and self.arc2:
                return -1
                
                
            return max(self.arc1.deviation(self.calcBezier), self.arc2.deviation(self.calcBezier),key=lambda item:item[0])
            
        def calcIncenter(self):


            if not self.intersection:
                self.incenter = None
                return


            if len(self.calcBezier.points) == 3:
                p1,p2,p3 = self.calcBezier.points
                
                
                
                triPnt1  = p1.interpolate(p3,0.5)
                triPnt2 = p1.interpolate(p2,0.5)
                triPnt3 = p2.interpolate(p3,0.5)
                
                #triPnt1.draw()
                #triPnt2.draw()
                #triPnt3.draw()
                

                triLen1 = triPnt1.distance(triPnt3)
                triLen2 = triPnt1.distance(triPnt2)
                triLen3 = triPnt2.distance(triPnt3)

                #Line(triPnt1,triPnt2).draw()
                #Line(triPnt2,triPnt3).draw()
                #Line(triPnt3,triPnt1).draw()
                
                
                self.incenter =  Point(
                    (triLen1*p1.x + triLen2*p2.x + triLen3 *p3.x)/ (triLen1+triLen2+triLen3),
                    (triLen1*p1.y + triLen2*p2.y + triLen3 *p3.y)/ (triLen1+triLen2+triLen3)
                    )
                    
                """
                self.incenter =  Point(
                    (triLen1*triPnt1.x + triLen2*triPnt2.x + triLen3 *triPnt3.x)/ (triLen1+triLen2+triLen3),
                    (triLen1*triPnt1.y + triLen2*triPnt2.y + triLen3 *triPnt3.y)/ (triLen1+triLen2+triLen3)
                    )
                """
                
                
                
            elif len(self.calcBezier.points) == 4:
                p1,p2,p3,p4 = self.calcBezier.points

                triPnt1  =p1.interpolate(p4,0.5)
                triPnt2 = p1.interpolate(self.intersection,0.5)
                triPnt3 = self.intersection.interpolate(p4,0.5)

                triLen1 = self.intersection.distance(p4)
                triLen2 = p4.distance(p1)
                triLen3 = p1.distance(self.intersection)
                """
                self.incenter =  Point(
                    (triLen1*triPnt1.x + triLen2*triPnt2.x + triLen3 *triPnt3.x)/ (triLen1+triLen2+triLen3),
                    (triLen1*triPnt1.y + triLen2*triPnt2.y + triLen3 *triPnt3.y)/ (triLen1+triLen2+triLen3)
                    )
                    
                """    
                self.incenter =  Point(
                        (triLen1*p1.x + triLen2*self.intersection.x + triLen3 *p4.x)/ (triLen1+triLen2+triLen3),
                        (triLen1*p1.y + triLen2*self.intersection.y + triLen3 *p4.y)/ (triLen1+triLen2+triLen3)
                        )
                

        def draw(self,color=(1.0,1.0,1.0,1.0)):
                
                if not self.intersection:
                        return
                
                
                
                
                if self.arc1:
                
                    drawArc = Arc(self.calcBezier.points[0],self.incenter,self.arc1.angle)
                    drawArc = drawArc.rotate(-self.offsetAngle,self.calcBezier.points[0])
                    drawArc = drawArc.moveTo((self.bezier.points[-1] if self.orderReversed else self.bezier.points[0]))    
                    drawArc.draw(RED)
                    
                if self.arc2:

                    
                    drawArc = Arc(self.incenter,self.calcBezier.points[-1],self.arc2.angle)
                    drawArc = drawArc.rotate(-self.offsetAngle,self.calcBezier.points[0])
                    drawArc = drawArc.moveTo((self.bezier.points[-1] if self.orderReversed else self.bezier.points[0]) + self.incenter.rotate(-self.offsetAngle))
                    drawArc.draw(RED)

        def calculateArcs(self):
            
            if not self.intersection:
                self.arc1 = self.arc2 = None
                return

        
            if len(self.calcBezier.points) == 3:
            
                p1,p2,p3= self.calcBezier.points
                tangent1 = p2 - p1
                tangent2 = p2 - p3
                
                self.arc1 = Arc(p1,self.incenter,tangent=tangent1)
                self.arc2 = Arc(self.incenter,p3,tangent=tangent2)
                
            if len(self.calcBezier.points) == 4:
                p1,p2,p3,p4 = self.calcBezier.points

                
                tangent1 = self.intersection - p1
                tangent2 = self.intersection - p4
                
                self.arc1 = Arc(p1,self.incenter,tangent=tangent1)
                self.arc2 = Arc(self.incenter,p4,tangent=tangent2)
    
            if (self.arc1.angle) > math.pi:
                self.arc1 = None
                self.arc2 = Arc(self.incenter,p4,tangent=tangent2)
            if (self.arc2.angle) > math.pi:
                self.arc2 = None

        def angle(self):
                return self.arc1.angle + self.arc2.angle
        
        def arcs(self):
            resultArcs = []
            if self.arc1:
                resultArc = Arc(self.calcBezier.points[0],self.incenter,self.arc1.angle)
                resultArc = resultArc.rotate(-self.offsetAngle,self.calcBezier.points[0])
                resultArc = resultArc.moveTo((self.bezier.points[-1] if self.orderReversed else self.bezier.points[0]))    
                resultArcs.append(resultArc)
            if self.arc2:
                resultArc = Arc(self.incenter,self.calcBezier.points[-1],self.arc2.angle)
                resultArc = resultArc.rotate(-self.offsetAngle,self.calcBezier.points[0])
                resultArc = resultArc.moveTo((self.bezier.points[-1] if self.orderReversed else self.bezier.points[0]) + self.incenter.rotate(-self.offsetAngle))
                resultArcs.append(resultArc)
    
            return resultArcs

class DXFImportDialog(QDialog):
    
    LABEL_WIDTH = 75
    RIGHT_SPACING_WIDTH = 0

    LAYER_ENUMERATION_COMPLETE_EVENT = QEvent.User+1
    
    def __init__(self):
        
        QDialog.__init__(self)
        
        self.setWindowIcon(QIcon(QPixmap(":/eagleimages/eaglepy.png")))
        self.setWindowTitle("Eagle DXF Importer")
        self.setGeometry(0,0,600,500)
        self.centerToWidget()

        self.setLayout(QVBoxLayout())

        
        
        self.filePathLayout = QHBoxLayout()
        self.filePathName = QLabel("File Path : ")
        self.filePathName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.filePathName.setMaximumWidth(self.LABEL_WIDTH)
        self.filePathName.setMinimumWidth(self.LABEL_WIDTH)
        self.filePathSelectButton = QPushButton()
        self.filePathSelectButton.setIcon(QApplication.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.filePathEdit = QLineEdit()
        self.filePathLayout.addWidget(self.filePathName)
        self.filePathLayout.addWidget(self.filePathEdit)
        self.filePathLayout.addWidget(self.filePathSelectButton)
        self.filePathLayout.addSpacerItem(QSpacerItem(self.RIGHT_SPACING_WIDTH,1,QSizePolicy.Fixed,QSizePolicy.Fixed))
        
        
        
        
        self.scaleLayout = QHBoxLayout()
        self.scaleName = QLabel("Scale : ")
        self.scaleName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.scaleName.setMaximumWidth(self.LABEL_WIDTH)
        self.scaleName.setMinimumWidth(self.LABEL_WIDTH)
        self.scaleSpinBox = QDoubleSpinBox()
        self.scaleSpinBox.setMinimum(0.00001)
        self.scaleSpinBox.setMaximum(10)
        
        self.scaleSpinBox.setDecimals(5)
        self.scaleSpinBox.setSingleStep(0.00001)
        self.scaleSpinBox.setValue(1)
        self.scaleLayout.addWidget(self.scaleName)
        self.scaleLayout.addWidget(self.scaleSpinBox)
        self.scaleLayout.addSpacerItem(QSpacerItem(self.RIGHT_SPACING_WIDTH,1,QSizePolicy.Fixed,QSizePolicy.Fixed))
        
        self.toleranceLayout = QHBoxLayout()
        self.toleranceName = QLabel("Tolerance : ")
        self.toleranceName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.toleranceName.setMaximumWidth(self.LABEL_WIDTH)
        self.toleranceName.setMinimumWidth(self.LABEL_WIDTH)
        self.toleranceSpinBox = QDoubleSpinBox()
        self.toleranceSpinBox.setMinimum(0.0001)
        self.toleranceSpinBox.setMaximum(0.1)
        self.toleranceSpinBox.setSingleStep(0.0001)
        self.toleranceSpinBox.setDecimals(4)
        self.toleranceSpinBox.setValue(0.001)
        self.toleranceLayout.addWidget(self.toleranceName)
        self.toleranceLayout.addWidget(self.toleranceSpinBox)
        self.toleranceLayout.addSpacerItem(QSpacerItem(self.RIGHT_SPACING_WIDTH,1,QSizePolicy.Fixed,QSizePolicy.Fixed))
        
        self.wireWidthLayout = QHBoxLayout()
        self.wireWidthName = QLabel("Wire Width : ")
        self.wireWidthName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.wireWidthName.setMaximumWidth(self.LABEL_WIDTH)
        self.wireWidthName.setMinimumWidth(self.LABEL_WIDTH)
        self.wireWidthSpinBox = QDoubleSpinBox()
        self.wireWidthSpinBox.setMinimum(0.0001)
        self.wireWidthSpinBox.setMaximum(0.1)
        self.wireWidthSpinBox.setSingleStep(0.0001)
        self.wireWidthSpinBox.setDecimals(4)
        self.wireWidthSpinBox.setValue(0.1)
        self.wireWidthLayout.addWidget(self.wireWidthName)
        self.wireWidthLayout.addWidget(self.wireWidthSpinBox)
        self.wireWidthLayout.addSpacerItem(QSpacerItem(self.RIGHT_SPACING_WIDTH,1,QSizePolicy.Fixed,QSizePolicy.Fixed))        

        self.layerLayout = QHBoxLayout()
        self.layerName = QLabel("Layer : ")
        self.layerName.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.layerName.setMaximumWidth(self.LABEL_WIDTH)
        self.layerName.setMinimumWidth(self.LABEL_WIDTH)
        self.layerComboBox = QComboBox()
        self.layerComboBox.addItem("emumerating..")
        self.layerComboBox.setEnabled(False)
        self.layerLayout.addWidget(self.layerName)
        self.layerLayout.addWidget(self.layerComboBox)
        
        self.fileInfoName = QLabel("File Name : ")
        self.fileInfoName.setAlignment(Qt.AlignTop | Qt.AlignRight)
        self.fileInfoName.setMaximumWidth(self.LABEL_WIDTH)
        self.fileInfoName.setMinimumWidth(self.LABEL_WIDTH)
        
        self.fileInfoTable = QTableWidget()
        self.fileInfoTable.setColumnCount(3)
        self.fileInfoTable.verticalHeader().hide()
        self.fileInfoTable.setHorizontalHeaderLabels(["Layer","Entity Type","Import","Info"])
        self.fileInfoTable.horizontalHeader().setClickable(False)
        self.fileInfoTable.setColumnWidth(0,200)
        self.fileInfoTable.setColumnWidth(1,200)
        self.fileInfoTable.setColumnWidth(2,50)
        self.fileInfoTable.setColumnWidth(3,200)
        self.fileInfoTable.horizontalHeader().setStretchLastSection(True)
        self.fileInfoTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.fileInfoLayout =QHBoxLayout()
        self.fileInfoTableLayout = QVBoxLayout()
        #self.fileInfoTableLayout.setSpacing(0)
        
        self.fileInfoTableButtonLayout = QHBoxLayout()
        
        self.fileInfoTableSelectAllButton = QPushButton("Select All")
        self.fileInfoTableDeselectAllButton = QPushButton("Deselect All")
        """
        buttonWidth = 150
        self.fileInfoTableSelectAllButton.setMinimumWidth(buttonWidth)
        self.fileInfoTableSelectAllButton.setMaximumWidth(buttonWidth)
        self.fileInfoTableDeselectAllButton.setMaximumWidth(buttonWidth)
        self.fileInfoTableDeselectAllButton.setMinimumWidth(buttonWidth)
        """
        
        self.fileInfoTableSelectAllButton.clicked.connect(self.selectAll)
        self.fileInfoTableDeselectAllButton.clicked.connect(self.deselectAll)
        
        self.fileInfoTableButtonLayout.addWidget(self.fileInfoTableSelectAllButton)
        self.fileInfoTableButtonLayout.addWidget(self.fileInfoTableDeselectAllButton)
        #self.fileInfoTableButtonLayout.addSpacerItem(QSpacerItem(1,1,QSizePolicy.Expanding,QSizePolicy.Fixed))
        
        self.fileInfoLayout.addWidget(self.fileInfoName)
        self.fileInfoLayout.addLayout(self.fileInfoTableLayout)
        self.fileInfoLayout.addSpacerItem(QSpacerItem(self.RIGHT_SPACING_WIDTH,1,QSizePolicy.Fixed,QSizePolicy.Fixed))
        
        #self.fileInfoTableLayout.addLayout(self.fileInfoTableButtonLayout)    
        self.fileInfoTableLayout.addWidget(self.fileInfoTable)
        
        #self.fileInfoTable.setStyleSheet("QTableWidget::item{border: 0px;padding-left:10px;}")

        
        self.filePathSelectButton.clicked.connect(self.fileOpenDialog)
        
        
        self.importButtonLayout = QHBoxLayout()
        
        self.cancelButton = QPushButton("Cancel")
        self.importButton = QPushButton("Import..")
        self.importCloseButton = QPushButton("Import && Close..")
        buttonWidth  = 150
        buttonHeight = 35
        
        self.importButton.setMinimumWidth(buttonWidth)
        self.importButton.setMaximumWidth(buttonWidth)
        self.importButton.setMinimumHeight(buttonHeight)
        self.importButton.setMaximumHeight(buttonHeight)
        
        self.importCloseButton.setMinimumWidth(buttonWidth)
        self.importCloseButton.setMaximumWidth(buttonWidth)
        self.importCloseButton.setMinimumHeight(buttonHeight)
        self.importCloseButton.setMaximumHeight(buttonHeight)
        
        self.cancelButton.setMinimumWidth(buttonWidth)
        self.cancelButton.setMaximumWidth(buttonWidth)
        self.cancelButton.setMinimumHeight(buttonHeight)
        self.cancelButton.setMaximumHeight(buttonHeight)
        
        self.importButtonLayout.addSpacerItem(QSpacerItem(1,1,QSizePolicy.Expanding,QSizePolicy.Fixed))
        self.importButtonLayout.addWidget(self.cancelButton)
        self.importButtonLayout.addWidget(self.importButton)
        self.importButtonLayout.addWidget(self.importCloseButton)
        
        self.cancelButton.clicked.connect(self.close)
        self.importButton.clicked.connect(self.importFile)
        self.importCloseButton.clicked.connect(self.importCloseFile)
        
        self.layout().addLayout(self.filePathLayout)
        self.layout().addLayout(self.scaleLayout)
        self.layout().addLayout(self.toleranceLayout)
        self.layout().addLayout(self.wireWidthLayout)
        self.layout().addLayout(self.layerLayout)
        self.layout().addLayout(self.fileInfoLayout)
        self.layout().addLayout(self.importButtonLayout)
        
        self.enumerateLayers()
     
    def event(self,event):
    
        if event.type() == self.LAYER_ENUMERATION_COMPLETE_EVENT:
            self.populateLayerCombo()
            event.setAccepted(True)
            return True
            
        return QDialog.event(self,event)

    def populateLayerCombo(self):
    
        for layerItem in self.layerData:
            name,colorIndex,index = layerItem
            map = QPixmap(12,12)
            map.fill(QColor(*self.palette[colorIndex]))
            self.layerComboBox.addItem(QIcon(map),name,QVariant(index))
        
        self.layerComboBox.removeItem(0)
        self.layerComboBox.setEnabled(True)
    
    def enumerateLayers(self):

        self.layerData = []
        def enumerateThread(layerData): 
            
            self.palette = Eaglepy.paletteall()

            for index,layer in enumerate(Eaglepy.ULContext().layers(True)):
                layerData.append((layer.name.get(True),layer.color.get(True),index))
            QApplication.postEvent(self,QEvent(self.LAYER_ENUMERATION_COMPLETE_EVENT))

        threading.Thread(target=enumerateThread,args=[self.layerData]).start()

    def importCloseFile(self):
        if not self.importFile():
            self.close()
        
    def importFile(self):
        filePath = str(self.filePathEdit.text())
    
        if not os.path.exists(filePath):
            messageBox = QMessageBox(
            QMessageBox.Warning,
            "File Not Found","The file path '%s' does not exist. Please specify an existing file." % filePath,
            QMessageBox.Ok,self)
            
            return messageBox.exec_()

        importItems = {}
        for index in range(self.fileInfoTable.rowCount()):
            if self.fileInfoTable.item(index,2).checkState() == Qt.Checked:
                importItems[str(self.fileInfoTable.item(index,0).text())] = str(self.fileInfoTable.item(index,1).text()    )
            
        if not len(importItems.keys()):
            messageBox = QMessageBox(
            QMessageBox.Warning,
            "Nothing Selected","You must select at least one entity to import.",
            QMessageBox.Ok,self)
            
            return messageBox.exec_()
            
            
        

        dxfFile = readfile(filePath)
        
        
        wire_width    = self.wireWidthSpinBox.value()
        scale         = self.scaleSpinBox.value()
        max_deviation = self.toleranceSpinBox.value()
        layer         = str(self.layerComboBox.currentText())
        curves = []
        lines  = []
        
        for entity in dxfFile.entities:
            if not importItems.has_key(entity.layer):
                continue
            
            if not entity.dxftype in importItems[str(entity.layer)]:
                continue
            
            
            if isinstance(entity,Polyline):
                points = [p for p in entity.points()]
                
                pointIndex = 0
                
                while(pointIndex < len(points)-1):
                    lines.append(Line(Point(points[pointIndex][0]*scale,points[pointIndex][1]*scale),Point(points[pointIndex+1][0]*scale,points[pointIndex+1][1]*scale)))
                    pointIndex += 1
                
                continue
                
            
        
            hasControlPoints  = True
            controlPointIndex = 0
            while hasControlPoints:
                points = []
                for index in range(controlPointIndex,controlPointIndex+4):
                    points.append(Point(*list(entity.controlpoints[index][:2])))

                    
                newCurve = BezierCurve.Construct(*[ p*scale for p in points])
                
                if isinstance(newCurve,Line):
                    lines.append(newCurve)
                else:
                    curves.append(newCurve)
                controlPointIndex +=3
                
                if controlPointIndex == len(entity.controlpoints)-1:            
                    break
                
        del dxfFile

        splittingCurves = False
        curveIndex  = 0
        
        if len(curves):
            while not splittingCurves:
 
                thisCurve = curves[curveIndex]
                inflectionPnts = thisCurve.inflection()
                if len(inflectionPnts):
                    
                    curves.pop(curveIndex)
                    splitCurves = thisCurve.split(inflectionPnts[0])
                    
                    for curve in splitCurves:
                        if isinstance(curve,Line):
                            lines.append(curve)
                        else:
                            curves.insert(curveIndex,curve)
                    continue
                
                biarc = Biarc(thisCurve)
                
                if (biarc.angle()) > math.pi/2:
                    intersect = biarc.incenterIntersect()
                    curves.pop(curveIndex)
                    splitCurves = thisCurve.split(intersect[0])
                                    
                    for curve in splitCurves:
                        if isinstance(curve,Line):
                            lines.append(curve)
                        else:
                            curves.insert(curveIndex,curve)
                    continue

                
                deviation = biarc.deviation()    
                if deviation[0] > max_deviation:
                    curves.pop(curveIndex)
                    splitCurves = thisCurve.split(deviation[1][2])
                    for curve in splitCurves:
                        if isinstance(curve,Line):
                            lines.append(curve)
                        else:
                            curves.insert(curveIndex,curve)
                    continue
                
                    
                if curveIndex == len(curves)-1:
                    break
                    
                curveIndex +=1
            
        resultText = "LAYER " + layer + ";SET CONFIRM YES;"
        for index,curve in enumerate(curves):            
            biarc = Biarc(curve)
            arcs = biarc.arcs()
            for arc in arcs:
                resultText += arc.asScr(wire_width)
            
        for index,line in enumerate(lines):
            resultText += line.asScr(wire_width)
        
        resultText += "SET CONFIRM OFF;"
        

        Eaglepy.executescr(resultText);
        
    def selectAll(self):
        for index in range(self.fileInfoTable.rowCount()):
            self.fileInfoTable.item(index,2).setCheckState(Qt.Checked)
            
    def deselectAll(self):
        for index in range(self.fileInfoTable.rowCount()):
            self.fileInfoTable.item(index,2).setCheckState(Qt.Unchecked)
    
    def findEagleWindow(self):
        pass
    
    
    def fileOpenDialog(self):
    
        fileDialog = QFileDialog(filter="*.dxf")
        fileDialog.setFileMode(QFileDialog.ExistingFile)
        
        result = fileDialog.exec_()
        
        if result:        
            self.filePathEdit.setText(fileDialog.selectedFiles()[0])
            self.readFileInfo()
    

    def clearFileInfo(self):
        for index in range(self.fileInfoTable.rowCount()):
            self.fileInfoTable.removeRow(0)
    
    def readFileInfo(self):
    
        self.clearFileInfo()
        filePath = self.filePathEdit.text()
        if not os.path.exists(filePath):
            return
            
         
        dxfFile = readfile(str(filePath))

        entityLayers = {}
        for entity in dxfFile.entities:
            if not entityLayers.has_key( str(entity.layer) ) == None:
                entityLayers[str(entity.layer)] = []
                
            entityLayers[str(entity.layer)].append(entity)
        
        for layername,entityList in entityLayers.iteritems():
            for index,entity in enumerate(entityList):
        
                layerItem  = QTableWidgetItem(layername)
                layerItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                entityItem = QTableWidgetItem(str(entity.dxftype))
                entityItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                
                selectItem = QTableWidgetItem()
                selectItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                selectItem.setTextAlignment(Qt.AlignRight)
                selectItem.setCheckState(Qt.Checked)
                
                entityInfoText = ""
                if isinstance(entity,Line):
                    entityInfoText += "Start:" + str(entity.start) + ", Stop:" + str(entity.stop)
                elif isinstance(entity,Point):
                    entityInfoText += "Position:" + str(entity.point)
                elif isinstance(entity,Circle):
                    entityInfoText += "Center:" + str(entity.center) + ", Radius:" + str(entity.radius)
                elif isinstance(entity,Arc):
                    entityInfoText += "Center:" + str(entity.center) + ", Radius:" + str(entity.radius) + ", Start Angle:" + str(entity.startangle) + ", End Angle:" + str(entity.endangle)
                elif isinstance(entity,Spline):
                    entityInfoText += "Degree:" + str(entity.degree) + ", Start Tangent:" + str(entity.starttangent) + ", End Tangent:" + str(entity.endtangent) + ", Num Ctrl Pnts:" + str(len(entity.controlpoints)) + \
                    ", Num Fit Pnts:" + str(len(entity.fitpoints)) + ", Num Knots:" + str(len(entity.knots)) + ", Weights:" + str(len(entity.weights))

                    
                entityInfoItem = QTableWidgetItem(entityInfoText)
                
                
                self.fileInfoTable.insertRow(index)
                
                self.fileInfoTable.setItem(index,0,layerItem)
                self.fileInfoTable.setItem(index,1,entityItem)
                self.fileInfoTable.setItem(index,2,selectItem)
                self.fileInfoTable.setItem(index,3,entityInfoItem)
        del dxfFile
        
    def centerToWidget(self,target=None):

        if not target:
            rect = QApplication.desktop().availableGeometry(target if target != None else self)
        else:
            rect = target.geometry()   
        
        center = rect.center()
        self.move(center.x() - self.width()  * 0.5, center.y() - self.height() * 0.5);
      

Eaglepy.initialize()

application = QApplication([])
dialog = DXFImportDialog()
dialog.show()
application.exec_()
Eaglepy.shutdown()
