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
import logging
import tempfile
import time

logging.basicConfig(level=logging.DEBUG)

root_dir = tempfile.mkdtemp()

exp_desc = ExperimentDescription()

testbed_id = "omf"
omf_provider = FactoriesProvider(testbed_id)
omf_desc = exp_desc.add_testbed_description(omf_provider)
omf_desc.set_attribute_value("homeDirectory", root_dir)
omf_desc.set_attribute_value("enableDebug", True)
omf_desc.set_attribute_value("xmppSlice", "default_slice")
omf_desc.set_attribute_value("xmppHost", "xmpp-plexus.onelab.eu")
omf_desc.set_attribute_value("xmppPort", 5222)
omf_desc.set_attribute_value("xmppPassword", "1234")

# Add node1
node1 = omf_desc.create("Node")
node1.set_attribute_value("hostname", "omf.plexus.wlab17")

# Add configuration for interface 1
iface1 = omf_desc.create("WifiInterface")
iface1.set_attribute_value("alias", "w0")
iface1.set_attribute_value("mode", "adhoc")
iface1.set_attribute_value("channel", "6")
iface1.set_attribute_value("type", "g")
iface1.set_attribute_value("essid", "cvlcmode")
iface1.set_attribute_value("ip", "192.168.0.17")
node1.connector("devs").connect(iface1.connector("node"))

# Add multicast route to node 1
route1 = node1.add_route()
route1.set_attribute_value("Destination", "224.0.0.0")
route1.set_attribute_value("NetPrefix", 4)
route1.set_attribute_value("Device", "wlan0")

# Add node2
node2 = omf_desc.create("Node")
node2.set_attribute_value("hostname", "omf.plexus.wlab37")

# Add configuration for interface 2
iface2 = omf_desc.create("WifiInterface")
iface2.set_attribute_value("alias", "w0")
iface2.set_attribute_value("mode", "adhoc")
iface2.set_attribute_value("channel", "6")
iface2.set_attribute_value("type", "g")
iface2.set_attribute_value("essid", "cvlcmode")
iface2.set_attribute_value("ip", "192.168.0.37")
node2.connector("devs").connect(iface2.connector("node"))

# Add multicast route to node 2
route2 = node2.add_route()
route2.set_attribute_value("Destination", "224.0.0.0")
route2.set_attribute_value("NetPrefix", 4)
route2.set_attribute_value("Device", "wlan0")

# Add a channel... this could be ommited
channel = omf_desc.create("Channel")
channel.set_attribute_value("mode", "adhoc")
channel.set_attribute_value("channel", "6")
channel.set_attribute_value("type", "g")
channel.set_attribute_value("essid", "cvlcmode")
channel.connector("devs").connect(iface1.connector("chan"))
channel.connector("devs").connect(iface2.connector("chan"))

# Add a vlc server to stream a video using multicast
app1 = omf_desc.create("OmfApplication")
app1.set_attribute_value("appId", "Vlc#1")
app1.set_attribute_value("arguments", "/opt/bbb_240p_mpeg4_lq.ts --sout '#rtp{dst=239.255.0.1,port=1234,mux=ts}' vlc://quit")
app1.set_attribute_value("path", "/opt/vlc-1.1.13/cvlc")
app1.set_attribute_value("env", "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
app1.connector("node").connect(node1.connector("apps"))

# Add a vlc client to receive the video stream
app2 = omf_desc.create("OmfApplication")
app2.set_attribute_value("appId", "Vlc#2")
app2.set_attribute_value("arguments", "rtp://239.255.0.1:1234")
app2.set_attribute_value("path", "/opt/vlc-1.1.13/cvlc")
# To see the stream to a ssh -X connection, the DISPLAY variable must be set to the value of the node.
# Also don't forget to execute in 'xhost + localhost' in the node
app2.set_attribute_value("env", "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
app2.connector("node").connect(node2.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
#while not (controller.is_finished(app1.guid) and \
#        controller.is_finished(app2.guid)):
#    time.sleep(0.5)

time.sleep(30)

controller.set(iface2.guid, "channel", "1")

time.sleep(15)

controller.stop()
controller.shutdown()

