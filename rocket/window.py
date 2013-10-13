# -*- coding: utf-8 -*-

import math

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLX import *
from OpenGL.GLUT import *

from PyQt4 import QtCore, QtOpenGL
from PyQt4 import QtGui
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtOpenGL import *

from Box2D import *

from utils import *
from utils.opengl import *

from rocket.player import Player
from rocket.renderer import Renderer
from rocket.clouds import CloudManager
from rocket.level import Level
from rocket.object import Object, Door

VIEWPORT_WIDTH = 768*2
VIEWPORT_HEIGHT = 512*2

class Main(QGLWidget, b2ContactListener):

    def __init__(self):
        QGLWidget.__init__(self)
        
        self.frames = 0
        self.fps = 0
        self.elapsed = 0.0
        self.clock = Clock()
        
        self.zoom = 10.0
        self.offset = (0, 0)
        
        self.keyAdapter = KeyAdapter()
        
        self.timer = QtCore.QTimer(self)
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL('timeout()'), self.updateGL)
        
        #self.showFullScreen()

        self.setMinimumSize(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
        self.setMaximumSize(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
        
        # Position the window in the center of the screen
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
        self.showMaximized()
        
    def createWorld(self):
        self.world = b2World(gravity=(0, -9.81*0.5), doSleep=True)
        self.world.warmStarting = True
        self.world.continuousPhysics = True
        self.world.subStepping = False
        self.world.renderer = Renderer()
        
    def createLevel(self, name):
        self.level = Level(self.keyAdapter, self.world)
        self.level.deserialize(name)
        self.player = Player(self.keyAdapter, self.world, self.level.spawnPoint)
        self.level.player = self.player
        return
        self.level.objects.append(Object.loadFromFile(world=self.world, fileName="data/objects/platform.json",
            position=(0, 0), extension={"fixtures":[{"touching":[{"options":{"rate": 10}}], "size": [25, 4]}]}))
        self.level.objects.append(Object.loadFromFile(world=self.world, fileName="data/objects/door.json",
            position=(-14.5, 25)))
        self.level.objects.append(Object.loadFromFile(world=self.world, fileName="data/objects/key.json",
            position=(18, 10)))
        self.level.objects.append(Object.loadFromFile(world=self.world, fileName="data/objects/blower.json",
            position=(140,60)))
        
    def resizeGL(self, w, h): 
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-w * 0.5, w * 0.5, -h * 0.5, h * 0.5, 0, 128)
        #glOrtho(0, w, 0, h, 0, 128)
        glMatrixMode(GL_MODELVIEW)
        
        print("Resize to %sx%s" % (w, h))
        
    
    def initializeGL(self):
        if bool(glXSwapIntervalSGI):
            glXSwapIntervalSGI(0)
        elif bool(glXSwapIntervalMESA):
            glXSwapIntervalMESA(0)
        else:
            print("Error: Could not disable vsync")
            
        # set viewing projection
        glClearColor(0.29803922, 0.4, 1.0, 1.0)
        glClearDepth(1.0)
        
        glutInit([""])
        self.createWorld()

        self.textureManager = TextureManager.instance()
        self.textureManager.loadFromFolder("data/textures/*.png", "textures")
        self.textureManager.loadFromFolder("data/textures/background/*.png", "textures/background")
        self.cloudManager = CloudManager(screen=(self.width(), self.height()), maxClouds=8)
        #self.cloudManager.createCloud(Vec2d(0, 0), 200, 200)
        
        self.timer.start()
        self.clock.reset()
        
    def keyPressEvent(self, e):
        pressed = lambda x: x in self.keyAdapter.pressed
        
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        
        self.keyAdapter.keyEvent(e)
        
        if pressed("+"):
            #self.zoom += 1.0
            self.offset = (self.offset[0] + 10, self.offset[1])
            
        if pressed("-"):
            self.offset = (self.offset[0] - 10, self.offset[1])
            #self.zoom -= 1.0
        
    def keyReleaseEvent(self, e):
        self.keyAdapter.keyEvent(e)

    def paintGL(self):  
        dt = self.clock.get()

        self.elapsed += dt
        self.clock.reset()
        self.frames += 1

        if self.elapsed > 1.0:
            self.fps = self.frames
            self.frames = 0
            self.elapsed -= 1.0
            self.setWindowTitle("FPS: %s" % self.fps)
            #print(self.player.body.transform.position)
            
        self.level.update(dt)
        self.player.update(dt)
            
        self.world.Step(dt, 8, 3)
        self.world.ClearForces()
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glDisable(GL_TEXTURE_2D)
        
        if self.world.renderer:
            self.world.renderer.flags=dict(
                    drawShapes = True,
                    drawJoints = False,
                    drawAABBs  = False,
                    drawPairs  = False,
                    drawCOMs   = False,
                    convertVertices = True)
            
            
        self.cloudManager.render(dt, self.offset, self.player.body.linearVelocity)
        self.world.renderer.StartDraw(center=self.offset, zoom=self.zoom, screen=(self.width(), self.height()))
        self.world.DrawDebugData()
        self.world.renderer.EndDraw()
        
        
        glPushMatrix()
        """
        glBegin(GL_LINE_LOOP)
        glVertex2f(-VIEWPORT_WIDTH*0.5+200, VIEWPORT_HEIGHT*0.5-200)
        glVertex2f( VIEWPORT_WIDTH*0.5-200, VIEWPORT_HEIGHT*0.5-200)
        glVertex2f( VIEWPORT_WIDTH*0.5-200, -VIEWPORT_HEIGHT*0.5+200)
        glVertex2f(-VIEWPORT_WIDTH*0.5+200, -VIEWPORT_HEIGHT*0.5+200)
        glEnd()
        glBegin(GL_LINE_LOOP)
        glVertex2f(-175, -175)
        glVertex2f( 175, -175)
        glVertex2f( 175,  175)
        glVertex2f(-175,  175)
        glEnd()
        glBegin(GL_LINE_LOOP)
        glVertex2f(-250, -250)
        glVertex2f( 250, -250)
        glVertex2f( 250,  250)
        glVertex2f(-250,  250)
        glEnd()
        glBegin(GL_LINE_LOOP)
        glVertex2f(-100, -100)
        glVertex2f( 100, -100)
        glVertex2f( 100,  100)
        glVertex2f(-100,  100)
        glEnd()
        """
        glTranslatef(self.offset[0], self.offset[1], 0)

        glScale(self.zoom, self.zoom, 1)
        self.level.render()
        self.player.render()
        #self.object.render()
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(-VIEWPORT_WIDTH*0.5 + 10, VIEWPORT_HEIGHT*0.5 - 20, 0)
        glScalef(0.1, 0.1, 1)
        for c in "Fuel: %.2f%%" % self.player.fuel:
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))
        glPopMatrix()
        
        
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] > VIEWPORT_WIDTH*0.5 - 200:
            self.offset = (self.offset[0] - 500*dt, self.offset[1])
            
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] < -VIEWPORT_WIDTH*0.5 + 200:
            self.offset = (self.offset[0] + 500*dt, self.offset[1])
            
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] > VIEWPORT_HEIGHT*0.5 - 200:
            self.offset = (self.offset[0], self.offset[1] - 500*dt)
            
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] < -VIEWPORT_HEIGHT*0.5 + 200:
            self.offset = (self.offset[0], self.offset[1] + 500*dt)
            
            
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] > 100:
            self.offset = (self.offset[0] - 50*dt, self.offset[1])
            
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] < -100:
            self.offset = (self.offset[0] + 50*dt, self.offset[1])
        
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] > 100:
            self.offset = (self.offset[0], self.offset[1] - 50*dt)
            
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] < -100:
            self.offset = (self.offset[0], self.offset[1] + 50*dt)
            

        if self.player.body.transform.position[0]*self.zoom + self.offset[0] > 175:
            self.offset = (self.offset[0] - 100*dt, self.offset[1])
            
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] < -175:
            self.offset = (self.offset[0] + 100*dt, self.offset[1])
        
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] > 175:
            self.offset = (self.offset[0], self.offset[1] - 100*dt)
            
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] < -175:
            self.offset = (self.offset[0], self.offset[1] + 100*dt)


        if self.player.body.transform.position[0]*self.zoom + self.offset[0] > 250:
            self.offset = (self.offset[0] - 200*dt, self.offset[1])
            
        if self.player.body.transform.position[0]*self.zoom + self.offset[0] < -250:
            self.offset = (self.offset[0] + 200*dt, self.offset[1])
        
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] > 250:
            self.offset = (self.offset[0], self.offset[1] - 200*dt)
            
        if self.player.body.transform.position[1]*self.zoom + self.offset[1] < -250:
            self.offset = (self.offset[0], self.offset[1] + 200*dt)
