import math
import copy
import json

from OpenGL.GL import *

from Box2D import *

from utils.opengl import *
from utils import *

        

class Player():
    def __init__(self, keyAdapter, world, position):
        self.keyAdapter = keyAdapter
        self.world = world
        
        self.fuel = 50.0
        
        w = 1.0
        h = 2.5

        self.body = self.world.CreateDynamicBody(
            position=position,
            userData=self,
            fixtures=b2FixtureDef(
                shape=b2PolygonShape(box=(1.0, 1.5)),
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
        
        if pressed("right"):
            if abs(self.body.angularVelocity) <= 3.0:
                self.body.ApplyAngularImpulse(-5.0, True)
            self.wasRotating = True
        elif pressed("left"):
            if abs(self.body.angularVelocity) <= 3.0:
                self.body.ApplyAngularImpulse(5.0, True)
            self.wasRotating = True
        elif self.wasRotating:
            self.body.angularVelocity = 0
            self.wasRotating = False

        if self.fuel > 0.0 and pressed("up"):
            if pressed("shift"):
                f = self.body.GetWorldVector(localVector=(0.0, 200.0*0.5))
                self.fuel -= 3 * dt
            else:
                f = self.body.GetWorldVector(localVector=(0.0, 100.0*0.5))
                self.fuel -= 1 * dt
            p = self.body.GetWorldPoint(localPoint=(0.0, 0.0))
            self.body.ApplyForce(f, p, True)
            self.fuel = max(0.0, self.fuel)


        
    def render(self):
        glColor3f(1.0, 1.0, 1.0)
        TextureManager.instance()["textures/rocket"].bind()
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
        
        
    def __unicode__(self):
        return "Player<>"
    
    def __str__(self):
        return "Player<>"
    

            
        