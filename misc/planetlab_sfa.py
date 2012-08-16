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
slicehrn = os.environ["PL_SLICE_HRN"]
plchost = os.environ["PL_HOST"]
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
pl_desc.set_attribute_value("sliceHrn", slicehrn)
pl_desc.set_attribute_value("sfa", True)
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

app = pl_desc.create("Application")
app.set_attribute_value("command", "ping -qc1 173.194.34.51")
app.enable_trace("stdout")
app.connector("node").connect(pl_node.connector("apps"))

xml = exp_desc.to_xml()

controller = ExperimentController(xml, root_dir)
controller.start()
while not controller.is_finished(app.guid):
    time.sleep(0.5)
    
ping_result = controller.trace(app.guid, "stdout")
print ping_result

controller.stop()
controller.shutdown()

