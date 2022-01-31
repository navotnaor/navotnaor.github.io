# -*- coding: utf-8 -*-
from __future__ import division
import math
import random

import cocos
import cocos.euclid as eu
import cocos.particle_systems as ps
from collections import OrderedDict
from cocos.euclid import Vector2 as Vec2

import numpy as np

'''
Steering library based on the "Understanding Steering Behaviors" series
https://gamedevelopment.tutsplus.com/series/understanding-steering-behaviors--gamedev-12732

Incomplete, unpolished, but at least it has a steering manager unlike
everything else I saw available...

'''




'''
not sure how to elegantly limit steering along certain directions
but it might not matter?
'''



#clean:  not sure if having these functions is better than wrapping
# objects as needed to support standard names
# standard names are nice, but conversions are problematic
# also, I'm not using the functions always.  should fix that.
# will this ever be not 2D?  


#doc: needs docstrings and more comments

def aabbCheck(lo,hi,p):    
    return p.x>=lo.x and p.x<=hi.x and p.y>=lo.y and p.y<=hi.y

def normalized(v):
    return v.normalized()
def normalize(v):
    return v.normalize()
def truncated(v, max_v):
    mag = abs(v)
    if mag > max_v:
        v = v*max_v / mag
    else:
        v = v.copy()
    return v
def truncate(v, max_v):
    mag = abs(v)
    if mag > max_v:
        v *= max_v / mag
    return v
def scaledBy(v,s):
    return v*s
def scaleBy(v,s):
    v*=s
    return v

def magnitude(v):
    return v.magnitude()


def setAngle(v,a):
    m = v.magnitude()
    v.x = math.cos(a)*m
    v.y = math.sin(a)*m
    return v




class Seek(object):
    def __init__(self,target,slowing_radius=0,detection_distance=np.inf):
        self.target=target
        self.slowing_radius=slowing_radius
        self.detection_distance=detection_distance
    def __call__(self,src):
        if self.target.pos is None:
            return type(src.vel)()
        
        desired = self.target.pos - src.pos
        distance = desired.magnitude()
        #normalize(desired)
        
        if distance>self.detection_distance:
            return type(src.vel)()
        
        if src.max_vel:
            normalize(desired)
            if distance <= self.slowing_radius:
                #print('scale',src.max_vel*distance/self.slowing_radius)
                scaleBy(desired, src.max_vel*distance/self.slowing_radius)
            else:
                #print(distance,self.slowing_radius)
                scaleBy(desired,src.max_vel)
        #else:
        #    print('x')
        
        force = desired - src.vel
        return force

class Avoid(object):
    def __init__(self,target,stopping_radius=None):
        self.target=target
        self.stopping_radius=stopping_radius
    def __call__(self,src):
        if self.target.pos is None:
            return type(src.vel)()
        
        desired = src.pos - self.target.pos
        distance = desired.magnitude()
        #normalize(desired)
        
        if src.max_vel:
            normalize(desired)
            if self.stopping_radius and distance >= self.stopping_radius:
                desired=src.vel
            else:
                scaleBy(desired,src.max_vel)
        
        force = desired - src.vel
        return force



class Wander(object):
    def __init__(self,radius,distance,change=math.pi/4, angle=0):
        '''
        early tests indicate you should scale your radius and distance
        to match any changes you make to max_vel.
        
        It may be worth having this scaling done automatically
        '''
        self.radius = radius
        self.distance = distance
        self.change = change
        self.angle = angle
    def __call__(self,src):
        # center of circle
        circle = normalized(src.vel)*self.distance
        # displacement vector
        displacement = type(circle)()
        displacement[0]=self.radius
        # wander a bit
        setAngle(displacement,self.angle)
        
        # change wander angle a bit for next time
        self.angle += (random.random()-0.5) * self.change
        #force
        force = circle+displacement
        print(force)
        return force

class SteeringManager(object):
    def __init__(self, src):
        self.src=src
        
        self._queue=OrderedDict()
        self._total_weight=0    
    
    def add(self,name,behav,weight=1):
        try:
            self.remove(name)
        except KeyError:
            pass
        behav._weight=weight
        behav._contrib=0
        self._queue[name] = behav
        self._total_weight+=behav._weight
    def remove(self,name):
        behav=self._queue.pop(name)
        self._total_weight-=behav._weight
    def get(self,name,d=None):
        return self._queue.get(name,d)
    def __getitem__(self,name):
        behav = self.get(name)
        if behav is None:
            raise KeyError(name)
        return behav            
    def __setitem__(self,name,behav):
        self.add(name,behav)
    def weight(self,name,value=None):
        '''get or set the weight of a named behavior'''
        behav = self[name]
        if value is None:
            return behav._weight
        self._total_weight += (value - behav._weight)
        behav._weight=value
    def update(self,dt):
        src=self.src
        steering = src.vel*0 # to keep the same type
        
        for name,behav in self._queue.items():
            force = behav(self.src)
            #print(name,force)
            weight = behav._weight/self._total_weight
            contrib = weight*force
            behav._contrib = contrib
            steering += contrib
        
        if src.max_force:
            truncate(steering,src.max_force)
        if src.mass!=1:
            scaleBy(steering,1/src.mass)
        
        src.vel+=steering
        if src.max_vel:
            truncate(src.vel,src.max_vel)
        
        src.pos+=dt*src.vel

class SimpleSteerable(object):
    '''
    The attributes required for steering are
    simply added.  For example you can use this
    as a target for the seek behavior and modify
    the pos attribute to follow the mouse coordinates.
    '''
    def __init__(self):
        self.pos=Vec2(0,0)
        self.vel=Vec2(0,0)
        
        self.mass=1
        self.max_vel=None
        self.max_force=0.2

#clean: max_vel is actually max speed...