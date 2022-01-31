# -*- coding: utf-8 -*-


from __future__ import division
import numpy as np
import pandas as pd
import simpleaudio as sa
import pyglet
from pyglet.window import key
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
import time
import copy
import os
import pickle
import sys

'''
requirements:
    anaconda
    cocos
    simpleaudio
'''

try:
    from itertools import izip
except ImportError:
    izip=zip

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    import Tkinter as tk
    from Tkinter import messagebox

from scipy.interpolate import interp1d

# on-demand key state checking
keys = key.KeyStateHandler()

# load some images
def loadImage(fname,centered=True,**kwargs):
    img = pyglet.resource.image(fname,**kwargs)
    if centered:
        img.anchor_x = img.width/2
        img.anchor_y = img.height/2
    return img


#%% various functions and classes

def timestamp(*args, **kwargs):
    '''
    more convenient timestamp that defaults to iso8601 format
    
    dsep = separator for date part
    tsep = separator for time part
    sep = separator between date and time part
    
    
    timestamp()
    timestamp(format,time_tuple)
    timestamp(time_tuple)
    timestamp(format)
    '''
    
    N=len(args)
    fmt=None
    tup=None
    if N==0:
        pass
    elif N==1:
        arg=args[0]
        if hasattr(arg,'capitalize'):
            fmt=arg
        else:
            tup=arg
    elif N==2:
        (fmt,tup)=args
    else:
        raise RuntimeError('expected 0-2 arguments, got {}'.format(N))
    
    if fmt is None:
        dsep=kwargs.get('dsep','')
        tsep=kwargs.get('tsep','')
        sep =kwargs.get('sep','_')
        fmt = "%Y{0}%m{0}%d{1}%H{2}%M{2}%S".format(dsep,sep,tsep)
    if tup is None:
        args=(fmt,)
    else:
        args=(fmt,tup)
    
    return time.strftime(*args)


def loads(txt,latin1_fallback=True,silent=False):
    '''
    a slightly more robust pickle.loads
    made to handle changes in py2->py3
    handling of unicode and defaults
    for pickling.
    
    pulled from jkpy
    '''
    try:
        return pickle.loads(txt)
    except UnicodeDecodeError as e:
        print(e)
        pass
    except TypeError as e:
        print(e)
        pass
    
    if not latin1_fallback:
        raise
    if not silent:
        print(e)
        print('attempting latin1 encoding fallback...')
    return pickle.loads(str(txt.decode('latin1')))

import sqlite3
from collections import MutableMapping
class PersistentDict(MutableMapping):
    '''
    Theoretically thread safe sqlite backed dictionary
    http://stackoverflow.com/questions/9320463/persistent-memoization-in-python
    
    pulled from jkpy
    '''
    def __init__(self, dbpath, iterable=None, **kwargs):
        self.dbpath = dbpath
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'create table if not exists memo '
                '(key blob primary key not null, value blob not null)'
            )
        if iterable is not None:
            self.update(iterable)
        self.update(kwargs)
    
    def encode(self, obj):
        #return pickle.dumps(obj)
        return pickle.dumps(obj,protocol=0)
    
    def decode(self, blob):
        #return loads(blob,silent=True)
        return pickle.loads(blob)
        
    
    def get_connection(self):
        return sqlite3.connect(self.dbpath)
    
    def  __getitem__(self, key):
        key = self.encode(key)
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'select value from memo where key=?',
                (key,)
            )
            value = cursor.fetchone()
        if value is None:
            raise KeyError(key)
        return self.decode(value[0])
    
    def __setitem__(self, key, value):
        key = self.encode(key)
        value = self.encode(value)
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'insert or replace into memo values (?, ?)',
                (key, value)
            )
    
    def __delitem__(self, key):
        key = self.encode(key)
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'select count(*) from memo where key=?',
                (key,)
            )
            if cursor.fetchone()[0] == 0:
                raise KeyError(key)
            cursor.execute(
                'delete from memo where key=?',
                (key,)
            )
    
    def __iter__(self):
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'select key from memo'
            )
            records = cursor.fetchall()
        for r in records:
            yield self.decode(r[0])
    
    def __len__(self):
        with self.get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                'select count(*) from memo'
            )
            return cursor.fetchone()[0]


import traceback
def str_err(*args,**kwargs):
    '''
    turns an exception into a string
    see inline comments for details on usage if needed
    
    pulled from jkpy
    '''
    N=len(args)
    
    # sys.exc_info style
    if N==0:
        return traceback.format_exc(**kwargs)
    # e_ty, e_val, tb
    if N==3:
        return '\n'.join(traceback.format_exception(*args,**kwargs))
    # e_ty, e_val
    if N==2:
        (ty,val)=args
        if isinstance(ty,BaseException):
            (val,ty)=(ty,val)
        #fixme: does this handle assertions well?
        return '\n'.join(traceback.format_exception_only(ty,val))
    # decide by type
    if N==1:
        arg=args[0]
        # just exception
        if isinstance(args,BaseException):
            return str_err(type(arg),arg,**kwargs)
        # just a traceback
        return '\n'.join(traceback.format_tb(tb,**kwargs))
    
    raise ValueError('expected 0-3 arguments, was given {}'.format(N))


def perr(fn):
    '''
    prints exception before reraising it.  Good for async callback methods
    and properties, where the exceptions can get lost or misinterpreted
    
    pulled from jkpy
    '''
    def wrapper(*args,**kwargs):
        try:
            return fn(*args,**kwargs)
        except Exception:
            print(str_err())
            print('\n')
            raise
    return wrapper

def clamp(v,lo,hi,w=0):
    '''
    restricts v such that lo<=v<=hi
    returns the result (lo, hi, or v)
    w is the optional width of v to further limit it
    '''
    hw=w/2
    if v-hw<lo:
        return lo+hw
    if v+hw>hi:
        return hi-hw
    return v

def constrainedExponential(u,lo,hi,size=None):
    '''
    np.random.exponential but further constrains the returned value
    to [lo,hi]
    '''
    if lo>hi:
        raise ValueError('lower limit must be below upper limit')
    
    if size in (None,1):
        while True:
            v = np.random.exponential(u)
            if lo<=v<=hi:
                return v
    else:
        parts = []
        need = size
        while need:
            v = np.random.exponential(u,size=need)
            v = v[v>=lo]
            v = v[v<=hi]
            need -= len(v)
            parts.append(v)
        return np.concatenate(parts)

def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return izip(*[iter(iterable)]*n)

class ScannerComs(object):
    '''
    Uses pyserial to monitor serial port for messages.  To be used in the scanner,
    for the button box.  Note that the port is different for the mock scanner
    and real scanner.
    
    # set to 3 for the real scanner, 2 for the mock scanner
    
    monitoring a serial port from the scanner is instead a queue of messages.  Care needs to be taken
    not to handle old messages by accident.  Like if the subject is pressing buttons before a trial,
    they might select a response when the trial starts.
    '''
    def __init__(self,port=2, timeout=0.001, baudrate=19200, verbose=False):
        self.verbose=verbose
        self.alive=False
        
        try:
            # stopbits?  bytesize?
            import serial
            self._coms = serial.Serial(port, timeout=timeout, baudrate=baudrate)
            if verbose:
                print('using serial port {}'.format(self._coms.portstr))
            self._str = 'ScannerComs(port={}, timeout={}, baudrate={})'.format(port,timeout,baudrate)
            self.alive = True
        except:
            self._coms = None
            print('could not connect to serial port.  This is OK if not hooked up to a scanner.  Else check your connections,ports,settings,pyserial installed,etc...')
            self._str = 'Dummy ScannerComs instance, never connected properly'
        self._messages=[]
        
    def close(self):
        if self._coms:
            self._coms.close()
            self._coms=None
            self._str='closed ScannerComs instance'
            self.alive=False
    
    def clear(self):
        '''
        clear all incoming messages
        '''
        if self._coms:
            self._coms.flushInput()
        self._messages=[]
    
    def _read(self):
        while True:
            msg = self._coms.read()
            if not msg:
                break
            self._messages.append(msg)
    
    def wait_for_message(self,*valid_messages):
        '''
        returns whenever a valid message is encountered
        '''
        if not self._coms:
            return
        
        old_settings = self._coms.getSettingsDict()
        settings = old_settings.copy()
        settings['timeout']=None
        self._coms.applySettingsDict(settings)
        while True:
            msg = self._coms.read()
            if msg in valid_messages:
                self._coms.applySettingsDict(old_settings)
                return
    
    def messages(self, clear_after=True, as_set=True):
        if self._coms:
            self._read()
            ret = self._messages
        else:
            ret=[]
        
        if as_set:
            ret=set(ret)
        if clear_after:
            self._messages=[]
        return ret
    
    def __bool__(self):
        return self.alive
    def __repr__(self):
        return self._str
    
    __nonzero__=__bool__
    __str__=__repr__

#%% GUIs for starting info

class CreateToolTip(object):
    """
    create a tooltip for a given widget
    delay is milliseconds, wrap is in pixels
    
    based on:
        https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
        crxguy52
    """
    def __init__(self, widget, text='widget info', delay=500, wrap=1000):
        self.waittime = delay
        self.wraplength = wrap
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


#idea: have a button to load defaults (known file like default_start.ini?)  then testers
# can have their own folder of various settings and just overwrite what is in the program
# folder and click a button to quickly switch
class StartForm(tk.Tk):
    '''
    Tkinter root class just used to ask for details at the start
    '''
    def __init__(self,save_folder,details):
        tk.Tk.__init__(self)
        self.details=[list(d) for d in details]
        self.results=None
        self.save_folder=save_folder
        self._build()
    
    @perr
    def _build(self):
        self.title('Enter Subject Details')
        
        self.grid()
        group=tk.LabelFrame(self)
        group.grid(row=0,columnspan=7,sticky='W',padx=5,pady=5,ipadx=5,ipady=5)
        
        # flexible simple input with label grid
        for row,detail in enumerate(self.details):
            tip = detail.pop()
            default = detail.pop()
            (name,ty) = detail
            
            # label
            label=tk.Label(group,text=name)
            label.grid(row=row,column=0,sticky='W')
            
            # variable for get/set value and a widget for user
            if ty is bool:
                entry=tk.BooleanVar()
                entry.set(default)
                widget=tk.Checkbutton(group,variable=entry)
            else:
                widget=entry=tk.Entry(group)
                entry.insert(0,default)
            widget.grid(row=row,column=1,sticky='W')
            
            # tooltip text
            CreateToolTip(label,tip)
            CreateToolTip(widget,tip)
            
            # save entry for later
            detail.append(entry)
        
        # dropdown lists for selecting the modes
        self.modes=dict()
        for (what,modes,default,tip_text) in MODES_INFO:
            row+=1
            
            label=tk.Label(group,text=what)
            label.grid(row=row,column=0,sticky='W')
            
            # drop down list
            var=tk.StringVar(self)
            var.set(default)
            dd = tk.OptionMenu(group,var,*modes)
            dd.grid(row=row,column=1,sticky='E')
            
            CreateToolTip(label,tip_text)
            CreateToolTip(dd,tip_text)
            
            self.modes[what]=var
        # annoying, best way I could find to add a spacer of some sort...
        label=tk.Label(group,text="")
        label.grid(pady=10)
        
        but=tk.Button(group,text="Submit",command=self.submit)
        but.grid(sticky='E',column=1,pady=0)
        self.bind('<Return>',self.submit)
        self.bind('<Escape>',self.abort)
        self.protocol('WM_DELETE_WINDOW',self.abort)
        
        
        but=tk.Button(group,text="Save Settings",command=self.save)
        but.grid(sticky='E',pady=0)
        but=tk.Button(group,text="Load Settings",command=self.load)
        but.grid(sticky='E',pady=0)
    
    def save(self,event=None):
        with open('exp_info.pkl','wb') as f:
            pickle.dump(self._results(),f)
    
    def load(self,event=None):
        with open('exp_info.pkl','rb') as f:
            results=pickle.load(f)
        
        for (name,ty,entry) in self.details:
            if ty is bool:
                entry.set(bool(results[name]))
            else:
                entry.delete(0,tk.END)
                entry.insert(0,str(results[name]))
        
        for mode,var in self.modes.items():
            var.set(results[mode])
        
    def abort(self,event=None):
        self.results=None
        self.close()
    def close(self,event=None):
        self.destroy()
            
    def _results(self):
        results=dict()
        for (name,ty,entry) in self.details:
            txt=entry.get()
            
            value=ty(txt)
            results[name]=value
        
        for mode,var in self.modes.items():
            results[mode] = var.get()
        
        return results
    
    def submit(self,event=None):
        self.results = self._results()
        
        self.results['fpath']=fpath=os.path.join(self.save_folder,timestamp()+'_'+self.results['Subject ID']+'.pickle')
        if os.path.exists(fpath):
            msg='The subject {} already has data (see {})\nDo you want to overwrite?'.format(self.results['Subject ID'],fpath)
            res = messagebox.showwarning('Overwrite Warning',msg,type=messagebox.ABORTRETRYIGNORE)
            if res==messagebox.ABORT:
                self.results=None
            elif res==messagebox.RETRY:
                return
            elif res==messagebox.IGNORE:
                pass
            else:
                self.results=None
        
        self.close()

def getStartDetails(save_folder,what):
    '''
    returns dictionary of desired details
    pass in pairs of (name,type)
    '''
    root=StartForm(save_folder,what)
    root.mainloop()
    print(root.results)
    return root.results


def prettySample(large_sample,N,vmin,vmax,max_iterations=1000,mode='uniform',nbins=None):
    '''
    Copied from jkpy 2018-07-24
    
    list_of_numbers=prettySample(large_sample,N,vmin,vmax,**kwargs)
     
    Get a pretty looking pseudorandom sample (of a set length) from a larger sample.  The idea is that the larger sample
    is a good enough approximation for whatever distribution you want.  The approach is to then make a histogram of the
    larger sample, use that to get an approximate distribution, then search out a factor f such that:
        N==sum(round(f*dist))
     
    This gives the histogram for our desired pretty sample.  In other words, round(f*dist) are the counts per bin that
    should come from our final pretty sample.  How we work backwards from this histogram to our final sample depends on
    the mode parameter.
     
     
    Arguments
    ------------------------------------
    large_sample: sequence of values
        len(large_sample) should be a good deal higher than N after excluding values outside [vmin,vmax].  The
        large_sample should be basically what you would hope to be using as your sample, just with too many values.
    N: integer
        How many values you want to return.
    vmin: 
        smallest value to be included in your final sample
    vmax:
        largest value to be included in your final sample
     
    nbins=N/3:
        The number of bins to use for our histograms.  N/3 seemed to work well for my tests, but you should see what
        looks good for your large_sample. That is the best way, really...
     
    mode: one of 'center','uniform', (and that's it for now)
        'center': per bin of our final histogram, assume all values are at the center of a bin.  Thus there will only be
                  at most nbins unique values returned.
        'uniform': for our final histogram, assume the values are uniformly distributed within each bin
     
    max_iterations=1000:
        this method is iterative, and there is a possibility that it won't be able to find a solution.  Set this to
        some value to limit how long it'll keep trying.  Currently, there is no implementation for when the algorithm
        fails to find a solution.  One should be possible, I just haven't gotten there yet.
         
    SEE SOURCE FOR EXAMPLE
    '''
    class MaxIterationsReachedException(Exception):
        pass
     
    # get a fairly good histogram counts of the large_sample (large enough to be very close to the actual distribution)
    bN=nbins if nbins else int(N/3)
    if not bN:
        raise Exception('''You are asking for way too few numbers for prettySample to be useful.
        Carefully examine your code to make sure it is doing what you want.''')
    centers=np.linspace(vmin,vmax,bN)
    if mode=='uniform':
        bins=np.linspace(vmin,vmax,bN+1)
    elif mode=='center':
        bins=np.linspace(vmin-.5/bN,vmax+.5/bN,bN+1)
    (counts,bins)=np.histogram(large_sample,bins=bins)
    #(counts,bins,patches)=pylab.hist(large_sample,bins=bins)
    prof=counts/sum(counts)
     
    # initialize variables
    C=0
    f=N*1.0
    s=1.0
    i=0
     
    # iterate
    try:
        while C!=N:
            while C<N if s>0 else C>N:
                V=list(map(int,f*prof))
                C=np.sum(V)
                i+=1
                f+=s
                if i>max_iterations:
                    raise MaxIterationsReachedException        
            s=-s/2.0
    except MaxIterationsReachedException:
        print('stopped, max_iterations setting exceeded')
     
    # convert to the final sampling
    if mode=='uniform':
        def get_values(i,v):
            return list(np.linspace(bins[i],bins[i+1],v))
    elif mode=='center':
        def get_values(i,v):
            return [centers[i]]*v
     
    S=[]
    for i,v in enumerate(V):
        S+=get_values(i,v)
    #V=[x for i,v in enumerate(V) for x in [centers[i]]*v]
    random.shuffle(S)
    if (len(S)<N):
        print('achieving desired count by pulling {} more values from the beginning of large_sample'.format(N-len(S)))
        S+=large_sample[:N-len(S)]
    if (len(S)>N):
        print('achieving desired count by dropping the last {} values from the pretty sample'.format(len(S)-N))
        S=S[:N]
    return S


#clean: this sequence stuff needs more testing, documentation,
# and perhaps expansion given how useful it is.
# still can't get a version that can be built gradually, need to experiment
# more with that.
class ActionSequence(object):
    def __init__(self,*args):
        '''
        A sequence of targeted actions for cocos.  Each action has an explicit
        target to be applied to, and each action is done sequentially when run.
        Like a normal cocos sequence, but now you can join them even with different
        targets.
        
        aseq=ActionSequence()
        aseq+=('t1','a1')
        aseq+=('t2','a2')+('t3','a3')
        
        aseq2=ActionSequence()
        aseq2+=('t4','a4')
        aseq2+=('t5','a5')+('t6','a6')
        
        a=aseq+('t3.5','a3.5')+aseq2+('t7','a7','t8','a8')
        
        a2=ActionSequence(aseq,aseq2,('t?','a?'),a,('t77','a77','t88','a88'))
        
        
        aseq.start()
        '''
        self._data=[]
        if args:
            self.extend(args)
    def append(self,other):
        '''
        '''
        self._data+=list(other)
        return self
    def extend(self,others):
        '''
        '''
        for other in others:
            self.append(other)
    def start(self):
        '''
        '''
        delay=0
        for (target,action) in grouped(self._data,2):
            action = cocos.actions.Delay(delay)+action
            delay = action.duration
            target.do(action)
    def __iter__(self):
        return iter(self._data)
    __iadd__=append
    def __add__(self,other):
        return ActionSequence(self._data+list(other))
    __call__=start    
    def __repr__(self):
        return 'ActionSequence({})'.format(str(list(grouped(self._data,2)))[1:-1])



class _TestSequence(ca.Action):
    def init(self, *pairs):
        # targets can't be copied nicely
        self._pairs = pairs
        #self._pairs = [(copy.deepcopy(t),a) for (t,a) in pairs]
        #self._pairs = [(0,a) for (t,a) in pairs]
        #self._pairs = [(lambda:t,a) for (t,a) in pairs]
        #self._pairs = [(closer(t),a) for (t,a) in pairs]
        
        self._i = 0

    def start(self):
        self.current_action = copy.deepcopy(self._pairs[0][1])
        #self.current_action.target = self.target
        self.current_action.target = self._pairs[0][0]()
        self.current_action.start()

    def step(self, dt):
        self._elapsed += dt
        self.current_action.step(dt)
        if self.current_action.done():
            self.current_action.stop()
            self._i+=1
            if self._i==len(self._pairs):
                self._done = True
            else:
                self.current_action = copy.deepcopy(self._pairs[self._i][1])
                #self.current_action.target = self.target
                self.current_action.target = self._pairs[self._i][0]()
                self.current_action.start()
    
    def stop(self):
        if not self._done:
            self.current_action.stop()
def TestSequence(*pairs):
    return _TestSequence(*[(closer(t),a) for (t,a) in pairs])
def closer(target):
    def fn():
        return target
    return fn




#%% establish the mode details
SHOCK_MODES=('none','lab','mock','scan')
CONFIG_MODES=('debug','practice','full')

DEFAULT_SHOCK_MODE='lab'
DEFAULT_CONFIG_MODE='full'

#idea: add model numbers for shock machines
SHOCK_MODES_TIP='''
none: no shock will happen, no shock machine is connected to
lab: connects to the shock machine in the lab
mock: connects to the shock machine in the mock scanner
scan: connects to the shock machine in the real scanner
'''.strip()

CONFIG_MODES_TIP='''
debug: for debugging and testing, goes faster and runs forever, might show debug messages
practice: practice mode, basically the same settings as full experiment but goes forever
full: full experiment
'''.strip()

MODES_INFO = (('Shock Mode',SHOCK_MODES,DEFAULT_SHOCK_MODE,SHOCK_MODES_TIP),('Config Mode',CONFIG_MODES,DEFAULT_CONFIG_MODE,CONFIG_MODES_TIP))

for (mode,modes,default,tips) in MODES_INFO:
    if default not in modes:
        raise RuntimeError('Default {} "{}" not an actual mode!'.format(mode,default))