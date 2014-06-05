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

    Example :
      - Testbed : Nitos
      - Explanation :

       VLC Streaming on VLC
                   
     Node
     omf.nitos.node0xx 
     0
     |
     |
     0
     xEyes
   
      - Experiment:
        - t0 : Deployment
        - t1 : xEeyes Start
        - t2 (t1 + 10s) : xEyes stop
        - t3 (t2 + 2s) : Kill the application
"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

# Create the EC
ec = ExperimentController()

# Create and Configure the Nodes
node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'omf.nitos.node0XX')
ec.set(node1, 'xmppServer', "ZZZ")
ec.set(node1, 'xmppUser', "nitlab.inf.uth.gr")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")
ec.set(node1, 'version', "5")

# Create and Configure the Interfaces
iface1 = ec.register_resource("OMFWifiInterface")
ec.set(iface1, 'name', "wlan0")
ec.set(iface1, 'mode', "adhoc")
ec.set(iface1, 'hw_mode', "g")
ec.set(iface1, 'essid', "xeyes")
ec.set(iface1, 'ip', "192.168.0.XX/24")
ec.set(iface1, 'version', "5")

# Create and Configure the Channel
channel = ec.register_resource("OMFChannel")
ec.set(channel, 'channel', "6")
ec.set(channel, 'xmppServer', "ZZZ")
ec.set(channel, 'xmppUser', "nitlab.inf.uth.gr")
ec.set(channel, 'xmppPort', "5222")
ec.set(channel, 'xmppPassword', "1234")
ec.set(channel, 'version', "5")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'appid', 'XEyes#1')
ec.set(app1, 'command', "/usr/bin/xeyes")
ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app1, 'version', "5")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'appid', 'Kill#1')
ec.set(app2, 'path', "/usr/bin/kill")
ec.set(app2, 'args', "xeyes")
ec.set(app2, 'env', " ")
ec.set(app2, 'version', "5")

# Connection
ec.register_connection(app2, node1)
ec.register_connection(app1, node1)
ec.register_connection(node1, iface1)
ec.register_connection(iface1, channel)

# User Behaviour
ec.register_condition(app1, ResourceAction.STOP, app1, ResourceState.STARTED , "10s")
ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "12s")
ec.register_condition(app2, ResourceAction.STOP, app2, ResourceState.STARTED , "1s")

# Deploy
ec.deploy()

ec.wait_finished([app1, app2])

# Stop Experiment
ec.shutdown()
