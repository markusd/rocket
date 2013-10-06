
from Box2D import *
from OpenGL.GL import *

from math import sin, cos

class Renderer(b2DrawExtended):
    surface = None
    axisScale = 10.0
    def __init__(self, **kwargs): 
        b2DrawExtended.__init__(self, **kwargs)
        self.flipX = False
        self.flipY = False
        self.convertVertices = True

    def StartDraw(self, center, zoom=10, screen=(0, 0)):
        self.zoom = zoom
        self.center = ((screen[0]*0.5 - center[0]) * zoom / 10.0, (screen[1]*0.5-center[1]) * zoom / 10.0)
        self.offset = (self.center[0] - screen[0]*0.5, self.center[1] - screen[1]*0.5)
        self.screenSize = screen
        self.screenHalf = (self.screenSize[0]*0.5, self.screenSize[1]*0.5)

    def EndDraw(self): pass

    def DrawPoint(self, p, size, color):
        self.DrawCircle(p, size/self.zoom, color, drawwidth=0)
        
    def DrawAABB(self, aabb, color):
        vertices = [  (aabb.lowerBound.x, aabb.lowerBound.y ),
                    (aabb.upperBound.x, aabb.lowerBound.y ),
                    (aabb.upperBound.x, aabb.upperBound.y ),
                    (aabb.lowerBound.x, aabb.upperBound.y ) ]
        
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_LINE_LOOP)
        for v in vertices:
            glVertex2fv(v)
        glEnd()
       #print("AABB")

    def DrawSegment(self, p1, p2, color):
        return
        if (p1[0] < -self.screenHalf[0] or p1[0] > self.screenHalf[0]) and (p2[0] < -self.screenHalf[0] or p2[0] > self.screenHalf[0]):
            return
        if (p1[1] < -self.screenHalf[1] or p1[1] > self.screenHalf[1]) and (p2[1] < -self.screenHalf[1] or p2[1] > self.screenHalf[1]):
            return
        glColor3f(1.0, 1.0, 1.0)

        glBegin(GL_LINES)
        glVertex2fv(p1)
        glVertex2fv(p2)
        glEnd()
        #print("Segment %s - %s" % (p1, p2))

    def DrawTransform(self, xf):
        p1 = xf.position
        p2 = self.to_screen(p1 + self.axisScale * xf.R.col1)
        p3 = self.to_screen(p1 + self.axisScale * xf.R.col2)
        p1 = self.to_screen(p1)
        raise NotImplementedError()

    def DrawCircle(self, center, radius, color, drawwidth=1):
        SEGMENTS = 20
        radius *= self.zoom
        if radius < 1: radius = 1
        else: radius = int(radius)

        angle = 2.0 *  3.141 / float(SEGMENTS)
        glBegin(GL_LINE_LOOP)
        angle1 = 0.0;
        glVertex2f(radius * cos(0.0), radius * sin(0.0))
        for i in range(SEGMENTS):
            glVertex2f(radius * cos(angle1), radius * sin(angle1))
            angle1 += angle
        glEnd()
        
        #print("Circle")

    def DrawSolidCircle(self, center, radius, axis, color):
        SEGMENTS = 20
        radius *= self.zoom
        if radius < 1: radius = 1
        else: radius = int(radius)

        angle = 2.0 *  3.141 / float(SEGMENTS)
        glBegin(GL_LINE_LOOP)
        angle1 = 0.0;
        glVertex2f(center[0] + radius * cos(0.0), center[1] + radius * sin(0.0))
        for i in range(SEGMENTS):
            glVertex2f(center[0] + radius * cos(angle1), center[1] + radius * sin(angle1))
            angle1 += angle
        glEnd()
        #glBegin(GL_LINES)
        #glVertex2fv(center)
        #glVertex2f(center[0] - radius*axis[0], center[1] + radius*axis[1])
        #glEnd()
        
        #print("Solid Circle %s - %s" % (center, radius))

    def DrawPolygon(self, vertices, color):
        if not vertices:
            return

        if len(vertices) == 2:
            glBegin(GL_LINES)
            glVertex2fv(vertices[0])
            glVertex2fv(vertices[1])
            glEnd()
        else:
            glBegin(GL_LINE_LOOP)
            for v in vertices:
                glVertex2fv(v)
            glEnd()
            
        #print("Polygon")
        
    def DrawSolidPolygon(self, vertices, color):
        if not vertices:
            return

        if len(vertices) == 2:
            glBegin(GL_LINES)
            glVertex2fv(vertices[0])
            glVertex2fv(vertices[1])
            glEnd()
        else:
            glBegin(GL_LINE_LOOP)
            for v in vertices:
                glVertex2fv(v)
                #print(v)
            glEnd()
            
        #print("SolidPolygon")
        