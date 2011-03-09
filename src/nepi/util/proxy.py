#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import validation
import sys

class AccessConfiguration(AttributesMap):
    MODE_SINGLE_PROCESS = "SINGLE"
    MODE_DAEMON = "DAEMON"
    ACCESS_SSH = "SSH"
    ACCESS_LOCAL = "LOCAL"

    def __init__(self):
        super(AccessConfiguration, self).__init__()
        self.add_attribute(name = "Mode", 
                help = "Instance execution mode", 
                type = Attribute.ENUM,
                value = AccessConfiguration.MODE_SINGLE_PROCESS,
                allowed = [AccessConfiguration.MODE_DAEMON, 
                    AccessConfiguration.MODE_SINGLE_PROCESS], 
                validation_function = validation.is_enum)
        self.add_attribute(name = "Communication", 
                help = "Instance communication mode", 
                type = Attribute.ENUM,
                value = AccessConfiguration.ACCESS_LOCAL,
                allowed = [AccessConfiguration.ACCESS_LOCAL, 
                    AccessConfiguration.ACCESS_SSH], 
                validation_function = validation.is_enum)
        self.add_attribute(name = "Host", 
                help = "Host where the instance will be executed", 
                type = Attribute.STRING,
                value = "localhost",
                validation_function = validation.is_string)
        self.add_attribute(name = "User", 
                help = "User on the Host to execute the instance", 
                type = Attribute.STRING,
                validation_function = validation.is_string)
        self.add_attribute(name = "Port", 
                help = "Port on the Host", 
                type = Attribute.INTEGER,
                value = 22,
                validation_function = validation.is_integer)
        self.add_attribute(name = "useAgent",
                help = "Use -A option for forwarding of the authentication agent, if ssh access is used", 
                type = Attribute.BOOL,
                value = False,
                validation_function = validation.is_bool)

def create_controller(xml, access_config):
    from nepi.core.execute import ExperimentController
    if not access_config or access_config.get_attribute_value("Mode") \
            == AccessConfiguration.MODE_SINGLE_PROCESS:
       return ExperimentController(xml)
    # TODO!!
    return None

def create_testbed_instance(testbed_id, testbed_version, access_config):
    if not access_config or access_config.get_attribute_value("Mode") \
            == AccessConfiguration.MODE_SINGLE_PROCESS:
        return  _build_testbed_instance(testbed_id, testbed_version)
    # TODO!!
    return None

def _build_testbed_instance(testbed_id, testbed_version):
    mod_name = "nepi.testbeds.%s" % (testbed_id.lower())
    if not mod_name in sys.modules:
        __import__(mod_name)
    module = sys.modules[mod_name]
    return module.TestbedInstance(testbed_version)


