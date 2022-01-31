#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modified extract from PsychoPy's clock.  


Created on Tue Apr 23 11:28:32 2013
Provides the high resolution timebase used by psychopy, and defines some time
related utility Classes.
Moved functionality from core.py so a common code
base could be used in core.py and logging.py; vs. duplicating the getTime and
Clock logic.
@author: Sol
@author: Jon
"""
import time
import sys


# set the default timing mechanism
getTime = None


# Select the timer to use as the psychopy high resolution time base. Selection
# is based on OS and Python version.
#
# Three requirements exist for the psychopy time base implementation:
#     A) The Python interpreter does not apply an offset to the times returned
#        based on when the timer module being used was loaded or when the
#        timer function first called was first called.
#     B) The timer implementation used must be monotonic and report elapsed
#        time between calls, 'not' system or CPU usage time.
#     C) The timer implementation must provide a resolution of 50 usec or
#        better.
#
# Given the above requirements, psychopy selects a timer implementation as
# follows:
#     1) On Windows, the Windows Query Performance Counter API is used using
#        ctypes access.
#     2) On other OS's, if the Python version being used is 2.6 or lower,
#        time.time is used. For Python 2.7 and above, the timeit.default_timer
#        function is used.

if sys.platform == 'win32':
    from ctypes import byref, c_int64, windll
    _fcounter = c_int64()
    _qpfreq = c_int64()
    windll.Kernel32.QueryPerformanceFrequency(byref(_qpfreq))
    _qpfreq = float(_qpfreq.value)
    _winQPC = windll.Kernel32.QueryPerformanceCounter

    def getTime():
        _winQPC(byref(_fcounter))
        return _fcounter.value / _qpfreq
else:
    import timeit
    getTime = timeit.default_timer


class MonotonicClock(object):
    """A convenient class to keep track of time in your experiments using a
    sub-millisecond timer.
    Unlike the :class:`~psychopy.core.Clock` this cannot be reset to
    arbitrary times. For this clock t=0 always represents the time that
    the clock was created.
    Don't confuse this `class` with `core.monotonicClock` which is an
    `instance` of it that got created when PsychoPy.core was imported.
    That clock instance is deliberately designed always to return the
    time since the start of the study.
    Version Notes: This class was added in PsychoPy 1.77.00
    """

    def __init__(self, start_time=None):
        super(MonotonicClock, self).__init__()
        if start_time is None:
            # this is sub-millisec timer in python
            self._timeAtLastReset = getTime()
        else:
            self._timeAtLastReset = start_time

    def getTime(self):
        """Returns the current time on this clock in secs (sub-ms precision)
        """
        return getTime() - self._timeAtLastReset

    def getLastResetTime(self):
        """
        Returns the current offset being applied to the high resolution
        timebase used by Clock.
        """
        return self._timeAtLastReset

monotonicClock = MonotonicClock()


class Clock(MonotonicClock):
    """A convenient class to keep track of time in your experiments.
    You can have as many independent clocks as you like (e.g. one
    to time responses, one to keep track of stimuli...)
    This clock is identical to the :class:`~psychopy.core.MonotonicClock`
    except that it can also be reset to 0 or another value at any point.
    """

    def __init__(self):
        super(Clock, self).__init__()

    def reset(self, newT=0.0):
        """Reset the time on the clock. With no args time will be
        set to zero. If a float is received this will be the new
        time on the clock
        """
        self._timeAtLastReset = getTime() + newT

    def add(self, t):
        """Add more time to the clock's 'start' time (t0).
        Note that, by adding time to t0, you make the current time
        appear less. Can have the effect that getTime() returns a negative
        number that will gradually count back up to zero.
        e.g.::
            timer = core.Clock()
            timer.add(5)
            while timer.getTime()<0:
                # do something
        """
        self._timeAtLastReset += t