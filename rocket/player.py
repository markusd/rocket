import math
import copy
import json

from OpenGL.GL import *

from Box2D import *

from utils.opengl import *
from utils import *

from rocket.object import Missile

class Player():
    def __init__(self, keyAdapter, mouse, world, level, position):
        self.keyAdapter = keyAdapter
        self.world = world
        self.level = level
        self.mouse = mouse
        
        self.fuel = 500.0
        self.possessions = []
        self.rockets = 100
        self.elapsed_since_rocket = 0
        
        w = 1.0
        h = 2.5

        self.body = self.world.CreateDynamicBody(
            position=position,
            userData=self,
            fixtures=b2FixtureDef(
                #shape=b2PolygonShape(box=(1.0, 1.5)),
                shape=b2PolygonShape(vertices=[(-1, -1.5), (1, -1.5), (1, 0), (0, 1.5), (-1, 0)]),
                density=1,
                angularDamping=50,
                friction=5,
                #linearDamping=0.1,
            )
        )
        
        w*=2.5
        h*=1.5
        
        self.size =   [([0.0, 1.0], [-w*0.5,  h*0.5]),
                       ([0.0, 0.0], [-w*0.5, -h*0.5-1]),
                       ([1.0, 0.0], [ w*0.5, -h*0.5-1]),
                       ([1.0, 1.0], [ w*0.5,  h*0.5])]
        
        self.wasRotating = False
        
    def update(self, dt):
        pressed = lambda x: x in self.keyAdapter.pressed
        
        self.elapsed_since_rocket += dt
        
        if pressed("right") or pressed("d"):
            if abs(self.body.angularVelocity) <= 3.0:
                self.body.ApplyAngularImpulse(-5.0, True)
            self.wasRotating = True
        elif pressed("left") or pressed("a"):
            if abs(self.body.angularVelocity) <= 3.0:
                self.body.ApplyAngularImpulse(5.0, True)
            self.wasRotating = True
        elif self.wasRotating:
            self.body.angularVelocity = 0
            self.wasRotating = False

        if self.fuel > 0.0 and (pressed("up") or pressed("w")):
            if pressed("shift"):
                f = self.body.GetWorldVector(localVector=(0.0, 500.0*0.5))
                self.fuel -= 3 * dt
            else:
                f = self.body.GetWorldVector(localVector=(0.0, 100.0*0.5))
                self.fuel -= 1 * dt
            p = self.body.GetWorldPoint(localPoint=(0.0, 0.0))
            self.body.ApplyForce(f, p, True)
            self.fuel = max(0.0, self.fuel)
            
        if pressed(" ") and self.elapsed_since_rocket > 1.0 and self.rockets > 0:
            self.rockets -= 1
            self.elapsed_since_rocket = 0
            
            position = self.body.transform.position
            #dir = Vec2d(0.0, 1.0)
            #dir.rotate(self.body.transform.angle * 180.0/3.14)
            #dir = b2Vec2(dir.x, dir.y)
            target = self.mouse["wpos"]()
            target = b2Vec2(target[0], target[1])
            dir = target - position
            dir.Normalize()
            position = position + dir * 3
        
            missile = Missile.launch(world=self.world, target=None, position=position, velocity=dir * 50)
            self.level.objects.append(missile)
        
    def render(self):
        pressed = lambda x: x in self.keyAdapter.pressed
        texture = "textures/rocket-idle"
        if pressed("up") or pressed("left") or pressed("right") or pressed("a") or pressed("w") or pressed("d"):
            texture = "textures/rocket"
            if pressed("shift"):
                texture = "textures/rocket-afterburner"
        
        glColor3f(1.0, 1.0, 1.0)
        TextureManager.instance()[texture].bind()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glPushMatrix()
        glTranslatef(self.body.transform.position.x, self.body.transform.position.y, 0.0)
        glRotatef(self.body.transform.angle * 180.0/3.14, 0.0, 0.0, 1.0)
        glBegin(GL_QUADS)
        for v in self.size:
            glTexCoord2fv(v[0]) ; glVertex2fv(v[1])
        glEnd()
        glPopMatrix()
        glDisable(GL_TEXTURE_2D)
    

            
        