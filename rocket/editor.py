# -*- coding: utf-8 -*-

import math

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLX import *

from PyQt4 import QtCore, QtOpenGL
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4.QtCore import QCoreApplication
from PyQt4.QtOpenGL import *

from Box2D import *

from utils import *
from utils.opengl import *

from rocket.renderer import Renderer
from rocket.clouds import CloudManager
from rocket.level import Level

VIEWPORT_WIDTH = 768*2
VIEWPORT_HEIGHT = 512*2

class Editor(QMainWindow):
    
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        
        self.modified = True
        self.tmpFile = None
        self.fileName = ""

        self.setWindowTitle("rocket - Editor")
        self.createMenu()
        
        self.viewport = Viewport(self)
        self.toolbox = Toolbox(self)
        
        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.insertWidget(0, self.toolbox)
        splitter.insertWidget(1, self.viewport)

        #splitter.setSizes([200, 1300])
        #splitter.setStretchFactor(0, 1)
        #splitter.setStretchFactor(1, 1)
        #splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        #self.showMaximized()
        self.show()
        #self.viewport.updateGL()
        #self.viewport.timer.start()
        
    def createMenu(self):
        
        menuFile = self.menuBar().addMenu("&File")
        
        newLevel = QAction("&New", self)
        newLevel.setShortcuts(QKeySequence.New)
        QtCore.QObject.connect(newLevel, QtCore.SIGNAL('triggered()'), self.onNewPressed)
        
        menuFile.addAction(newLevel)
        
        openLevel = QAction("&Open", self)
        openLevel.setShortcuts(QKeySequence.Open)
        QtCore.QObject.connect(openLevel, QtCore.SIGNAL('triggered()'), self.onOpenPressed)
        menuFile.addAction(openLevel)
        
        save = QAction("&Save", self)
        save.setShortcuts(QKeySequence.Save)
        QtCore.QObject.connect(save, QtCore.SIGNAL('triggered()'), self.onSavePressed)
        menuFile.addAction(save)
        
        self.saveas = QAction("Save &As", self)
        self.saveas.setShortcuts(QKeySequence.SaveAs)
        QtCore.QObject.connect(self.saveas, QtCore.SIGNAL('triggered()'), self.onSavePressed)
        menuFile.addAction(self.saveas)
        
        menuFile.addSeparator()
        
        exitEditor = QAction("E&xit", self)
        exitEditor.setShortcuts(QKeySequence.Quit)
        QtCore.QObject.connect(exitEditor, QtCore.SIGNAL('triggered()'), self.onClosePressed)
        menuFile.addAction(exitEditor)
        
    def onNewPressed(self):
        input, ok = QInputDialog.getText(self, "Level Name", "Name", text="Test")
        if not ok:
            return
        self.viewport.createWorld()
        self.viewport.createLevel(input)
    
    def onOpenPressed(self):
        od = QFileDialog(self)
        od.setAcceptMode(QFileDialog.AcceptOpen)
        od.setFileMode(QFileDialog.ExistingFile)
        od.setDirectory("data/levels/")
        od.setFilter("rocket (*.json)")
        
        if od.exec_():
            self.fileName = str(od.selectedFiles()[0])
            self.modified = False
            self.viewport.level.deserialize(self.fileName)
    
    def onSavePressed(self):
        if self.fileName == "" or self.sender() == self.saveas:
            self.fileName = str(QFileDialog.getSaveFileName(self, "rocket - Editor - Save file", "data/levels/", "rocket (*.json)"))
        self.modified = False
        self.viewport.level.serialize(self.fileName)
    
    def onClosePressed(self):
        msgBox = QMessageBox()
        msgBox.setText("Do you want to exit rocket - Editor?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.No)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            self.close()
        
class Toolbox(QWidget):
    
    def __init__(self, parent):
        QGLWidget.__init__(self, parent)
        self.editor = parent
        
        self.setMaximumWidth(300)
        self.setMinimumWidth(300)
        

class Viewport(QGLWidget):
    '''
    Widget for drawing two spirals.
    '''
    
    def __init__(self, parent):
        QGLWidget.__init__(self, parent)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)
        
        self.editor = parent
        
        self.frames = 0
        self.fps = 0
        self.elapsed = 0.0
        self.clock = Clock()
        
        self.zoom = 10.0
        self.offset = (0, 0)
        
        self.keyAdapter = KeyAdapter()
        self.setMouseTracking(True)
        
        self.mouse = { "pos": (0, 0), QtCore.Qt.LeftButton: False, QtCore.Qt.RightButton: False, QtCore.Qt.MidButton: False,
                      "wpos": lambda: ((self.mouse["pos"][0] - VIEWPORT_WIDTH*0.5 - self.offset[0])/self.zoom, (self.mouse["pos"][1] - VIEWPORT_HEIGHT*0.5 - self.offset[1])/self.zoom),
                      "double_clicked": { QtCore.Qt.LeftButton: False, QtCore.Qt.RightButton: False, QtCore.Qt.MidButton: False} , "press_pos": (0, 0)
        }
        
        self.selectedPoints = []
        
        self.timer = QtCore.QTimer(self)
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL('timeout()'), self.updateGL)
        
        self.setMinimumSize(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)

    
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-w * 0.5, w * 0.5, -h * 0.5, h * 0.5, 0, 128)
        #glOrtho(0, w, 0, h, 0, 128)
        glMatrixMode(GL_MODELVIEW)
        
        print("Resize to %sx%s" % (w, h))
        
    def createWorld(self):
        self.world = b2World(gravity=(0, -9.81*0.5), doSleep=True)
        self.world.warmStarting = True
        self.world.continuousPhysics = True
        self.world.subStepping = False
        self.world.renderer = Renderer()
        
    def createLevel(self, name):
        self.level = Level(self.keyAdapter, self.world, name)
    
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
        
        self.createWorld()
        self.createLevel("New Level")

        self.textureManager = TextureManager.instance()
        self.textureManager.loadFromFolder("data/textures/*.png", "textures")
        self.textureManager.loadFromFolder("data/textures/background/*.png", "textures/background")
        
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
    
    def mouseMoveEvent(self, e):
        new = (e.pos().x(), self.height() - e.pos().y())
        if self.mouse[QtCore.Qt.RightButton]:
            dx = self.mouse["pos"][0] - new[0]
            dy = self.mouse["pos"][1] - new[1]
            self.offset = (self.offset[0] - dx, self.offset[1] - dy)
        self.mouse["pos"] = new
        
        
        

    def mousePressEvent(self, e):
        self.mouse["pos"] = (e.pos().x(), self.height() - e.pos().y())
        self.mouse["press_pos"] = self.mouse["pos"]
        self.mouse[e.button()] = True
        self.mouse["double_clicked"][e.button()] = False
        
    def mouseReleaseEvent(self, e):
        pressed = lambda x: x in self.keyAdapter.pressed
        
        self.mouse["pos"] = (e.pos().x(), self.height() - e.pos().y())
        self.mouse[e.button()] = False
        
        if e.button() == QtCore.Qt.LeftButton:
            if self.mouse["pos"] == self.mouse["press_pos"]:
                if not self.mouse["double_clicked"][QtCore.Qt.LeftButton]:
                    if pressed("s"):
                        self.level.spawnPoint = self.mouse["wpos"]()
                    else:
                        self.selectedPoints.append(self.mouse["wpos"]())
            
        print(self.selectedPoints)
    
    def mouseDoubleClickEvent(self, e):
        self.mouse["pos"] = (e.pos().x(), self.height() - e.pos().y())
        self.mouse["double_clicked"][e.button()] = True
        
        if e.button() == QtCore.Qt.LeftButton:
        #    self.selectedPoints.append(self.mouse["wpos"]())
            print(self.selectedPoints)
            self.level.edgeFixtures.CreateEdgeChain(self.selectedPoints)
            self.level.list = -1
            self.selectedPoints = []
        
        
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
            
        glColor4f(0.0, 0.0, 1.0, 0.15)
        glLineWidth(1.0)
        glPushMatrix()
        glTranslatef(self.offset[0], self.offset[1], 0)
        glBegin(GL_LINES)
        for x in range(-250, 250):
            glVertex2f(x * 32.0, -10000.0)
            glVertex2f(x * 32.0,  10000.0)
            glVertex2f(-10000.0, x * 32.0)
            glVertex2f( 10000.0,  x * 32.0)
        glEnd()
        
        glColor3f(1.0, 0.0, 0.0)
        glPointSize(3.0)
        glBegin(GL_POINTS)
        glVertex2f(self.level.spawnPoint[0]*self.zoom, self.level.spawnPoint[1]*self.zoom)
        glEnd()
        glPopMatrix()
            
        #self.world.renderer.StartDraw(center=self.offset, zoom=self.zoom, screen=(self.width(), self.height()))
        #self.world.DrawDebugData()
        #self.world.renderer.EndDraw()

        glPushMatrix()
        glTranslatef(self.offset[0], self.offset[1], 0)
        glScale(self.zoom, self.zoom, 1)
        self.level.render()
        glPopMatrix()
