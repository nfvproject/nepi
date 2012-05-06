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
netns_root_dir = os.path.join(root_dir, "netns")
os.makedirs(netns_root_dir)
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
pl_desc.set_attribute_value("cleanProc", True)
pl_desc.set_attribute_value("plLogLevel", "DEBUG")
       
pl_inet = pl_desc.create("Internet")

pl_node = pl_desc.create("Node")
pl_iface = pl_desc.create("NodeInterface")
pl_iface.connector("inet").connect(pl_inet.connector("devs"))
pl_node.connector("devs").connect(pl_iface.connector("node"))

pl_tap = pl_desc.create("TunInterface")
pl_tap.enable_trace("pcap")
pl_tap.enable_trace("packets")
pl_node.connector("devs").connect(pl_tap.connector("node"))

ip1 = pl_tap.add_address()
ip1.set_attribute_value("Address", "192.168.3.1")
ip1.set_attribute_value("NetPrefix", 24)

netns_provider = FactoriesProvider("netns")
netns_desc = exp_desc.add_testbed_description(netns_provider)
netns_desc.set_attribute_value("homeDirectory", root_dir)
netns_desc.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
netns_desc.set_attribute_value(DC.ROOT_DIRECTORY, netns_root_dir)
netns_desc.set_attribute_value(DC.LOG_LEVEL, DC.DEBUG_LEVEL)
netns_desc.set_attribute_value(DC.USE_SUDO, True)

netns_node = netns_desc.create("Node")
netns_node.set_attribute_value("forward_X11", True)

netns_tap = netns_desc.create("TunNodeInterface")
netns_tap.set_attribute_value("up", True)
netns_tap.set_attribute_value("mtu", 1448)
netns_node.connector("devs").connect(netns_tap.connector("node"))
netns_tunchannel = netns_desc.create("TunChannel")
netns_tunchannel.connector("->fd").connect(netns_tap.connector("fd->"))

pl_tap.connector("tcp").connect(netns_tunchannel.connector("tcp"))

ip2 = netns_tap.add_address()
ip2.set_attribute_value("Address", "192.168.3.2")
ip2.set_attribute_value("NetPrefix", 30)

app = netns_desc.create("Application")
app.set_attribute_value("command", "xterm")
app.set_attribute_value("user", user)
app.connector("node").connect(netns_node.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
while not controller.is_finished(app.guid):
    time.sleep(0.5)

controller.stop()
controller.shutdown()

