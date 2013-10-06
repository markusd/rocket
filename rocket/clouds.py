from utils.opengl import TextureManager
from utils import Vec2d

from OpenGL.GL import *
import random
from math import sin

class CloudManager(object):

    def __init__(self, screen, maxClouds=5):
        self.screen = Vec2d(screen)
        self.offset = Vec2d(0, 0)
        self.clouds = []
        self.maxClouds = maxClouds
        for i in range(self.maxClouds):
            self.createCloud(initial=True)
        
    def createCloud(self, pos=None, left=False, top=False, texture=None, w=None, h=None, vel=None, tide=None, age=None, initial=False):
        if pos is None:
            pos = Vec2d(0, 0)
            
            if initial:
                pos.x = random.randint(int(self.offset[0]) - self.screen[0]/2 - 260,
                                       int(self.offset[0]) + self.screen[0]/2 + 260)
                pos.y = random.randint(int(self.offset[1]) - self.screen[1]/2 - 260,
                                       int(self.offset[1]) + self.screen[1]/2 + 260)
            elif left is not None or top is not None:
                if left is not None and left is True:
                    pos.x = -self.offset[0] - self.screen[0]/2 - 260
                    pos.y = random.randint(int(self.offset[1]) - self.screen[1]/2 - 260,
                                           int(self.offset[1]) + self.screen[1]/2 + 260)
                elif left is not None and left is False:
                    pos.x = -self.offset[0] + self.screen[0]/2 + 260
                    pos.y = random.randint(int(self.offset[1]) - self.screen[1]/2 - 260,
                                           int(self.offset[1]) + self.screen[1]/2 + 260)
                elif top is not None and top is True:
                    pos.x = random.randint(int(self.offset[0]) - self.screen[0]/2 - 260,
                                           int(self.offset[0]) + self.screen[0]/2 + 260)
                    pos.y = -self.offset[1] + self.screen[1]/2 + 260
                elif top is not None and top is False:
                    pos.x = random.randint(int(self.offset[0]) - self.screen[0]/2 - 260,
                                           int(self.offset[0]) + self.screen[0]/2 + 260)
                    pos.y = -self.offset[1] - self.screen[1]/2 - 260
            else:
                if bool(random.getrandbits(1)):
                    pos.x = -self.offset[0] - self.screen[0]/2 - 260                     
                else:
                    pos.x = -self.offset[0] + self.screen[0]/2 + 260
                if bool(random.getrandbits(1)):
                    pos.y = -self.offset[1] - self.screen[1]/2 - 260                    
                else:
                    pos.y = -self.offset[1] + self.screen[1]/2 + 260


            
        if texture is None:
            options = [n for n in TextureManager.instance().keys() if n.startswith("textures/background/cloud")]
            texture = options[random.randint(0, len(options)-1)]
        
        if w is None and h is None:
            w = random.randint(150, 250)
            h = w
        elif w is None:
            w = h
        else:
            h = w
            
        if vel is None:
            vel = random.randint(5, 25)
            
        if tide is None:
            tide = random.randint(0, 10)
            
        if age is None:
            age = random.randint(0, 315) / 100.0
            
        self.clouds.append({
            "pos": pos,
            "w": w,
            "h": h,
            "vel": vel,
            "age": age,
            "tide": tide,
            "texture": texture,
            "size": [([0.0, 1.0], [-w*0.5,  h*0.5]),
                     ([0.0, 0.0], [-w*0.5, -h*0.5]),
                     ([1.0, 0.0], [ w*0.5, -h*0.5]),
                     ([1.0, 1.0], [ w*0.5,  h*0.5])]                           
        })
        
    def removeDistantClouds(self):
        def in_range(cloud):
            distance = cloud["pos"] + self.offset
            #print (self.offset, cloud["pos"])
            return abs(distance.x) < self.screen.x and abs(distance.y) < self.screen.y
        self.clouds = list(filter(in_range, self.clouds))
        
        
    def spawnCloud(self, vel):
        left, right, top, bottom = 0, 0, 0, 0
        for c in self.clouds:
            distance = c["pos"] - self.offset
            if distance.x > 0:
                left += 1
            else:
                right += 1

        left = vel[0] < 0
        top = vel[1] > 0
        
        if abs(vel[0]) > abs(vel[1]):
            top = None
        else:
            left = None
        
        self.createCloud(left=left, top=top)
        
    def render(self, dt, offset=(0, 0), vel=(0, 0)):
        self.offset = Vec2d(offset)
        self.removeDistantClouds()
        if len(self.clouds) < self.maxClouds:
            self.spawnCloud(vel)
        
        glColor3f(1.0, 1.0, 1.0)
        self.clouds.sort(key=lambda c: c["texture"])
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        if len(self.clouds) > 0:
            old = self.clouds[0]["texture"]
            TextureManager.instance()[old].bind()
            glBegin(GL_QUADS)
        
        for c in self.clouds:
            pos = c["pos"]
            age = c["age"]
            tide = c["tide"]
            c["pos"] = pos + Vec2d(c["vel"] * dt, 0.0)
            c["age"] = age + dt
            
            pos += offset
            
            if old != c["texture"]:
                glEnd()
                old = c["texture"]
                TextureManager.instance()[old].bind()
                glBegin(GL_QUADS)
            
            for v in c["size"]:
                glTexCoord2fv(v[0])
                glVertex2f(pos.x + v[1][0], pos.y + v[1][1] + sin(age) * tide)
        
        if len(self.clouds) > 0:
            glEnd()
        
        
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)