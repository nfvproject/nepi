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
    
    def validate(self):
        pass

