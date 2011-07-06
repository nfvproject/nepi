#!/usr/bin/env python
# -*- coding: utf-8 -*-

AF_INET = 0
AF_INET6 = 1

TIME_NOW = "0s"

CONNECTION_DELAY = 0

ATTR_NEPI_TESTBED_ENVIRONMENT_SETUP = "_nepi_testbed_environment_setup"

class AttributeCategories:
    CATEGORY_DEPLOYMENT = "Deployment"
   
class FactoryCategories:
    CATEGORY_APPLICATIONS = "Applications"
    CATEGORY_CHANNELS = "Channels"
    CATEGORY_DEVICES = "Devices"
    CATEGORY_DELAY_MODELS = "Delay models"
    CATEGORY_ENERGY_MODELS = "Energy models"
    CATEGORY_ERROR_MODELS = "Error models"
    CATEGORY_MAC_MODELS = "Mac models"
    CATEGORY_MANAGERS = "Managers"
    CATEGORY_MOBILITY_MODELS = "Mobility models"
    CATEGORY_NODES = "Nodes"
    CATEGORY_LOSS_MODELS = "Loss models"
    CATEGORY_PHY_MODELS = "Phy models"
    CATEGORY_PROTOCOLS = "Protocols"
    CATEGORY_ROUTING = "Routing"
    CATEGORY_QUEUES = "Queues"
    CATEGORY_SERVICE_FLOWS = "Service Flows"
    CATEGORY_TUNNELS = "Tunnels"

class ApplicationStatus:
    STATUS_NOT_STARTED = 0
    STATUS_RUNNING = 1
    STATUS_FINISHED = 2
    STATUS_UNDETERMINED = 3

class TestbedStatus:
    STATUS_ZERO = 0
    STATUS_SETUP = 1
    STATUS_CREATED = 2
    STATUS_CONNECTED = 3
    STATUS_CROSS_CONNECTED = 4
    STATUS_CONFIGURED = 5
    STATUS_STARTED = 6
    STATUS_STOPPED = 7

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

