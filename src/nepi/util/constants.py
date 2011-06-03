#!/usr/bin/env python
# -*- coding: utf-8 -*-

AF_INET = 0
AF_INET6 = 1

STATUS_NOT_STARTED = 0
STATUS_RUNNING = 1
STATUS_FINISHED = 2
STATUS_UNDETERMINED = 3

TESTBED_STATUS_ZERO = 0
TESTBED_STATUS_SETUP = 1
TESTBED_STATUS_CREATED = 2
TESTBED_STATUS_CONNECTED = 3
TESTBED_STATUS_CROSS_CONNECTED = 4
TESTBED_STATUS_CONFIGURED = 5
TESTBED_STATUS_STARTED = 6
TESTBED_STATUS_STOPPED = 7

TIME_NOW = "0s"


ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP = "_nepi_testbed_environment_setup"


class DeploymentConfiguration:
    MODE_SINGLE_PROCESS = "SINGLE"
    MODE_DAEMON = "DAEMON"
    ACCESS_SSH = "SSH"
    ACCESS_LOCAL = "LOCAL"
    ERROR_LEVEL = "Error"
    DEBUG_LEVEL = "Debug"
    
    DEPLOYMENT_MODE = "deployment_mode"
    DEPLOYMENT_COMMUNICATION = "deployment_communication"

    DEPLOYMENT_HOST = "deployment_host"
    DEPLOYMENT_USER = "deployment_user"
    DEPLOYMENT_PORT = "deployment_port"
    DEPLOYMENT_KEY  = "deployment_key"
    
    DEPLOYMENT_ENVIRONMENT_SETUP = "deployment_environment_setup"
    
    ROOT_DIRECTORY = "rootDirectory"
    USE_AGENT = "useAgent"
    LOG_LEVEL = "logLevel"
    RECOVER = "recover"

