# -*- coding: utf-8 -*-
from common import *
from staircasing import Staircase
from shocker import Shocker
import xarray as xr
from steer import *

#%% get the startup details
#update by Navot - acouting for 2 levels of threat
save_folder='results'
if not os.path.exists(save_folder):
    os.mkdir(save_folder)
exp_info=getStartDetails(save_folder,[
        ['Subject ID',str,'x','Unique ID for the participant, used for saving important results'],
        ['High Shock Level',int,1,"shock intensity"], 
        ['Low Shock Level',int,2,"shock intensity"],
        ['Threat Speed Min',float,0.95,"Threats will move at least this fast relative to the player."],
        ['Threat Speed Max',float,1.15,"Threats will move at most this fast relative to the player."],
        ['Risk Min',float,0.55,"Rewards will be placed at least this far up the screen (fraction of screen)."],
        ['Risk Max',float,0.65,"Rewards will be placed at most this far up the screen (fraction of screen)."],
        ['Detection Min',float,0.4,"Minimum detection distance at which threats will start chasing the player (fraction of screen)."],
        ['Detection Max',float,0.6,"Maximum detection distance at which threats will start chasing the player (fraction of screen)."],
        ['Distraction Min',float,1.3,"Threat wandering  behavior weight will be at least this much (chase behavior is 1.0)."],
        ['Distraction Max',float,1.5,"Threat wandering behavior weight will be at most this much (chase behavior is 1.0)."],
        ['Caught Penalty',int,-1,"Score penalty when caught (integer).  If negative, it is a factor of the potential reward."],
        ['Actor Scale',float,0.5,"Player, threat, and reward images are scaled by this.  Use to tune the feel of distance."],
        ['Actor Speed Factor',float,10.0,"Adjust the speed of actors in terms of how long it would take the player to run to top of screen."],
        ['Time Limit Factor',float,2.0,"How long the player has to complete the trial (a factor of 1.0 gives player enough time to run to top of screen)."],
        ['Safe Zone',bool,True,"If True the threat can't cross the starting zone line."],
        ['Show Cumulative Score',bool,False,"Monetary reward for subjects probably won't be based on cumulative score, but if you want to see it..."]])

'''
0,0 is bottom center of screen?
'''
        
# experimenter decided to abort, so abort
if not exp_info:
    print('aborting')
    sys.exit()

CAUGHT_PENALTY=exp_info['Caught Penalty']
ACTOR_SCALE=exp_info['Actor Scale']
START_IS_SAFE=exp_info['Safe Zone']
SHOW_SCORE=exp_info['Show Cumulative Score']

shock_mode = exp_info['Shock Mode']
config_mode = exp_info['Config Mode']

if shock_mode=='none':
    shocker=Shocker(1,address=0,mode=None)
elif shock_mode=='lab':
    shocker=Shocker(192,address=0xD070,mode='in_lab')
elif shock_mode=='mock':
    raise NotImplementedError("can't do mock scanner shocker yet")
elif shock_mode=='scan':
    shocker=Shocker(1,address="/Dev1/ao0",mode='scanner')
else:
    raise RuntimeError('unhandled shock mode {}, code needs fixed'.format(shock_mode))

#shocker.level = exp_info['Shock Level']


#impl: need to think more about how to do configuration gui better (is it scanner, shocker, and general config?)
#clean: naming of constants throughout
#idea: move defaults for modes here, so common doesn't also need changed depending on location.

#%% constants and globals
# the values here represent the full experiment as should be run in the scanner
# most things worth experimenting with are currently in the startup gui

WIDTH=800
HEIGHT=600
COLLISION_SCALE=1.0
REWARD_FONT_SIZE=26 # was 16.  26 still fits "100" inside

# though these can be overwritten to adjust situations
THREAT_SPEED=PLAYER_SPEED=HEIGHT/exp_info['Actor Speed Factor']
MAX_SITUATION_DUR=exp_info['Time Limit Factor']*HEIGHT/PLAYER_SPEED
print(MAX_SITUATION_DUR)
# no selection period, no delay period, and only fast threats
DEFAULT_SITUATION_SELECTION=None
SITUATION_SELECTION_DUR=0
DELAY_DUR_FUN=lambda: 0
THREAT_FAST_CHANCE=1

SITUATION_FEEDBACK_DUR=2
ZAP_DUR=1
MAX_SHOCKS=100

if config_mode=='full':
    ITI_DUR_FUN=lambda: constrainedExponential(8,6,10)#(4,2,6)
    MAX_TRIAL_DUR = SITUATION_SELECTION_DUR + MAX_SITUATION_DUR + SITUATION_FEEDBACK_DUR + 6
    
    TRIALS_PER_BLOCK=np.inf
    BLOCK_DUR=60*25
    
elif config_mode=='debug':
    ITI_DUR_FUN=lambda: 1
    MAX_TRIAL_DUR = SITUATION_SELECTION_DUR + MAX_SITUATION_DUR + SITUATION_FEEDBACK_DUR + 1 #doesn't matter if BLOCK_DUR is infinite
    
    TRIALS_PER_BLOCK=np.inf
    BLOCK_DUR=np.inf
elif config_mode=='practice':
    ITI_DUR_FUN=lambda: constrainedExponential(8,6,10)#(4,2,6)
    MAX_TRIAL_DUR = SITUATION_SELECTION_DUR + MAX_SITUATION_DUR + SITUATION_FEEDBACK_DUR + 6 #doesn't matter if BLOCK_DUR is infinite
    
    TRIALS_PER_BLOCK=np.inf
    BLOCK_DUR=np.inf
    


#KEEP_STAIRCASE=False # if True, the last 
def DefaultStaircase():
    #return Staircase(diff_min=0.1)
    from staircasing import ForagingStaircase
    return ForagingStaircase()

def makeSituationNormalizedRisk(risk,reward,fast):
    
    RISK_LOW=exp_info['Risk Min']
    RISK_HIGH=exp_info['Risk Max']
    # this is as a percent of the screen.  distance based, not position
    DETECTION_LOW=exp_info['Detection Min']
    DETECTION_HIGH=exp_info['Detection Max']
    
    d=dict()
    # where the cover starts
    d['cover']=HEIGHT-img_cover.height
    d['fast']=fast
    
    # max speed
    d['speed'] = PLAYER_SPEED*np.random.uniform(exp_info['Threat Speed Min'],exp_info['Threat Speed Max'])
    # weight for wandering behavior (seek is 1.0)
    d['distracted']=np.random.uniform(exp_info['Distraction Min'],exp_info['Distraction Max'])
    
    #low or high threat selection
    d['weak']=random.choice([True, False])
    
    # threat detection distance
    #idea: could be a different distribution, only need occasional attacks close up?
    d['detect']=HEIGHT*np.random.uniform(DETECTION_LOW,DETECTION_HIGH)
    #d['detect']=HEIGHT*DETECTION_HIGH
    # reward value
    d['reward']=reward
    # where to place the coin
    d['reward_pos']=HEIGHT*(RISK_LOW+(RISK_HIGH-RISK_LOW)*risk)
    #print('reward',d['reward_pos'],'risk',risk,'reward',reward,'speed',d['speed'])
    
    #idea: function to do random but also return a % for easier gauging of relative setting?
    print('========================================')
    print('NEW SITUATION')
    for (k,v) in d.items():
        print('    {}={}'.format(k,v))
    
    return Situation(d)

#%% some automatic initialization

# connect to the scanner (prints warning if can't connect)
# port is 3 for the real scanner, 2 for the mock scanner
# and if no scanner is detected, you'll just get a warning message
# the config_mode at least gives a decent guess at what port you want.
if config_mode=='practice':
    port=2
elif config_mode=='full':
    port=3
else:
    port=2
scanner_coms = ScannerComs(port=port, timeout=0.001, baudrate=19200)

#%%

#%% load game resources

# define resources directory
pyglet.resource.path.insert(0,'resources') # = ['resources']
pyglet.resource.reindex()

img_player = loadImage("RabbitCoin75.png")
img_threat = loadImage("LayingWolfBlackCoinBlue75.png")
img_low_threat = loadImage("CatCoin75.png")
img_threat_fast = loadImage("WolfBlackCoinRed75.png")
img_reward = loadImage("LettuceCoin75.png")
img_situation_background = loadImage("Trail.jpg")
img_cover = loadImage("cave_smaller.png")
img_hline = loadImage("HorizontalLine300.jpg")
img_caught = loadImage("bite.png")

success_sound = sa.WaveObject.from_wave_file('resources/success.wav')
fail_sound = sa.WaveObject.from_wave_file('resources/fail.wav')

##%% joystick stuff
import pyglet
joystick=None

# joystick position is [-1,1].  You need to define a deadzone that accounts for 
# joystick error (so small offsets aren't detected as intended)
JOY_DEADZONE=0.3
# the first listed joystick is used.  probably best to not have multiple
# joystick like devices attached than to assume you know the list order...
JOY_NUM=0

joysticks = pyglet.input.get_joysticks()
if joysticks:
    joystick = joysticks[JOY_NUM]
    try:
        joystick.open()
        test=float(joystick.y)
    except Exception as e:
        print(e)
        joystick=None

if joystick is None:
    print('WARNING: no usable joystick detected')
    class joystick:
        y=0
#%% key classes

#doc: copied from devils 2018-10-10 version.  haven't updated the docs entirely

#impl: more flexible way?
def clampToWindow(pos,w=None,h=None):
    '''
    given a center position, ensure an object of width w and height h
    is within the screen
    
    modifies and returns the same eu.Vector2
    '''
    if w is not None:
        hw = w/2
        pos.x = max(pos.x,hw)
        pos.x = min(pos.x,WIDTH-hw)
    if h is not None:
        hh = h/2
        pos.y = max(pos.y,hh)
        pos.y = min(pos.y,HEIGHT-hh)
    return pos

# the collision stuff is overkill for a 1D game, oh well
class Actor(CocosNode):
    '''
    My attempt at a convenient base class for entities in the game.
    it is steerable, has a sprite, supports collision.
    
    pos and position return a Vec2, just note that you cannot
    modify the x and y of that Vec2 and expect the changes
    to carry over to the Actor's x and y.
    
    
    '''
    def __init__(self,sprite,pos=None,collision_type=None,collision_scale=None,wrapped_sprite=None,clamped=True):
        '''
        The sprite is saved as self.sprite and added to the node.
        It is used to define the position and boundaries of the
        Actor (anchor is the center).  collision_type can be
        'r' (AARect) or 'c' (Circle).  Moving the Actor via
        x, y, position, or pos will update the collision shape
        automatically.
        
        collision_scale can be used to scale just the cshape of the Actor
        for collision detection purposes.  The width and height attributes
        will not be adjusted.
        
        '''
        CocosNode.__init__(self)
        
        self._clamped=clamped=False #testing: both ways
        
        # initial position
        if pos is None:
            pos=(0,0)
        self.cshape=None
        (self.x,self.y) = pos
        
        # sprite
        self.sprite = sprite
        self.add(sprite)
        
        # collision
        if collision_scale is None:
            collision_scale = 1.0
        if not collision_type:
            self.cshape = None
        elif collision_type.startswith('c'):
            self.cshape = cm.CircleShape(self.pos,collision_scale*self.width/2)
        elif collision_type.startswith('r'):
            try:
                (ws,hs)=collision_scale
            except TypeError:
                ws=hs=collision_scale
            self.cshape = cm.AARectShape(self.pos, ws*self.width/2, hs*self.height/2)
        else:
            raise ValueError('unrecognized collision_type {}'.format(collision_type))
        
        # for steering
        self.mass=1
        self.max_vel=None
        self.max_force=None
        self.vel=Vec2(0,0)
        
        # used to allow nicely looping a sprite to the top as it crosses the
        # bottom of the screen
        self._wrapped_sprite=wrapped_sprite
        if wrapped_sprite:
            wrapped_sprite.y=sprite.y+HEIGHT
            self.add(wrapped_sprite)
        
    def showWrapped(self,show):
        if self._wrapped_sprite:
            self._wrapped_sprite.visible=show
    
    @property
    def width(self):
       return self.sprite.width
    @property
    def height(self):
        return self.sprite.height
    
    @property
    def pos(self):
        return Vec2(self._x,self._y)
    @pos.setter
    def pos(self,p):
        ##testing:
        #(x,y)=p
        #CocosNode._set_position(self,(int(x),int(y)))
        if self._clamped:
            p = clampToWindow(p,self.width,self.height)
        
        CocosNode._set_position(self,p)
        if self.cshape:
            self.cshape.center = p
    position=pos
    
    @property
    def x(self):
        return self._x
    @x.setter
    def x(self,v):
        CocosNode._set_x(self,v)
        if self.cshape:
            self.cshape.center = (v,self.cshape.center[1])

    @property
    def y(self):
        return self._y
    @y.setter
    def y(self,v):
        CocosNode._set_y(self,v)
        if self.cshape:
            self.cshape.center = (self.cshape.center[0],v)
    
    def drawCollision(self):
        #cocos.draw.Circle(self.pos,float(self.height))
        pass

class Player(Actor):
    '''
    User controlled character
    '''
    def __init__(self,pos=None):
        sprite = Sprite(img_player,scale=ACTOR_SCALE)
        # represented as a circle, but tighter collision.
        Actor.__init__(self, sprite, pos=pos, collision_type='c', collision_scale=COLLISION_SCALE)
        #fixme: why doesn't this work during selection mode?
        #self.pos = clampToWindow(self.pos,self.width,self.height)
        self.speed = PLAYER_SPEED
    
    def update(self,dt):
        d=0
        messages=scanner_coms.messages()
        
        # check for arrow keys, Num Lock'd numbers (could just be arrows...) or button box inputs, or joystick
        if keys[key.UP] or keys[key._8] or '1' in messages or joystick.buttons[2]: #joystick.y<-JOY_DEADZONE:
            d=1
        elif keys[key.DOWN] or keys[key._2] or keys[key._5] or '2' in messages or joystick.buttons[3]: #joystick.y>JOY_DEADZONE:
            d=-1
        
        self.pos = self.pos + eu.Vector2(0,self.speed*d*dt)
        #print(self.pos)
        
class RewardSprite(Sprite):
    '''
    A coin sprite with text overlay showing the value.
    Value can be changed by the value property.
    To change reward values and number of possibale rewards change  ForagingStaircase class in straicasing.py
    '''
    def __init__(self,v=0):
        Sprite.__init__(self,img_reward,scale=ACTOR_SCALE)
        self.txt = cocos.text.Label(str(v),
              font_name='Times New Roman',
              font_size=REWARD_FONT_SIZE,
              bold=True,
              color=(0, 0, 0, 255),
              anchor_x='center', anchor_y='center')
        self.add(self.txt)
        self.value = v
        #self.value = 10
    
    @property
    def value(self):
        return self._value
    @value.setter
    def value(self,v):
        #self._value = 10
        self._value = v
        self.txt.element.text = str(v)

class Reward(Actor):
    def __init__(self,pos=None,v=20):
        Actor.__init__(self,RewardSprite(v=v),pos=pos,collision_type='r')
    def update(self,dt):
        pass
    @property
    def value(self):
        return self.sprite.value
    @value.setter
    def value(self,v):
        self.sprite.value = v
        #self.sprite.value = 10

class Threat(Actor):
    '''
    '''
    def __init__(self,pos=None, fast=False, detection_distance=HEIGHT*.6, speed=THREAT_SPEED, distracted=1.6, safe_y=0, weak=False):
        #update by Navot - acouting for 2 levels of threat
        self.weak=weak
        if weak:
            img=img_low_threat
            shocker.level = exp_info['Low Shock Level']
        else:
            img=img_threat_fast
            shocker.level = exp_info['High Shock Level']
        
        sprite=Sprite(img,scale=ACTOR_SCALE)
        # this would show the detection distance I think, but collision is based on the sprite.
        #sprite=Sprite(img,scale=2*detection_distance/img.height)
        
        Actor.__init__(self,sprite,pos=pos,collision_type='r')
        
        self.max_vel = speed
        self.target = SimpleSteerable()
        self.steering = SteeringManager(self)
        self.steering.add('seek',Seek(self.target,slowing_radius=0.1,detection_distance=detection_distance),weight=1)
        self.steering.add('wander',Wander(10,10),weight=distracted)
        
        self._ymin = safe_y
    
    def update(self,dt):        
        self.target.pos = (0,self.parent.player.y)
        #self.target.pos = (self.parent.player.x,self.parent.player.y)
        self.steering.update(dt)
        
        if magnitude(self.steering['seek']._contrib):
            print('chasing')
        
        #self.x=clamp(self.x,-self.parent.width/2,self.parent.width/2,self.width)
        self.x=clamp(self.x,-self.parent.width/2,self.parent.width/2,self.width)
        self.y=clamp(self.y,self._ymin,HEIGHT,self.height)
        
        ##testing:
        #from primitives import Circle
        #c = Circle(0,0,width=100,color=(0.,.9,0.,1.))
        #c.render()

class Situation(Layer):
    def __init__(self,settings=None):
        Layer.__init__(self)
        
        
        self.settings = settings
        settings.setdefault('reward_pos',HEIGHT/2)
        s=settings
        
        self._background_sprite = Sprite(img_situation_background)
        self._forest_sprite = Sprite(img_cover)
        self._line_sprite = Sprite(img_hline)
        
        self.player = Player()
        self.reward = Reward()
        
        # moving up the safe zone, it isn't considered as a limit for parameters though
        #line_y=self.player.height+self._line_sprite.height/2
        line_y=self.player.height*1.5+self._line_sprite.height/2
        safe_y=line_y+self._line_sprite.height/2
        if not START_IS_SAFE:
            safe_y=0        
        self.threat = Threat(fast=settings['fast'],detection_distance=s['detect'], speed=s['speed'], distracted=s['distracted'], safe_y=safe_y, weak=s['weak'])
        
        self.add(self._background_sprite,z=0)
        self.add(self._line_sprite,z=1)
        self.add(self.reward,z=1)
        self.add(self.player,z=2)
        self.add(self.threat,z=3)
        #self.add(self._forest_sprite,z=4) #don't bother with cover anymore
        
        
        
        
        #annoy: positioning and clamping are all sort of strange
        # more so when adding layers it seems?  wasn't this much trouble in 
        # devils.
        self._background_sprite.position = eu.Vector2(0,HEIGHT/2)
        self.player.pos = eu.Vector2(0,self.player.height/2)
        
        self.reward.pos = eu.Vector2(0,settings['reward_pos'])
        self.threat.pos = eu.Vector2(0,HEIGHT-self.threat.height/2)
        self._line_sprite.position = eu.Vector2(0,line_y)
        #self._safe_y=self.player.y #update by Navot: This version does't allow the threat to go under the player also need ot change in playerIsSafe line 525
        self._safe_y=safe_y
        
        # +75 is just to ensure always covered, but I'm ignoring that now
        #self._forest_sprite.position = eu.Vector2(0,self._forest_sprite.height/2+s['cover']-75)
        self._forest_sprite.position = eu.Vector2(0,self._forest_sprite.height/2+s['cover'])
        #self.threat.speed = s['speed']
        #self.threat.detection_distance = s['detect']
        self.reward.value = s['reward']
        
        self.selected = False
        
        #print('safe player_y = {}'.format(self._safe_y-self.player.height/2))
        #raise RuntimeError()
        
    def update(self,dt):
        pass #impl: enemy behavior, but also everything else?
        # or at all?
    
    def playerIsSafe(self):
        return self.player.y+self.player.height/2 < self._safe_y
        #return self.threat.y < self._safe_y #update by Navot: This version does't allow the threat to go under the player
    
    @property
    def width(self):
        return self._background_sprite.width
    
    @property
    def selected(self):
        return self._selected
    @selected.setter
    def selected(self,s):
        self._selected = s
        self.player.visible = s
        #self.player.pos = clampToWindow(self.player.pos,self.player.width,self.player.height)
        #self.player.pos = eu.Vector2(0,0)




class MessageLayer(Layer): 
    '''
    Simple layer with centered text
    progresses the game_state when enter is pressed
    '''
    is_event_handler=True
    
    def __init__(self,txt=None,timeout=None,next_layer=None):
        Layer.__init__(self)
        if txt is None:
            txt=''
        
        label = cocos.text.Label(
            txt,
            font_name='Times New Roman',
            font_size=32,
            anchor_x='center',anchor_y='center')
        
        #fixme: is there a more flexible way?
        label.position=(WIDTH/2,HEIGHT/2)
        
        self.add(label)
        self._label=label
        self._finished = False
        self._next_layer=next_layer
        
        if timeout is None:
            timeout = np.inf
        else:
            self.schedule(self._timeoutCheck)
        self._timeout=timeout
    
    def _timeoutCheck(self,dt):
        self._timeout-=dt
        if self._timeout<=0:
            self.finish()
    
    def finish(self):
        if self._finished:
            return
        self._finished=True
        if self._next_layer is not None:
            core.setLayer(self._next_layer)
    
    
    @property
    def text(self):
        return self._label.element.text
    @text.setter
    def text(self,txt):
        self._label.element.text=txt
    def on_key_press(self,k,modifiers):
        if k==key.ENTER:
            self.finish()

def FakeLayer(txt,**kwargs):
    def inner():
        return MessageLayer(txt)
    return inner

class IntroLayer(MessageLayer):
    '''
    Main menu, probably some instructions
    '''
    def __init__(self):
        #annoy: don't know how to do this multiline.  Might need to implement something
        # myself, estimate height and split based on newlines.  Not automatic, but
        # should suffice...
        MessageLayer.__init__(self,'Instructions go here.  Press enter to start.')


class HUD(Layer):
    '''
    overlay to show score and such
    '''
    def __init__(self):
        Layer.__init__(self)
        self.score_text = cocos.text.Label('?',font_size=18)
        self.score_text.position = (10,HEIGHT-20)
        self.score=0
        self.add(self.score_text)
    @property
    def score(self):
        return self._score
    @score.setter
    def score(self,v):
        self._score = v
        self.score_text.element.text = 'Score: {:d}'.format(v)

class Log(object):
    '''
    Helper class for Logs
    each call adds a new row to the log table
    '''
    def __init__(self,names):
        names=[name.strip() for name in names.split(',')]
        #opt: if performance becomes an issue, this can be
        # done with arrays and such (more complicated)
        self._names = names
        self._data = dict()
        for name in names:
            self._data[name]=[]
        
    def __call__(self,**kwargs):
        for k,v in kwargs.items():
            self._data[k].append(v)
    
    def toDataFrame(self):
        return pd.DataFrame(self._data)

class Logs(object):
    def __init__(self,verbose=True):
        # tracking
        self._time=0
        self._frame=0
        self._init=False
        self._trial=np.inf # just to catch any mishandling
        self.state='invalid'
        
        # the stored data
        self._events=Log('frame,name,value,msg')
        self._ongoing=Log('frame,time,trial,state,situation_i,threat_x,threat_y,player_y,safe,reward_value,threat_level')
        self._trials=Log('trial,onset,dur,situation_sel,value,result,sc_f') # later can add conveniences like reaction time
        self._situation_names='trial,risk,reward,cover,threat_speed,detect_dist,reward_pos,weak'
        self._situations=[Log(self._situation_names) for i in range(2)]
        
        self._verbose=verbose
    
    @property
    def frame(self):
        return self._frame
    
    def update(self,dt):
        '''
        Should be called each frame to establish the timing
        for subsequently logged details.
        '''
        if self._init:
            self._time+=dt
            self._frame+=1
        else:
            # for convenience (the update is called at the top of the frame)
            # don't actually update time or frame  the first call
            self._init=True
    
    def ongoing(self,situation_i,threat_x,threat_y,player_y,safe,reward_value,threat_level):
        self._ongoing(frame=self._frame,time=self._time,trial=self._trial,state=self.state,situation_i=situation_i,threat_x=threat_x,threat_y=threat_y,player_y=player_y,safe=safe,reward_value=reward_value,threat_level=threat_level)
    
    def event(self,name,value,msg='',*args,**kwargs):
        if msg:
            if args or kwargs:
                msg=msg.format(*args,**kwargs)
        if self._verbose:
            print('{:.2f} | {}:{} [{}]'.format(self._time,name,value,msg))
        self._events(frame=self._frame,name=name,value=value,msg=msg)
    
    def situation(self,i,risk,reward,cover,threat_speed,detect_dist,reward_pos,weak):
        log = self._situations[i]
        log(trial=self._trial,risk=risk,reward=reward,cover=cover,threat_speed=threat_speed,detect_dist=detect_dist,reward_pos=reward_pos,weak=weak)
    
    def trial(self,onset,dur,situation_sel,value,result,sc_f):
        self._trials(trial=self._trial,onset=onset,dur=dur,situation_sel=situation_sel,value=value,result=result,sc_f=sc_f)
    
    def process(self):
        '''
        final result:
            events DataFrame
            ongoing DataFrame
            trial summary Dataset (includes situation details too)
        '''
        d=dict()
        d['ongoing'] = self._ongoing.toDataFrame()
        d['events'] = self._events.toDataFrame()
        
        temp=[]
        for log in [self._trials]+self._situations:
            df = log.toDataFrame().set_index('trial')
            ds = xr.Dataset(df)
            temp.append(ds)
        
        ds = xr.concat(temp[1:],'situation')
        ds.coords['situation']=pd.Index(np.arange(len(temp)-1))
        ds = xr.merge((temp[0],ds))
        
        d['trials'] = ds
        
        return d
    
    def save(self,fname):
        fpath = os.path.join(save_folder,fname)
        data = self.process()
        #opt: better to save with xarray than to pickle I think...
        raise NotImplementedError('saving...')


class BlockLayer(Layer):
    '''
    Layer for managing each block (multiple trials per block).
    
    '''
    is_event_handler=True

    
    def __init__(self):
        Layer.__init__(self)
        self.elapsed=0 #fixme: need to think how best to time what.  
        self._finished=False
        self.trial=-1
        self.sc = DefaultStaircase()
        self.log = Logs()
        
        self._shocks=0
        
        # used for situation selection to show no selection
        self._fake_player = Player()
        self.add(self._fake_player,z=2)
        self._fake_player.visible=False
        self._fake_player.pos = eu.Vector2(WIDTH/2,self._fake_player.height/2)
        
        # used for feedback state
        self._feedback_reward=Reward()
        self.add(self._feedback_reward,z=10)
        self._feedback_reward.scale = 2
        self._feedback_reward.pos = eu.Vector2(WIDTH/2,HEIGHT/2)
        self._feedback_reward.visible = False
        self._feedback_fail=Sprite(img_caught,position=(WIDTH/2,HEIGHT/2)) #annoy: Sprite doesn't have a pos to set...
        self.add(self._feedback_fail,z=10)
        self._feedback_fail.visible = False
        self._feedback_txt = cocos.text.Label('asdf',font_name='Times New Roman',font_size=32,anchor_x='center',anchor_y='bottom')
        self._feedback_txt.position=(WIDTH/2,0)
        self.add(self._feedback_txt,z=9)
        self._feedback_txt.visible=False
        
        self._score=0
        if SHOW_SCORE:
            self._score_txt = cocos.text.Label('0',font_name='Times New Roman',font_size=16,anchor_x='left',anchor_y='top')
            self._score_txt.position = (2,HEIGHT)
            self.add(self._score_txt,z=10)
            self.updateScore(0)
        
        # simple cyclic state system
        self.states=('select','delay','play','feedback','iti')
        self.state=None
        self.startState('select')
        
        self.schedule(self.update)
    
    def updateScore(self,change):
        self._score+=change
        if SHOW_SCORE:
            #self._score_txt.element.text = 'Score: {:d}'.format(self._score)
            self._score_txt.element.text = '{:d}'.format(self._score) # writing Score takes up valuable space...
    
    def nextState(self):
        # start next state
        self.logEvent('state_end',self.state)
        state = self.states[(self.states.index(self.state)+1)%len(self.states)]
        self.startState(state)
    
    def startState(self,state):
        # start a specific state
        self.logEvent('state_start',state)
        self.state=state
        self.log.state=state
        self.time_limit=np.inf
        starter=getattr(self,'_startState'+state.capitalize())
        starter()
        
        if not self.time_limit:
            self.nextState()
    
    def stateTimeout(self,dt):
        # check if state has been running for too long
        self.time_limit-=dt
        if self.time_limit<=0:
            self.logEvent('timedout',self.state)
            
            # makes it possible to detect if the play state timed out
            #clean: 
            self.trial_value = None
            
            self.nextState()
            return True
        return False
    
    def _startStateSelect(self):      
        '''
        Situation selection phase to start each trial.
        '''
        self.trial+=1
        #clean: ick...
        self.log._trial=self.trial
        self._trial_onset=self.log._time
        
        if self.trial+1>=TRIALS_PER_BLOCK:
            self.logEvent('block_end','max trials')
            return self.finish()
        if self.elapsed+MAX_TRIAL_DUR>=BLOCK_DUR:
            self.logEvent('block_end','max duration')
            return self.finish()
        if self._shocks>=MAX_SHOCKS:
            assert(self._shocks==MAX_SHOCKS)
            self.logEvent('block_end','max shocks')
            return self.finish()
        
        self.situation = None
        self.time_limit=SITUATION_SELECTION_DUR
        self.trial_value=0
        
        fast = np.random.rand()<THREAT_FAST_CHANCE
        
        situations=self.situations=[]
        details=[]
        for i,(risk,rewd) in enumerate(self.sc.params):
            print(self.sc.f)
            s = makeSituationNormalizedRisk(risk,rewd,fast)
            self.situations.append(s)
            
            d=dict(risk=risk,reward=rewd,cover=s.settings['cover'],threat_speed=s.settings['speed'],detect_dist=s.settings['detect'],reward_pos=s.settings['reward_pos'], weak=s.settings['weak'])
            #if i==0:
            #    d[']
            details.append(d)
        # don't want the order to matter
        if np.random.rand()<0.5:
            details=details[::-1]
            situations=self.situations=self.situations[::-1]
        #np.random.shuffle(self.situations)
        
        # log the new situations
        for i,d in enumerate(details):
            self.log.situation(i=i,**d)
        
        
        
        w = situations[0].width
        w += 20 # adds a black separator easily
        x = WIDTH/2
        x -= w*(len(situations)-1)/2        
        for i,s in enumerate(situations):
            s.x = x
            s.y = 0 #clean: situation is a Layer, can I set anchors centered for consistancy?
            x += w
            self.add(s)
            s.selected = False
        
        if DEFAULT_SITUATION_SELECTION is None:
            i=None
        elif DEFAULT_SITUATION_SELECTION=='half':
            i=(len(situations)-1)//2 # goes left if needed
        elif DEFAULT_SITUATION_SELECTION=='left':
            i=0
        elif DEFAULT_SITUATION_SELECTION=='right':
            i=len(situations)-1
        else:
            raise RuntimeError('unrecognized default situation selection mode {}'.format(DEFAULT_SITUATION_SELECTION))
        
        self._situation_i=Ellipsis # invalid initial value so that the highlight is logged (None represents no selection)
        self.highlightSituation(i)
    
    def _finishSelection(self):
        # random selection if none given
        if self._situation_i is None:
            i=np.random.randint(len(self.situations))
            self.logEvent('situation_timeout_default',i)
            self.highlightSituation(i)
        
        # hide the other situations
        for s in self.situations:
            if not s.selected:
                s.kill()
            else:
                self.situation=s
        self.situations=None
    
    def _startStateDelay(self):
        self.time_limit=DELAY_DUR_FUN()
        #self._finishSelection()
    
    def _startStatePlay(self):
        self.logEvent('situation_play',self._situation_i)
        self.time_limit=MAX_SITUATION_DUR
        self.trial_value = 0
        self.may_escape=False
        self._finishSelection()
        
        #might staircase here
        #self.sc.pick(self.situation.kind=='lo')
        
    def _startStateFeedback(self):
        self.situation.kill()
        self.situation=None
        self.time_limit=SITUATION_FEEDBACK_DUR
        
        #testing: new staircasing, currently escaping is considered failure (situations are considered too hard)
        #idea: could have it be failure, but eaten is more of a failure
        
        #clean: should be done better
        # some logging details
        dur=self.log._time - self._trial_onset
        val = self.trial_value
        if val is None:
            val = 0
        info=dict(onset=self._trial_onset,dur=dur,situation_sel=self._situation_i,value=val,sc_f=self.sc.f)
        
        #impl: need to handle timeout situatinos better.
        
        #self._feedback_txt_layer.visible=True
        self._feedback_txt.visible=True
        self.updateScore(val)
        if self.trial_value is None:
            txt='Out of Time!'
            self.sc.update(False)
        elif self.trial_value==0:
            txt='Escaped!'
            self.sc.update(False)
        elif self.trial_value>0:
            txt='Got Food!'
            self._feedback_reward.visible=True
            self._feedback_reward.value=self.trial_value
            success_sound.play()
            self.sc.update(True)
        else:
            txt='Eaten! ({})'.format(self.trial_value)
            self._feedback_fail.visible=True
            fail_sound.play()
            
            a =ca.InstantAction()
            a+=ca.CallFunc(shocker.start)
            a+=ca.Delay(ZAP_DUR)
            a+=ca.CallFunc(shocker.stop)
            
            self.do(a)
            
            self.sc.update(False)
            
            self._shocks+=1
        
        self.log.trial(result=txt,**info)
        
        #self._feedback_txt_layer.text=txt
        self._feedback_txt.element.text=txt
        
        
    def _startStateIti(self):
        self.time_limit=ITI_DUR_FUN()
        #clean: start and end should be contained, like a context...
        self._feedback_reward.visible = False
        self._feedback_fail.visible = False
        #self._feedback_txt_layer.visible=False
        self._feedback_txt.visible = False
    
    def shiftSituationSelection(self,d):
        if not d:
            return
        if self._situation_i is None:
            fn=np.ceil if d>0 else np.floor
            i=int(fn((len(self.situations)-1)/2))
        else:
            i=self._situation_i+d
        self.highlightSituation(i)
    
    def highlightSituation(self,i):
        
        # test wasn't necessary, also I use this to select if player failed to select
        #if self.state != 'select':
        #    raise RuntimeError('attempting to select a situation after selection phase')
        
        # deselect everything
        self._fake_player.visible = False
        for s in self.situations:
            s.selected=False
        
        # odd number of situations, can just choose the center
        if i is None and len(self.situations)%2!=0:
            i=int((len(self.situations)-1)/2)
        
        # show fake selection only
        if i is None:
            self._fake_player.visible = True
        elif i<=0:
            i=0
        elif i>=len(self.situations):
            i=len(self.situations)-1
            
        if self._situation_i!=i:
            self._situation_i = i
            self.logEvent('situation_highlight',i)
        
        if i is not None:
            self.situations[i].selected = True
    def logEvent(self,*args,**kwargs):
        self.log.event(*args,**kwargs)
    '''
    def logEvent(self,name,value,msg='',*args,**kwargs):
        if msg:
            if args or kwargs:
                msg=msg.format(*args,**kwargs)
            print(msg)
        #impl: would log name, value, and maybe the message properly here
        print('{:.2f} | {}:{}'.format(self.elapsed,name,value))
    '''
    def update(self,dt):
        
        if self._finished:
            return
        if not self.elapsed:
            print('first dt={}'.format(dt))
        self.elapsed+=dt
        
        ##testing:
        #if self.elapsed<10:
        #    return

        # new frame for the logger
        self.log.update(dt)
        
        # handles state timeouts (might also end the block)
        self.stateTimeout(dt)
        
        # log general per-frame details like state (anything else?)
        #impl:
        #self.log.ongoing()
        
        # stateTimeout might have ended things
        if self._finished:
            return
        
        ongoing=dict(situation_i=self._situation_i,threat_x=None,threat_y=None,player_y=None,safe=None,reward_value=None,threat_level=None) #update by Navot - adding value and threat level to ongoing log
        advance_state=False
        if self.state=='play':
            p=self.situation.player
            t=self.situation.threat
            r=self.situation.reward
            
            for o in (p,t,r):
                o.update(dt)
            
            ongoing['threat_x']=t.x
            ongoing['threat_y']=t.y
            ongoing['player_y']=p.y
            #update by Navot - adding value and threat level to ongoing log
            ongoing['reward_value']=r.value
            if t.weak == True: 
                ongoing['threat_level']='touch'
            elif t.weak == False:
                ongoing['threat_level']='shock'
            ongoing['safe']=self.situation.playerIsSafe()
            
            if not self.situation.playerIsSafe():
                self.may_escape=True
            
            if p.cshape.overlaps(r.cshape):
                self.logEvent('reward',r.value)
                self.trial_value = r.value
                r.pos = eu.Vector2(0,2*HEIGHT) # for now, just moving it offscreen.
            
            if p.cshape.overlaps(t.cshape):
                self.logEvent('caught',self.trial_value)
                if CAUGHT_PENALTY<0:
                    self.trial_value = CAUGHT_PENALTY*r.value
                else:
                    self.trial_value = -CAUGHT_PENALTY
                #return self.nextState()
                advance_state=True
            elif p.pos.y-p.height/2 < 0:
                if self.may_escape:
                    self.logEvent('escaped',self.trial_value)
                    #return self.nextState()
                    advance_state=True
                else:
                    p.y=ongoing['player_y']=p.height/2
                    
        elif self.state=='select':
            pass
        elif self.state=='delay':
            pass
        elif self.state=='feedback':
            pass
        elif self.state=='iti':
            pass
        else:
            raise RuntimeError('unrecognized state {}'.format(self.state))
        
        # could have threat_y and player_y in some states, but I don't think it is necessary.
        self.log.ongoing(**ongoing)
        
        if advance_state:
            return self.nextState()
    
    def on_key_press(self,k,modifiers):
        # only selection phase needs a key press to be handled
        if self._finished or self.state!='select':
            return
        
        messages=scanner_coms.messages()
        
        dx=0
        dy=0
        # all key presses are exclusive, no diagonal movement to consider for example.
        if k in (key.LEFT,key._4) or '1' in messages:
            dx=-1
        elif k in (key.RIGHT,key._6) or '3' in messages:
            dx=1
        elif k in (key.UP,key._8,key.ENTER) or '2' in messages:
            dy=1
        elif k in (key.DOWN,key._5,key._2) or '4' in messages:
            dy=-1
        
        if dy==1:
            # start the selected situation, if one is selected...
            if self._situation_i is not None:
                self.nextState()
        elif dx:
            self.shiftSituationSelection(dx)
            
    def finish(self):
        self._finished=True
        core.setLayer(None) # ends after one block
        #impl: log block summaries?
        #impl: hand off control
##testing:
#SituationSelectionLayer = FakeLayer('situation selection')
#SituationLayer = FakeLayer('situation!')
#%% main loop


#staircase = Staircase(diff_min=0.1)
#game_state = GameState()

# wait for the scanner trigger
# if there is a connection, you will have to
# use control-c to abort if needed.
print('waiting for scanner trigger')

#fixme: need better automatic configuration.  But for now there is no scanner,
# so just disabling it
#scanner_coms.wait_for_message(6)

from clock import Clock
class Core(object):
    '''
    Collecting some core items into a single object, adding convenience methods
    for handling them.  
    '''
    def __init__(self,**kwargs):
        self.clock = Clock()
        self.director = director
        director.init(**kwargs)
        director.show_FPS=False
        director.window.push_handlers(keys)
                
        self._scene = None
        self._layer = None
    
    def setLayer(self,layer):
        '''
        makes scene from given layer and makes it running.  If layer is None,
        the director is closed
        '''
        # quit
        if layer is None:
            #testing: this helps quick qick logs.  should add a finshed flag later
            #self._scene=self._layer=None
            self.director.pop()
            self.director.window.close()
        else:
            # first scene is run, rest replace previous
            if self._scene is None:
                setScene=self.director.run
            else:
                setScene=self.director.replace
            
            self._scene = Scene(layer)
            self._layer = layer
            setScene(self._scene)
        
        return self._layer

#NOTE: seems like cocos2d can be a bit laggy at the start.  Took 2 seconds for the first real scheduled update
# to be called, which was counted for the situation selection delay (bad!)
# not a problem if you have a instruction layer first with press enter to continue etc.
core = Core(caption='Foraging',width=WIDTH,height=HEIGHT, autoscale=True, resizable=True)
core.setLayer(MessageLayer("press enter to begin",next_layer=BlockLayer()))


#%% final saves


#testing:
try:
    core.setLayer(None)
except Exception as e:
    print(e)

block_layer = core._layer
logs = block_layer.log.process()
import pickle

data=dict(logs=logs,exp_info=exp_info)
with open(exp_info['fpath'],'wb') as f:
    pickle.dump(data,f) #can't be lazy and just use locals().  In this situation a namespace would be good, probably worth the added typing.


print('logs saved')
sys.exit()
#%% notes
