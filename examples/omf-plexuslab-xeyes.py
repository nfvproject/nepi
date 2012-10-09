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

node1 = omf_desc.create("Node")
node1.set_attribute_value("hostname", "omf.plexus.wlab17")

app1 = omf_desc.create("OmfApplication")
app1.set_attribute_value("appId", "xeyes#1")
app1.set_attribute_value("path", "/usr/bin/xeyes")
app1.set_attribute_value("env", "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
app1.connector("node").connect(node1.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()

time.sleep(30)

controller.stop()
controller.shutdown()

