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
                   
     Node                                               Node   
     omf.nitos.node0xx                                  omf.nitos.node0xx
     0--------------------------------------------------0
     |                                                  |
     |                                                  |
     0                                                  0
     VLC Server                                         VLC Client
   
      - Experiment:
        - t0 : Deployment
        - t1 : VLC Server start
        - t2 (t1 + 4s) : VLC Client start
        - t3 (t2 + 22s) : Client and Server Stop
        - t4 (t3 + 3s): Kill all the applications

"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

# Create the EC
ec = ExperimentController()

# Create and Configure the Nodes
node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'omf.nitos.node025')
ec.set(node1, 'xmppServer', "tribino")
ec.set(node1, 'xmppUser', "nitlab.inf.uth.gr")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")
ec.set(node1, 'version', "5")

node2 = ec.register_resource("OMFNode")
ec.set(node2, 'hostname', "omf.nitos.node028")
ec.set(node2, 'xmppServer', "tribino")
ec.set(node2, 'xmppUser', "nitlab.inf.uth.gr")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")
ec.set(node2, 'version', "5")

# Create and Configure the Interfaces
iface1 = ec.register_resource("OMFWifiInterface")
ec.set(iface1, 'name', "wlan0")
ec.set(iface1, 'mode', "adhoc")
ec.set(iface1, 'hw_mode', "g")
ec.set(iface1, 'essid', "vlcexp")
ec.set(iface1, 'ip', "192.168.0.25/24")
ec.set(iface1, 'version', "5")

iface2 = ec.register_resource("OMFWifiInterface")
ec.set(iface2, 'name', "wlan0")
ec.set(iface2, 'mode', "adhoc")
ec.set(iface2, 'hw_mode', 'g')
ec.set(iface2, 'essid', "vlcexp")
ec.set(iface2, 'ip', "192.168.0.28/24")
ec.set(iface2, 'version', "5")

# Create and Configure the Channel
channel = ec.register_resource("OMFChannel")
ec.set(channel, 'channel', "6")
ec.set(channel, 'xmppServer', "tribino")
ec.set(channel, 'xmppUser', "nitlab.inf.uth.gr")
ec.set(channel, 'xmppPort', "5222")
ec.set(channel, 'xmppPassword', "1234")
ec.set(channel, 'version', "5")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'appid', 'Vlc#1')
ec.set(app1, 'command', "/root/vlc/vlc-1.1.13/cvlc /root/10-by-p0d.avi --sout '#rtp{dst=192.168.0.28,port=1234,mux=ts}'")
ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app1, 'version', "5")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'appid', 'Vlc#2')
ec.set(app2, 'command', "/root/vlc/vlc-1.1.13/cvlc rtp://192.168.0.28:1234")
ec.set(app2, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app2, 'version', "5")

app3 = ec.register_resource("OMFApplication")
ec.set(app3, 'appid', 'Kill#2')
ec.set(app3, 'command', "/usr/bin/killall vlc_app")
ec.set(app3, 'env', " ")
ec.set(app3, 'version', "5")

app4 = ec.register_resource("OMFApplication")
ec.set(app4, 'appid', 'Kill#1')
ec.set(app4, 'command', "/usr/bin/killall vlc_app")
ec.set(app4, 'env', " ")
ec.set(app4, 'version', "5")

# Connection
ec.register_connection(app3, node1)
ec.register_connection(app1, node1)
ec.register_connection(node1, iface1)
ec.register_connection(iface1, channel)
ec.register_connection(iface2, channel)
ec.register_connection(node2, iface2)
ec.register_connection(app2, node2)
ec.register_connection(app4, node2)

# User Behaviour
ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "4s")
ec.register_condition([app1, app2], ResourceAction.STOP, app2, ResourceState.STARTED , "22s")
ec.register_condition([app3, app4], ResourceAction.START, app2, ResourceState.STARTED , "25s")
ec.register_condition([app3, app4], ResourceAction.STOP, app3, ResourceState.STARTED , "1s")

# Deploy
ec.deploy()

ec.wait_finished([app1, app2, app3, app4])

# Stop Experiment
ec.shutdown()
