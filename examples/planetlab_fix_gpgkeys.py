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

def add_node(pl_desc, pl_inet, hostname):
    pl_node = pl_desc.create("Node")
    pl_node.set_attribute_value("hostname", hostname)
    pl_iface = pl_desc.create("NodeInterface")
    pl_iface.connector("inet").connect(pl_inet.connector("devs"))
    pl_node.connector("devs").connect(pl_iface.connector("node"))

    return pl_node

def add_app(pl_desc, pl_node):
    pl_app = pl_desc.create("Application")
    pl_app.set_attribute_value("command", "yum reinstall -y --nogpgcheck fedora-release")
    pl_app.set_attribute_value("sudo", True)
    pl_app.enable_trace("stderr")
    pl_app.enable_trace("stdout")
    pl_app.connector("node").connect(pl_node.connector("apps"))
    
    return pl_app

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
pl_desc.set_attribute_value("cleanProc", True)
pl_desc.set_attribute_value("plLogLevel", "DEBUG")
       
pl_inet = pl_desc.create("Internet")

hostnames = ["ait21.us.es", "planetlab4.cslab.ece.ntua.gr", "kostis.di.uoa.gr", "pl1.uni-rostock.de" ]
apps = []

for hostname in hostnames:
    pl_node = add_node(pl_desc, pl_inet, hostname)
    pl_app = add_app(pl_desc, pl_node)
    apps.append(pl_app)

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()

stop = False

while not stop:
    time.sleep(0.5)

    stop = True
    for pl_app in set(apps):
        if not controller.is_finished(pl_app.guid):
            stop = False
            break
        else:
            apps.remove(pl_app)

controller.stop()
controller.shutdown()
