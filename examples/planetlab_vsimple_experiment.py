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
print "experiment description class inicializada"

pl_provider = FactoriesProvider("planetlab")
print "factories provider class inicializada con planetlab"

pl_desc = exp_desc.add_testbed_description(pl_provider)
print "add testbed description"
pl_desc.set_attribute_value("homeDirectory", root_dir)
print "set attr home dir"
pl_desc.set_attribute_value("slice", slicename)
print "set attr slicename"
pl_desc.set_attribute_value("sliceSSHKey", pl_ssh_key)
print "set attr sshkey"
pl_desc.set_attribute_value("authUser", pl_user)
print "set attr user"
pl_desc.set_attribute_value("authPass", pl_pwd)
print "set attr pass"
pl_desc.set_attribute_value("plcHost", plchost)
print "set attr plchost"
pl_desc.set_attribute_value("tapPortBase", port_base)
print "set attr tap port"
pl_desc.set_attribute_value("p2pDeployment", False) # it's interactive, we don't want it in tests
print "set attr p2p deployment en false"
pl_desc.set_attribute_value("cleanProc", True)
print "set attr clean proc en true"
pl_desc.set_attribute_value("plLogLevel", "DEBUG")
print "set attr log level en debug"
       
pl_inet = pl_desc.create("Internet")

print "crea desde el testbed descritpion internet"

pl_node1 = pl_desc.create("Node")

print "crea nodo"
pl_iface1 = pl_desc.create("NodeInterface")
print "crea interface"
pl_iface1.set_attribute_value("label", "iface1")
print "set attr de label para la interface"
pl_iface1.connector("inet").connect(pl_inet.connector("devs"))
print "conecta iface con internet con iface"
pl_node1.connector("devs").connect(pl_iface1.connector("node"))
print "conecta nodo con iface"

xml = exp_desc.to_xml()
print "crea el xml desde el exp description"

controller = ExperimentController(xml, root_dir)
print "inicializa el controller del experimento con el dir y el xml"
controller.start()
print "start del controller"

print "sleep 0 segundos"
time.sleep(5)
print "sleep 5 segundos"

controller.stop()
print "stop del controller"

controller.shutdown()
print "shutdown del controller"


