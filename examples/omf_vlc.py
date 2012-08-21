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

root_dir = tempfile.mkdtemp()

exp_desc = ExperimentDescription()

testbed_id = "omf"
omf_provider = FactoriesProvider(testbed_id)
omf_desc = exp_desc.add_testbed_description(omf_provider)
omf_desc.set_attribute_value("homeDirectory", root_dir)
omf_desc.set_attribute_value("enableDebug", True)
omf_desc.set_attribute_value("xmppSlice", "default_slice")
omf_desc.set_attribute_value("xmppHost", "xmpp-omf.onelab.eu")
omf_desc.set_attribute_value("xmppPort", 5222)
omf_desc.set_attribute_value("xmppPassword", "1234")

node1 = omf_desc.create("Node")
node1.set_attribute_value("hostname", "omf.my.wlab18")
node2 = omf_desc.create("Node")
node2.set_attribute_value("hostname", "omf.my.wlab49")

iface12 = omf_desc.create("WifiInterface")
iface12.set_attribute_value("mode", "adhoc")
iface12.set_attribute_value("channel", "6")
iface12.set_attribute_value("type", "g")
iface12.set_attribute_value("essid", "cvlcmode")
iface12.set_attribute_value("ip", "192.168.0.18")
node1.connector("devs").connect(iface12.connector("node"))

iface21 = omf_desc.create("WifiInterface")
iface21.set_attribute_value("mode", "adhoc")
iface21.set_attribute_value("channel", "6")
iface21.set_attribute_value("type", "g")
iface21.set_attribute_value("essid", "cvlcmode")
iface21.set_attribute_value("ip", "192.168.0.49")
node2.connector("devs").connect(iface21.connector("node"))

channel = omf_desc.create("Channel")
channel.set_attribute_value("mode", "adhoc")
channel.set_attribute_value("channel", "6")
channel.set_attribute_value("type", "g")
channel.set_attribute_value("essid", "cvlcmode")
channel.connector("devs").connect(iface12.connector("chan"))
channel.connector("devs").connect(iface21.connector("chan"))

app2 = omf_desc.create("OmfApplication")
app2.set_attribute_value("appId", "Vlc#2")
app2.set_attribute_value("arguments", "rtp://239.255.0.1:1234")
app2.set_attribute_value("path", "/opt/vlc-1.1.13/vlc")
app2.connector("node").connect(node2.connector("apps"))

app1 = omf_desc.create("OmfApplication")
app1.set_attribute_value("appId", "Vlc#1")
app1.set_attribute_value("arguments", "/opt/10-by-p0d.avi --sout '#duplicate{dst=display,dst=rtp{mux=ts,dst=239.255.0.1,port=1234}}'")
app1.set_attribute_value("path", "/opt/vlc-1.1.13/vlc")
app1.connector("node").connect(node1.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
#while not (controller.is_finished(app1.guid) and \
#        controller.is_finished(app2.guid)):
#    time.sleep(0.5)

time.sleep(20)

controller.set(iface21.guid, "channel", "1")

time.sleep(15)

controller.stop()
controller.shutdown()

