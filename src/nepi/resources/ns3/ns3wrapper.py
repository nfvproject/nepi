import logging
import os
import sys
import threading
import uuid

class NS3Wrapper(object):
    def __init__(self, homedir = None):
        super(NS3Wrapper, self).__init__()
        self._ns3 = None
        self._uuid = self.make_uuid()
        self._homedir = homedir or os.path.join("/tmp", self._uuid)
        self._simulation_thread = None
        self._condition = None

        self._started = False
        self._stopped = False

        # holds reference to all ns-3 objects in the simulation
        self._resources = dict()

        # create home dir (where all simulation related files will end up)
        home = os.path.normpath(self.homedir)
        if not os.path.exists(home):
            os.makedirs(home, 0755)

        # Logging
        loglevel = os.environ.get("NS3LOGLEVEL", "debug")
        self._logger = logging.getLogger("ns3wrapper.%s" % self.uuid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))
        hdlr = logging.FileHandler(os.path.join(self.homedir, "ns3wrapper.log"))
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self._logger.addHandler(hdlr) 

        # Load ns-3 shared libraries and import modules
        self._load_ns3_module()
        
    @property
    def ns3(self):
        return self._ns3

    @property
    def homedir(self):
        return self._homedir

    @property
    def uuid(self):
        return self._uuid

    @property
    def logger(self):
        return self._logger

    def make_uuid(self):
        return "uuid%s" % uuid.uuid4()

    def singleton(self, clazzname):
        uuid = "uuid%s"%clazzname

        if not uuid in self._resources:
            if not hasattr(self.ns3, clazzname):
                msg = "Type %s not supported" % (typeid) 
                self.logger.error(msg)

            clazz = getattr(self.ns3, clazzname)
            typeid = "ns3::%s" % clazzname
            self._resources[uuid] = (clazz, typeid)

        return uuid

    def get_trace(self, trace, offset = None, nbytes = None ):
        pass

    def is_running(self):
        return self._started and not self._stopped

    def get_resource(self, uuid):
        (resource, typeid) =  self._resources.get(uuid)
        return resource
    
    def get_typeid(self, uuid):
        (resource, typeid) =  self._resources.get(uuid)
        return typeid

    def create(self, clazzname, *args):
        if not hasattr(self.ns3, clazzname):
            msg = "Type %s not supported" % (clazzname) 
            self.logger.error(msg)

        clazz = getattr(self.ns3, clazzname)
        #typeid = clazz.GetInstanceTypeId().GetName()
        typeid = "ns3::%s" % clazzname

        realargs = [self.get_resource(arg) if \
                str(arg).startswith("uuid") else arg for arg in args]
      
        resource = clazz(*realargs)
        
        uuid = self.make_uuid()
        self._resources[uuid] = (resource, typeid)
        return uuid

    def set(self, uuid, name, value):
        resource = self.get_resource(uuid)

        if hasattr(resource, name):
            setattr(resource, name, value)
        else:
            self._set_ns3_attr(uuid, name, value)

    def get(self, name, uuid = None):
        resource = self.get_resource(uuid)

        value = None
        if hasattr(resource, name):
            value = getattr(resource, name)
        else:
            value = self._get_ns3_attr(uuid, name)

        return value

    def invoke(self, uuid, operation, *args):
        resource = self.get_resource(uuid)
        typeid = self.get_typeid(uuid)
        method = getattr(resource, operation)

        realargs = [self.get_resource(arg) if \
                str(arg).startswith("uuid") else arg for arg in args]

        result = method(*realargs)

        if not result:
            return None
        
        uuid = self.make_uuid()
        self._resources[uuid] = (result, typeid)

        return uuid

    def start(self):
        self._condition = threading.Condition()
        self._simulator_thread = threading.Thread(
                target = self._simulator_run,
                args = [self._condition])
        self._simulator_thread.setDaemon(True)
        self._simulator_thread.start()
        self._started = True

    def stop(self, time = None):
        if not self.ns3:
            return

        if time is None:
            self.ns3.Simulator.Stop()
        else:
            self.ns3.Simulator.Stop(self.ns3.Time(time))
        self._stopped = True

    def shutdown(self):
        if self.ns3:
            if not self.ns3.Simulator.IsFinished():
                self.stop()
            
            # TODO!!!! SHOULD WAIT UNTIL THE THREAD FINISHES
            if self._simulator_thread:
                self._simulator_thread.join()
            
            self.ns3.Simulator.Destroy()
        
        self._resources.clear()
        
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
        """ Schedules event on running simulation, and wait until
            event is executed"""

        def execute_event(contextId, condition, has_event_occurred, func, *args):
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

    def _set_ns3_attr(self, uuid, name, value):
        resource = self.get_resource(uuid)
        ns3_value = self._to_ns3_value(uuid, name, value)

        def set_attr(resource, name, ns3_value):
            resource.SetAttribute(name, ns3_value)

        if self._is_running:
            # schedule the event in the Simulator
            self._schedule_event(self._condition, set_attr, resource,
                    name, ns3_value)
        else:
            set_attr(resource, name, ns3_value)

    def _get_ns3_attr(self, uuid, name):
        resource = self.get_resource(uuid)
        ns3_value = self._create_ns3_value(uuid, name)

        def get_attr(resource, name, ns3_value):
            resource.GetAttribute(name, ns3_value)

        if self._is_running:
            # schedule the event in the Simulator
            self._schedule_event(self._condition, get_attr, resource,
                    name, ns3_value)
        else:
            get_attr(resource, name, ns3_value)

        return self._from_ns3_value(uuid, name, ns3_value)

    def _create_ns3_value(self, uuid, name):
        typeid = get_typeid(uuid)
        TypeId = self.ns3.TypeId()
        tid = TypeId.LookupByName(typeid)
        info = TypeId.AttributeInformation()
        if not tid.LookupAttributeByName(name, info):
            msg = "TypeId %s has no attribute %s" % (typeid, name) 
            self.logger.error(msg)

        checker = info.checker
        ns3_value = checker.Create() 
        return ns3_value

    def _from_ns3_value(self, uuid, name, ns3_value):
        typeid = get_typeid(uuid)
        TypeId = self.ns3.TypeId()
        tid = TypeId.LookupByName(typeid)
        info = TypeId.AttributeInformation()
        if not tid.LookupAttributeByName(name, info):
            msg = "TypeId %s has no attribute %s" % (typeid, name) 
            self.logger.error(msg)

        checker = info.checker
        value = ns3_value.SerializeToString(checker)

        type_name = checker.GetValueTypeName()
        if type_name in ["ns3::UintegerValue", "ns3::IntegerValue"]:
            return int(value)
        if type_name == "ns3::DoubleValue":
            return float(value)
        if type_name == "ns3::BooleanValue":
            return value == "true"

        return value

    def _to_ns3_value(self, uuid, name, value):
        typeid = get_typeid(uuid)
        TypeId = self.ns3.TypeId()
        typeid = TypeId.LookupByName(typeid)
        info = TypeId.AttributeInformation()
        if not tid.LookupAttributeByName(name, info):
            msg = "TypeId %s has no attribute %s" % (typeid, name) 
            self.logger.error(msg)

        str_value = str(value)
        if isinstance(value, bool):
            str_value = str_value.lower()

        checker = info.checker
        ns3_value = checker.Create()
        ns3_value.DeserializeFromString(str_value, checker)
        return ns3_value

    def _load_ns3_module(self):
        if self.ns3:
            return 

        import ctypes
        import imp
        import re
        import pkgutil

        bindings = os.environ.get("NS3BINDINGS")
        libdir = os.environ.get("NS3LIBRARIES")

        # Load the ns-3 modules shared libraries
        if libdir:
            files = os.listdir(libdir)
            regex = re.compile("(.*\.so)$")
            libs = [m.group(1) for filename in files for m in [regex.search(filename)] if m]

            libscp = list(libs)
            while len(libs) > 0:
                for lib in libs:
                    libfile = os.path.join(libdir, lib)
                    try:
                        ctypes.CDLL(libfile, ctypes.RTLD_GLOBAL)
                        libs.remove(lib)
                    except:
                        pass

                # if did not load any libraries in the last iteration break
                # to prevent infinit loop
                if len(libscp) == len(libs):
                    raise RuntimeError("Imposible to load shared libraries %s" % str(libs))
                libscp = list(libs)

        # import the python bindings for the ns-3 modules
        if bindings:
            sys.path.append(bindings)

        # create a module to add all ns3 classes
        ns3mod = imp.new_module("ns3")
        sys.modules["ns3"] = ns3mod

        # retrieve all ns3 classes and add them to the ns3 module
        import ns
        for importer, modname, ispkg in pkgutil.iter_modules(ns.__path__):
            fullmodname = "ns.%s" % modname
            module = __import__(fullmodname, globals(), locals(), ['*'])

            # netanim.Config singleton overrides ns3::Config
            if modname in ['netanim']:
                continue

            for sattr in dir(module):
                if not sattr.startswith("_"):
                    attr = getattr(module, sattr)
                    setattr(ns3mod, sattr, attr)

        self._ns3 = ns3mod

