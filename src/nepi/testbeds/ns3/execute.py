#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.core.attributes import Attribute
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
        # configure addressess
        for guid, addresses in self._add_address.iteritems():
            element = self._elements[guid]
            for address in addresses:
                (family, address, netprefix, broadcast) = address
                if family == AF_INET:
                    pass
                    # TODO!!!
        # configure routes
        for guid, routes in self._add_route.iteritems():
            element = self._elements[guid]
            for route in routes:
                (destination, netprefix, nexthop) = route
                # TODO!!
        """
        context = self.server.modules.ns3
        ipv4 = self._object
        for interface in self._interface2addr:
            ifindex = ipv4.AddInterface(interface._object)
            for addr in self._interface2addr[interface]:
                inaddr = context.Ipv4InterfaceAddress(
                        context.Ipv4Address(
                            addr.get_attribute("Address").value),
                        context.Ipv4Mask(
                            addr.get_attribute("NetPrefix").value))
                ipv4.AddAddress(ifindex, inaddr)
                ipv4.SetMetric(ifindex, 1)
                ipv4.SetUp(ifindex)
                self._interface_addrs[addr] = inaddr
                self._interfaces[interface] = ifindex
        for entry in self.get_node().routing_table.get_entries(self._af):
            self._rt_add(entry)

        def _rt_add(self, entry):
        # Called both at install-time (by NS3Ipv4Stack.post_install) and at
        # run-time (by RoutingTable.add_entry).
        context = self.server.modules.ns3
        ifindex = self._interfaces[entry.interface]
        prefixlen = entry.prefixlen
        # print "rt_add %s %s %s %d"% (prefix, prefixlen, entry.nexthop, ifindex)        
        if entry.nexthop:
            self._static_routing.AddNetworkRouteTo(
                    context.Ipv4Address(entry.prefix.address),
                    context.Ipv4Mask(entry.mask.address),
                    context.Ipv4Address(entry.nexthop.address),
                    ifindex)
        else:
            self._static_routing.AddNetworkRouteTo(
                    context.Ipv4Address(entry.prefix.address),
                    context.Ipv4Mask(entry.mask.address),
                    ifindex)
        """

    def set(self, time, guid, name, value):
        super(TestbedInstance, self).set(time, guid, name, value)
        # TODO: take on account schedule time for the task
        factory_id = self._crerate[guid]
        element = self._elements[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInfo()
        if not typeid.LookupAttributeByName(name, info):
            raise RuntimeError("Attribute %s doesn't belong to element %s" \
                   % (name, factory_id))
        value = str(value)
        if isinstance(value, bool):
            value = value.lower()
        ns3_value = info.checker.Create()
        ns3_value.DeserializeFromString(value, checker)
        element.SetAttribute(name, ns3_value)

    def get(self, time, guid, name):
        # TODO: take on account schedule time for the task
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        info = TypeId.AttributeInfo()
        if not typeid.LookupAttributeByName(name, info):
            raise RuntimeError("Attribute %s doesn't belong to element %s" \
                   % (name, factory_id))
        checker = info.checker
        ns3_value = checker.Create() 
        element = self._elements[guid]
        element.GetAttribute(name, ns3_value)
        value = ns3_value.SerializeToString(checker)
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
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

    def trace(self, guid, trace_id):
        fd = open("%s" % self.trace_filename(guid, trace_id), "r")
        content = fd.read()
        fd.close()
        return content

    def shutdown(self):
        for element in self._elements.values():
            element.destroy()

    def trace_filename(self, guid, trace_id):
        # TODO: Need to be defined inside a home!!!! with and experiment id_code
        filename = self._trace_filenames[guid][trace_id]
        return os.path.join(self.home_directory, filename)

    def follow_trace(self, guid, trace_id, filename):
        if guid not in self._traces:
            self._traces[guid] = dict()
        self._traces[guid][trace_id] = filename

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

    def _get_construct_parameters(self, guid):
        params = self._get_parameters(guid)
        construct_params = dict()
        factory_id = self._create[guid]
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(factory_id)
        for name, value in params:
            info = self.ns3.TypeId.AttributeInfo()
            typeid.LookupAttributeByName(name, info)
            if info.flags & TypeId.ATTR_CONSTRUCT == TypeId.ATTR_CONSTRUCT:
                construct_params[name] = value
        return construct_params

