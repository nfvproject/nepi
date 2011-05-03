#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import server, validation
from nepi.util.constants import TIME_NOW, ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP, DeploymentConfiguration as DC
import getpass
import cPickle
import sys
import time
import tempfile
import shutil

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
EXPERIMENT_SET = 37
EXPERIMENT_GET = 38

# PARAMETER TYPE
STRING  =  100
INTEGER = 101
BOOL    = 102
FLOAT   = 103

# EXPERIMENT CONTROLER PROTOCOL MESSAGES
controller_messages = dict({
    XML:    "%d" % XML,
    TRACE:  "%d|%s" % (TRACE, "%d|%d|%s|%s"),
    FINISHED:   "%d|%s" % (FINISHED, "%d"),
    START:  "%d" % START,
    STOP:   "%d" % STOP,
    RECOVER : "%d" % RECOVER,
    SHUTDOWN:   "%d" % SHUTDOWN,
    })

# TESTBED INSTANCE PROTOCOL MESSAGES
testbed_messages = dict({
    TRACE:  "%d|%s" % (TRACE, "%d|%s|%s"),
    START:  "%d" % START,
    STOP:   "%d" % STOP,
    SHUTDOWN:   "%d" % SHUTDOWN,
    CONFIGURE: "%d|%s" % (CONFIGURE, "%s|%s|%d"),
    CREATE: "%d|%s" % (CREATE, "%d|%s"),
    CREATE_SET: "%d|%s" % (CREATE_SET, "%d|%s|%s|%d"),
    FACTORY_SET: "%d|%s" % (FACTORY_SET, "%d|%s|%s|%d"),
    CONNECT: "%d|%s" % (CONNECT, "%d|%s|%d|%s"),
    CROSS_CONNECT: "%d|%s" % (CROSS_CONNECT, "%d|%s|%d|%d|%s|%s|%s"),
    ADD_TRACE: "%d|%s" % (ADD_TRACE, "%d|%s"),
    ADD_ADDRESS: "%d|%s" % (ADD_ADDRESS, "%d|%s|%d|%s"),
    ADD_ROUTE: "%d|%s" % (ADD_ROUTE, "%d|%s|%d|%s"),
    DO_SETUP:   "%d" % DO_SETUP,
    DO_CREATE:  "%d" % DO_CREATE,
    DO_CONNECT_INIT:    "%d" % DO_CONNECT_INIT,
    DO_CONNECT_COMPL:   "%d" % DO_CONNECT_COMPL,
    DO_CONFIGURE:       "%d" % DO_CONFIGURE,
    DO_PRECONFIGURE:    "%d" % DO_PRECONFIGURE,
    DO_CROSS_CONNECT_INIT:  "%d|%s" % (DO_CROSS_CONNECT_INIT, "%s"),
    DO_CROSS_CONNECT_COMPL: "%d|%s" % (DO_CROSS_CONNECT_COMPL, "%s"),
    GET:    "%d|%s" % (GET, "%d|%s|%s"),
    SET:    "%d|%s" % (SET, "%d|%s|%s|%d|%s"),
    EXPERIMENT_GET:    "%d|%s" % (EXPERIMENT_GET, "%d|%d|%s|%s"),
    EXPERIMENT_SET:    "%d|%s" % (EXPERIMENT_SET, "%d|%d|%s|%s|%d|%s"),
    GET_ROUTE: "%d|%s" % (GET, "%d|%d|%s"),
    GET_ADDRESS: "%d|%s" % (GET, "%d|%d|%s"),
    ACTION: "%d|%s" % (ACTION, "%s|%d|%s"),
    STATUS: "%d|%s" % (STATUS, "%s"),
    GUIDS:  "%d" % GUIDS,
    GET_ATTRIBUTE_LIST:  "%d" % GET_ATTRIBUTE_LIST,
    TESTBED_ID:  "%d" % TESTBED_ID,
    TESTBED_VERSION:  "%d" % TESTBED_VERSION,
   })

instruction_text = dict({
    OK:     "OK",
    ERROR:  "ERROR",
    XML:    "XML",
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
    ACTION: "ACTION",
    STATUS: "STATUS",
    GUIDS:  "GUIDS",
    STRING: "STRING",
    INTEGER:    "INTEGER",
    BOOL:   "BOOL",
    FLOAT:  "FLOAT",
    TESTBED_ID: "TESTBED_ID",
    TESTBED_VERSION: "TESTBED_VERSION",
    EXPERIMENT_SET: "EXPERIMENT_SET",
    EXPERIMENT_GET: "EXPERIMENT_GET",
    })

def get_type(value):
    if isinstance(value, bool):
        return BOOL
    elif isinstance(value, int):
        return INTEGER
    elif isinstance(value, float):
        return FLOAT
    else:
        return STRING

def set_type(type, value):
    if type == INTEGER:
        value = int(value)
    elif type == FLOAT:
        value = float(value)
    elif type == BOOL:
        value = value == "True"
    else:
        value = str(value)
    return value

def log_msg(server, params):
    instr = int(params[0])
    instr_txt = instruction_text[instr]
    server.log_debug("%s - msg: %s [%s]" % (server.__class__.__name__, 
        instr_txt, ", ".join(map(str, params[1:]))))

def log_reply(server, reply):
    res = reply.split("|")
    code = int(res[0])
    code_txt = instruction_text[code]
    txt = base64.b64decode(res[1])
    server.log_debug("%s - reply: %s %s" % (server.__class__.__name__, 
            code_txt, txt))

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
        
        for _,attr_info in Metadata.DEPLOYMENT_ATTRIBUTES:
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

def create_controller(xml, access_config = None):
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
    return module.TestbedController(testbed_version)

class TestbedControllerServer(server.Server):
    def __init__(self, root_dir, log_level, testbed_id, testbed_version):
        super(TestbedControllerServer, self).__init__(root_dir, log_level)
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._testbed = None

    def post_daemonize(self):
        self._testbed = _build_testbed_controller(self._testbed_id, 
                self._testbed_version)

    def reply_action(self, msg):
        if not msg:
            result = base64.b64encode("Invalid command line")
            reply = "%d|%s" % (ERROR, result)
        else:
            params = msg.split("|")
            instruction = int(params[0])
            log_msg(self, params)
            try:
                if instruction == TRACE:
                    reply = self.trace(params)
                elif instruction == START:
                    reply = self.start(params)
                elif instruction == STOP:
                    reply = self.stop(params)
                elif instruction == SHUTDOWN:
                    reply = self.shutdown(params)
                elif instruction == CONFIGURE:
                    reply = self.defer_configure(params)
                elif instruction == CREATE:
                    reply = self.defer_create(params)
                elif instruction == CREATE_SET:
                    reply = self.defer_create_set(params)
                elif instruction == FACTORY_SET:
                    reply = self.defer_factory_set(params)
                elif instruction == CONNECT:
                    reply = self.defer_connect(params)
                elif instruction == CROSS_CONNECT:
                    reply = self.defer_cross_connect(params)
                elif instruction == ADD_TRACE:
                    reply = self.defer_add_trace(params)
                elif instruction == ADD_ADDRESS:
                    reply = self.defer_add_address(params)
                elif instruction == ADD_ROUTE:
                    reply = self.defer_add_route(params)
                elif instruction == DO_SETUP:
                    reply = self.do_setup(params)
                elif instruction == DO_CREATE:
                    reply = self.do_create(params)
                elif instruction == DO_CONNECT_INIT:
                    reply = self.do_connect_init(params)
                elif instruction == DO_CONNECT_COMPL:
                    reply = self.do_connect_compl(params)
                elif instruction == DO_CONFIGURE:
                    reply = self.do_configure(params)
                elif instruction == DO_PRECONFIGURE:
                    reply = self.do_preconfigure(params)
                elif instruction == DO_CROSS_CONNECT_INIT:
                    reply = self.do_cross_connect_init(params)
                elif instruction == DO_CROSS_CONNECT_COMPL:
                    reply = self.do_cross_connect_compl(params)
                elif instruction == GET:
                    reply = self.get(params)
                elif instruction == SET:
                    reply = self.set(params)
                elif instruction == GET_ADDRESS:
                    reply = self.get_address(params)
                elif instruction == GET_ROUTE:
                    reply = self.get_route(params)
                elif instruction == ACTION:
                    reply = self.action(params)
                elif instruction == STATUS:
                    reply = self.status(params)
                elif instruction == GUIDS:
                    reply = self.guids(params)
                elif instruction == GET_ATTRIBUTE_LIST:
                    reply = self.get_attribute_list(params)
                elif instruction == TESTBED_ID:
                    reply = self.testbed_id(params)
                elif instruction == TESTBED_VERSION:
                    reply = self.testbed_version(params)
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

    def guids(self, params):
        guids = self._testbed.guids
        value = cPickle.dumps(guids)
        result = base64.b64encode(value)
        return "%d|%s" % (OK, result)

    def testbed_id(self, params):
        testbed_id = self._testbed.testbed_id
        result = base64.b64encode(str(testbed_id))
        return "%d|%s" % (OK, result)

    def testbed_version(self, params):
        testbed_version = self._testbed.testbed_version
        result = base64.b64encode(str(testbed_version))
        return "%d|%s" % (OK, result)

    def defer_create(self, params):
        guid = int(params[1])
        factory_id = params[2]
        self._testbed.defer_create(guid, factory_id)
        return "%d|%s" % (OK, "")

    def trace(self, params):
        guid = int(params[1])
        trace_id = params[2]
        attribute = base64.b64decode(params[3])
        trace = self._testbed.trace(guid, trace_id, attribute)
        result = base64.b64encode(trace)
        return "%d|%s" % (OK, result)

    def start(self, params):
        self._testbed.start()
        return "%d|%s" % (OK, "")

    def stop(self, params):
        self._testbed.stop()
        return "%d|%s" % (OK, "")

    def shutdown(self, params):
        self._testbed.shutdown()
        return "%d|%s" % (OK, "")

    def defer_configure(self, params):
        name = base64.b64decode(params[1])
        value = base64.b64decode(params[2])
        type = int(params[3])
        value = set_type(type, value)
        self._testbed.defer_configure(name, value)
        return "%d|%s" % (OK, "")

    def defer_create_set(self, params):
        guid = int(params[1])
        name = base64.b64decode(params[2])
        value = base64.b64decode(params[3])
        type = int(params[4])
        value = set_type(type, value)
        self._testbed.defer_create_set(guid, name, value)
        return "%d|%s" % (OK, "")

    def defer_factory_set(self, params):
        name = base64.b64decode(params[1])
        value = base64.b64decode(params[2])
        type = int(params[3])
        value = set_type(type, value)
        self._testbed.defer_factory_set(name, value)
        return "%d|%s" % (OK, "")

    def defer_connect(self, params):
        guid1 = int(params[1])
        connector_type_name1 = params[2]
        guid2 = int(params[3])
        connector_type_name2 = params[4]
        self._testbed.defer_connect(guid1, connector_type_name1, guid2, 
            connector_type_name2)
        return "%d|%s" % (OK, "")

    def defer_cross_connect(self, params):
        guid = int(params[1])
        connector_type_name = params[2]
        cross_guid = int(params[3])
        connector_type_name = params[4]
        cross_guid = int(params[5])
        cross_testbed_guid = int(params[6])
        cross_testbed_id = params[7]
        cross_factory_id = params[8]
        cross_connector_type_name = params[9]
        self._testbed.defer_cross_connect(guid, connector_type_name, cross_guid, 
            cross_testbed_guid, cross_testbed_id, cross_factory_id, 
            cross_connector_type_name)
        return "%d|%s" % (OK, "")

    def defer_add_trace(self, params):
        guid = int(params[1])
        trace_id = params[2]
        self._testbed.defer_add_trace(guid, trace_id)
        return "%d|%s" % (OK, "")

    def defer_add_address(self, params):
        guid = int(params[1])
        address = params[2]
        netprefix = int(params[3])
        broadcast = params[4]
        self._testbed.defer_add_address(guid, address, netprefix,
                broadcast)
        return "%d|%s" % (OK, "")

    def defer_add_route(self, params):
        guid = int(params[1])
        destination = params[2]
        netprefix = int(params[3])
        nexthop = params[4]
        self._testbed.defer_add_route(guid, destination, netprefix, nexthop)
        return "%d|%s" % (OK, "")

    def do_setup(self, params):
        self._testbed.do_setup()
        return "%d|%s" % (OK, "")

    def do_create(self, params):
        self._testbed.do_create()
        return "%d|%s" % (OK, "")

    def do_connect_init(self, params):
        self._testbed.do_connect_init()
        return "%d|%s" % (OK, "")

    def do_connect_compl(self, params):
        self._testbed.do_connect_compl()
        return "%d|%s" % (OK, "")

    def do_configure(self, params):
        self._testbed.do_configure()
        return "%d|%s" % (OK, "")

    def do_preconfigure(self, params):
        self._testbed.do_preconfigure()
        return "%d|%s" % (OK, "")

    def do_cross_connect_init(self, params):
        pcross_data = base64.b64decode(params[1])
        cross_data = cPickle.loads(pcross_data)
        self._testbed.do_cross_connect_init(cross_data)
        return "%d|%s" % (OK, "")

    def do_cross_connect_compl(self, params):
        pcross_data = base64.b64decode(params[1])
        cross_data = cPickle.loads(pcross_data)
        self._testbed.do_cross_connect_compl(cross_data)
        return "%d|%s" % (OK, "")

    def get(self, params):
        guid = int(param[1])
        name = base64.b64decode(params[2])
        value = self._testbed.get(guid, name, time)
        time = params[3]
        result = base64.b64encode(str(value))
        return "%d|%s" % (OK, result)

    def set(self, params):
        guid = int(params[1])
        name = base64.b64decode(params[2])
        value = base64.b64decode(params[3])
        type = int(params[2])
        time = params[4]
        value = set_type(type, value)
        self._testbed.set(guid, name, value, time)
        return "%d|%s" % (OK, "")

    def get_address(self, params):
        guid = int(params[1])
        index = int(params[2])
        attribute = base64.b64decode(param[3])
        value = self._testbed.get_address(guid, index, attribute)
        result = base64.b64encode(str(value))
        return "%d|%s" % (OK, result)

    def get_route(self, params):
        guid = int(params[1])
        index = int(params[2])
        attribute = base64.b64decode(param[3])
        value = self._testbed.get_route(guid, index, attribute)
        result = base64.b64encode(str(value))
        return "%d|%s" % (OK, result)

    def action(self, params):
        time = params[1]
        guid = int(params[2])
        command = base64.b64decode(params[3])
        self._testbed.action(time, guid, command)
        return "%d|%s" % (OK, "")

    def status(self, params):
        guid = None
        if params[1] != "None":
            guid = int(params[1])
        status = self._testbed.status(guid)
        result = base64.b64encode(str(status))
        return "%d|%s" % (OK, result)

    def get_attribute_list(self, params):
        guid = int(params[1])
        attr_list = self._testbed.get_attribute_list(guid)
        value = cPickle.dumps(attr_list)
        result = base64.b64encode(value)
        return "%d|%s" % (OK, result)

class ExperimentControllerServer(server.Server):
    def __init__(self, root_dir, log_level, experiment_xml):
        super(ExperimentControllerServer, self).__init__(root_dir, log_level)
        self._experiment_xml = experiment_xml
        self._controller = None

    def post_daemonize(self):
        from nepi.core.execute import ExperimentController
        self._controller = ExperimentController(self._experiment_xml, 
            root_dir = self._root_dir)

    def reply_action(self, msg):
        if not msg:
            result = base64.b64encode("Invalid command line")
            reply = "%d|%s" % (ERROR, result)
        else:
            params = msg.split("|")
            instruction = int(params[0])
            log_msg(self, params)
            try:
                if instruction == XML:
                    reply = self.experiment_xml(params)
                elif instruction == TRACE:
                    reply = self.trace(params)
                elif instruction == FINISHED:
                    reply = self.is_finished(params)
                elif instruction == EXPERIMENT_GET:
                    reply = self.get(params)
                elif instruction == EXPERIMENT_SET:
                    reply = self.set(params)
                elif instruction == START:
                    reply = self.start(params)
                elif instruction == STOP:
                    reply = self.stop(params)
                elif instruction == RECOVER:
                    reply = self.recover(params)
                elif instruction == SHUTDOWN:
                    reply = self.shutdown(params)
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

    def experiment_xml(self, params):
        xml = self._controller.experiment_xml
        result = base64.b64encode(xml)
        return "%d|%s" % (OK, result)
        
    def trace(self, params):
        testbed_guid = int(params[1])
        guid = int(params[2])
        trace_id = params[3]
        attribute = base64.b64decode(params[4])
        trace = self._controller.trace(testbed_guid, guid, trace_id, attribute)
        result = base64.b64encode(trace)
        return "%d|%s" % (OK, result)

    def is_finished(self, params):
        guid = int(params[1])
        status = self._controller.is_finished(guid)
        result = base64.b64encode(str(status))
        return "%d|%s" % (OK, result)

    def get(self, params):
        testbed_guid = int(param[1])
        guid = int(params[2])
        name = base64.b64decode(params[3])
        value = self._controller.get(testbed_guid, guid, name, time)
        time = params[4]
        result = base64.b64encode(str(value))
        return "%d|%s" % (OK, result)

    def set(self, params):
        testbed_guid = int(params[1])
        guid = int(params[2])
        name = base64.b64decode(params[3])
        value = base64.b64decode(params[4])
        type = int(params[3])
        time = params[5]
        value = set_type(type, value)
        self._controller.set(testbed_guid, guid, name, value, time)
        return "%d|%s" % (OK, "")

    def start(self, params):
        self._controller.start()
        return "%d|%s" % (OK, "")

    def stop(self, params):
        self._controller.stop()
        return "%d|%s" % (OK, "")

    def recover(self, params):
        self._controller.recover()
        return "%d|%s" % (OK, "")

    def shutdown(self, params):
        self._controller.shutdown()
        return "%d|%s" % (OK, "")

class TestbedControllerProxy(object):
    def __init__(self, root_dir, log_level, testbed_id = None, 
            testbed_version = None, launch = True, host = None, 
            port = None, user = None, ident_key = None, agent = None,
            environment_setup = ""):
        if launch:
            if testbed_id == None or testbed_version == None:
                raise RuntimeError("To launch a TesbedInstance server a \
                        testbed_id and testbed_version are required")
            # ssh
            if host != None:
                python_code = "from nepi.util.proxy import \
                        TesbedInstanceServer;\
                        s = TestbedControllerServer('%s', %d, '%s', '%s');\
                        s.run()" % (root_dir, log_level, testbed_id, 
                                testbed_version)
                proc = server.popen_ssh_subprocess(python_code, host = host,
                    port = port, user = user, agent = agent,
                    ident_key = ident_key,
                    environment_setup = environment_setup)
                if proc.poll():
                    err = proc.stderr.read()
                    raise RuntimeError("Server could not be executed: %s" % \
                            err)
            else:
                # launch daemon
                s = TestbedControllerServer(root_dir, log_level, testbed_id, 
                    testbed_version)
                s.run()

        # connect client to server
        self._client = server.Client(root_dir, host = host, port = port, 
                user = user, agent = agent)

    @property
    def guids(self):
        msg = testbed_messages[GUIDS]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        guids = cPickle.loads(text)
        return guids

    @property
    def testbed_id(self):
        msg = testbed_messages[TESTBED_ID]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return int(text)

    @property
    def testbed_version(self):
        msg = testbed_messages[TESTBED_VERSION]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return int(text)

    def defer_configure(self, name, value):
        msg = testbed_messages[CONFIGURE]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (name, value, type)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_create(self, guid, factory_id):
        msg = testbed_messages[CREATE]
        msg = msg % (guid, factory_id)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_create_set(self, guid, name, value):
        msg = testbed_messages[CREATE_SET]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (guid, name, value, type)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_factory_set(self, guid, name, value):
        msg = testbed_messages[FACTORY_SET]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (guid, name, value, type)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        msg = testbed_messages[CONNECT]
        msg = msg % (guid1, connector_type_name1, guid2, 
            connector_type_name2)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_guid, cross_testbed_id, cross_factory_id, 
            cross_connector_type_name):
        msg = testbed_messages[CROSS_CONNECT]
        msg = msg % (guid, connector_type_name, cross_guid, cross_testbed_guid,
            cross_testbed_id, cross_factory_id, cross_connector_type_name)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_add_trace(self, guid, trace_id):
        msg = testbed_messages[ADD_TRACE]
        msg = msg % (guid, trace_id)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_add_address(self, guid, address, netprefix, broadcast): 
        msg = testbed_messages[ADD_ADDRESS]
        msg = msg % (guid, address, netprefix, broadcast)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def defer_add_route(self, guid, destination, netprefix, nexthop):
        msg = testbed_messages[ADD_ROUTE]
        msg = msg % (guid, destination, netprefix, nexthop)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_setup(self):
        msg = testbed_messages[DO_SETUP]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_create(self):
        msg = testbed_messages[DO_CREATE]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_connect_init(self):
        msg = testbed_messages[DO_CONNECT_INIT]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_connect_compl(self):
        msg = testbed_messages[DO_CONNECT_COMPL]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_configure(self):
        msg = testbed_messages[DO_CONFIGURE]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_preconfigure(self):
        msg = testbed_messages[DO_PRECONFIGURE]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_cross_connect_init(self, cross_data):
        msg = testbed_messages[DO_CROSS_CONNECT_INIT]
        pcross_data = cPickle.dumps(cross_data)
        cross_data = base64.b64encode(pcross_data)
        msg = msg % (cross_data)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def do_cross_connect_compl(self, cross_data):
        msg = testbed_messages[DO_CROSS_CONNECT_COMPL]
        pcross_data = cPickle.dumps(cross_data)
        cross_data = base64.b64encode(pcross_data)
        msg = msg % (cross_data)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def start(self, time = TIME_NOW):
        msg = testbed_messages[START]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def stop(self, time = TIME_NOW):
        msg = testbed_messages[STOP]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def set(self, guid, name, value, time = TIME_NOW):
        msg = testbed_messages[SET]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (guid, name, value, type, time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def get(self, guid, name, time = TIME_NOW):
        msg = testbed_messages[GET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        msg = msg % (guid, name, time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def get_address(self, guid, index, attribute):
        msg = testbed_messages[GET_ADDRESS]
        # avoid having "|" in this parameters
        attribute = base64.b64encode(attribute)
        msg = msg % (guid, index, attribute)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def get_route(self, guid, index, attribute):
        msg = testbed_messages[GET_ROUTE]
        # avoid having "|" in this parameters
        attribute = base64.b64encode(attribute)
        msg = msg % (guid, index, attribute)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def action(self, time, guid, action):
        msg = testbed_messages[ACTION]
        msg = msg % (time, guid, action)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def status(self, guid = None):
        msg = testbed_messages[STATUS]
        msg = msg % str(guid)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return int(text)

    def trace(self, guid, trace_id, attribute='value'):
        msg = testbed_messages[TRACE]
        attribute = base64.b64encode(attribute)
        msg = msg % (guid, trace_id, attribute)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def get_attribute_list(self, guid):
        msg = testbed_messages[GET_ATTRIBUTE_LIST]
        msg = msg % (guid)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        attr_list = cPickle.loads(text)
        return attr_list

    def shutdown(self):
        msg = testbed_messages[SHUTDOWN]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        self._client.send_stop()
        self._client.read_reply() # wait for it

class ExperimentControllerProxy(object):
    def __init__(self, root_dir, log_level, experiment_xml = None, 
            launch = True, host = None, port = None, user = None, 
            ident_key = None, agent = None, environment_setup = ""):
        if launch:
            # launch server
            if experiment_xml == None:
                raise RuntimeError("To launch a ExperimentControllerServer a \
                        xml description of the experiment is required")
            # ssh
            if host != None:
                xml = experiment_xml
                python_code = "from nepi.util.proxy import ExperimentControllerServer;\
                        s = ExperimentControllerServer(%r, %r, %r);\
                        s.run()" % (root_dir, log_level, xml)
                proc = server.popen_ssh_subprocess(python_code, host = host,
                    port = port, user = user, agent = agent,
                    ident_key = ident_key,
                    environment_setup = environment_setup)
                if proc.poll():
                    err = proc.stderr.read()
                    raise RuntimeError("Server could not be executed: %s" % \
                            err)
            else:
                # launch daemon
                s = ExperimentControllerServer(root_dir, log_level, experiment_xml)
                s.run()

        # connect client to server
        self._client = server.Client(root_dir, host = host, port = port, 
                user = user, agent = agent)

    @property
    def experiment_xml(self):
        msg = controller_messages[XML]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def trace(self, testbed_guid, guid, trace_id, attribute='value'):
        msg = controller_messages[TRACE]
        attribute = base64.b64encode(attribute)
        msg = msg % (testbed_guid, guid, trace_id, attribute)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == OK:
            return text
        raise RuntimeError(text)

    def start(self):
        msg = controller_messages[START]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def stop(self):
        msg = controller_messages[STOP]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def recover(self):
        msg = controller_messages[RECOVER]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def is_finished(self, guid):
        msg = controller_messages[FINISHED]
        msg = msg % guid
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text == "True"

    def set(self, testbed_guid, guid, name, value, time = TIME_NOW):
        msg = testbed_messages[EXPERIMENT_SET]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (testbed_guid, guid, name, value, type, time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def get(self, testbed_guid, guid, name, time = TIME_NOW):
        msg = testbed_messages[EXPERIMENT_GET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        msg = msg % (testbed_guid, guid, name, time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

    def shutdown(self):
        msg = controller_messages[SHUTDOWN]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        self._client.send_stop()
        self._client.read_reply() # wait for it

