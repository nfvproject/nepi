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
import getpass
import tempfile
import time

user = getpass.getuser()
root_dir = tempfile.mkdtemp()

exp_desc = ExperimentDescription()

testbed_id = "netns"
netns_provider = FactoriesProvider(testbed_id)
netns_desc = exp_desc.add_testbed_description(netns_provider)
netns_desc.set_attribute_value("homeDirectory", root_dir)
#netns_desc.set_attribute_value("enableDebug", True)

node1 = netns_desc.create("Node")
node1.set_attribute_value("forward_X11", True)
node2 = netns_desc.create("Node")
node2.set_attribute_value("forward_X11", True)

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
app1.set_attribute_value("command", "xterm")
app1.set_attribute_value("user", user)
app1.connector("node").connect(node1.connector("apps"))

app2 = netns_desc.create("Application")
app2.set_attribute_value("command", "xterm")
app2.set_attribute_value("user", user)
app2.connector("node").connect(node2.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
while not (controller.is_finished(app1.guid) and \
        controller.is_finished(app2.guid)):
    time.sleep(0.5)

controller.stop()
controller.shutdown()
