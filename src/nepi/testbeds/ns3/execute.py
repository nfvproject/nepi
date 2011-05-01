#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.core.attributes import Attribute
from nepi.util.constants import TIME_NOW
import os
import sys
import threading

class TestbedController(testbed_impl.TestbedController):
    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
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
        self._ns3 = self._load_ns3_module()
        super(TestbedController, self).do_setup()

    def start(self):
        super(TestbedController, self).start()
        self._condition = threading.Condition()
        self._simulator_thread = threading.Thread(target = self._simulator_run,
                args = [self._condition])
        self._simulator_thread.start()

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return
        element = self._elements[guid]
        ns3_value = self._to_ns3_value(guid, name, value) 
        element.SetAttribute(name, ns3_value)

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name):
            return value
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInfo()
        if not typeid or not typeid.LookupAttributeByName(name, info):
            raise AttributeError("Invalid attribute %s for element type %d" % \
                (name, guid))
        checker = info.checker
        ns3_value = checker.Create() 
        element = self._elements[guid]
        element.GetAttribute(name, ns3_value)
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

    def trace_filename(self, guid, trace_id):
        # TODO: Need to be defined inside a home!!!! with and experiment id_code
        filename = self._traces[guid][trace_id]
        return os.path.join(self.home_directory, filename)

    def follow_trace(self, guid, trace_id, filename):
        if guid not in self._traces:
            self._traces[guid] = dict()
        self._traces[guid][trace_id] = filename

    def shutdown(self):
        for element in self._elements.values():
            element = None

    def _simulator_run(self, condition):
        # Run simulation
        self.ns3.Simulator.Run()
        # Signal condition on simulation end to notify waiting threads
        condition.acquire()
        condition.notifyAll()
        condition.release()

    def _schedule_event(self, condition, func, *args):
        """Schedules event on running experiment"""
        def execute_event(condition, has_event_occurred, func, *args):
            # exec func
            func(*args)
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
        if not self.ns3.Simulator.IsFinished():
            self.ns3.Simulator.ScheduleWithContext(contextId, delay, execute_event,
                 condition, has_event_occurred, func, *args)
            while not has_event_occurred[0] and not self.ns3.Simulator.IsFinished():
                condition.wait()
                condition.release()
                if not has_event_occurred[0]:
                    raise RuntimeError('Event could not be scheduled : %s %s ' \
                    % (repr(func), repr(args)))

    def _to_ns3_value(self, guid, name, value):
        factory_id = self._create[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInfo()
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

    def _load_ns3_module(self):
        import ctypes
        import imp

        simu_impl_type = self._attributes.get_attribute_value(
                "SimulatorImplementationType")
        checksum = self._attributes.get_attribute_value("ChecksumEnabled")

        bindings = os.environ["NEPI_NS3BINDINGS"] \
                if "NEPI_NS3BINDINGS" in os.environ else None
        libfile = os.environ["NEPI_NS3LIBRARY"] \
                if "NEPI_NS3LIBRARY" in os.environ else None

        if libfile:
            ctypes.CDLL(libfile, ctypes.RTLD_GLOBAL)

        path = [ os.path.dirname(__file__) ] + sys.path
        if bindings:
            path = [ bindings ] + path

        module = imp.find_module ('ns3', path)
        mod = imp.load_module ('ns3', *module)
    
        if simu_impl_type:
            value = mod.StringValue(simu_impl_type)
            mod.GlobalValue.Bind ("SimulatorImplementationType", value)
        if checksum:
            value = mod.BooleanValue(checksum)
            mod.GlobalValue.Bind ("ChecksumEnabled", value)
        return mod

    def _get_construct_parameters(self, guid):
        params = self._get_parameters(guid)
        construct_params = dict()
        factory_id = self._create[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        for name, value in params.iteritems():
            info = self.ns3.TypeId.AttributeInfo()
            found = typeid.LookupAttributeByName(name, info)
            if found and \
                (info.flags & TypeId.ATTR_CONSTRUCT == TypeId.ATTR_CONSTRUCT):
                construct_params[name] = value
        return construct_params

