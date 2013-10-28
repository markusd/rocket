import sys
import json

from Box2D import *
from OpenGL.GL import *

from utils.opengl import TextureManager
from utils import nested_merge
from Box2D.Box2D import b2Vec2
import random


def create_polygon_fixture(body, fixture):
    if fixture["type"] == "box":
        size = fixture["size"]
        fpos = fixture.get("position", (0, 0))
        fangle = fixture.get("angle", 0)
        density = fixture.get("density", 1)
        sensor = fixture.get("sensor", False)
        if fixture.get("auto-create", True):
            body.CreatePolygonFixture(box=(size[0]*0.5, size[1]*0.5, fpos, fangle), isSensor=sensor, density=density, userData=fixture)
    else:
        raise NotImplementedError()
    
def launchProjectile(level, position, range, missile=False):
    player = level.player
    if player is None:
        return
    
    position = b2Vec2(position[0], position[1])
    distance = (player.body.transform.position - position).Normalize()
    dir = (player.body.transform.position + player.body.linearVelocity*0.5) - position
    if dir.Normalize() < range:
        position = position + dir * 3
        
        if missile:
            obj = Missile.launch(world=level.world, target=player, position=position, velocity=dir * 50, agility=random.uniform(0.2, 2))
            level.objects.append(obj)
        else:
            obj = Missile.launch(world=level.world, target=None, position=position, velocity=dir * 50)
            level.objects.append(obj)

class Object():

    def __init__(self, world):
        self.world = world
        self.name = "New Object"
        self.type = "static"
        self.list = -1
        
        
    def destroy(self):
        body = getattr(self, "body", None)
        if body is not None:
            self.world.DestroyBody(body)
        
    #def serialize(self, fileName):
    #    raise NotImplementedError()
    #    object = {}
    #    
    #    fp = open(fileName, "w")
    #    json.dump(object, fp, sort_keys=True, indent=4)
    #    fp.close()
    
    def getDict(self):
        result = dict(self.creationParameters)
        result["filename"] = self.fileName
        result["position"] = self.position
        return result
    
    @staticmethod
    def loadFromFile(world, fileName, position=(0, 0), **kwargs):
        fp = open(fileName, "r")
        object = json.load(fp)
        fp.close()
        
        splitted = object["class"].rsplit(".", 1)
        cls = getattr(sys.modules[splitted[0]], splitted[-1])
        result = cls(world)
        result.fileName = fileName
        result._deserialize(object, position, **kwargs)
        return result
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.creationParameters = obj
        
        self.name = obj["name"]
        self.type = obj["type"]
        self.position = position
        
        if self.type == "static":
            self.body = self.world.CreateStaticBody(position=position, userData=self)
        else:
            self.body = self.world.CreateDynamicBody(position=position, userData=self)
        
        for f in obj["fixtures"]:
            create_polygon_fixture(self.body, f)
            
    def buildList(self, render=False):
        if self.list == -1:
            self.list = glGenLists(1)
        glNewList(self.list, GL_COMPILE_AND_EXECUTE if render else GL_COMPILE)
       
        for f in self.body:
            if f.sensor:
                continue
            texture = TextureManager.instance().get(f.userData["texture"], None)
            if texture:
                glEnable(GL_TEXTURE_2D)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                texture.bind()
            size = f.userData["size"]
            glBegin(GL_QUADS)
            px = self.body.transform.position.x if self.type == "static" else 0
            py = self.body.transform.position.y if self.type == "static" else 0
            glTexCoord2f(0, 0) ; glVertex2f(f.shape.vertices[0][0] + px, f.shape.vertices[0][1] + py)
            glTexCoord2f(1, 0) ; glVertex2f(f.shape.vertices[1][0] + px, f.shape.vertices[1][1] + py)
            glTexCoord2f(1, 1) ; glVertex2f(f.shape.vertices[2][0] + px, f.shape.vertices[2][1] + py)
            glTexCoord2f(0, 1) ; glVertex2f(f.shape.vertices[3][0] + px, f.shape.vertices[3][1] + py)
            glEnd()
        glEndList()
        
    def render(self):
        if self.list == -1:
            self.buildList(render=self.type == "static")
        elif self.type == "static":
            glCallList(self.list)

        if self.type == "dynamic":
            glPushMatrix()
            glTranslatef(self.body.transform.position.x, self.body.transform.position.y, 0.0)
            glRotatef(self.body.transform.angle * 180.0/3.14, 0.0, 0.0, 1.0)
            glCallList(self.list)
            glPopMatrix()
        
    def update(self, dt):
        return None
        
        
class Door(Object):

    def __init__(self, world, position=(0, 0)):
        super(Door, self).__init__(world)
        self.doorFixture = None
        self.opening = False
        self.closing = False
        self.destroyingFixture = False
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.creationParameters = obj
        
        self.name = obj["name"]
        self.type = obj["type"]
        self.speed = obj["speed"]
        self.direction = obj["direction"]
        self.door_index = obj["door_index"]
        self.position = position
        
        self.body = self.world.CreateStaticBody(position=position, userData=self)
        
        for f in obj["fixtures"]:
            create_polygon_fixture(self.body, f)
            
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
            self.destroyingFixture = True
            self.body.DestroyFixture(self.doorFixture)
            self.destroyingFixture = False
            self.doorFixture = None
        
        size = (self.size[0] * (self._state if self.direction[0] != 0 else 1), self.size[1] * (self._state if self.direction[1] != 0 else 1))
        position = (self.direction[0] * (1.0 - self._state) * self.size[0] * 0.5, self.direction[1] * (1.0 - self._state) * self.size[1] * 0.5)
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
        return None
            
            
class Cannon(Object):

    def __init__(self, world, position=(0, 0)):
        super(Cannon, self).__init__(world)
        self.elapsed = 0
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.creationParameters = obj
        
        self.name = obj["name"]
        self.type = obj["type"]
        self.range = obj["range"]
        self.position = position
        
        self.body = self.world.CreateStaticBody(position=position, userData=self)
        
        for f in obj["fixtures"]:
            create_polygon_fixture(self.body, f)
            


    def update(self, dt):
        self.elapsed += dt
        if self.elapsed > 1.75:
            self.elapsed -= 1.75
            return lambda l: launchProjectile(l, self.position, self.range, missile=True)
        
class Missile(Object):
    
    def __init__(self, world, position=(0, 0)):
        super(Missile, self).__init__(world)
        self.type = "dynamic"
        self.elapsed = 0
        self.agility = 1
        
    @staticmethod
    def launch(world, target=None, position=(0,0), velocity=(0,0), agility=1):
        obj = Missile(world)
        obj.body = world.CreateDynamicBody(position=position, userData=obj, gravityScale=0)
        #obj.target = target
        obj.mass = 50
        obj.agility = agility
        f = { "size": (0.5, 0.5), "texture": "textures/red", "type": "box", "density": obj.mass, "touching": [{"action": "destroy"}] }
        create_polygon_fixture(obj.body, f)
        obj.body.linearVelocity = velocity
        return obj
        
    def _deserialize(self, obj, position=(0, 0), **kwargs):
        obj = nested_merge(kwargs.get("extension", dict()), obj)
        
        self.creationParameters = obj
        
        self.name = obj["name"]
        self.type = obj["type"]
        self.position = position
        
        self.body = self.world.CreateDynamicBody(position=position, userData=self)
        
        for f in obj["fixtures"]:
            create_polygon_fixture(self.body, f)

    def update(self, dt):
        self.elapsed += dt
        if getattr(self, "target", None) is not None and self.elapsed > 0.05:
            self.elapsed -= 0.05

            position = self.body.transform.position
            distance = (self.target.body.transform.position - position).Normalize()
            dir = (self.target.body.transform.position) - position
            dir.Normalize()
            #self.body.linearVelocity = dir * 50
        
            force = self.body.GetWorldVector(localVector=dir*self.mass*self.agility)
            point = self.body.GetWorldPoint(localPoint=(0.0, 0.0))
            self.body.ApplyLinearImpulse(force, point, True)
            
            self.body.linearVelocity.Normalize()
            self.body.linearVelocity *= 30
            self.body.angularVelocity = 0