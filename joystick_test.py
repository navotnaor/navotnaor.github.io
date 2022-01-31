import cocos
import cocos.collision_model as cm
import cocos.actions as ca
import cocos.euclid as eu
import cocos.particle_systems as ps
from cocos.director import director
from cocos.cocosnode import CocosNode
from cocos.sprite import Sprite
from cocos.scene import Scene
from cocos.layer import Layer
from cocos.euclid import Vector2 as Vec2
import pyglet
#%% configuration and notes
'''
You need to determine the joystick_number and a good deadzone value.  Hopefully these defaults work though?

The program will show the x position of the joystick [-1,1] along with a determination of left or right (or nothing)
based on the deadzone.
'''

# joystick position is [-1,1].  You need to define a deadzone that accounts for 
# joystick error (so small offsets aren't detected as intended)
deadzone=0.3
# hopefully there is only 1 joystick.  Otherwise, you may need to change this
# to pick a different joystick out of a list
joystick_number=0

#%% basic initialization
WIDTH=800
HEIGHT=600

joysticks = pyglet.input.get_joysticks()
if len(joysticks)!=1:
    print('WARNING:  found {} joysticks, be sure to edit "joystick_number" to pick the correct one.'.format(len(joysticks)))

print('detected joysticks:')    
for i,joystick in enumerate(joysticks):
    print('joystick {}: {}'.format(i,joystick.device))
print('=============================================')
joystick = joysticks[joystick_number]
joystick.open()

#%% display classes

class FeedbackLayer(Layer):
    #is_event_handler=True
    def __init__(self):
        Layer.__init__(self)
        self.dir_txt = cocos.text.Label('',
              font_name='Times New Roman',
              font_size=36,
              anchor_x='center', anchor_y='center')
        self.dir_txt.position=(WIDTH/2,HEIGHT/2)
        self.add(self.dir_txt)
        self.x_txt = cocos.text.Label('',
              font_name='Times New Roman',
              font_size=36,
              anchor_x='center', anchor_y='center')
        self.x_txt.position=(WIDTH/2,HEIGHT*.4)
        self.add(self.x_txt)
        
        label = cocos.text.Label('deadzone = {}'.format(deadzone),anchor_y='bottom',anchor_x='left')
        self.add(label)
        
        
        self.schedule(self.update)
    def update(self,dt):
        if abs(joystick.y)<deadzone:
            txt=''
        elif joystick.y<0:
            txt='up'
        else:
            txt='down'
        #raise RuntimeError('asdf')
        self.dir_txt.element.text=txt
        self.x_txt.element.text = '{:0.4f}'.format(joystick.y)
'''
    def update(self,dt):
        for v in ('x','y','z',')
        print('x={}'.format(joystick.y))
        print('y={}'.format(joystick.y))
        print('x={}'.format(joystick.y))
        
'''     
#%% run it
director.init(caption='Joystick Test',width=WIDTH,height=HEIGHT, autoscale=True, resizable=True)
layer = FeedbackLayer()
scene = Scene(layer)
director.run(scene)

director.window.close()