#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import nepi.core.execute
from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import server, validation
from nepi.util.constants import TIME_NOW, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP, DeploymentConfiguration as DC
import getpass
import cPickle
import sys
import time
import tempfile
import shutil
import functools

# PROTOCOL REPLIES
OK = 0
ERROR = 1

# PROTOCOL INSTRUCTION MESSAGES
XML = 2 
TRACE   = 4
FINISHED    = 5
START   = 6
STOP    = 7
SHUTDOWN    = 8
CONFIGURE   = 9
CREATE      = 10
CREATE_SET  = 11
FACTORY_SET = 12
CONNECT     = 13
CROSS_CONNECT   = 14
ADD_TRACE   = 15
ADD_ADDRESS = 16
ADD_ROUTE   = 17
DO_SETUP    = 18
DO_CREATE   = 19
DO_CONNECT_INIT = 20
DO_CONFIGURE    = 21
DO_CROSS_CONNECT_INIT   = 22
GET = 23
SET = 24
ACTION  = 25
STATUS  = 26
GUIDS  = 27
GET_ROUTE = 28
GET_ADDRESS = 29
RECOVER = 30
DO_PRECONFIGURE     = 31
GET_ATTRIBUTE_LIST  = 32
DO_CONNECT_COMPL    = 33
DO_CROSS_CONNECT_COMPL  = 34
TESTBED_ID  = 35
TESTBED_VERSION  = 36
DO_PRESTART = 37
GET_FACTORY_ID = 38
GET_TESTBED_ID = 39
GET_TESTBED_VERSION = 40
TRACES_INFO = 41
EXEC_XML = 42

instruction_text = dict({
    OK:     "OK",
    ERROR:  "ERROR",
    XML:    "XML",
    EXEC_XML:    "EXEC_XML",
    TRACE:  "TRACE",
    FINISHED:   "FINISHED",
    START:  "START",
    STOP:   "STOP",
    RECOVER: "RECOVER",
    SHUTDOWN:   "SHUTDOWN",
    CONFIGURE:  "CONFIGURE",
    CREATE: "CREATE",
    CREATE_SET: "CREATE_SET",
    FACTORY_SET:    "FACTORY_SET",
    CONNECT:    "CONNECT",
    CROSS_CONNECT: "CROSS_CONNECT",
    ADD_TRACE:  "ADD_TRACE",
    ADD_ADDRESS:    "ADD_ADDRESS",
    ADD_ROUTE:  "ADD_ROUTE",
    DO_SETUP:   "DO_SETUP",
    DO_CREATE:  "DO_CREATE",
    DO_CONNECT_INIT: "DO_CONNECT_INIT",
    DO_CONNECT_COMPL: "DO_CONNECT_COMPL",
    DO_CONFIGURE:   "DO_CONFIGURE",
    DO_PRECONFIGURE:   "DO_PRECONFIGURE",
    DO_CROSS_CONNECT_INIT:  "DO_CROSS_CONNECT_INIT",
    DO_CROSS_CONNECT_COMPL: "DO_CROSS_CONNECT_COMPL",
    GET:    "GET",
    SET:    "SET",
    GET_ROUTE: "GET_ROUTE",
    GET_ADDRESS: "GET_ADDRESS",
    GET_ATTRIBUTE_LIST: "GET_ATTRIBUTE_LIST",
    GET_FACTORY_ID: "GET_FACTORY_ID",
    GET_TESTBED_ID: "GET_TESTBED_ID",
    GET_TESTBED_VERSION: "GET_TESTBED_VERSION",
    ACTION: "ACTION",
    STATUS: "STATUS",
    GUIDS:  "GUIDS",
    TESTBED_ID: "TESTBED_ID",
    TESTBED_VERSION: "TESTBED_VERSION",
    TRACES_INFO: "TRACES_INFO",
    })

def log_msg(server, params):
    try:
        instr = int(params[0])
        instr_txt = instruction_text[instr]
        server.log_debug("%s - msg: %s [%s]" % (server.__class__.__name__, 
            instr_txt, ", ".join(map(str, params[1:]))))
    except:
        # don't die for logging
        pass

def log_reply(server, reply):
    try:
        res = reply.split("|")
        code = int(res[0])
        code_txt = instruction_text[code]
        try:
            txt = base64.b64decode(res[1])
        except:
            txt = res[1]
        server.log_debug("%s - reply: %s %s" % (server.__class__.__name__, 
                code_txt, txt))
    except:
        # don't die for logging
        server.log_debug("%s - reply: %s" % (server.__class__.__name__, 
                reply))
        pass

def to_server_log_level(log_level):
    return (
        server.DEBUG_LEVEL
            if log_level == DC.DEBUG_LEVEL 
        else server.ERROR_LEVEL
    )

def get_access_config_params(access_config):
    root_dir = access_config.get_attribute_value(DC.ROOT_DIRECTORY)
    log_level = access_config.get_attribute_value(DC.LOG_LEVEL)
    log_level = to_server_log_level(log_level)
    user = host = port = agent = key = None
    communication = access_config.get_attribute_value(DC.DEPLOYMENT_COMMUNICATION)
    environment_setup = (
        access_config.get_attribute_value(DC.DEPLOYMENT_ENVIRONMENT_SETUP)
        if access_config.has_attribute(DC.DEPLOYMENT_ENVIRONMENT_SETUP)
        else None
    )
    if communication == DC.ACCESS_SSH:
        user = access_config.get_attribute_value(DC.DEPLOYMENT_USER)
        host = access_config.get_attribute_value(DC.DEPLOYMENT_HOST)
        port = access_config.get_attribute_value(DC.DEPLOYMENT_PORT)
        agent = access_config.get_attribute_value(DC.USE_AGENT)
        key = access_config.get_attribute_value(DC.DEPLOYMENT_KEY)
    return (root_dir, log_level, user, host, port, key, agent, environment_setup)

class AccessConfiguration(AttributesMap):
    def __init__(self, params = None):
        super(AccessConfiguration, self).__init__()
        
        from nepi.core.metadata import Metadata
        
        for _,attr_info in Metadata.DEPLOYMENT_ATTRIBUTES.iteritems():
            self.add_attribute(**attr_info)
        
        if params:
            for attr_name, attr_value in params.iteritems():
                parser = Attribute.type_parsers[self.get_attribute_type(attr_name)]
                attr_value = parser(attr_value)
                self.set_attribute_value(attr_name, attr_value)

class TempDir(object):
    def __init__(self):
        self.path = tempfile.mkdtemp()
    
    def __del__(self):
        shutil.rmtree(self.path)

class PermDir(object):
    def __init__(self, path):
        self.path = path

def create_experiment_controller(xml, access_config = None):
    mode = None if not access_config \
            else access_config.get_attribute_value(DC.DEPLOYMENT_MODE)
    launch = True if not access_config \
            else not access_config.get_attribute_value(DC.RECOVER)
    if not mode or mode == DC.MODE_SINGLE_PROCESS:
        if not launch:
            raise ValueError, "Unsupported instantiation mode: %s with lanch=False" % (mode,)
        
        from nepi.core.execute import ExperimentController
        
        if not access_config or not access_config.has_attribute(DC.ROOT_DIRECTORY):
            root_dir = TempDir()
        else:
            root_dir = PermDir(access_config.get_attribute_value(DC.ROOT_DIRECTORY))
        controller = ExperimentController(xml, root_dir.path)
        
        # inject reference to temporary dir, so that it gets cleaned
        # up at destruction time.
        controller._tempdir = root_dir
        
        return controller
    elif mode == DC.MODE_DAEMON:
        (root_dir, log_level, user, host, port, key, agent, environment_setup) = \
                get_access_config_params(access_config)
        return ExperimentControllerProxy(root_dir, log_level,
                experiment_xml = xml, host = host, port = port, user = user, ident_key = key,
                agent = agent, launch = launch,
                environment_setup = environment_setup)
    raise RuntimeError("Unsupported access configuration '%s'" % mode)

def create_testbed_controller(testbed_id, testbed_version, access_config):
    mode = None if not access_config \
            else access_config.get_attribute_value(DC.DEPLOYMENT_MODE)
    launch = True if not access_config \
            else not access_config.get_attribute_value(DC.RECOVER)
    if not mode or mode == DC.MODE_SINGLE_PROCESS:
        if not launch:
            raise ValueError, "Unsupported instantiation mode: %s with lanch=False" % (mode,)
        return  _build_testbed_controller(testbed_id, testbed_version)
    elif mode == DC.MODE_DAEMON:
        (root_dir, log_level, user, host, port, key, agent, environment_setup) = \
                get_access_config_params(access_config)
        return TestbedControllerProxy(root_dir, log_level, testbed_id = testbed_id, 
                testbed_version = testbed_version, host = host, port = port, ident_key = key,
                user = user, agent = agent, launch = launch,
                environment_setup = environment_setup)
    raise RuntimeError("Unsupported access configuration '%s'" % mode)

def _build_testbed_controller(testbed_id, testbed_version):
    mod_name = "nepi.testbeds.%s" % (testbed_id.lower())
    if not mod_name in sys.modules:
        __import__(mod_name)
    module = sys.modules[mod_name]
    tc = module.TestbedController()
    if tc.testbed_version != testbed_version:
        raise RuntimeError("Bad testbed version on testbed %s. Asked for %s, got %s" % \
                (testbed_id, testbed_version, tc.testbed_version))
    return tc

# Just a namespace class
class Marshalling:
    class Decoders:
        @staticmethod
        def pickled_data(sdata):
            return cPickle.loads(base64.b64decode(sdata))
        
        @staticmethod
        def base64_data(sdata):
            return base64.b64decode(sdata)
        
        @staticmethod
        def nullint(sdata):
            return None if sdata == "None" else int(sdata)
        
        @staticmethod
        def bool(sdata):
            return sdata == 'True'
        
    class Encoders:
        @staticmethod
        def pickled_data(data):
            return base64.b64encode(cPickle.dumps(data))
        
        @staticmethod
        def base64_data(data):
            return base64.b64encode(data)
        
        @staticmethod
        def nullint(data):
            return "None" if data is None else int(data)
        
        @staticmethod
        def bool(data):
            return str(bool(data))
           
    # import into Marshalling all the decoders
    # they act as types
    locals().update([
        (typname, typ)
        for typname, typ in vars(Decoders).iteritems()
        if not typname.startswith('_')
    ])

    _TYPE_ENCODERS = dict([
        # id(type) -> (<encoding_function>, <formatting_string>)
        (typname, (getattr(Encoders,typname),"%s"))
        for typname in vars(Decoders)
        if not typname.startswith('_')
           and hasattr(Encoders,typname)
    ])

    # Builtins
    _TYPE_ENCODERS["float"] = (float, "%r")
    _TYPE_ENCODERS["int"] = (int, "%d")
    _TYPE_ENCODERS["long"] = (int, "%d")
    _TYPE_ENCODERS["str"] = (str, "%s")
    _TYPE_ENCODERS["unicode"] = (str, "%s")
    
    # Generic encoder
    _TYPE_ENCODERS[None] = (str, "%s")
    
    @staticmethod
    def args(*types):
        """
        Decorator that converts the given function into one that takes
        a single "params" list, with each parameter marshalled according
        to the given factory callable (type constructors are accepted).
        
        The first argument (self) is left untouched.
        
        eg:
        
        @Marshalling.args(int,int,str,base64_data)
        def somefunc(self, someint, otherint, somestr, someb64):
           return someretval
        """
        def decor(f):
            @functools.wraps(f)
            def rv(self, params):
                return f(self, *[ ctor(val)
                                  for ctor,val in zip(types, params[1:]) ])
            
            rv._argtypes = types
            
            # Derive type encoders by looking up types in _TYPE_ENCODERS
            # make_proxy will use it to encode arguments in command strings
            argencoders = []
            TYPE_ENCODERS = Marshalling._TYPE_ENCODERS
            for typ in types:
                if typ.__name__ in TYPE_ENCODERS:
                    argencoders.append(TYPE_ENCODERS[typ.__name__])
                else:
                    # generic encoder
                    argencoders.append(TYPE_ENCODERS[None])
            
            rv._argencoders = tuple(argencoders)
            
            rv._retval = getattr(f, '_retval', None)
            return rv
        return decor

    @staticmethod
    def retval(typ=Decoders.base64_data):
        """
        Decorator that converts the given function into one that 
        returns a properly encoded return string, given that the undecorated
        function returns suitable input for the encoding function.
        
        The optional typ argument specifies a type.
        For the default of base64_data, return values should be strings.
        The return value of the encoding method should be a string always.
        
        eg:
        
        @Marshalling.args(int,int,str,base64_data)
        @Marshalling.retval(str)
        def somefunc(self, someint, otherint, somestr, someb64):
           return someint
        """
        encode, fmt = Marshalling._TYPE_ENCODERS.get(
            typ.__name__,
            Marshalling._TYPE_ENCODERS[None])
        fmt = "%d|"+fmt
        
        def decor(f):
            @functools.wraps(f)
            def rv(self, *p, **kw):
                data = f(self, *p, **kw)
                return fmt % (
                    OK,
                    encode(data)
                )
            rv._retval = typ
            rv._argtypes = getattr(f, '_argtypes', None)
            rv._argencoders = getattr(f, '_argencoders', None)
            return rv
        return decor
    
    @staticmethod
    def retvoid(f):
        """
        Decorator that converts the given function into one that 
        always return an encoded empty string.
        
        Useful for null-returning functions.
        """
        OKRV = "%d|" % (OK,)
        
        @functools.wraps(f)
        def rv(self, *p, **kw):
            f(self, *p, **kw)
            return OKRV
        
        rv._retval = None
        rv._argtypes = getattr(f, '_argtypes', None)
        rv._argencoders = getattr(f, '_argencoders', None)
        return rv
    
    @staticmethod
    def handles(whichcommand):
        """
        Associates the method with a given command code for servers.
        It should always be the topmost decorator.
        """
        def decor(f):
            f._handles_command = whichcommand
            return f
        return decor

class BaseServer(server.Server):
    def reply_action(self, msg):
        if not msg:
            result = base64.b64encode("Invalid command line")
            reply = "%d|%s" % (ERROR, result)
        else:
            params = msg.split("|")
            instruction = int(params[0])
            log_msg(self, params)
            try:
                for mname,meth in vars(self.__class__).iteritems():
                    if not mname.startswith('_'):
                        cmd = getattr(meth, '_handles_command', None)
                        if cmd == instruction:
                            meth = getattr(self, mname)
                            reply = meth(params)
                            break
                else:
                    error = "Invalid instruction %s" % instruction
                    self.log_error(error)
                    result = base64.b64encode(error)
                    reply = "%d|%s" % (ERROR, result)
            except:
                error = self.log_error()
                result = base64.b64encode(error)
                reply = "%d|%s" % (ERROR, result)
        log_reply(self, reply)
        return reply

class TestbedControllerServer(BaseServer):
    def __init__(self, root_dir, log_level, testbed_id, testbed_version):
        super(TestbedControllerServer, self).__init__(root_dir, log_level)
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._testbed = None

    def post_daemonize(self):
        self._testbed = _build_testbed_controller(self._testbed_id, 
                self._testbed_version)

    @Marshalling.handles(GUIDS)
    @Marshalling.args()
    @Marshalling.retval( Marshalling.pickled_data )
    def guids(self):
        return self._testbed.guids

    @Marshalling.handles(TESTBED_ID)
    @Marshalling.args()
    @Marshalling.retval()
    def testbed_id(self):
        return str(self._testbed.testbed_id)

    @Marshalling.handles(TESTBED_VERSION)
    @Marshalling.args()
    @Marshalling.retval()
    def testbed_version(self):
        return str(self._testbed.testbed_version)

    @Marshalling.handles(CREATE)
    @Marshalling.args(int, str)
    @Marshalling.retvoid
    def defer_create(self, guid, factory_id):
        self._testbed.defer_create(guid, factory_id)

    @Marshalling.handles(TRACE)
    @Marshalling.args(int, str, Marshalling.base64_data)
    @Marshalling.retval()
    def trace(self, guid, trace_id, attribute):
        return self._testbed.trace(guid, trace_id, attribute)

    @Marshalling.handles(TRACES_INFO)
    @Marshalling.args()
    @Marshalling.retval( Marshalling.pickled_data )
    def traces_info(self):
        return self._testbed.traces_info()

    @Marshalling.handles(START)
    @Marshalling.args()
    @Marshalling.retvoid
    def start(self):
        self._testbed.start()

    @Marshalling.handles(STOP)
    @Marshalling.args()
    @Marshalling.retvoid
    def stop(self):
        self._testbed.stop()

    @Marshalling.handles(SHUTDOWN)
    @Marshalling.args()
    @Marshalling.retvoid
    def shutdown(self):
        self._testbed.shutdown()

    @Marshalling.handles(CONFIGURE)
    @Marshalling.args(Marshalling.base64_data, Marshalling.pickled_data)
    @Marshalling.retvoid
    def defer_configure(self, name, value):
        self._testbed.defer_configure(name, value)

    @Marshalling.handles(CREATE_SET)
    @Marshalling.args(int, Marshalling.base64_data, Marshalling.pickled_data)
    @Marshalling.retvoid
    def defer_create_set(self, guid, name, value):
        self._testbed.defer_create_set(guid, name, value)

    @Marshalling.handles(FACTORY_SET)
    @Marshalling.args(Marshalling.base64_data, Marshalling.pickled_data)
    @Marshalling.retvoid
    def defer_factory_set(self, name, value):
        self._testbed.defer_factory_set(name, value)

    @Marshalling.handles(CONNECT)
    @Marshalling.args(int, str, int, str)
    @Marshalling.retvoid
    def defer_connect(self, guid1, connector_type_name1, guid2, connector_type_name2):
        self._testbed.defer_connect(guid1, connector_type_name1, guid2, 
            connector_type_name2)

    @Marshalling.handles(CROSS_CONNECT)
    @Marshalling.args(int, str, int, int, str, str, str)
    @Marshalling.retvoid
    def defer_cross_connect(self, 
            guid, connector_type_name,
            cross_guid, cross_testbed_guid,
            cross_testbed_id, cross_factory_id,
            cross_connector_type_name):
        self._testbed.defer_cross_connect(guid, connector_type_name, cross_guid, 
            cross_testbed_guid, cross_testbed_id, cross_factory_id, 
            cross_connector_type_name)

    @Marshalling.handles(ADD_TRACE)
    @Marshalling.args(int, str)
    @Marshalling.retvoid
    def defer_add_trace(self, guid, trace_id):
        self._testbed.defer_add_trace(guid, trace_id)

    @Marshalling.handles(ADD_ADDRESS)
    @Marshalling.args(int, str, int, Marshalling.pickled_data)
    @Marshalling.retvoid
    def defer_add_address(self, guid, address, netprefix, broadcast):
        self._testbed.defer_add_address(guid, address, netprefix,
                broadcast)

    @Marshalling.handles(ADD_ROUTE)
    @Marshalling.args(int, str, int, str, int)
    @Marshalling.retvoid
    def defer_add_route(self, guid, destination, netprefix, nexthop, metric):
        self._testbed.defer_add_route(guid, destination, netprefix, nexthop, metric)

    @Marshalling.handles(DO_SETUP)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_setup(self):
        self._testbed.do_setup()

    @Marshalling.handles(DO_CREATE)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_create(self):
        self._testbed.do_create()

    @Marshalling.handles(DO_CONNECT_INIT)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_connect_init(self):
        self._testbed.do_connect_init()

    @Marshalling.handles(DO_CONNECT_COMPL)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_connect_compl(self):
        self._testbed.do_connect_compl()

    @Marshalling.handles(DO_CONFIGURE)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_configure(self):
        self._testbed.do_configure()

    @Marshalling.handles(DO_PRECONFIGURE)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_preconfigure(self):
        self._testbed.do_preconfigure()

    @Marshalling.handles(DO_PRESTART)
    @Marshalling.args()
    @Marshalling.retvoid
    def do_prestart(self):
        self._testbed.do_prestart()

    @Marshalling.handles(DO_CROSS_CONNECT_INIT)
    @Marshalling.args( Marshalling.Decoders.pickled_data )
    @Marshalling.retvoid
    def do_cross_connect_init(self, cross_data):
        self._testbed.do_cross_connect_init(cross_data)

    @Marshalling.handles(DO_CROSS_CONNECT_COMPL)
    @Marshalling.args( Marshalling.Decoders.pickled_data )
    @Marshalling.retvoid
    def do_cross_connect_compl(self, cross_data):
        self._testbed.do_cross_connect_compl(cross_data)

    @Marshalling.handles(GET)
    @Marshalling.args(int, Marshalling.base64_data, str)
    @Marshalling.retval( Marshalling.pickled_data )
    def get(self, guid, name, time):
        return self._testbed.get(guid, name, time)

    @Marshalling.handles(SET)
    @Marshalling.args(int, Marshalling.base64_data, Marshalling.pickled_data, str)
    @Marshalling.retvoid
    def set(self, guid, name, value, time):
        self._testbed.set(guid, name, value, time)

    @Marshalling.handles(GET_ADDRESS)
    @Marshalling.args(int, int, Marshalling.base64_data)
    @Marshalling.retval()
    def get_address(self, guid, index, attribute):
        return str(self._testbed.get_address(guid, index, attribute))

    @Marshalling.handles(GET_ROUTE)
    @Marshalling.args(int, int, Marshalling.base64_data)
    @Marshalling.retval()
    def get_route(self, guid, index, attribute):
        return str(self._testbed.get_route(guid, index, attribute))

    @Marshalling.handles(ACTION)
    @Marshalling.args(str, int, Marshalling.base64_data)
    @Marshalling.retvoid
    def action(self, time, guid, command):
        self._testbed.action(time, guid, command)

    @Marshalling.handles(STATUS)
    @Marshalling.args(Marshalling.nullint)
    @Marshalling.retval(int)
    def status(self, guid):
        return self._testbed.status(guid)

    @Marshalling.handles(GET_ATTRIBUTE_LIST)
    @Marshalling.args(int, int, Marshalling.bool)
    @Marshalling.retval( Marshalling.pickled_data )
    def get_attribute_list(self, guid, filter_flags = None, exclude = False):
        return self._testbed.get_attribute_list(guid, filter_flags, exclude)

    @Marshalling.handles(GET_FACTORY_ID)
    @Marshalling.args(int)
    @Marshalling.retval()
    def get_factory_id(self, guid):
        return self._testbed.get_factory_id(guid)

class ExperimentControllerServer(BaseServer):
    def __init__(self, root_dir, log_level, experiment_xml):
        super(ExperimentControllerServer, self).__init__(root_dir, log_level)
        self._experiment_xml = experiment_xml
        self._experiment = None

    def post_daemonize(self):
        from nepi.core.execute import ExperimentController
        self._experiment = ExperimentController(self._experiment_xml, 
            root_dir = self._root_dir)

    @Marshalling.handles(GUIDS)
    @Marshalling.args()
    @Marshalling.retval( Marshalling.pickled_data )
    def guids(self):
        return self._experiment.guids

    @Marshalling.handles(XML)
    @Marshalling.args()
    @Marshalling.retval()
    def experiment_design_xml(self):
        return self._experiment.experiment_design_xml
        
    @Marshalling.handles(EXEC_XML)
    @Marshalling.args()
    @Marshalling.retval()
    def experiment_execute_xml(self):
        return self._experiment.experiment_execute_xml
        
    @Marshalling.handles(TRACE)
    @Marshalling.args(int, str, Marshalling.base64_data)
    @Marshalling.retval()
    def trace(self, guid, trace_id, attribute):
        return str(self._experiment.trace(guid, trace_id, attribute))

    @Marshalling.handles(TRACES_INFO)
    @Marshalling.args()
    @Marshalling.retval( Marshalling.pickled_data )
    def traces_info(self):
        return self._experiment.traces_info()

    @Marshalling.handles(FINISHED)
    @Marshalling.args(int)
    @Marshalling.retval(Marshalling.bool)
    def is_finished(self, guid):
        return self._experiment.is_finished(guid)

    @Marshalling.handles(GET)
    @Marshalling.args(int, Marshalling.base64_data, str)
    @Marshalling.retval( Marshalling.pickled_data )
    def get(self, guid, name, time):
        return self._experiment.get(guid, name, time)

    @Marshalling.handles(SET)
    @Marshalling.args(int, Marshalling.base64_data, Marshalling.pickled_data, str)
    @Marshalling.retvoid
    def set(self, guid, name, value, time):
        self._experiment.set(guid, name, value, time)

    @Marshalling.handles(START)
    @Marshalling.args()
    @Marshalling.retvoid
    def start(self):
        self._experiment.start()

    @Marshalling.handles(STOP)
    @Marshalling.args()
    @Marshalling.retvoid
    def stop(self):
        self._experiment.stop()

    @Marshalling.handles(RECOVER)
    @Marshalling.args()
    @Marshalling.retvoid
    def recover(self):
        self._experiment.recover()

    @Marshalling.handles(SHUTDOWN)
    @Marshalling.args()
    @Marshalling.retvoid
    def shutdown(self):
        self._experiment.shutdown()

    @Marshalling.handles(GET_TESTBED_ID)
    @Marshalling.args(int)
    @Marshalling.retval()
    def get_testbed_id(self, guid):
        return self._experiment.get_testbed_id(guid)

    @Marshalling.handles(GET_FACTORY_ID)
    @Marshalling.args(int)
    @Marshalling.retval()
    def get_factory_id(self, guid):
        return self._experiment.get_factory_id(guid)

    @Marshalling.handles(GET_TESTBED_VERSION)
    @Marshalling.args(int)
    @Marshalling.retval()
    def get_testbed_version(self, guid):
        return self._experiment.get_testbed_version(guid)

class BaseProxy(object):
    _ServerClass = None
    _ServerClassModule = "nepi.util.proxy"
    
    def __init__(self, 
            ctor_args, root_dir, 
            launch = True, host = None, 
            port = None, user = None, ident_key = None, agent = None,
            environment_setup = ""):
        if launch:
            # ssh
            if host != None:
                python_code = (
                    "from %(classmodule)s import %(classname)s;"
                    "s = %(classname)s%(ctor_args)r;"
                    "s.run()" 
                % dict(
                    classname = self._ServerClass.__name__,
                    classmodule = self._ServerClassModule,
                    ctor_args = ctor_args
                ) )
                proc = server.popen_ssh_subprocess(python_code, host = host,
                    port = port, user = user, agent = agent,
                    ident_key = ident_key,
                    environment_setup = environment_setup,
                    waitcommand = True)
                if proc.poll():
                    err = proc.stderr.read()
                    raise RuntimeError, "Server could not be executed: %s" % (err,)
            else:
                # launch daemon
                s = self._ServerClass(*ctor_args)
                s.run()

        # connect client to server
        self._client = server.Client(root_dir, host = host, port = port, 
                user = user, agent = agent, 
                environment_setup = environment_setup)
    
    @staticmethod
    def _make_message(argtypes, argencoders, command, methname, classname, *args):
        if len(argtypes) != len(argencoders):
            raise ValueError, "Invalid arguments for _make_message: "\
                "in stub method %s of class %s "\
                "argtypes and argencoders must match in size" % (
                    methname, classname )
        if len(argtypes) != len(args):
            raise ValueError, "Invalid arguments for _make_message: "\
                "in stub method %s of class %s "\
                "expected %d arguments, got %d" % (
                    methname, classname,
                    len(argtypes), len(args))
        
        buf = []
        for argnum, (typ, (encode, fmt), val) in enumerate(zip(argtypes, argencoders, args)):
            try:
                buf.append(fmt % encode(val))
            except:
                import traceback
                raise TypeError, "Argument %d of stub method %s of class %s "\
                    "requires a value of type %s, but got %s - nested error: %s" % (
                        argnum, methname, classname,
                        getattr(typ, '__name__', typ), type(val),
                        traceback.format_exc()
                )
        
        return "%d|%s" % (command, '|'.join(buf))
    
    @staticmethod
    def _parse_reply(rvtype, methname, classname, reply):
        if not reply:
            raise RuntimeError, "Invalid reply: %r "\
                "for stub method %s of class %s" % (
                    reply,
                    methname,
                    classname)
        
        try:
            result = reply.split("|")
            code = int(result[0])
            text = result[1]
        except:
            import traceback
            raise TypeError, "Return value of stub method %s of class %s "\
                "cannot be parsed: must be of type %s, got %r - nested error: %s" % (
                    methname, classname,
                    getattr(rvtype, '__name__', rvtype), reply,
                    traceback.format_exc()
            )
        if code == ERROR:
            text = base64.b64decode(text)
            raise RuntimeError(text)
        elif code == OK:
            try:
                if rvtype is None:
                    return
                else:
                    return rvtype(text)
            except:
                import traceback
                raise TypeError, "Return value of stub method %s of class %s "\
                    "cannot be parsed: must be of type %s - nested error: %s" % (
                        methname, classname,
                        getattr(rvtype, '__name__', rvtype),
                        traceback.format_exc()
                )
        else:
            raise RuntimeError, "Invalid reply: %r "\
                "for stub method %s of class %s - unknown code" % (
                    reply,
                    methname,
                    classname)
    
    @staticmethod
    def _make_stubs(server_class, template_class):
        """
        Returns a dictionary method_name -> method
        with stub methods.
        
        Usage:
        
            class SomeProxy(BaseProxy):
               ...
               
               locals().update( BaseProxy._make_stubs(
                    ServerClass,
                    TemplateClass
               ) )
        
        ServerClass is the corresponding Server class, as
        specified in the _ServerClass class method (_make_stubs
        is static and can't access the method), and TemplateClass
        is the ultimate implementation class behind the server,
        from which argument names and defaults are taken, to
        maintain meaningful interfaces.
        """
        rv = {}
        
        class NONE: pass
        
        import os.path
        func_template_path = os.path.join(
            os.path.dirname(__file__),
            'proxy_stub.tpl')
        func_template_file = open(func_template_path, "r")
        func_template = func_template_file.read()
        func_template_file.close()
        
        for methname in vars(template_class).copy():
            if methname.endswith('_deferred'):
                # cannot wrap deferreds...
                continue
            dmethname = methname+'_deferred'
            if hasattr(server_class, methname) and not methname.startswith('_'):
                template_meth = getattr(template_class, methname)
                server_meth = getattr(server_class, methname)
                
                command = getattr(server_meth, '_handles_command', None)
                argtypes = getattr(server_meth, '_argtypes', None)
                argencoders = getattr(server_meth, '_argencoders', None)
                rvtype = getattr(server_meth, '_retval', None)
                doprop = False
                
                if hasattr(template_meth, 'fget'):
                    # property getter
                    template_meth = template_meth.fget
                    doprop = True
                
                if command is not None and argtypes is not None and argencoders is not None:
                    # We have an interface method...
                    code = template_meth.func_code
                    argnames = code.co_varnames[:code.co_argcount]
                    argdefaults = ( (NONE,) * (len(argnames) - len(template_meth.func_defaults or ()))
                                  + (template_meth.func_defaults or ()) )
                    
                    func_globals = dict(
                        BaseProxy = BaseProxy,
                        argtypes = argtypes,
                        argencoders = argencoders,
                        rvtype = rvtype,
                        functools = functools,
                    )
                    context = dict()
                    
                    func_text = func_template % dict(
                        self = argnames[0],
                        args = '%s' % (','.join(argnames[1:])),
                        argdefs = ','.join([
                            argname if argdef is NONE
                            else "%s=%r" % (argname, argdef)
                            for argname, argdef in zip(argnames[1:], argdefaults[1:])
                        ]),
                        command = command,
                        methname = methname,
                        classname = server_class.__name__
                    )
                    
                    func_text = compile(
                        func_text,
                        func_template_path,
                        'exec')
                    
                    exec func_text in func_globals, context
                    
                    if doprop:
                        rv[methname] = property(context[methname])
                        rv[dmethname] = property(context[dmethname])
                    else:
                        rv[methname] = context[methname]
                        rv[dmethname] = context[dmethname]
                    
                    # inject _deferred into core classes
                    if hasattr(template_class, methname) and not hasattr(template_class, dmethname):
                        def freezename(methname, dmethname):
                            def dmeth(self, *p, **kw): 
                                return getattr(self, methname)(*p, **kw)
                            dmeth.__name__ = dmethname
                            return dmeth
                        dmeth = freezename(methname, dmethname)
                        setattr(template_class, dmethname, dmeth)
        
        return rv
                        
class TestbedControllerProxy(BaseProxy):
    
    _ServerClass = TestbedControllerServer
    
    def __init__(self, root_dir, log_level, testbed_id = None, 
            testbed_version = None, launch = True, host = None, 
            port = None, user = None, ident_key = None, agent = None,
            environment_setup = ""):
        if launch and (testbed_id == None or testbed_version == None):
            raise RuntimeError("To launch a TesbedControllerServer a "
                    "testbed_id and testbed_version are required")
        super(TestbedControllerProxy,self).__init__(
            ctor_args = (root_dir, log_level, testbed_id, testbed_version),
            root_dir = root_dir,
            launch = launch, host = host, port = port, user = user,
            ident_key = ident_key, agent = agent, 
            environment_setup = environment_setup)

    locals().update( BaseProxy._make_stubs(
        server_class = TestbedControllerServer,
        template_class = nepi.core.execute.TestbedController,
    ) )
    
    # Shutdown stops the serverside...
    def shutdown(self, _stub = shutdown):
        rv = _stub(self)
        self._client.send_stop()
        self._client.read_reply() # wait for it
        return rv
    

class ExperimentControllerProxy(BaseProxy):
    _ServerClass = ExperimentControllerServer
    
    def __init__(self, root_dir, log_level, experiment_xml = None, 
            launch = True, host = None, port = None, user = None, 
            ident_key = None, agent = None, environment_setup = ""):
        if launch and experiment_xml is None:
            raise RuntimeError("To launch a ExperimentControllerServer a \
                    xml description of the experiment is required")
        super(ExperimentControllerProxy,self).__init__(
            ctor_args = (root_dir, log_level, experiment_xml),
            root_dir = root_dir,
            launch = launch, host = host, port = port, user = user,
            ident_key = ident_key, agent = agent, 
            environment_setup = environment_setup)

    locals().update( BaseProxy._make_stubs(
        server_class = ExperimentControllerServer,
        template_class = nepi.core.execute.ExperimentController,
    ) )

    
    # Shutdown stops the serverside...
    def shutdown(self, _stub = shutdown):
        rv = _stub(self)
        self._client.send_stop()
        self._client.read_reply() # wait for it
        return rv

