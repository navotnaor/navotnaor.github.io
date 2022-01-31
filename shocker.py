class Shocker(object):
    def __init__(self, level,address,mode):
        '''
        # works with 125F shock machine (parallel port)
        shocker=Shocker(192,address=0xD070,mode='in_lab')
        # supposedly works at the MNC.
        shocker=Shocker(192,address="/Dev1/ao0",mode='scanner')
        
        if not mode, will not attempt to connect to any shocking device.
        
        I don't know what the shock level values actually are, 
        just that 192 apparently works?
        
        for in_lab mode:
            On Windows 7 x64, need to use inpoutx64.  C:\Windows\System32\inpoutx64.dll
            Might need to install or add it manually
            https://stackoverflow.com/questions/26762015/psychopy-sending-triggers-on-64bit-os
            pyparallel doesn't work
        for scanner mode:
            Python package PyDAQmx is required
        
        
        if shocker.level is 0, the state will always be off
        
        '''
        if mode=='in_lab':
            from ctypes import windll
            self._windll=windll
        elif mode=='scanner':
            import PyDAQmx as pdmx
            # Shock box interface
            t= pdmx.Task()
            t.CreateAOVoltageChan(address,"",-10.0,10.0,pdmx.DAQmx_Val_Volts,None)
            t.StartTask()
            self._task=t
        elif not mode:
            pass
        else:
            raise ValueError('unrecognized mode "{}"'.format(mode))
        
        self._address=address
        self._mode=mode
        
        self._level = level
        self._refresh(0)
    
    @property
    def level(self):
        return self._level
    @level.setter
    def level(self,level):
        self._level=level
        if self._on:
            self._refresh(level)
    
    @property
    def on(self):
        return self._on
    @on.setter
    def on(self,on):
        self._refresh(self._level if on else 0)
    
    def _refresh(self,value):
        '''
        Fully specify the shock level to be active currently.
        does not change the default shock level used by other
        methods, but does change the on/off state as appropriate.
        '''
        self._on=bool(value)
        if self._mode=='in_lab':
            self._windll.inpoutx64.Out32(self._address, int(value))
        elif self._mode=='scanner':
            self._task.WriteAnalogScalarF64(1, 10.0, float(value), None)
    
    def toggle(self):
        # toggle shock state
        self.on=not self.on
    def start(self):
        # start shocking, using default shock level
        self.on=True
    def stop(self):
        # stop shocking
        self.on=False

        
        
if __name__=='__main__':
    import time
    
    '''
    shocker=Shocker(192,address=0xD070,mode='in_lab')
    shocker.level=78 # needed for in lab now?
    #shocker=Shocker(1,address="/Dev1/ao0",mode='scanner')
    #shocker.level=10
    for i in range(20):
        print('-')
        shocker.toggle()
        time.sleep(1)
    '''
    
    # couldn't get a full test of this at the scanner, doesn't have a simple indicator on the machine itself.
    import PyDAQmx as pdmx
    # Shock box interface
    t = pdmx.Task()
    t.CreateAOVoltageChan("/Dev1/ao0","",-10.0,10.0,pdmx.DAQmx_Val_Volts,None)
    t.StartTask()
    
    t.WriteAnalogScalarF64(1,10.0,float(3.0),None)