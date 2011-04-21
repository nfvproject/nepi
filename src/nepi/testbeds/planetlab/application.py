#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator
import os

from nepi.util.constants import STATUS_NOT_STARTED, STATUS_RUNNING, \
        STATUS_FINISHED

class Application(object):
    def __init__(self, api=None):
        if not api:
            api = plcapi.PLCAPI()
        self._api = api
        
        # Attributes
        self.command = None
        self.sudo = False
        
        self.stdout = None
        self.stderr = None
        
        # Those are filled when an actual node is connected
        self.node = None
        
        # Those are filled when the app is started
        #   Having both pid and ppid makes it harder
        #   for pid rollover to induce tracking mistakes
        self._pid = None
        self._ppid = None
        self._stdout_path = None
        self._stderr_path = None
    
    def __str__(self):
        return "%s<command:%s%s>" % (
            self.__class__.__name__,
            "sudo " if self.sudo else "",
            self.command,
        )
    
    def validate(self):
        pass

    def start(self):
        pass
    
    def status(self):
        return STATUS_FINISHED
    
    def kill(self):
        status = self.status()
        if status == STATUS_RUNNING:
            # TODO: kill by pid & ppid
            pass
    
    def remote_trace_path(self, whichtrace):
        if whichtrace == 'stdout':
            tracefile = self._stdout_path
        elif whichtrace == 'stderr':
            tracefile = self._stderr_path
        else:
            tracefile = None
        
        return tracefile
    
    def sync_trace(self, local_dir, whichtrace):
        tracefile = self.remote_trace_path(whichtrace)
        if not tracefile:
            return None
        
        local_path = os.join(local_dir, tracefile)
        
        # TODO: sync files
        f = open(local_path, "w")
        f.write("BLURP!")
        f.close()
        
        return local_path
    

