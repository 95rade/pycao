"""
    This is Pycao, a modeler and raytracer interpreter for 3D drawings
    Copyright (C) 2015  Laurent Evain

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import numpy as np
#import bpy
import math
from math import *
import sys,os
sys.path.append(os.getcwd()) # pour une raison inconnue, le path de python ne contient pas ce dir dans l'install de la fac

from uservariables import *
from generic import *
from mathutils import *
from aliases import *
from genericwithmaths import *
from elaborate import *



class Compound(ElaborateOrCompound):
    """
    A class for objects for compound objects, which share a move_alone function 
    """
    def __new__(cls,*args,**kwargs):
        comp=ElaborateOrCompound.__new__(cls,*args,**kwargs)
        csgOperation=Object()
        csgOperation.csgKeyword="union"
        csgOperation.csgSlaves=[]
        comp.csgOperations=[csgOperation]
        return comp
        
    def __init__(self,slavesList=[]):
        """
        Each entry of  slavesList is
        - an object in World with no genealogy
        - or a sublist [name,objectInworld], where name is a string. 
        In the second case, the subobject will be accessible with self.name
        """

        builtList=[]
        for slave in slavesList:
            if isinstance(slave,ObjectInWorld):
                builtList+=[slave]
            else :
                name=slave[0]
                slave=slave[1]
                setattr(self,name,slave)
                builtList+=[slave]
        self.csgOperations[0].csgSlaves=builtList

    def print_slaves(self):
        print(self.csgOperations[0].csgSlaves)
        
    def move_alone(self,mape):
        """
        the obect o is a compound iff o admits a union in its list of csg operations iff o has a unique union in its csg operations
        and this union is the first item. """
        self.mapFromParts=mape*self.mapFromParts
        slaves=self.csgOperations[0].csgSlaves
        for slave in slaves:
            slave.move(mape)
        return self

        
    def build_from_slaves(self):
        Compound.__init__(self,slavesList=self.slaves)

    def __str__(self):
        return "This is a compound"

    def colored(self,string):
        slaves=self.csgOperations[0].csgSlaves
        for slave  in slaves :
            slave.colored(string)
        return self
    
class Lathe(Elaborate):
    """
    Class for Lathe objects

    """
    def __init__(self,curve):
        # The curve is assumed to have points of the form [0,y,z]
        self.parts=Object()
        self.parts.curve=curve
        self.markers=Object()
        self.markers.box=FrameBox(listOfPoints=[eachPoint for eachPoint in curve ])
        self.markers_as_functions()
        self.move_alone(Map.affine(X,Z,Y,origin))
    @staticmethod
    def fromPolyline(curve):
        return Lathe(curve)
    @staticmethod
    def fromBezierCurve(curve):
        # To be printable by povray, the curve must have four points 
        return Lathe(curve)
    @staticmethod
    def fromPiecewiseCurve(curve):
        #  all the y components of the curve need  to be positive. 
        return Compound([Lathe(c) for c in curve])

    




class FrameAxis(Compound):
    """
    Class for 'arrows', ie. cylinder+cone at the end.

    Constructor:
    FrameAxis(start,end,cylinderPercentage,cylinderRadius,arrowRadius) : start,end=points for the extremities of the arrow. CylinderPercentage: the portion 
    of the arrow filled by the cylinder( the reminder being filled by the cone). 

    """
    def __init__(self,start,end,cylinderPercentage,cylinderRadius,arrowRadius):
        start=start.copy()
        end=end.copy()
        endCylinder=(1-cylinderPercentage)*start+cylinderPercentage*end
        cyl=Cylinder(start,endCylinder,cylinderRadius)
        #cyl.color=color
        cone=Cone(endCylinder,end,arrowRadius,0)
        #cone.color=color
        self.slaves=[["cyl",cyl],["arrow",cone]]
        self.build_from_slaves()


class BentCylinder(Compound):
    """
    A class for BentCylinders, similar to obects obtained from a Cylindric tube and a bending machine. Technically, this is 
    a succession of cylinders, and SlicedTorus. 

    Constructor
    BentCylinder(listOfPoints,radius,startWithTorus=False):
    if startWithTorus==True, the first piece is a sliced Torus, otherwise the first piece is a cylinder.
    The radius argument is both the radius of the Cylinder and the small radius of the torus. 
    The list of points =[p0,p1,,,,pn] is such that p0 is the starting point of the
    first piece, pn is the ending point of the last piece, p1,...p(n-1) are the junction points between the pieces.
    The large radius, normal and center of the torus are automatically computed from the data. 
    If n==1 and startWithTorus==True, an error is raised as the mathematical problem of determining the torus is not feasible.  
    """
    def __init__(self,listOfPoints,radius,startWithTorus=False):
        # construction des tangentes
        tangents=[]
        if not startWithTorus:
            for i in range(len(listOfPoints)-1):
                if i % 2==0:
                    tangents.append(listOfPoints[i+1]-listOfPoints[i])
                else:
                    tangents.append(listOfPoints[i]-listOfPoints[i-1])
        else:
            for i in range(1,len(listOfPoints)-1):
                if i % 2== 1:
                    tangents.append(listOfPoints[i+1]-listOfPoints[i])
                else:
                    tangents.append(listOfPoints[i]-listOfPoints[i-1])
            # it remains to compute the first tangent
            c=Circle.from_2_points_and_tangent(listOfPoints[1],listOfPoints[0],tangents[0])
            mape=Map.rotational_difference(listOfPoints[1]-c.center,listOfPoints[0]-c.center)
            tangents=[tangents[0].copy().remove_children().move_alone(mape)]+tangents
        # Now I add the last tangent
        oddNumberOfPoints= (len(listOfPoints)% 2 == 1)
        endWithCylinder=( startWithTorus == oddNumberOfPoints)
        nbp=len(listOfPoints)
        if endWithCylinder:
            tangents.append(listOfPoints[nbp-1]-listOfPoints[nbp-2])
        else:
            c=Circle.from_2_points_and_tangent(listOfPoints[nbp-2],listOfPoints[nbp-1],tangents[nbp-2])
            mape=Map.rotational_difference(listOfPoints[nbp-2]-c.center,listOfPoints[nbp-1]-c.center)
            tangents.append(tangents[nbp-2].copy().remove_children().move_alone(mape))
        # construction du slave(start,tangentStart,end,tangentEnd)
        def buildSlave(start,tangentStart,end,tangentEnd):
            if tangentStart==tangentEnd:
                return Cylinder(start,end,radius)
            else:
                c=Circle.from_2_points_and_tangent(start,end,tangentStart)
                torus=Torus(c.radius,radius,c.plane.normal,c.center)
                acute=(((start-c.center).cross(tangentStart)).dot((start-c.center).cross(end-c.center))>=0)
                # There may be problems if start and end are opposite points of the circle
                if np.allclose(end+start,2*c.center):
                    precision=10**(-5)
                    deviation=precision*c.plane.normal.cross(end-start)
                    end=end+deviation
                    #print("little change")
                torus.sliced_by(start,end,acute)
                return torus
        self.slaves=[]
        for i in range(len(listOfPoints)-1):
            self.slaves.append([str(i),buildSlave(listOfPoints[i],tangents[i],listOfPoints[i+1],tangents[i+1])])
        self.build_from_slaves()

    @staticmethod
    def from_polyline(listOfPoints,curvatureRadius,tubeRadius):
        """
        Returns a bent cylinder obtained from a polyline. First, the polyline is modified 
        with the replacement of each angle by an arc of circle with radius curvatureRadius.
        The curve obtained is a sequence of lines and arc or circles. Finally, cylinders and 
        slices of tori are drawn along this curve. 
        
        The construction is not possible and the results are inconsistent visually if the curvatureRadius is too large. 
        The precise condition is that if a and b are the angles at the vertexes of a segment of the polyline, then
        length(segment)/(tan(a/2)+length(segment)/tan(b/2))>curvatureRadius. This is the condition for the end of the last portion of the torus not 
        to interfere with the beginning of the next torus. On the first and last segment, there is a unique angle a and the 
        condition is tan(a/2)<length(segment)/curvatureRadius, otherwise the circle is too large to fit in the angle. 

        constructor
        BentCylinder.from_polyline(listOfPoints,curvatureRadius,tubeRadius)
        The points in the list are described by absolute coordinates (as a point) or by a coordinate relative to the previous point (as a vector).
        The previous point is the origin by definition for the first point in the list. 
        Example: [origin,X,Y] is equivalent to [origin,origin+X,origin+Y]
        """

        # I start to construct the absolute list of the polyline from the possible relative list
        def cotan(x):
            return math.cos(x)/math.sin(x)
        spline_=Polyline(listOfPoints)
        anglesList=[math.pi]+spline_.angles()+[math.pi]
        lengthsList=spline_.lengths()
        possibleRadius=[]
        for i in range(len(spline_)-1):
            #print("length,anglei,anglei+1")
            #print(lengthsList[i])
            #print(anglesList[i]/3.14)
            #print(anglesList[i+1]/3.14)
            #print(tan(0.5*anglesList[i]))
            #print("radius")
            #print ()
            possibleRadius.append((1.*lengthsList[i]*cotan(0.5*anglesList[i])+lengthsList[i]*cotan(0.5*anglesList[i+1])))
        #print("possRadius",possibleRadius)
        #print min(possibleRadius)
        if  min(possibleRadius)<curvatureRadius:
            raise NameError("The curvatureRadius is too large and not compatible with the angles and lengths of the segments")
        #for i in range(len(spline_-2)
        # Now I build the bentCylinder list of points from the polyline list of Points 
        bentList=[spline_[0]]
        for i in range(1,len(spline_)-1):
            c=Circle.from_tangent_triangle(Triangle(spline_[i-1],spline_[i],spline_[i+1]),curvatureRadius)
            bentList.append(c.contact[0])
            bentList.append(c.contact[1])
        bentList.append(spline_[-1])
        #for point in bentList:
        #    print(point)
        retour=BentCylinder(bentList,tubeRadius)
        retour.spline=spline_
        #print (retour.spline)
        return retour

