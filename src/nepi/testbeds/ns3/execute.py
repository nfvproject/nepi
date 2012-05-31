# -*- coding: utf-8 -*-

from util import  _get_ipv4_protocol_guid, _get_node_guid, _get_dev_number
from nepi.core import testbed_impl
from nepi.core.attributes import Attribute
from constants import TESTBED_ID, TESTBED_VERSION
from nepi.util.constants import TIME_NOW, TestbedStatus as TS
import os
import sys
import threading
import random
import socket
import weakref

def load_ns3_module():
    import sys
    if 'ns3' in sys.modules:
        return

    import ctypes
    import imp
    import re

    bindings = os.environ["NEPI_NS3BINDINGS"] \
		if "NEPI_NS3BINDINGS" in os.environ else None
    libdir = os.environ["NEPI_NS3LIBRARY"] \
		if "NEPI_NS3LIBRARY" in os.environ else None

    if libdir:
        files = os.listdir(libdir)
        regex = re.compile("(.*\.so)$")
        libs = [m.group(1) for filename in files for m in [regex.search(filename)] if m]

        libscp = list(libs)
        while len(libs) > 0:
            for lib in libscp:
                libfile = os.path.join(libdir, lib)
                try:
                    ctypes.CDLL(libfile, ctypes.RTLD_GLOBAL)
                    libs.remove(lib)
                except:
                    pass
            # if did not load any libraries in the last iteration
            if len(libscp) == len(libs):
                raise RuntimeError("Imposible to load shared libraries %s" % str(libs))
            libscp = list(libs)

    if bindings:
        sys.path.append(bindings)

    import ns3_bindings_import as mod
    sys.modules["ns3"] = mod

class TestbedController(testbed_impl.TestbedController):
    from nepi.util.tunchannel_impl import TunChannel
    
    LOCAL_FACTORIES = {
        'ns3::Nepi::TunChannel' : TunChannel,
    }
    
    LOCAL_TYPES = tuple(LOCAL_FACTORIES.values())

    def __init__(self):
        super(TestbedController, self).__init__(TESTBED_ID, TESTBED_VERSION)
        self._ns3 = None
        self._home_directory = None
        self._traces = dict()
        self._simulator_thread = None
        self._condition = None

    @property
    def home_directory(self):
        return self._home_directory

    @property
    def ns3(self):
        return self._ns3

    def do_setup(self):
        self._home_directory = self._attributes.\
            get_attribute_value("homeDirectory")
        self._ns3 = self._configure_ns3_module()
        
        # create home...
        home = os.path.normpath(self.home_directory)
        if not os.path.exists(home):
            os.makedirs(home, 0755)
        
        super(TestbedController, self).do_setup()

    def start(self):
        super(TestbedController, self).start()
        self._condition = threading.Condition()
        self._simulator_thread = threading.Thread(target = self._simulator_run,
                args = [self._condition])
        self._simulator_thread.setDaemon(True)
        self._simulator_thread.start()

    def stop(self, time = TIME_NOW):
        super(TestbedController, self).stop(time)
        self._stop_simulation(time)

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        element = self._elements[guid]
        if factory_id in self.LOCAL_FACTORIES:
            setattr(element, name, value)
        elif not factory.box_attributes.is_attribute_metadata(name):
            if name == "Up":
                ipv4_guid =  _get_ipv4_protocol_guid(self, guid)
                if not ipv4_guid in self._elements:
                    return
                ipv4 = self._elements[ipv4_guid]
                if value == False:
                    nint = ipv4.GetNInterfaces()
                    for i in xrange(0, nint):
                        ipv4.SetDown(i)
                else:
                    nint = ipv4.GetNInterfaces()
                    for i in xrange(0, nint):
                        ipv4.SetUp(i)
            else:
                ns3_value = self._to_ns3_value(guid, name, value)
                self._set_attribute(name, ns3_value, element)

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        element = self._elements[guid]
        if factory_id in self.LOCAL_FACTORIES:
            if hasattr(element, name):
                return getattr(element, name)
            else:
                return value
        else: 
            if name == "Up":
                ipv4_guid =  _get_ipv4_protocol_guid(self, guid)
                if not ipv4_guid in self._elements:
                    return True
                ipv4 = self._elements[ipv4_guid]
                nint = ipv4.GetNInterfaces()
                value = True
                for i in xrange(0, nint):
                    value = ipv4.IsUp(i)
                    if not value: break
                return value

        if factory.box_attributes.is_attribute_metadata(name):
            return value

        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInformation()
        if not typeid or not typeid.LookupAttributeByName(name, info):
            raise AttributeError("Invalid attribute %s for element type %d" % \
                (name, guid))
        checker = info.checker
        ns3_value = checker.Create() 
        self._get_attribute(name, ns3_value, element)
        value = ns3_value.SerializeToString(checker)
        attr_type = factory.box_attributes.get_attribute_type(name)

        if attr_type == Attribute.INTEGER:
            return int(value)
        if attr_type == Attribute.DOUBLE:
            return float(value)
        if attr_type == Attribute.BOOL:
            return value == "true"
        return value

    def action(self, time, guid, action):
        raise NotImplementedError

    def trace_filepath(self, guid, trace_id):
        filename = self._traces[guid][trace_id]
        return os.path.join(self.home_directory, filename)

    def trace_filename(self, guid, trace_id):
        return self._traces[guid][trace_id]

    def follow_trace(self, guid, trace_id, filename):
        if not guid in self._traces:
            self._traces[guid] = dict()
        self._traces[guid][trace_id] = filename

    def shutdown(self):
        for element in self._elements.itervalues():
            if isinstance(element, self.LOCAL_TYPES):
                # graceful shutdown of locally-implemented objects
                element.cleanup()
        if self.ns3:
            if not self.ns3.Simulator.IsFinished():
                self.stop()
            
            # TODO!!!! SHOULD WAIT UNTIL THE THREAD FINISHES
            if self._simulator_thread:
                self._simulator_thread.join()
            
            self.ns3.Simulator.Destroy()
        
        self._elements.clear()
        
        self._ns3 = None
        sys.stdout.flush()
        sys.stderr.flush()

    def _simulator_run(self, condition):
        # Run simulation
        self.ns3.Simulator.Run()
        # Signal condition on simulation end to notify waiting threads
        condition.acquire()
        condition.notifyAll()
        condition.release()

    def _schedule_event(self, condition, func, *args):
        """Schedules event on running experiment"""
        def execute_event(contextId, condition, has_event_occurred, func, *args):
            # exec func
            try:
                func(*args)
            finally:
                # flag event occured
                has_event_occurred[0] = True
                # notify condition indicating attribute was set
                condition.acquire()
                condition.notifyAll()
                condition.release()

        # contextId is defined as general context
        contextId = long(0xffffffff)
        # delay 0 means that the event is expected to execute inmediately
        delay = self.ns3.Seconds(0)
        # flag to indicate that the event occured
        # because bool is an inmutable object in python, in order to create a
        # bool flag, a list is used as wrapper
        has_event_occurred = [False]
        condition.acquire()
        try:
            if not self.ns3.Simulator.IsFinished():
                self.ns3.Simulator.ScheduleWithContext(contextId, delay, execute_event,
                     condition, has_event_occurred, func, *args)
                while not has_event_occurred[0] and not self.ns3.Simulator.IsFinished():
                    condition.wait()
        finally:
            condition.release()

    def _set_attribute(self, name, ns3_value, element):
        if self.status() == TS.STATUS_STARTED:
            # schedule the event in the Simulator
            self._schedule_event(self._condition, self._set_ns3_attribute, 
                    name, ns3_value, element)
        else:
            self._set_ns3_attribute(name, ns3_value, element)

    def _get_attribute(self, name, ns3_value, element):
        if self.status() == TS.STATUS_STARTED:
            # schedule the event in the Simulator
            self._schedule_event(self._condition, self._get_ns3_attribute, 
                    name, ns3_value, element)
        else:
            self._get_ns3_attribute(name, ns3_value, element)

    def _set_ns3_attribute(self, name, ns3_value, element):
        element.SetAttribute(name, ns3_value)

    def _get_ns3_attribute(self, name, ns3_value, element):
        element.GetAttribute(name, ns3_value)

    def _stop_simulation(self, time):
        if self.status() == TS.STATUS_STARTED:
            # schedule the event in the Simulator
            self._schedule_event(self._condition, self._stop_ns3_simulation, 
                    time)
        else:
            self._stop_ns3_simulation(time)

    def _stop_ns3_simulation(self, time = TIME_NOW):
        if not self.ns3:
            return
        if time == TIME_NOW:
            self.ns3.Simulator.Stop()
        else:
            self.ns3.Simulator.Stop(self.ns3.Time(time))

    def _to_ns3_value(self, guid, name, value):
        factory_id = self._create[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInformation()
        if not typeid.LookupAttributeByName(name, info):
            raise RuntimeError("Attribute %s doesn't belong to element %s" \
                   % (name, factory_id))
        str_value = str(value)
        if isinstance(value, bool):
            str_value = str_value.lower()
        checker = info.checker
        ns3_value = checker.Create()
        ns3_value.DeserializeFromString(str_value, checker)
        return ns3_value

    def _configure_ns3_module(self):
        simu_impl_type = self._attributes.get_attribute_value(
                "SimulatorImplementationType")
        sched_impl_type = self._attributes.get_attribute_value(
                "SchedulerType")
        checksum = self._attributes.get_attribute_value("ChecksumEnabled")
        stop_time = self._attributes.get_attribute_value("StopTime")

        load_ns3_module()

        import ns3 as mod
 
        if simu_impl_type:
            value = mod.StringValue(simu_impl_type)
            mod.GlobalValue.Bind ("SimulatorImplementationType", value)
        if sched_impl_type:
            value = mod.StringValue(sched_impl_type)
            mod.GlobalValue.Bind ("SchedulerType", value)
        if checksum:
            value = mod.BooleanValue(checksum)
            mod.GlobalValue.Bind ("ChecksumEnabled", value)
        if stop_time:
            value = mod.Time(stop_time)
            mod.Simulator.Stop (value)
        return mod

    def _get_construct_parameters(self, guid):
        params = self._get_parameters(guid)
        construct_params = dict()
        factory_id = self._create[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        for name, value in params.iteritems():
            info = self.ns3.TypeId.AttributeInformation()
            found = typeid.LookupAttributeByName(name, info)
            if found and \
                (info.flags & TypeId.ATTR_CONSTRUCT == TypeId.ATTR_CONSTRUCT):
                construct_params[name] = value
        return construct_params



