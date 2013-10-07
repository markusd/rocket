import sys
import json

from Box2D import *
from OpenGL.GL import *

from utils.opengl import TextureManager
from utils import nested_merge

class Object():

    def __init__(self, world):
        self.world = world
        self.name = "New Object"
        self.type = "static"
        self.list = -1
        
    #def serialize(self, fileName):
    #    raise NotImplementedError()
    #    object = {}
    #    
    #    fp = open(fileName, "w")
    #    json.dump(object, fp, sort_keys=True, indent=4)
    #    fp.close()
    
    @staticmethod
    def loadFromFile(world, fileName, position=(0, 0), **kwargs):
        fp = open(fileName, "r")
        object = json.load(fp)
        fp.close()
        
        splitted = object["class"].rsplit(".", 1)
        cls = getattr(sys.modules[splitted[0]], splitted[-1])
        result = cls(world)
        result._deserialize(object, position, **kwargs)
        return result
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.name = obj["name"]
        self.type = obj["type"]
        
        if self.type == "static":
            self.body = self.world.CreateStaticBody(position=position, userData=self)
        else:
            raise NotImplementedError()
        
        for f in obj["fixtures"]:
            if f["type"] == "box":
                size = f["size"]
                if f.get("auto-create", True):
                    self.body.CreatePolygonFixture(box=(size[0]*0.5, size[1]*0.5), isSensor=f["sensor"], userData=f)
            else:
                raise NotImplementedError()
            
    def buildList(self):
        if self.list > -1:
            glDeleteLists(self.list, 1)
        self.list = glGenLists(1)
        glNewList(self.list, GL_COMPILE)
       
        for f in self.body:
            if f.sensor:
                continue
            texture = TextureManager.instance().get(f.userData["texture"], None)
            if texture:
                glEnable(GL_TEXTURE_2D)
                glEnable(GL_BLEND)
                texture.bind()
            size = f.userData["size"]
            glBegin(GL_QUADS)
            #glTexCoord2f(0, 0) ; glVertex2f(-size[0]*0.5 + self.body.transform.position.x, -size[1]*0.5 + self.body.transform.position.y)
            #glTexCoord2f(1, 0) ; glVertex2f( size[0]*0.5 + self.body.transform.position.x, -size[1]*0.5 + self.body.transform.position.y)
            #glTexCoord2f(1, 1) ; glVertex2f( size[0]*0.5 + self.body.transform.position.x,  size[1]*0.5 + self.body.transform.position.y)
            #glTexCoord2f(0, 1) ; glVertex2f(-size[0]*0.5 + self.body.transform.position.x,  size[1]*0.5 + self.body.transform.position.y)
            
            glTexCoord2f(0, 0) ; glVertex2f(f.shape.vertices[0][0] + self.body.transform.position.x, f.shape.vertices[0][1] + self.body.transform.position.y)
            glTexCoord2f(1, 0) ; glVertex2f(f.shape.vertices[1][0] + self.body.transform.position.x, f.shape.vertices[1][1] + self.body.transform.position.y)
            glTexCoord2f(1, 1) ; glVertex2f(f.shape.vertices[2][0] + self.body.transform.position.x, f.shape.vertices[2][1] + self.body.transform.position.y)
            glTexCoord2f(0, 1) ; glVertex2f(f.shape.vertices[3][0] + self.body.transform.position.x, f.shape.vertices[3][1] + self.body.transform.position.y)
            glEnd()
        glEndList()
        
    def render(self):
        if self.list == -1:
            self.buildList()
        glCallList(self.list)
        
    def update(self, dt):
        pass
        
        
class Door(Object):

    def __init__(self, world, position=(0, 0)):
        super(Door, self).__init__(world)
        self.doorFixture = None
        self.opening = False
        self.closing = False
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.name = obj["name"]
        self.type = obj["type"]
        self.speed = obj["speed"]
        self.direction = obj["direction"]
        self.door_index = obj["door_index"]
        
        if self.type == "default":
            self.body = self.world.CreateStaticBody(position=position, userData=self)
        else:
            raise NotImplementedError()
        
        for f in obj["fixtures"]:
            if f["type"] == "box":
                size = f["size"]
                if f.get("auto-create", True):
                    self.body.CreatePolygonFixture(box=(size[0]*0.5, size[1]*0.5), isSensor=f["sensor"], userData=f)
            else:
                raise NotImplementedError()
            
        self.size = obj["fixtures"][self.door_index]["size"]
        self.state = obj["state"]
        
    def isOpened(self):
        return self._state == 0.0
    
    def isClosed(self):
        return self._state == 1.0
    
    def open(self):
        if not self.isOpened():
            self.opening = True
            self.closing = False
            
    def close(self):
        if not self.isClosed():
            self.closing = True
            self.opening = False
        
    def setState(self, value):
        old = getattr(self, "_state", None)
        self._state = min(1.0, max(0.0, value))
        
        if self.isOpened():
            self.opening = False
        elif self.isClosed():
            self.closing = False
                
        if old == self._state:
            return

        if self.doorFixture:
            self.body.DestroyFixture(self.doorFixture)
            self.doorFixture = None
        
        size = (self.size[0] * self._state, self.size[1])
        position = (self.direction * (1.0 - self._state) * self.size[0] * 0.5, 0)
        f = { "size": size, "texture": "textures/platform" }
        self.body.CreatePolygonFixture(box=(size[0]*0.5, size[1]*0.5, position, 0), userData=f)
        self.doorFixture = self.body.fixtures[-1]
        self.buildList()
        
    state = property(lambda self: self._state, setState)

    def update(self, dt):
        if self.opening:
            self.state -= self.speed * dt
        elif self.closing:
            self.state += self.speed * dt
        else:
            self.close()
                