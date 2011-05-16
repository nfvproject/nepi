#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID
from nepi.core import testbed_impl
from nepi.core.attributes import Attribute
from nepi.util.constants import TIME_NOW
import os
import sys
import threading
import random
import socket
import weakref

class TunChannel(object):
    def __init__(self):
        # These get initialized when the channel is configured
        self.external_addr = None
        
        # These get initialized when the channel is configured
        # They're part of the TUN standard attribute set
        self.tun_port = None
        self.tun_addr = None
        
        # These get initialized when the channel is connected to its peer
        self.peer_proto = None
        self.peer_addr = None
        self.peer_port = None
        
        # These get initialized when the channel is connected to its iface
        self.tun_socket = None

        # same as peer proto, but for execute-time standard attribute lookups
        self.tun_proto = None 
        
        # some state
        self.prepared = False
        self.listen = False
        self._terminate = [] # terminate signaller
        self._connected = threading.Event()
        self._forwarder_thread = None
        
        # Generate an initial random cryptographic key to use for tunnelling
        # Upon connection, both endpoints will agree on a common one based on
        # this one.
        self.tun_key = ( ''.join(map(chr, [ 
                    r.getrandbits(8) 
                    for i in xrange(32) 
                    for r in (random.SystemRandom(),) ])
                ).encode("base64").strip() )        
        

    def __str__(self):
        return "%s<ip:%s/%s %s%s>" % (
            self.__class__.__name__,
            self.address, self.netprefix,
            " up" if self.up else " down",
            " snat" if self.snat else "",
        )

    def Prepare(self):
        if not self.udp and self.listen and not self._forwarder_thread:
            if self.listen or (self.peer_addr and self.peer_port and self.peer_proto):
                self._launch()
    
    def Setup(self):
        if not self._forwarder_thread:
            self._launch()
    
    def Cleanup(self):
        if self._forwarder_thread:
            self.Kill()

    def Wait(self):
        if self._forwarder_thread:
            self._connected.wait()

    def Kill(self):    
        if self._forwarder_thread:
            if not self._terminate:
                self._terminate.append(None)
            self._forwarder_thread.join()

    def _launch(self):
        # Launch forwarder thread with a weak reference
        # to self, so that we don't create any strong cycles
        # and automatic refcounting works as expected
        self._forwarder_thread = threading.Thread(
            self._forwarder,
            args = (weakref.ref(self),) )
        self._forwarder_thread.start()
    
    @staticmethod
    def _forwarder(weak_self):
        import tunchannel
        
        # grab strong reference
        self = weak_self()
        if not self:
            return
        
        peer_port = self.peer_port
        peer_addr = self.peer_addr
        peer_proto= self.peer_proto

        local_port = self.tun_port
        local_addr = self.tun_addr
        local_proto = self.tun_proto
        
        if local_proto != peer_proto:
            raise RuntimeError, "Peering protocol mismatch: %s != %s" % (local_proto, peer_proto)
        
        udp = local_proto == 'udp'
        listen = self.listen

        if (udp or not listen) and (not peer_port or not peer_addr):
            raise RuntimeError, "Misconfigured peer for: %s" % (self,)

        if (udp or listen) and (not local_port or not local_addr):
            raise RuntimeError, "Misconfigured TUN: %s" % (self,)
        
        TERMINATE = self._terminate
        cipher_key = self.tun_key
        tun = self.tun_socket
        
        if not tun:
            raise RuntimeError, "Unconnected TUN channel %s" % (self,)
        
        if udp:
            # listen on udp port
            if remaining_args and not remaining_args[0].startswith('-'):
                rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
                rsock.bind((local_addr,local_port))
                rsock.connect((peer_addr,peer_port))
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        elif listen:
            # accept tcp connections
            lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            lsock.bind((local_addr,local_port))
            lsock.listen(1)
            rsock,raddr = lsock.accept()
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        else:
            # connect to tcp server
            rsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            for i in xrange(30):
                try:
                    rsock.connect((peer_addr,peer_port))
                    break
                except socket.error:
                    # wait a while, retry
                    time.sleep(1)
            else:
                rsock.connect((peer_addr,peer_port))
            remote = os.fdopen(rsock.fileno(), 'r+b', 0)
        
        # notify that we're ready
        self._connected.set()
        
        # drop strong reference
        del self
        
        tunchannel.tun_fwd(tun, remote,
            with_pi = False, 
            ether_mode = True, 
            cipher_key = cipher_key, 
            udp = udp, 
            TERMINATE = TERMINATE,
            stderr = open("/dev/null","w") # silence logging
        )
        
        tun.close()
        remote.close()


class TestbedController(testbed_impl.TestbedController):
    LOCAL_FACTORIES = {
        'ns3::Nepi::TunChannel' : TunChannel,
    }

    def __init__(self, testbed_version):
        super(TestbedController, self).__init__(TESTBED_ID, testbed_version)
        self._ns3 = None
        self._home_directory = None
        self._traces = dict()
        self._simulator_thread = None
        self._condition = None
        
        # local factories
        self.TunChannel = TunChannel

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
        self._simulator_thread.start()

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name) or \
                factory.box_attributes.is_attribute_invisible(name):
            return
        element = self._elements[guid]
        if factory_id in self.LOCAL_FACTORIES:
            setattr(element, name, value)
        else:
            ns3_value = self._to_ns3_value(guid, name, value) 
            element.SetAttribute(name, ns3_value)

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        # TODO: take on account schedule time for the task
        factory_id = self._create[guid]
        factory = self._factories[factory_id]
        if factory.box_attributes.is_attribute_design_only(name) or \
                factory.box_attributes.is_attribute_invisible(name):
            return value
        if factory_id in self.LOCAL_FACTORIES:
            return getattr(element, name)
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

        try:
            module = imp.find_module ('ns3', path)
            mod = imp.load_module ('ns3', *module)
        except ImportError:
            # In some environments, ns3 per-se does not exist,
            # only the low-level _ns3
            module = imp.find_module ('_ns3', path)
            mod = imp.load_module ('_ns3', *module)
            sys.modules["ns3"] = mod # install it as ns3 too
            
            # When using _ns3, we have to make sure we destroy
            # the simulator when the process finishes
            import atexit
            atexit.register(mod.Simulator.Destroy)
    
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



