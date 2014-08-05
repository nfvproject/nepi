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

iface1 = ec.register_resource("OMFWifiInterface")
ec.set(iface1, 'name', 'wlan0')
ec.set(iface1, 'mode', "adhoc")
ec.set(iface1, 'hw_mode', "g")
ec.set(iface1, 'essid', "ping")
ec.set(iface1, 'ip', "192.168.0.12/24")

node2 = ec.register_resource("OMFNode")
ec.set(node2, 'hostname', 'wlab49')
ec.set(node2, 'xmppServer', "xmpp-plexus.onelab.eu")
ec.set(node2, 'xmppUser', "nepi")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")

iface2 = ec.register_resource("OMFWifiInterface")
ec.set(iface2, 'name', 'wlan0')
ec.set(iface2, 'mode', "adhoc")
ec.set(iface2, 'hw_mode', "g")
ec.set(iface2, 'essid', "ping")
ec.set(iface2, 'ip', "192.168.0.49/24")

chan = ec.register_resource("OMFChannel")
ec.set(chan, 'channel', "6")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'command', '/bin/ping -c5 192.168.0.49')
ec.set(app1, 'env', "")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'command', '/bin/ping -c5 192.168.0.12')
ec.set(app2, 'env', "")


# Connection
ec.register_connection(iface1, node1)
ec.register_connection(iface2, node2)
ec.register_connection(iface1, chan)
ec.register_connection(iface2, chan)
ec.register_connection(app1, node1)
ec.register_connection(app2, node2)

ec.register_condition([app2], ResourceAction.START, app1, ResourceState.STARTED , "2s")
ec.register_condition([app1,app2], ResourceAction.STOP, app2, ResourceState.STARTED , "10s")


# Deploy
ec.deploy()

ec.wait_finished([app1,app2])

stdout_1 = ec.trace(app1, "stdout")
stdout_2 = ec.trace(app2, "stdout")

# Choose a directory to store the traces, by default
# It it the folder ehere you run Nepi.
 
f = open("app1.txt", "w")
f.write(stdout_1)
f.close()

g = open("app2.txt", "w")
g.write(stdout_2)
g.close()

# Stop Experiment
ec.shutdown()

