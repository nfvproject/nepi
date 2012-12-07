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

def add_dependency(pl_desc, pl_node):
    pl_dep = pl_desc.create("Dependency")
    pl_dep.set_attribute_value("depends", "gcc vim emacs")
    pl_dep.connector("node").connect(pl_node.connector("deps"))
    
    return pl_dep

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
deps = []

for hostname in hostnames:
    pl_node = add_node(pl_desc, pl_inet, hostname)
    pl_dep = add_dependency(pl_desc, pl_node)
    deps.append(pl_dep)

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()

stop = False

while not stop:
    stop = True
    for pl_dep in set(deps):
        if not controller.is_finished(pl_dep.guid):
            stop = False
            break
        else:
            deps.remove(pl_dep)

    time.sleep(0.5)

controller.stop()
controller.shutdown()

