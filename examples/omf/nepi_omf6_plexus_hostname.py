"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Author: Alina Quereilhac <alina.quereilhac@inria.fr>
            Julien Tribino <julien.tribino@inria.fr>


"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

# Create the EC
ec = ExperimentController()

# Create and Configure the Nodes

node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'wlab12')
ec.set(node1, 'xmppServer', "xmpp-plexus.onelab.eu")
ec.set(node1, 'xmppUser', "nepi")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'command', '/bin/hostname -f')
ec.set(app1, 'env', "")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'command', '/bin/date')
ec.set(app2, 'env', "")

app3 = ec.register_resource("OMFApplication")
ec.set(app3, 'command', '/bin/hostname -f')
ec.set(app3, 'env', "")

# Connection
ec.register_connection(app1, node1)
ec.register_connection(app2, node1)
ec.register_connection(app3, node1)

ec.register_condition([app2,app3], ResourceAction.START, app1, ResourceState.STARTED , "3s")
ec.register_condition([app1,app2,app3], ResourceAction.STOP, app2, ResourceState.STARTED , "5s")


# Deploy
ec.deploy()

ec.wait_finished([app1,app2,app3])

# Stop Experiment
ec.shutdown()

