# -*- coding: utf-8 -*-
"""
Created on Thu Oct 18 06:18:35 2018

@author: Josh

Updated Aug 20 15:13:00 2019

@author: Navot
"""

import numpy as np

'''
class Staircase(object):
    def __init__(self):
        self.absolute_min=0
        self.lo=0
        self.tracked_lo=0
        self.val=.5
        self.hi=1
        self.tracked_hi=1
        self.absolute_max=1
        
        self.next_trial()
    
    def next_trial(self):
        self.lo_f = np.random.uniform(self.lo,self.tracked_lo)
        self.hi_f = np.random.uniform(self.tracked_hi,self.hi)
        print('{} {} {} {}')
    
    def pick(self,low):
        if low:
            if self.val>self.tracked_hi:
                self.hi=self.absolute_max
            self.lo=min(self.tracked_lo,self.val)
            self.tracked_lo=max(self.tracked_lo,self.val)
            self.tracked_hi=max(self.tracked_hi,self.val)
        else:
            if self.val<self.tracked_lo:
                self.lo=self.absolute_min
            self.hi=max(self.tracked_hi,self.val)
            self.tracked_hi=min(self.tracked_hi,self.val)
            self.tracked_lo=min(self.tracked_lo,self.val)
        
        self.next_trial()

'''
class Staircase(object):
    '''
    Tries to estimate a true value by repeatedly offering choices between 2 values
    that are normally distributed around the current value estimate.  Values are
    limited to [0,1].  The scale of the normal distribution is reduced when the 
    offered value closest to the estimate value is chosen (else increased).
    
    '''
    def __init__(self,value=None,value_min=0,value_max=1,diff_min=0,diff_max=None,scale=1,scale_step=0.1,scale_min=0.1,scale_max=2):
        
        
        if value is None:
            value = (value_min+value_max)/2
        if diff_max is None:
            diff_max=value_max-value_min
        
        self.val=value
        self.value_min=value_min
        self.value_max=value_max
        self.scale=scale
        self.scale_step=scale_step
        self.scale_min=scale_min
        self.scale_max=scale_max
        self.diff_min=diff_min
        self.diff_max=diff_max
        
        self.n=1
        self._init_val=value
        self._init_scale=scale
        
        self.nextTrial()
        
    def nextTrial(self):
        while True:
            vals = np.random.normal(self.val,self.scale,2)
            vals[vals<self.value_min]=self.value_min
            vals[vals>self.value_max]=self.value_max
            (lo,hi)=vals
            diff = abs(hi-lo)
            if self.diff_min<=diff<=self.diff_max:
                break
        if hi<lo:
            (lo,hi)=(hi,lo)
        self.lo=lo
        self.hi=hi
    
    def pick(self,chose_low):
        predict_low = abs(self.val-self.lo) < abs(self.hi-self.val)
        # correct prediction tighten the scale, else expand scale
        if chose_low==predict_low:
            self.scale = max(self.scale_min,self.scale-self.scale_step)
        else:
            self.scale = min(self.scale_max,self.scale+self.scale_step)
        
        picked_val = self.lo if chose_low else self.hi
        
        self.n+=1
        
        ## running average for the value
        #self.val = self.val + (picked_val-self.val)/self.n
        # update with more sensitivity for last choice
        self.val=.75*self.val + 0.25*picked_val
        
        self.nextTrial()
    
    def reset(self):
        self.val=self._init_val
        self.scale=self._init_scale
        self.n=1

"""
class ForagingStaircase(object):
    '''
    '''
    def __init__(self,mode='updown',**kwargs):
        self.mode=mode
        self.state=dict()
        
        if mode=='updown':
            '''
            up=1
            down=2
            step=.1
            low=.1
            high=1
            init=.9
            '''
            #kwargs.setdefault()
            
            self.state['value'] = kwargs['init']
            pass
        else:
            raise NotImplementedError('unrecognized mode {}'.format(mode))
        
        self.settings=kwargs
        
        self.nextTrial()
    
    def nextTrial(self,**kwargs):
        if mode=='updown':
            pass
    def update(self,**kwargs):
        if mode=='updown':
            if kwargs['choice']=='easy':
                self.state['value']+=self.settings['step']
            else:
                self.state['value']-=self.settings['step']
            pass
    def reset(self):
        pass
"""

class ForagingStaircase(object):
    def __init__(self):
        '''
        rewards are fixed values, but risk is normalized [0,1]
        '''
        self.reset()
    
    def _rewards(self):
        lows=np.array(self.lows)
        bonuses=np.array(self.bonuses)
        N = len(lows)*len(bonuses)
        
        while True:
            np.random.shuffle(lows)
            np.random.shuffle(bonuses)
            for low in lows:
                for bonus in bonuses:
                    yield (low,low+bonus)
        
    def _nextTrial(self):
        # make sure f is limited properly
        if self.f<=self.min_f:
            self.f=self.min_f
        if self.f>=self.max_f:
            self.f=self.max_f
        
        # calculate new values
        (lo,hi)=next(self.rewards)
        lo_risk=lo*self.f
        hi_risk=hi*self.f
        
        self.params=((lo_risk,lo),(hi_risk,hi))
        return self.params

    def update(self,success):
        # based only on success, try to make it harder to succeed
        if success:
            self.f+=self.step
        else:
            self.f-=self.step
        
        return self._nextTrial()
    
    def reset(self):
        self.lows=np.array([10,20,30,40,50])
        self.bonuses=np.array([10,20,30,40])
        self.min_risk=.1
        self.max_risk=1
        self.min_rewd=self.lows[0]
        self.max_rewd=self.lows[-1]
        #self.max_rewd=self.lows[-1]+self.bonuses[-1]
        #self.min_f=self.min_risk/self.max_rewd
        #self.max_f=self.max_risk/self.min_rewd
        self.min_f=self.min_risk/self.max_rewd
        self.max_f=self.max_risk/self.min_rewd
        
        self.norm_step = 0.1
        self.norm_init = 0.7
        r=(self.max_f-self.min_f)
        self.step=self.norm_step*r
        self.f = self.min_f+self.norm_init*r
        
        self.rewards = iter(self._rewards())
        
        self._nextTrial()


class ForagingStaircase(object):
    def __init__(self):
        '''
        rewards are fixed values, but risk is normalized [0,1]
        '''
        self.reset()
    
    def _rewards(self):
        lows=np.array(self.lows)
        bonuses=np.array(self.bonuses)
        N = len(lows)*len(bonuses)
        
        while True:
            np.random.shuffle(lows)
            np.random.shuffle(bonuses)
            for low in lows:
                for bonus in bonuses:
                    yield (low,low+bonus)
        
    def _nextTrial(self):
        # make sure f is limited properly
        if self.f<=self.min_f:
            self.f=self.min_f
        if self.f>=self.max_f:
            self.f=self.max_f
        
        # calculate new values
        (lo_rewd,hi_rewd)=next(self.rewards)
        
        #lo_reward_norm = (lo_rewd-self.min_rewd)/(self.max_rewd-self.min_rewd))
        
        lo_risk=lo_rewd*self.f
        hi_risk=hi_rewd*self.f
        # normalize risk values for use externally
        lo_risk=(lo_risk-self.min_risk)/(self.max_risk-self.min_risk)
        hi_risk=(hi_risk-self.min_risk)/(self.max_risk-self.min_risk)
        
        self.params=((lo_risk,lo_rewd),(hi_risk,hi_rewd))
        return self.params

    def update(self,success):
        # a system for increasing step size if the player is trending away from the current
        # estimate.  Not sure if it is good or not.
        if self.last_success==success:
            self.run+=1
        else:
            self.run=0
            self.last_success=success
        self.step = self.min_step+self.run*self.step_step
        
        # based only on success, try to make it harder to succeed
        if success:
            self.f+=self.step
        else:
            self.f-=self.step
        
        return self._nextTrial()
    
    def reset(self):
        # real coin values, but risk is artificially scaled to match so they are
        # more comparable
        self.lows=np.array([10,20,30,40,50])
        self.bonuses=np.array([10,20,30,40])
        self.min_risk=self.min_rewd=self.lows[0]
        self.max_risk=self.max_rewd=self.lows[-1]+self.bonuses[-1]
        self.min_f=self.min_risk/self.max_rewd
        self.max_f=1
        
        # convert percentage steps for staircasing into actual values
        self.norm_step = 0.1
        self.norm_init = 0.7
        r=(self.max_f-self.min_f)
        self.step = self.norm_step*r
        self.f = self.min_f+self.norm_init*r
        
        self.max_step = self.step
        self.min_step = self.step/5
        self.step_step = self.min_step
        self.last_success = None
        self.run = 0
        
        # endlessly repeating combinations of low and high reward values
        # randomized order but tries to keep all combinations balanced
        self.rewards = iter(self._rewards())
        
        self._nextTrial()



class ForagingStaircase(object):
    def __init__(self):
        '''
        rewards are fixed values, but risk is normalized [0,1]
        
        #clean: copied from previous 2 situation staircasing
        '''
        self.reset()
    
    def _rewards(self):
        values=np.array(self.values)
        N = len(values)
        
        while True:
            np.random.shuffle(values)
            for value in values:
                yield value
        
    def _nextTrial(self):
        # make sure f is limited properly
        if self.f<=self.min_f:
            self.f=self.min_f
        if self.f>=self.max_f:
            self.f=self.max_f
        
        # calculate new values
        rewd=next(self.rewards)
        
        risk=rewd*self.f
        # normalize risk values for use externally
        risk=(risk-self.min_risk)/(self.max_risk-self.min_risk)
        
        self.params=((risk,rewd),)
        return self.params

    def update(self,success):
        # a system for increasing step size if the player is trending away from the current
        # estimate.  Not sure if it is good or not.
        if self.last_success==success:
            self.run+=1
        else:
            self.run=0
            self.last_success=success
        self.step = self.min_step+self.run*self.step_step
        
        # based only on success, try to make it harder to succeed
        if success:
            self.f+=self.step
        else:
            self.f-=self.step
        
        return self._nextTrial()
    
    def reset(self):
        # real coin values, but risk is artificially scaled to match so they are
        # more comparable
        #self.values = (np.arange(9)+1)*10
        self.values = (np.arange(1,6,4))*10 #Set's the levels of rewerds 
        self.min_risk=self.min_rewd=self.values[0]
        self.max_risk=self.max_rewd=self.values[-1]
        self.min_f=self.min_risk/self.max_rewd
        self.max_f=1
        
        # convert percentage steps for staircasing into actual values
        self.norm_step = 0.1
        self.norm_init = 0.7
        r=(self.max_f-self.min_f)
        self.step = self.norm_step*r
        self.f = self.min_f+self.norm_init*r
        
        self.max_step = self.step
        self.min_step = self.step/5
        self.step_step = self.min_step
        self.last_success = None
        self.run = 0
        
        # endlessly repeating combinations of low and high reward values
        # randomized order but tries to keep all combinations balanced
        self.rewards = iter(self._rewards())
        
        self._nextTrial()


if __name__=='__main__':
    sc = ForagingStaircase()
    """
    def constrainedExponential(u,lo,hi,size=None):
        '''
        np.random.exponential but further constrains the returned value
        to [lo,hi]
        '''
        if lo>hi:
            raise ValueError('lower limit must be below upper limit')
        
        v = np.random.exponential(u,size=None)
        if size in (None,1):
            if v<lo:
                v=lo
            if v>hi:
                v=hi
        else:
            v[v<lo]=lo
            v[v>hi]=hi
        
        return v
    
    import matplotlib.pyplot as plt
    
    plt.figure()
    vals=constrainedExponential(.6,.3,)
    plt.hist(,bins=100)
    """
"""
if __name__=='__main__':
    import matplotlib.pyplot as plt
    true_val = 0.9
    oops_chance = 0.1
    
    risk_min=0
    risk_max=1
    reward_min=.1
    reward_max=1
    val_min=risk_min/reward_max
    val_max=risk_max/reward_min
    
    los=[]
    his=[]
    vals=[]
    lo_picks=[]
    oops=[]
    scales=[]
    true_vals=[]
    #idea: more values should depend on percentages?
    # or should I convert outside?
    #sc=Staircase(value_min=val_min,value_max=val_max,diff_min=0.1*(val_max-val_min),scale_min=0.1,scale_max=10,scale=5,scale_step=1)
    sc=Staircase(diff_min=0.1)
    
    for i in range(100):
        
        true_val = 0.1+0.8*(i/100)
        true_vals.append(true_val)
        
        pick_lo = abs(true_val-sc.lo) < abs(sc.hi-true_val)
        if np.random.rand()<=oops_chance:
            pick_lo = not pick_lo
            oops.append(True)
        else:
            oops.append(False)
        
        lo_picks.append(pick_lo)    
        los.append(sc.lo)
        his.append(sc.hi)
        vals.append(sc.val)
        scales.append(sc.scale)
        
        sc.pick(pick_lo)
    
    
    
    plt.figure()
    plt.plot(los,label='lo')
    plt.plot(his,label='hi')
    plt.plot(vals,label='val')
    plt.plot(scales,label='scales')
    plt.plot(oops,label='mistake')
    #plt.axhline(true_val,linestyle='--',color='k',label='true')
    plt.plot(true_vals,'--k',label='true')
    plt.legend()
"""