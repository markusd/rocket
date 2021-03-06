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
        if player is None:
            return True
        return set(player.possessions).issuperset(set(requirements["possessions"]))
    
    def scheduleAction(self, func, action):
        pass
    
    def createAction(self, contact, action, k, fix, fixA, fixB, fixU, fixAu, fixBu, obj, objA, objB, player):
        if player is not None:
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
                self.actions[k] = lambda dt: refill(player, fixU, dt) if Clock.sysTime() - now > action["delay"] and self.checkRequirements(player, action.get("requirements", None)) else None
            elif action["action"] == "door-open":
                now = Clock.sysTime()
                self.actions[k] = lambda dt: obj.open() if Clock.sysTime() - now > action["delay"] and self.checkRequirements(player, action.get("requirements", None)) else None
            elif action["action"] == "pick-up" and player is not None:
                if self.checkRequirements(player, action.get("requirements", None)):
                    player.possessions.append(action["name"])
                    contact.enabled = False
                    self.actions[k] = lambda dt: self.destroyObject(obj)
            elif action["action"] == "apply-force":
                def apply_force(player, force, point):
                    f = player.body.GetWorldVector(localVector=force)
                    p = player.body.GetWorldPoint(localPoint=point)
                    player.body.ApplyForce(force, p, True)
                self.actions[k] = lambda dt: apply_force(player, action["force"], (0, 0))
            elif action["action"] == "win":
                pass
            
        if action["action"] == "destroy":
            if self.checkRequirements(player, action.get("requirements", None)):
                #contact.enabled = False
                self.actions[k] = lambda dt: self.destroyObject(objA)

    def processContact(self, contact, begin):
        fixA = contact.fixtureA
        fixB = contact.fixtureB
  
        k = (fixA, fixB)
        
        # if the contact is ending, delete actions
        if  k in self.actions and not begin:
            del self.actions[k]
            
        if  (fixB, fixA) in self.actions and not begin:
            del self.actions[k]
            
            
        fix = None
        player = None
        if self.player is not None:
            if fixA.body == self.player.body:
                player = fixA.body.userData
                fix = fixB
            elif fixB.body == self.player.body:
                player = fixB.body.userData
                fix = fixA
        
        objA = fixA.body.userData
        objB = fixB.body.userData
        obj = fix.body.userData if fix else None
        
        # Stupid workaround for nasty pybox2d bug:
        # Getting the user data of a fixture that is currently
        # begin deleted results in the process crashing without
        # any error due to heap corruption
        if not begin and (getattr(objA, "destroyingFixture", False) or getattr(objB, "destroyingFixture", False)):
            return
        
        fixAu = fixA.userData
        fixBu = fixB.userData
        fixU = fix.userData if fix else None
        
        if fixAu is None and fixBu is None:
            return
        
        actionsA = []
        actionsB = []
        #actions.extend(fixU.get("begin-contact", []) if begin else [])
        actionsA.extend(fixAu.get("touching", []) if begin and fixAu is not None and type(fixAu) == dict else [])
        actionsB.extend(fixBu.get("touching", []) if begin and fixBu is not None and type(fixBu) == dict else [])
        actionsA.extend(fixAu.get("end-contact", []) if not begin and fixAu is not None and type(fixAu) == dict else [])
        actionsB.extend(fixBu.get("end-contact", []) if not begin and fixBu is not None and type(fixBu) == dict else [])
        
        
        for action in actionsA:
            self.createAction(contact, action, k, fix, fixA, fixB, fixU, fixAu, fixBu, obj, objA, objB, player)

        for action in actionsB:
            self.createAction(contact, action, k, fix, fixB, fixA, fixU, fixBu, fixAu, obj, objB, objA, player)
            
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