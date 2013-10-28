from Box2D import *
from OpenGL.GL import *

from rocket.player import *
from rocket.object import Object

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
        
    def buildList(self, render=False):
        if self.list == -1:
            self.list = glGenLists(1)
        glNewList(self.list, GL_COMPILE_AND_EXECUTE if render else GL_COMPILE)
        
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
            func = o.update(dt)
            if func:
                func(self)
        
    def render(self):
        if self.list == -1:
            self.buildList(render=True)
        else:
            glCallList(self.list)
        
        for obj in self.objects:
            obj.render()
        
    def serialize(self, fileName):
        level = { "spawnPoint": self.spawnPoint,
                  "spawnOffset": self.spawnOffset,
                  "name": self.name,
                  "edgeFixtures": [],
                  "objects": []
        }
        
        #TODO: This saves too many fixtures
        for f in self.edgeFixtures:
            level["edgeFixtures"].append(f.shape.vertices)
        
        for o in self.objects:
            # TODO build difference of object json and getDict
            level["objects"].append(o.getDict())
        
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
            
        for o in level.get("objects", []):
            self.objects.append(Object.loadFromFile(world=self.world, fileName=o["filename"],
                        position=o["position"], extension=o))
            
    def destroyObject(self, obj):
        obj.destroy()
        self.objects.remove(obj)
            
            
    def checkRequirements(self, player, requirements):
        if requirements is None:
            return True
        if len(requirements.get("possessions", [])) == 0:
            return True
        return set(player.possessions).issuperset(set(requirements["possessions"]))
    
    def scheduleAction(self, func, action):
        pass
                   
    def processContact(self, contact, begin):
        #TODO actions can apply to other objects, not only players
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
        
        k = (player, fix)
        
        # if the contact is ending, delete actions
        if  k in self.actions and not begin:
            del self.actions[k]
        
        obj = fix.body.userData
        
        # Stupid workaround for nasty pybox2d bug:
        # Getting the user data of a fixture that is currently
        # begin deleted results in the process crashing without
        # any error due to heap corruption
        if not begin and getattr(obj, "destroyingFixture", False):
            return
        
        fixU = fix.userData
        
        if fixU is None:
            return
        
        
        actions =  []
        #actions.extend(fixU.get("begin-contact", []) if begin else [])
        actions.extend(fixU.get("touching", []) if begin else [])
        actions.extend(fixU.get("end-contact", []) if not begin else [])
        
        for action in actions:
            if action["action"] == "door-close":
                func = lambda: obj.close() if self.checkRequirements(player, action.get("requirements", None)) else None
                delay = action.get("delay", 0)
                if delay > 0:
                    self.timers.append(Timer(interval=delay, start=True, func=func, repeat=False))
                else:
                    func()
    
            if action["action"] == "refill":
                def refill(player, fixU, dt):
                    amount = min(action["capacity"], min(100.0 - player.fuel, action["rate"] * dt))
                    player.fuel = min(100, player.fuel + amount)
                    action["capacity"] = action["capacity"] - amount
                now = Clock.sysTime()
                self.actions[(player, fix)] = lambda dt: refill(player, fixU, dt) if Clock.sysTime() - now > action["delay"] and self.checkRequirements(player, action.get("requirements", None)) else None
            elif action["action"] == "door-open":
                now = Clock.sysTime()
                self.actions[(player, fix)] = lambda dt: obj.open() if Clock.sysTime() - now > action["delay"] and self.checkRequirements(player, action.get("requirements", None)) else None
            elif action["action"] == "pick-up":
                if self.checkRequirements(player, action.get("requirements", None)):
                    player.possessions.append(action["name"])
                    contact.enabled = False
                    self.actions[(player, fix)] = lambda dt: self.destroyObject(obj)
            elif action["action"] == "apply-force":
                def apply_force(player, force, point):
                    f = player.body.GetWorldVector(localVector=force)
                    p = player.body.GetWorldPoint(localPoint=point)
                    player.body.ApplyForce(force, p, True)
                self.actions[(player, fix)] = lambda dt: apply_force(player, action["force"], (0, 0))
            elif action["action"] == "win":
                pass
            elif action["action"] == "destroy":
                if self.checkRequirements(player, action.get("requirements", None)):
                    #contact.enabled = False
                    self.actions[(player, fix)] = lambda dt: self.destroyObject(obj)
            
    def PreSolve(self, contact, old_manifold):
        pass
    
    def BeginContact(self, contact):
        self.processContact(contact=contact, begin=True)
    
    def EndContact(self, contact):
        self.processContact(contact=contact, begin=False)
    
    def PostSolve(self, contact, impulse):
        pass

        
class Level(LevelBase):
    def __init__(self, keyAdapter, world, name=""):
        super(Level, self).__init__(keyAdapter, world, name)