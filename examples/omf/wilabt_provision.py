#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from nepi.execution.ec import ExperimentController
from nepi.execution.resource import ResourceAction, ResourceState

import os

# Create the EC
exp_id = "sfa_test"
ec = ExperimentController(exp_id)

slicename = 'ple.inria.lguevgeo'
sfauser = os.environ.get('SFA_USER')
sfaPrivateKey = os.environ.get('SFA_PK')

# nodes
node1 = ec.register_resource("WilabtSfaNode")
ec.set(node1, "host", 'zotacE5')
ec.set(node1, "slicename", slicename)
ec.set(node1, "sfauser", sfauser)
ec.set(node1, "sfaPrivateKey", sfaPrivateKey)
ec.set(node1, "gatewayUser", "nepi")
ec.set(node1, "gateway", "bastion.test.iminds.be")
ec.set(node1, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node1, 'xmppUser', "nepi")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")

node2 = ec.register_resource("WilabtSfaNode")
ec.set(node2, "host", 'zotacM20')
ec.set(node2, "slicename", slicename)
ec.set(node2, "sfauser", sfauser)
ec.set(node2, "sfaPrivateKey", sfaPrivateKey)
ec.set(node2, "gatewayUser", "nepi")
ec.set(node2, "gateway", "bastion.test.iminds.be")
ec.set(node2, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node2, 'xmppUser', "nepi")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")

node3 = ec.register_resource("WilabtSfaNode")
ec.set(node3, "host", 'zotacG1')
ec.set(node3, "slicename", slicename)
ec.set(node3, "sfauser", sfauser)
ec.set(node3, "sfaPrivateKey", sfaPrivateKey)
ec.set(node3, "gatewayUser", "nepi")
ec.set(node3, "gateway", "bastion.test.iminds.be")
ec.set(node3, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node3, 'xmppUser', "nepi")
ec.set(node3, 'xmppPort', "5222")
ec.set(node3, 'xmppPassword', "1234")


# Deploy
ec.deploy()

ec.wait_deployed([node1, node2, node3])

ec.shutdown()

# End
