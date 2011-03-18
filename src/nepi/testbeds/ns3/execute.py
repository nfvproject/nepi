#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.util.constants import AF_INET, AF_INET6
import os

class TestbedInstance(testbed_impl.TestbedInstance):
    def __init__(self, testbed_version):
        super(TestbedInstance, self).__init__(TESTBED_ID, testbed_version)
        self._ns3 = None
        self._home_directory = None
        self._traces = dict()

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

    def do_configure(self):
        # TODO: add traces!
        # configure addressess
        for guid, addresses in self._add_address.iteritems():
            element = self._elements[guid]
            for address in addresses:
                (family, address, netprefix, broadcast) = address
                if family == AF_INET:
                    element.add_v4_address(address, netprefix)
        # configure routes
        for guid, routes in self._add_route.iteritems():
            element = self._elements[guid]
            for route in routes:
                (destination, netprefix, nexthop) = route
                element.add_route(prefix = destination, prefix_len = netprefix,
                        nexthop = nexthop)

    def set(self, time, guid, name, value):
        super(TestbedInstance, self).set(time, guid, name, value)
        factory_id = self._crerate[guid]
        element = self._elements[guid]
        self._set(element, factory_id, name, value)

    def get(self, time, guid, name):
        raise NotImplementedError
        # TODO: take on account schedule time for the task
        #element = self._elements[guid]
        #return getattr(element, name)

    def action(self, time, guid, action):
        raise NotImplementedError

    def trace(self, guid, trace_id):
        fd = open("%s" % self.trace_filename(guid, trace_id), "r")
        content = fd.read()
        fd.close()
        return content

    def shutdown(self):
        for trace in self._traces.values():
            trace.close()
        for element in self._elements.values():
            element.destroy()

    def trace_filename(self, guid, trace_id):
        # TODO: Need to be defined inside a home!!!! with and experiment id_code
        return os.path.join(self.home_directory, "%d_%s" % (guid, trace_id))

    def follow_trace(self, trace_id, trace):
        self._traces[trace_id] = trace

    def _set(self, element, factory_id, name, value):
        TypeId = self.ns3.TypeId()
        typeId = TypeId.LookupByName(factory_id)
        index = None
        attr_count = typeId.GetAttributeN()
        for idx in range(attr_count):
            if name == typeId.GetAttributeName(idx)
                index = idx
                break
        checker = typeid.GetAttributeChecker(index)
        ns3_value = attribute_checker.Create()
        value = str(value)
        if isinstance(value, bool):
            value = value.lower()
        ns3_value.DeserializeFromString(value, checker)
        element.Set(name, ns3_value)

    def _load_ns3_module(self):
        import ctypes
        import imp

        bindings = self._attributes.get_attribute_value("ns3Bindings")
        libfile = self._attributes.get_attribute_value("ns3Library")
        simu_impl_type = self._attributes.get_attribute_value(
                "SimulatorImplementationType")
        checksum = self._attributes.get_attribute_value("ChecksumEnabled")

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

