#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import server, validation
from nepi.util.constants import TIME_NOW
import sys

# PROTOCOL REPLIES
OK = 0
ERROR = 1

# PROTOCOL INSTRUCTION MESSAGES
XML = 2 
ACCESS  = 3
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
DO_CONNECT  = 20
DO_CONFIGURE    = 21
DO_CROSS_CONNECT    = 22
GET = 23
SET = 24
ACTION  = 25
STATUS  = 26
GUIDS  = 27

# PARAMETER TYPE
STRING  =  100
INTEGER = 101
BOOL    = 102
FLOAT   = 103

# EXPERIMENT CONTROLER PROTOCOL MESSAGES
controller_messages = dict({
    XML:    "%d" % XML,
    ACCESS: "%d|%s" % (ACCESS, "%d|%s|%s|%s|%s|%d|%s|%r"),
    TRACE:  "%d|%s" % (TRACE, "%d|%d|%s"),
    FINISHED:   "%d|%s" % (FINISHED, "%d"),
    START:  "%d" % START,
    STOP:   "%d" % STOP,
    SHUTDOWN:   "%d" % SHUTDOWN,
    })

# TESTBED INSTANCE PROTOCOL MESSAGES
testbed_messages = dict({
    TRACE:  "%d|%s" % (TRACE, "%d|%s"),
    START:  "%d|%s" % (START, "%s"),
    STOP:    "%d|%s" % (STOP, "%s"),
    SHUTDOWN:   "%d" % SHUTDOWN,
    CONFIGURE: "%d|%s" % (CONFIGURE, "%s|%s|%d"),
    CREATE: "%d|%s" % (CREATE, "%d|%s"),
    CREATE_SET: "%d|%s" % (CREATE_SET, "%d|%s|%s|%d"),
    FACTORY_SET: "%d|%s" % (FACTORY_SET, "%d|%s|%s|%d"),
    CONNECT: "%d|%s" % (CONNECT, "%d|%s|%d|%s"),
    CROSS_CONNECT: "%d|%s" % (CROSS_CONNECT, "%d|%s|%d|%d|%s|%s"),
    ADD_TRACE: "%d|%s" % (ADD_TRACE, "%d|%s"),
    ADD_ADDRESS: "%d|%s" % (ADD_ADDRESS, "%d|%d|%s|%d|%s"),
    ADD_ROUTE: "%d|%s" % (ADD_ROUTE, "%d|%s|%d|%s"),
    DO_SETUP:   "%d" % DO_SETUP,
    DO_CREATE:  "%d" % DO_CREATE,
    DO_CONNECT: "%d" % DO_CONNECT,
    DO_CONFIGURE:   "%d" % DO_CONFIGURE,
    DO_CROSS_CONNECT:   "%d" % DO_CROSS_CONNECT,
    GET:    "%d|%s" % (GET, "%s|%d|%s"),
    SET:    "%d|%s" % (SET, "%s|%d|%s|%s|%d"),
    ACTION: "%d|%s" % (ACTION, "%s|%d|%s"),
    STATUS: "%d|%s" % (STATUS, "%d"),
    GUIDS:  "%d" % GUIDS,
    })

instruction_text = dict({
    OK:     "OK",
    ERROR:  "ERROR",
    XML:    "XML",
    ACCESS: "ACCESS",
    TRACE:  "TRACE",
    FINISHED:   "FINISHED",
    START:  "START",
    STOP:   "STOP",
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
    DO_CONNECT: "DO_CONNECT",
    DO_CONFIGURE:   "DO_CONFIGURE",
    DO_CROSS_CONNECT:   "DO_CROSS_CONNECT",
    GET:    "GET",
    SET:    "SET",
    ACTION: "ACTION",
    STATUS: "STATUS",
    GUIDS:  "GUIDS",
    STRING: "STRING",
    INTEGER:    "INTEGER",
    BOOL:   "BOOL",
    FLOAT:  "FLOAT"
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

class AccessConfiguration(AttributesMap):
    MODE_SINGLE_PROCESS = "SINGLE"
    MODE_DAEMON = "DAEMON"
    ACCESS_SSH = "SSH"
    ACCESS_LOCAL = "LOCAL"
    ERROR_LEVEL = "Error"
    DEBUG_LEVEL = "Debug"

    def __init__(self):
        super(AccessConfiguration, self).__init__()
        self.add_attribute(name = "mode",
                help = "Instance execution mode",
                type = Attribute.ENUM,
                value = AccessConfiguration.MODE_SINGLE_PROCESS,
                allowed = [AccessConfiguration.MODE_DAEMON,
                    AccessConfiguration.MODE_SINGLE_PROCESS],
                validation_function = validation.is_enum)
        self.add_attribute(name = "communication",
                help = "Instance communication mode",
                type = Attribute.ENUM,
                value = AccessConfiguration.ACCESS_LOCAL,
                allowed = [AccessConfiguration.ACCESS_LOCAL,
                    AccessConfiguration.ACCESS_SSH],
                validation_function = validation.is_enum)
        self.add_attribute(name = "host",
                help = "Host where the testbed will be executed",
                type = Attribute.STRING,
                value = "localhost",
                validation_function = validation.is_string)
        self.add_attribute(name = "user",
                help = "User on the Host to execute the testbed",
                type = Attribute.STRING,
                validation_function = validation.is_string)
        self.add_attribute(name = "port",
                help = "Port on the Host",
                type = Attribute.INTEGER,
                value = 22,
                validation_function = validation.is_integer)
        self.add_attribute(name = "rootDirectory",
                help = "Root directory for storing process files",
                type = Attribute.STRING,
                value = ".",
                validation_function = validation.is_string) # TODO: validation.is_path
        self.add_attribute(name = "useAgent",
                help = "Use -A option for forwarding of the authentication agent, if ssh access is used", 
                type = Attribute.BOOL,
                value = False,
                validation_function = validation.is_bool)
        self.add_attribute(name = "logLevel",
                help = "Log level for instance",
                type = Attribute.ENUM,
                value = AccessConfiguration.ERROR_LEVEL,
                allowed = [AccessConfiguration.ERROR_LEVEL,
                    AccessConfiguration.DEBUG_LEVEL],
                validation_function = validation.is_enum)

def create_controller(xml, access_config = None):
    mode = None if not access_config else access_config.get_attribute_value("mode")
    if not mode or mode == AccessConfiguration.MODE_SINGLE_PROCESS:
        from nepi.core.execute import ExperimentController
        return ExperimentController(xml)
    elif mode == AccessConfiguration.MODE_DAEMON:
        root_dir = access_config.get_attribute_value("rootDirectory")
        log_level = access_config.get_attribute_value("logLevel")
        return ExperimentControllerProxy(root_dir, log_level, experiment_xml = xml)
    raise RuntimeError("Unsupported access configuration 'mode'" % mode)

def create_testbed_instance(testbed_id, testbed_version, access_config):
    mode = None if not access_config else access_config.get_attribute_value("mode")
    if not mode or mode == AccessConfiguration.MODE_SINGLE_PROCESS:
        return  _build_testbed_testbed(testbed_id, testbed_version)
    elif mode == AccessConfiguration.MODE_DAEMON:
        root_dir = access_config.get_attribute_value("rootDirectory")
        log_level = access_config.get_attribute_value("logLevel")
        return TestbedIntanceProxy(root_dir, log_level, testbed_id = testbed_id, 
                testbed_version = testbed_version)
    raise RuntimeError("Unsupported access configuration 'mode'" % mode)

def _build_testbed_testbed(testbed_id, testbed_version):
    mod_name = "nepi.testbeds.%s" % (testbed_id.lower())
    if not mod_name in sys.modules:
        __import__(mod_name)
    module = sys.modules[mod_name]
    return module.TestbedInstance(testbed_version)

class TestbedInstanceServer(server.Server):
    def __init__(self, root_dir, testbed_id, testbed_version):
        super(TestbedInstanceServer, self).__init__(root_dir)
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._testbed = None

    def post_daemonize(self):
        self._testbed = _build_testbed_testbed(self._testbed_id, 
                self._testbed_version)

    def reply_action(self, msg):
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
                reply = self.configure(params)
            elif instruction == CREATE:
                reply = self.create(params)
            elif instruction == CREATE_SET:
                reply = self.create_set(params)
            elif instruction == FACTORY_SET:
                reply = self.factory_set(params)
            elif instruction == CONNECT:
                reply = self.connect(params)
            elif instruction == CROSS_CONNECT:
                reply = self.cross_connect(params)
            elif instruction == ADD_TRACE:
                reply = self.add_trace(params)
            elif instruction == ADD_ADDRESS:
                reply = self.add_address(params)
            elif instruction == ADD_ROUTE:
                reply = self.add_route(params)
            elif instruction == DO_SETUP:
                reply = self.do_setup(params)
            elif instruction == DO_CREATE:
                reply = self.do_create(params)
            elif instruction == DO_CONNECT:
                reply = self.do_connect(params)
            elif instruction == DO_CONFIGURE:
                reply = self.do_configure(params)
            elif instruction == DO_CROSS_CONNECT:
                reply = self.do_cross_connect(params)
            elif instruction == GET:
                reply = self.get(params)
            elif instruction == SET:
                reply = self.set(params)
            elif instruction == ACTION:
                reply = self.action(params)
            elif instruction == STATUS:
                reply = self.status(params)
            elif instruction == GUIDS:
                reply = self.guids(params)
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
        guids = ",".join(map(str, guids))
        result = base64.b64encode(guids)
        return "%d|%s" % (OK, result)

    def create(self, params):
        guid = int(params[1])
        factory_id = params[2]
        self._testbed.create(guid, factory_id)
        return "%d|%s" % (OK, "")

    def trace(self, params):
        guid = int(params[1])
        trace_id = params[2]
        trace = self._testbed.trace(guid, trace_id)
        result = base64.b64encode(trace)
        return "%d|%s" % (OK, result)

    def start(self, params):
        time = params[1]
        self._testbed.start(time)
        return "%d|%s" % (OK, "")

    def stop(self, params):
        time = params[1]
        self._testbed.stop(time)
        return "%d|%s" % (OK, "")

    def shutdown(self, params):
        self._testbed.shutdown()
        return "%d|%s" % (OK, "")

    def configure(self, params):
        name = base64.b64decode(params[1])
        value = base64.b64decode(params[2])
        type = int(params[3])
        value = set_type(type, value)
        self._testbed.configure(name, value)
        return "%d|%s" % (OK, "")

    def create_set(self, params):
        guid = int(params[1])
        name = base64.b64decode(params[2])
        value = base64.b64decode(params[3])
        type = int(params[4])
        value = set_type(type, value)
        self._testbed.create_set(guid, name, value)
        return "%d|%s" % (OK, "")

    def factory_set(self, params):
        name = base64.b64decode(params[1])
        value = base64.b64decode(params[2])
        type = int(params[3])
        value = set_type(type, value)
        self._testbed.factory_set(name, value)
        return "%d|%s" % (OK, "")

    def connect(self, params):
        guid1 = int(params[1])
        connector_type_name1 = params[2]
        guid2 = int(params[3])
        connector_type_name2 = params[4]
        self._testbed.connect(guid1, connector_type_name1, guid2, 
            connector_type_name2)
        return "%d|%s" % (OK, "")

    def cross_connect(self, params):
        guid = int(params[1])
        connector_type_name = params[2]
        cross_guid = int(params[3])
        connector_type_name = params[4]
        cross_guid = int(params[5])
        cross_testbed_id = params[6]
        cross_factory_id = params[7]
        cross_connector_type_name = params[8]
        self._testbed.cross_connect(guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name)
        return "%d|%s" % (OK, "")

    def add_trace(self, params):
        guid = int(params[1])
        trace_id = params[2]
        self._testbed.add_trace(guid, trace_id)
        return "%d|%s" % (OK, "")

    def add_address(self, params):
        guid = int(params[1])
        family = int(params[2])
        address = params[3]
        netprefix = int(params[4])
        broadcast = params[5]
        self._testbed.add_address(guid, family, address, netprefix,
                broadcast)
        return "%d|%s" % (OK, "")

    def add_route(self, params):
        guid = int(params[1])
        destination = params[2]
        netprefix = int(params[3])
        nexthop = params[4]
        self._testbed.add_route(guid, destination, netprefix, nexthop)
        return "%d|%s" % (OK, "")

    def do_setup(self, params):
        self._testbed.do_setup()
        return "%d|%s" % (OK, "")

    def do_create(self, params):
        self._testbed.do_create()
        return "%d|%s" % (OK, "")

    def do_connect(self, params):
        self._testbed.do_connect()
        return "%d|%s" % (OK, "")

    def do_configure(self, params):
        self._testbed.do_configure()
        return "%d|%s" % (OK, "")

    def do_cross_connect(self, params):
        self._testbed.do_cross_connect()
        return "%d|%s" % (OK, "")

    def get(self, params):
        time = params[1]
        guid = int(param[2] )
        name = base64.b64decode(params[3])
        value = self._testbed.get(time, guid, name)
        result = base64.b64encode(str(value))
        return "%d|%s" % (OK, result)

    def set(self, params):
        time = params[1]
        guid = int(params[2])
        name = base64.b64decode(params[3])
        value = base64.b64decode(params[4])
        type = int(params[3])
        value = set_type(type, value)
        self._testbed.set(time, guid, name, value)
        return "%d|%s" % (OK, "")

    def action(self, params):
        time = params[1]
        guid = int(params[2])
        command = base64.b64decode(params[3])
        self._testbed.action(time, guid, command)
        return "%d|%s" % (OK, "")

    def status(self, params):
        guid = int(params[1])
        status = self._testbed.status(guid)
        result = base64.b64encode(str(status))
        return "%d|%s" % (OK, result)
 
class ExperimentControllerServer(server.Server):
    def __init__(self, root_dir, experiment_xml):
        super(ExperimentControllerServer, self).__init__(root_dir)
        self._experiment_xml = experiment_xml
        self._controller = None

    def post_daemonize(self):
        from nepi.core.execute import ExperimentController
        self._controller = ExperimentController(self._experiment_xml)

    def reply_action(self, msg):
        params = msg.split("|")
        instruction = int(params[0])
        log_msg(self, params)
        try:
            if instruction == XML:
                reply = self.experiment_xml(params)
            elif instruction == ACCESS:
                reply = self.set_access_configuration(params)
            elif instruction == TRACE:
                reply = self.trace(params)
            elif instruction == FINISHED:
                reply = self.is_finished(params)
            elif instruction == START:
                reply = self.start(params)
            elif instruction == STOP:
                reply = self.stop(params)
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

    def set_access_configuration(self, params):
        testbed_guid = int(params[1])
        mode = params[2]
        communication = params[3]
        host = params[4]
        user = params[5]
        port = int(params[6])
        root_dir = params[7]
        use_agent = params[8] == "True"
        access_config = AccessConfiguration()
        access_config.set_attribute_value("mode", mode)
        access_config.set_attribute_value("communication", communication)
        access_config.set_attribute_value("host", host)
        access_config.set_attribute_value("user", user)
        access_config.set_attribute_value("port", port)
        access_config.set_attribute_value("rootDirectory", root_dir)
        access_config.set_attribute_value("useAgent", use_agent)
        self._controller.set_access_configuration(testbed_guid, 
                access_config)
        return "%d|%s" % (OK, "")

    def trace(self, params):
        testbed_guid = int(params[1])
        guid = int(params[2])
        trace_id = params[3]
        trace = self._controller.trace(testbed_guid, guid, trace_id)
        result = base64.b64encode(trace)
        return "%d|%s" % (OK, result)

    def is_finished(self, params):
        guid = int(params[1])
        status = self._controller.is_finished(guid)
        result = base64.b64encode(str(status))
        return "%d|%s" % (OK, result)

    def start(self, params):
        self._controller.start()
        return "%d|%s" % (OK, "")

    def stop(self, params):
        self._controller.stop()
        return "%d|%s" % (OK, "")

    def shutdown(self, params):
        self._controller.shutdown()
        return "%d|%s" % (OK, "")

class TestbedIntanceProxy(object):
    def __init__(self, root_dir, log_level, testbed_id = None, 
            testbed_version = None, launch = True):
        if launch:
            if testbed_id == None or testbed_version == None:
                raise RuntimeError("To launch a TesbedInstance server a \
                        testbed_id and testbed_version are required")
            # launch daemon
            s = TestbedInstanceServer(root_dir, testbed_id, testbed_version)
            if log_level == AccessConfiguration.DEBUG_LEVEL:
                s.set_debug_log_level()
            s.run()
        # create_client
        self._client = server.Client(root_dir)

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
        return map(int, text.split(","))

    def configure(self, name, value):
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

    def create(self, guid, factory_id):
        msg = testbed_messages[CREATE]
        msg = msg % (guid, factory_id)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def create_set(self, guid, name, value):
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

    def factory_set(self, guid, name, value):
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

    def connect(self, guid1, connector_type_name1, guid2, 
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

    def cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name):
        msg = testbed_messages[CROSS_CONNECT]
        msg = msg % (guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def add_trace(self, guid, trace_id):
        msg = testbed_messages[ADD_TRACE]
        msg = msg % (guid, trace_id)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def add_address(self, guid, family, address, netprefix, broadcast): 
        msg = testbed_messages[ADD_ADDRESS]
        msg = msg % (guid, family, address, netprefix, broadcast)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def add_route(self, guid, destination, netprefix, nexthop):
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

    def do_connect(self):
        msg = testbed_messages[DO_CONNECT]
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

    def do_cross_connect(self):
        msg = testbed_messages[DO_CROSS_CONNECT]
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def start(self, time = TIME_NOW):
        msg = testbed_messages[START]
        msg = msg % (time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def stop(self, time = TIME_NOW):
        msg = testbed_messages[STOP]
        msg = msg % (time)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def set(self, time, guid, name, value):
        msg = testbed_messages[SET]
        type = get_type(value)
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(str(value))
        msg = msg % (time, guid, name, value, type)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def get(self, time, guid, name):
        msg = testbed_messages[GET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        msg = msg % (time, guid, name)
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

    def status(self, guid):
        msg = testbed_messages[STATUS]
        msg = msg % (guid)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return int(text)

    def trace(self, guid, trace_id):
        msg = testbed_messages[TRACE]
        msg = msg % (guid, trace_id)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text = base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)
        return text

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

class ExperimentControllerProxy(object):
    def __init__(self, root_dir, log_level, experiment_xml = None, launch = True):
        if launch:
            if experiment_xml == None:
                raise RuntimeError("To launch a ExperimentControllerServer a \
                        xml description of the experiment is required")
            # launch daemon
            s = ExperimentControllerServer(root_dir, experiment_xml)
            if log_level == AccessConfiguration.DEBUG_LEVEL:
                s.set_debug_log_level()
            s.run()
        # create_client
        self._client = server.Client(root_dir)

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

    def set_access_configuration(self, testbed_guid, access_config):
        mode = access_config.get_attribute_value("mode")
        communication = access_config.get_attribute_value("communication")
        host = access_config.get_attribute_value("host")
        user = access_config.get_attribute_value("user")
        port = access_config.get_attribute_value("port")
        root_dir = access_config.get_attribute_value("rootDirectory")
        use_agent = access_config.get_attribute_value("useAgent")
        msg = controller_messages[ACCESS]
        msg = msg % (testbed_guid, mode, communication, host, user, port, 
                root_dir, use_agent)
        self._client.send_msg(msg)
        reply = self._client.read_reply()
        result = reply.split("|")
        code = int(result[0])
        text =  base64.b64decode(result[1])
        if code == ERROR:
            raise RuntimeError(text)

    def trace(self, testbed_guid, guid, trace_id):
        msg = controller_messages[TRACE]
        msg = msg % (testbed_guid, guid, trace_id)
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

