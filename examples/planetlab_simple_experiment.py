#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
from nepi.util.constants import DeploymentConfiguration as DC
import os
import shutil
import tempfile
import time

root_dir = tempfile.mkdtemp()
user = getpass.getuser()
slicename = os.environ["PL_SLICE"]
plchost = "www.planet-lab.eu"
port_base = 2000 + (os.getpid() % 1000) * 13
pl_ssh_key = os.environ.get(
    "PL_SSH_KEY",
    "%s/.ssh/id_rsa_planetlab" % (os.environ['HOME'],) )
pl_user = os.environ.get('PL_USER')
pl_pwd = os.environ.get('PL_PASS')

exp_desc = ExperimentDescription()

pl_provider = FactoriesProvider("planetlab")
pl_desc = exp_desc.add_testbed_description(pl_provider)
pl_desc.set_attribute_value("homeDirectory", root_dir)
pl_desc.set_attribute_value("slice", slicename)
pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
pl_desc.set_attribute_value("authUser", pl_user)
pl_desc.set_attribute_value("authPass", pl_pwd)
pl_desc.set_attribute_value("plcHost", plchost)
pl_desc.set_attribute_value("tapPortBase", port_base)
pl_desc.set_attribute_value("p2pDeployment", False) # it's interactive, we don't want it in tests
pl_desc.set_attribute_value("dedicatedSlice", True)
pl_desc.set_attribute_value("plLogLevel", "DEBUG")
       
pl_inet = pl_desc.create("Internet")

pl_node1 = pl_desc.create("Node")
pl_iface1 = pl_desc.create("NodeInterface")
pl_iface1.set_attribute_value("label", "iface1")
pl_iface1.connector("inet").connect(pl_inet.connector("devs"))
pl_node1.connector("devs").connect(pl_iface1.connector("node"))

pl_node2 = pl_desc.create("Node")
pl_iface2 = pl_desc.create("NodeInterface")
pl_iface2.set_attribute_value("label", "iface2")
pl_iface2.connector("inet").connect(pl_inet.connector("devs"))
pl_node2.connector("devs").connect(pl_iface2.connector("node"))

pl_app1 = pl_desc.create("Application")
pl_app1.set_attribute_value("command", "ping -qc3 {#[iface2].addr[0].[Address]#}")
pl_app1.enable_trace("stdout")
pl_app1.connector("node").connect(pl_node1.connector("apps"))

pl_app2 = pl_desc.create("Application")
pl_app2.set_attribute_value("command", "ping -qc3 {#[iface1].addr[0].[Address]#}")
pl_app2.enable_trace("stdout")
pl_app2.connector("node").connect(pl_node2.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
while (not controller.is_finished(pl_app1.guid) or not controller.is_finished(pl_app1.guid)):
    time.sleep(0.5)

ping_result1 = controller.trace(pl_app1.guid, "stdout")
print ping_result1
ping_result2 = controller.trace(pl_app2.guid, "stdout")
print ping_result2

controller.stop()
controller.shutdown()

