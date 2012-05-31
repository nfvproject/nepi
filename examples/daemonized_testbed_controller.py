#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Experiment Topology:
#
#  n1 --- n2
#  0.1   0.2 
#    

from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import getpass
import tempfile
import time
import os

user = getpass.getuser()
root_dir = tempfile.mkdtemp()
netns_dir = os.path.join(root_dir, "netns")
daemon_dir = os.path.join(netns_dir, "daemon")
os.makedirs(daemon_dir)


exp_desc = ExperimentDescription()

netns_provider = FactoriesProvider("netns")
netns_desc = exp_desc.add_testbed_description(netns_provider)
netns_desc.set_attribute_value("homeDirectory", netns_dir)
#netns_desc.set_attribute_value("enableDebug", True)
netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, daemon_dir)
netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
netns_desc.set_attribute_value(DC.USE_SUDO, True)

node1 = netns_desc.create("Node")
node2 = netns_desc.create("Node")

iface12 = netns_desc.create("P2PNodeInterface")
iface12.set_attribute_value("up", True)
node1.connector("devs").connect(iface12.connector("node"))

iface21 = netns_desc.create("P2PNodeInterface")
iface21.set_attribute_value("up", True)
node2.connector("devs").connect(iface21.connector("node"))

iface12.connector("p2p").connect(iface21.connector("p2p"))

ip12 = iface12.add_address()
ip12.set_attribute_value("Address", "192.168.0.1")
ip12.set_attribute_value("NetPrefix", 30)

ip21 = iface21.add_address()
ip21.set_attribute_value("Address", "192.168.0.2")
ip21.set_attribute_value("NetPrefix", 30)

app1 = netns_desc.create("Application")
app1.set_attribute_value("command", "ping -qc 10 192.168.0.1")
app1.set_attribute_value("user", user)
app1.connector("node").connect(node1.connector("apps"))

app1.enable_trace("stdout")

xml = exp_desc.to_xml()

controller_access_config = proxy.AccessConfiguration()
controller_access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
controller_access_config.set_attribute_value(DC.ROOT_DIRECTORY, root_dir)
controller_access_config.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)

controller = proxy.create_experiment_controller(xml, controller_access_config)

controller.start()
while not controller.is_finished(app1.guid):
    time.sleep(0.5)

result = controller.trace(app1.guid, "stdout")

controller.stop()
controller.shutdown()

print result

