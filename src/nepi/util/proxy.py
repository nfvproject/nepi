#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import server
from nepi.util import validation
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
    CONFIGURE: "%d|%s" % (CONFIGURE, "%s|%s"),
    CREATE: "%d|%s" % (CREATE, "%d|%s"),
    CREATE_SET: "%d|%s" % (CREATE_SET, "%d|%s|%s"),
    FACTORY_SET: "%d|%s" % (FACTORY_SET, "%d|%s|%s"),
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
    SET:    "%d|%s" % (SET, "%s|%d|%s|%s"),
    ACTION: "%d|%s" % (ACTION, "%s|%d|%s"),
    STATUS: "%d|%s" % (STATUS, "%d"),
    })

class AccessConfiguration(AttributesMap):
    MODE_SINGLE_PROCESS = "SINGLE"
    MODE_DAEMON = "DAEMON"
    ACCESS_SSH = "SSH"
    ACCESS_LOCAL = "LOCAL"

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
                help = "Host where the instance will be executed",
                type = Attribute.STRING,
                value = "localhost",
                validation_function = validation.is_string)
        self.add_attribute(name = "user",
                help = "User on the Host to execute the instance",
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

def create_controller(xml, access_config = None):
    mode = None if not access_config else access_config.get_attribute_value("mode")
    if not mode or mode == AccessConfiguration.MODE_SINGLE_PROCESS:
        from nepi.core.execute import ExperimentController
        return ExperimentController(xml)
    elif mode ==AccessConfiguration.MODE_DAEMON:
        root_dir = access_config.get_attribute_value("rootDirectory")
        return ExperimentControllerProxy(xml, root_dir)
    raise RuntimeError("Unsupported access configuration 'mode'" % mode)

def create_testbed_instance(testbed_id, testbed_version, access_config):
    mode = None if not access_config else access_config.get_attribute_value("mode")
    if not mode or mode == AccessConfiguration.MODE_SINGLE_PROCESS:
        return  _build_testbed_instance(testbed_id, testbed_version)
    elif mode == AccessConfiguration.MODE_DAEMON:
                root_dir = access_config.get_attribute_value("rootDirectory")
                return TestbedIntanceProxy(testbed_id, testbed_version, root_dir)
    raise RuntimeError("Unsupported access configuration 'mode'" % mode)

def _build_testbed_instance(testbed_id, testbed_version):
    mod_name = "nepi.testbeds.%s" % (testbed_id.lower())
    if not mod_name in sys.modules:
        __import__(mod_name)
    module = sys.modules[mod_name]
    return module.TestbedInstance(testbed_version)

class TestbedInstanceServer(server.Server):
    def __init__(self, testbed_id, testbed_version, root_dir):
        super(TestbedInstanceServer, self).__init__(root_dir)
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version
        self._instance = None

    def post_daemonize(self):
        self._instance = _build_testbed_instance(self._testbed_id, 
                self._testbed_version)

    def reply_action(self, msg):
        return "Reply to: %s" % msg
        """
        testbed_messages = dict({
            TRACE:  "%s|%s" % (TRACE, "%d|%s"),
            START:  "%s|%s" % (START, "%s"),
            STOP:    "%s|%s" % (STOP, "%s"),
            SHUTDOWN:   SHUTDOWN,
            CONFIGURE: "%s|%s" % (CONFIGURE, "%s|%s"),
            CREATE: "%s|%s" % (CREATE, "%d|%s"),
            CREATE_SET: "%s|%s" % (CREATE_SET, "%d|%s|%s"),
            FACTORY_SET: "%s|%s" % (FACTORY_SET, "%d|%s|%s"),
            CONNECT: "%s|%s" % (CONNECT, "%d|%s|%d|%s"),
            CROSS_CONNECT: "%s|%s" % (CROSS_CONNECT, "%d|%s|%d|%d|%s|%s"),
            ADD_TRACE: "%s|%s" % (ADD_TRACE, "%d|%s"),
            ADD_ADDRESS: "%s|%s" % (ADD_ADDRESS, "%d|%d|%s|%d|%s"),
            ADD_ROUTE: "%s|%s" % (ADD_ROUTE, "%d|%s|%d|%s"),
            DO_SETUP:   DO_SETUP,
            DO_CREATE:  DO_CREATE,
            DO_CONNECT: DO_CONNECT,
            DO_CONFIGURE:   DO_CONFIGURE,
            DO_CROSS_CONNECT:   DO_CROSS_CONNECT,
            GET:    "%s|%s" % (GET, "%s|%d|%s"),
            SET:    "%s|%s" % (SET, "%s|%d|%s|%s"),
            ACTION: "%s|%s" % (ACTION, "%s|%d|%s"),
            STATUS: "%s|%s" % (STATUS, "%d"),
            })
        """

class ExperimentControllerServer(server.Server):
    def __init__(self, experiment_xml, root_dir):
        super(ExperimentControllerServer, self).__init__(root_dir)
        self._experiment_xml = experiment_xml
        self._controller = None

    def post_daemonize(self):
        from nepi.core.execute import ExperimentController
        self._controller = ExperimentController(self._experiment_xml)

    def reply_action(self, msg):
        params = msg.split("|")
        instruction = int(params[0])
        try:
            if instruction == XML:
                xml = self._controller.experiment_xml
                result = base64.b64encode(xml)
                return "%d|%s" % (OK, result)
            elif instruction == ACCESS:
                testbed_guid = int(params[1])
                mode = params[2]
                communication = params[3]
                host = params[4]
                user = params[5]
                port = int(params[6])
                root_dir = params[7]
                use_agent = bool(params[8])
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
            elif instruction == TRACE:
                testbed_guid = int(params[1])
                guid = int(params[2])
                trace_id = params[3]
                trace = self._controller.trace(testbed_guid, guid, trace_id)
                result = base64.b64encode(trace)
                return "%d|%s" % (OK, "%s" % result)
            elif instruction == FINISHED:
                guid = int(params[1])
                result = self._controller.is_finished(guid)
                return "%d|%s" % (OK, "%r" % result)
            elif instruction == START:
                self._controller.start()
                return "%d|%s" % (OK, "")
            elif instruction == STOP:
                self._controller.stop()
                return "%d|%s" % (OK, "")
            elif instruction == SHUTDOWN:
                self._controller.shutdown()
                return "%d|%s" % (OK, "")
            else:
                error = "Invalid instruction %s" % instruction
                self.log_error(error)
                result = base64.b64encode(error)
                return "%d|%s" % (ERROR, result)
        except:
            error = self.log_error()
            result = base64.b64encode(error)
            return "%d|%s" % (ERROR, result)

class TestbedIntanceProxy(object):
    def __init__(self, testbed_id, testbed_version, root_dir):
        # launch daemon
        s = TestbedInstanceServer(testbed_id, testbed_version, 
                root_dir)
        s.run()
        # create_client
        self._client = server.Client(root_dir)

    def configure(self, name, value):
        msg = testbed_messages[CONFIGURE]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(value)
        msg = msg % (name, value)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def create(self, guid, factory_id):
        msg = testbed_messages[CREATE]
        msg = msg % (guid, factory_id)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def create_set(self, guid, name, value):
        msg = testbed_messages[CREATE_SET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(value)
        msg = msg % (guid, name, value)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def factory_set(self, guid, name, value):
        msg = testbed_messages[FACTORY_SET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(value)
        msg = msg % (guid, name, value)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        msg = testbed_messages[CONNECT]
        msg = msg % (guid1, connector_type_name1, guid2, 
            connector_type_name2)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def cross_connect(self, guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name):
        msg = testbed_messages[CROSS_CONNECT]
        msg = msg % (guid, connector_type_name, cross_guid, 
            cross_testbed_id, cross_factory_id, cross_connector_type_name)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def add_trace(self, guid, trace_id):
        msg = testbed_messages[ADD_TRACE]
        msg = msg % (guid, trace_id)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def add_address(self, guid, family, address, netprefix, broadcast): 
        msg = testbed_messages[ADD_ADDRESS]
        msg = msg % (guid, family, address, netprefix, broadcast)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def add_route(self, guid, destination, netprefix, nexthop):
        msg = testbed_messages[ADD_ROUTE]
        msg = msg % (guid, destination, netprefix, nexthop)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def do_setup(self):
        msg = testbed_messages[DO_SETUP]
        self._client.send_msg(msg)
        return self._client.read_reply()

    def do_create(self):
        msg = testbed_messages[DO_CREATE]
        self._client.send_msg(msg)
        return self._client.read_reply()

    def do_connect(self):
        msg = testbed_messages[DO_CONNECT]
        self._client.send_msg(msg)
        return self._client.read_reply()

    def do_configure(self):
        msg = testbed_messages[DO_CONFIGURE]
        self._client.send_msg(msg)
        return self._client.read_reply()

    def do_cross_connect(self):
        msg = testbed_messages[DO_CROSS_CONNECT]
        self._client.send_msg(msg)
        return self._client.read_reply()

    def start(self, time):
        msg = testbed_messages[START]
        msg = msg % (time)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def stop(self, time):
        msg = testbed_messages[STOP]
        msg = msg % (time)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def set(self, time, guid, name, value):
        msg = testbed_messages[SET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        value = base64.b64encode(value)
        msg = msg % (time, guid, name, value)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def get(self, time, guid, name):
        msg = testbed_messages[GET]
        # avoid having "|" in this parameters
        name = base64.b64encode(name)
        msg = msg % (time, guid, name)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def action(self, time, guid, action):
        msg = testbed_messages[ACTION]
        msg = msg % (time, guid, action)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def status(self, guid):
        msg = testbed_messages[STATUS]
        msg = msg % (guid)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def trace(self, guid, trace_id):
        msg = testbed_messages[TRACE]
        msg = msg % (guid, trace_id)
        self._client.send_msg(msg)
        return self._client.read_reply()

    def shutdown(self):
        msg = testbed_messages[SHUTDOWN]
        self._client.send_msg(msg)
        return self._client.read_reply()

class ExperimentControllerProxy(object):
    def __init__(self, experiment_xml, root_dir):
        # launch daemon
        s = ExperimentControllerServer(experiment_xml, root_dir)
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
        text =  base64.b64decode(result[1])
        if code == OK:
            return text
        raise RuntimeError(text)

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
        if code == OK:
            return bool(result[1])
        error =  base64.b64decode(result[1])
        raise RuntimeError(error)

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

