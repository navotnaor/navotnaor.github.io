#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 13:27:33 2019

@author: Josh
"""

import sys
import time

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
    
from shocker import Shocker

class MainForm(tk.Tk):
    '''
    Tkinter root class just used to ask for details at the start
    '''
    
    # range for program levels
    lo=71
    hi=104
    # range for dial values
    dlo=0.9
    dhi=4.4
    
    # dial<->program is roughly linear from someone else's tests
    # dials=np.array([0.9,1.1,1.4,1.7,2.1,2.5,2.8,3.3,4.4])
    # levels=np.array([71,72,75,79,80,84,91,96,104])
    
    def __init__(self):
        tk.Tk.__init__(self)
        self.title('Shock Value Tester')
        self.grid()
        self.group = group=tk.LabelFrame(self)
        group.grid(row=9,columnspan=7,sticky='W',padx=5,pady=5,ipadx=5,ipady=5)
        
        label=tk.Label(group,text="duration (s)")
        label.grid(row=0,column=0,sticky='W')
        
        self.db = tk.Entry(group)
        self.db.insert(0,1.0)
        self.db.grid(row=0,column=1,sticky='W')
        
        label=tk.Label(group,text="shock level")
        label.grid(row=1,column=0,sticky='W')
        
        self.sb = tk.Spinbox(group,from_=self.lo,to=self.hi)#,validate='focusout',validatecommand=self._validate)
        self.sb.grid(row=1,column=1,sticky='W')
        
        #spacer
        label=tk.Label(group,text="")
        label.grid(pady=10)
        
        self.zb = tk.Button(group,text="ZAP",command=self.shock)
        self.zb.grid(sticky='E',column=0,pady=0)
        
        self.bind('<Return>',self.shock)
        self.bind('<Escape>',self.close)
        self.protocol('WM_DELETE_WINDOW',self.close)
        
        try:
            shocker = Shocker(192,address=0xD070,mode='in_lab')
        except Exception as e:
            print(e)
            print('not enabling shocker')
            shocker = Shocker(0,0,0)
        self.shocker=shocker
        
        self._shockStop()
    
    def close(self,event=None):
        self.destroy()
    
    def _shockStop(self):
        self.shocker.stop()
        self.configure(background='grey')
        
    def shock(self,event=None):
        try:
            level=int(self.sb.get())
        except ValueError:
            print('invalid level (must be integer)')
            return
        if not self.lo<=level<=self.hi:
            print('invalid range for shock [{},{}]'.format(self.lo,self.hi))
            return
        self.shocker.level=level
        
        try:
            dur=float(self.db.get())
        except ValueError:
            print('invalid duration')
            return
        
        dial = (self.dhi-self.dlo)/(self.hi-self.lo) * (level-self.lo) + self.dlo
        print('shocking level {} for {} s (dial value would be about {:0.3f})'.format(level,dur,dial))
        
        self.configure(background='red')
        self.shocker.start()
        self.after(int(dur*1000), self._shockStop)


root=MainForm()
root.mainloop()