from Box2D import *
from OpenGL.GL import *

from rocket.player import *

from utils import Clock, Timer

class LevelBase(b2ContactListener):
    def __init__(self, keyAdapter, world, name=""):
        super(LevelBase, self).__init__()
        self.keyAdapter = keyAdapter
        self.world = world
        self.world.contactListener = self
        self.spawnPoint = [0, 0]
        self.spawnOffset = [0, 0]
        self.name = name
        self.list = -1
        self.edgeFixtures = self.world.CreateStaticBody()
        self.objects = []
        self.player = None
        self.actions = {}
        self.timers = []
        
    def buildList(self):
        if self.list > -1:
            glDeleteLists(self.list, 1)
        self.list = glGenLists(1)
        glNewList(self.list, GL_COMPILE)
        
        glBegin(GL_LINES)
        for f in self.edgeFixtures:
            for v in f.shape.vertices:
                glVertex2fv(v)
        glEnd()
        
        glEndList()
        
    def update(self, dt):
        for t in self.timers:
            t.update()
            
        self.timers = list(filter(lambda t: t.started(), self.timers))
        
        actions = dict(self.actions)
        for k, v in actions.items():
            v(dt)
        
        #self.actions.clear()    
            
        for o in self.objects:
            o.update(dt)
        
    def render(self):
        if self.list == -1:
            self.buildList()
        glCallList(self.list)
        
        for obj in self.objects:
            obj.render()
        
    def serialize(self, fileName):
        level = { "spawnPoint": self.spawnPoint,
                  "spawnOffset": self.spawnOffset,
                  "name": self.name,
                  "edgeFixtures": []
        }
        
        #TODO: Need to save chain caps
        for f in self.edgeFixtures:
            level["edgeFixtures"].append(f.shape.vertices)
        
        fp = open(fileName, "w")
        json.dump(level, fp, sort_keys=True, indent=4)
        fp.close()
        
    def deserialize(self, fileName):
        fp = open(fileName, "r")
        level = json.load(fp)
        fp.close()
        
        self.spawnOffset = level["spawnOffset"]
        self.spawnPoint = level["spawnPoint"]
        self.name = level["name"]
        
        self.edgeFixtures = self.world.CreateStaticBody()
        for f in level["edgeFixtures"]:
            self.edgeFixtures.CreateEdgeChain(f)
            
            
    def checkRequirements(self, player, requirements):
        if requirements is None:
            return True
        if len(requirements.get("possessions", [])) == 0:
            return True
        return set(player.possessions).issuperset(set(requirements["possessions"]))
            
            
    def PreSolve(self, contact, old_manifold):
        pass
    
    def BeginContact(self, contact):
        if self.player is None:
            return

        if contact.fixtureA.body == self.player.body:
            player = contact.fixtureA.body.userData
            fix = contact.fixtureB
        elif contact.fixtureB.body == self.player.body:
            player = contact.fixtureB.body.userData
            fix = contact.fixtureA
        else:
            return
        
        obj = fix.body.userData
        fixU = fix.userData
        
        if fixU is None or fixU.get("touching", None) is None:
            return
    
        if fixU["touching"]["action"] == "refill":
            def refill(player, fixU, dt):
                amount = min(fixU["touching"]["options"]["capacity"], min(100.0 - player.fuel, fixU["touching"]["options"]["rate"] * dt))
                player.fuel = min(100, player.fuel + amount)
                fixU["touching"]["options"]["capacity"] = fixU["touching"]["options"]["capacity"] - amount
            now = Clock.sysTime()
            self.actions[(player, fix)] = lambda dt: refill(player, fixU, dt) if Clock.sysTime() - now > fixU["touching"]["delay"] and self.checkRequirements(player, fixU["touching"].get("requirements", None)) else None
        elif fixU["touching"]["action"] == "door-open":
            now = Clock.sysTime()
            self.actions[(player, fix)] = lambda dt: obj.open() if Clock.sysTime() - now > fixU["touching"]["delay"] and self.checkRequirements(player, fixU["touching"].get("requirements", None)) else None
        elif fixU["touching"]["action"] == "pick-up":
            def destroy_obj(body, obj):
                self.world.DestroyBody(body)
                self.objects.remove(obj)
            if self.checkRequirements(player, fixU["touching"].get("requirements", None)):
                player.possessions.append(fixU["touching"]["options"]["name"])
                contact.enabled = False
                self.actions[(player, fix)] = lambda dt: destroy_obj(fix.body, obj) 
    
    def EndContact(self, contact):
        if self.player is None:
            return
        
        if contact.fixtureA.body == self.player.body:
            player = contact.fixtureA.body.userData
            fix = contact.fixtureB
        elif contact.fixtureB.body == self.player.body:
            player = contact.fixtureB.body.userData
            fix = contact.fixtureA
        else:
            return
        
        obj = fix.body.userData
        fixU = fix.userData

        k = (player, fix)
        if k in self.actions:
            del self.actions[k]
            
        if fixU is None or fixU.get("end-contact", None) is None:
            return
        
        if fixU["end-contact"]["action"] == "door-close":
            action = lambda: obj.close() if self.checkRequirements(player, fixU["touching"].get("requirements", None)) else None
            delay = fixU["end-contact"].get("delay", 0)
            if delay > 0:
                self.timers.append(Timer(interval=delay, start=True, func=action, repeat=False))
            else:
                action()
    
    def PostSolve(self, contact, impulse):
        pass

        
class Level(LevelBase):
    def __init__(self, keyAdapter, world, name=""):
        super(Level, self).__init__(keyAdapter, world, name)