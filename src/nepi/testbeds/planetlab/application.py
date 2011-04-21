#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
import plcapi
import operator

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
    
    def __str__(self):
        return "%s<command:%s%s>" % (
            self.__class__.__name__,
            "sudo " if self.sudo else "",
            self.command,
        )
    
    def validate(self):
        pass

