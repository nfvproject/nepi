#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.util.constants import TIME_NOW
import os
import fcntl
import threading

class TestbedController(testbed_impl.TestbedController):
    from nepi.util.tunchannel_impl import TunChannel
    
    class HostLock(object):
        # This class is used as a lock to prevent concurrency issues with more
        # than one instance of netns running in the same machine. Both in 
        # different processes or different threads.
        taken = False
        processcond = threading.Condition()
        
        def __init__(self, lockfile):
            processcond = self.__class__.processcond
            
            processcond.acquire()
            try:
                # It's not reentrant
                while self.__class__.taken:
                    processcond.wait()
                self.__class__.taken = True
            finally:
                processcond.release()
            
            self.lockfile = lockfile
            fcntl.flock(self.lockfile, fcntl.LOCK_EX)
        
        def __del__(self):
            processcond = self.__class__.processcond
            
            processcond.acquire()
            try:
                assert self.__class__.taken, "HostLock unlocked without being locked!"

                fcntl.flock(self.lockfile, fcntl.LOCK_UN)
                
                # It's not reentrant
                self.__class__.taken = False
                processcond.notify()
            finally:
                processcond.release()
    
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
        self._netns = None
        self._home_directory = None
        self._traces = dict()
        self._netns_lock = open("/tmp/nepi-netns-lock","a")
    
    def _lock(self):
        return self.HostLock(self._netns_lock)

    @property
    def home_directory(self):
        return self._home_directory

    @property
    def netns(self):
        return self._netns

    def do_setup(self):
        lock = self._lock()
        
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")
        # create home...
        home = os.path.normpath(self.home_directory)
        if not os.path.exists(home):
            os.makedirs(home, 0755)

        self._netns = self._load_netns_module()
        super(TestbedController, self).do_setup()
    
    def do_create(self):
        lock = self._lock()
        super(TestbedController, self).do_create()    

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task 
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return
        element = self._elements.get(guid)
        if element:
            setattr(element, name, value)

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return value
        element = self._elements.get(guid)
        try:
            return getattr(element, name)
        except KeyError, AttributeError:
            return value

    def action(self, time, guid, action):
        raise NotImplementedError

    def shutdown(self):
        lock = self._lock()
        
        for guid, traces in self._traces.iteritems():
            for trace_id, (trace, filename) in traces.iteritems():
                if hasattr(trace, "close"):
                    trace.close()
        for guid, element in self._elements.iteritems():
            if isinstance(element, self.TunChannel):
                element.Cleanup()
            else:
                factory_id = self._create[guid]
                if factory_id == "Node":
                    element.destroy()
        self._elements.clear()

    def trace_filepath(self, guid, trace_id, filename = None):
        if not filename:
            (trace, filename) = self._traces[guid][trace_id]
        return os.path.join(self.home_directory, filename)

    def follow_trace(self, guid, trace_id, trace, filename):
        if not guid in self._traces:
            self._traces[guid] = dict()
        self._traces[guid][trace_id] = (trace, filename)

    def _load_netns_module(self):
        # TODO: Do something with the configuration!!!
        import sys
        __import__("netns")
        netns_mod = sys.modules["netns"]
        # enable debug
        enable_debug = self._attributes.get_attribute_value("enableDebug")
        if enable_debug:
            netns_mod.environ.set_log_level(netns_mod.environ.LOG_DEBUG)
        return netns_mod

