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
# Author: Julien Tribino <julien.tribino@inria.fr>

from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

from nepi.resources.omf.node import OMFNode
from nepi.resources.omf.application import OMFApplication
from nepi.resources.omf.interface import OMFWifiInterface
from nepi.resources.omf.channel import OMFChannel

import logging
import time

logging.basicConfig()

# Create the EC
ec = ExperimentController()

# Create and Configure the Nodes
node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'omf.plexus.wlab17')
ec.set(node1, 'xmppSlice', "nepi")
ec.set(node1, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")
ec.set(node1, 'xmppSlice', "nepi")
ec.set(node1, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")

node2 = ec.register_resource("OMFNode")
ec.set(node2, 'hostname', "omf.plexus.wlab37")
ec.set(node2, 'xmppSlice', "nepi")
ec.set(node2, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")
ec.set(node2, 'xmppSlice', "nepi")
ec.set(node2, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")

# Create and Configure the Interfaces
iface1 = ec.register_resource("OMFWifiInterface")
ec.set(iface1, 'alias', "w0")
ec.set(iface1, 'mode', "adhoc")
ec.set(iface1, 'type', "g")
ec.set(iface1, 'essid', "vlcexp")
#ec.set(iface1, 'ap', "11:22:33:44:55:66")
ec.set(iface1, 'ip', "10.0.0.17")
ec.set(iface1, 'xmppSlice', "nepi")
ec.set(iface1, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(iface1, 'xmppPort', "5222")
ec.set(iface1, 'xmppPassword', "1234")

iface2 = ec.register_resource("OMFWifiInterface")
ec.set(iface2, 'alias', "w0")
ec.set(iface2, 'mode', "adhoc")
ec.set(iface2, 'type', 'g')
ec.set(iface2, 'essid', "vlcexp")
#ec.set(iface2, 'ap', "11:22:33:44:55:66")
ec.set(iface2, 'ip', "10.0.0.37")
ec.set(iface2, 'xmppSlice', "nepi")
ec.set(iface2, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(iface2, 'xmppPort', "5222")
ec.set(iface2, 'xmppPassword', "1234")

# Create and Configure the Channel
channel = ec.register_resource("OMFChannel")
ec.set(channel, 'channel', "6")
ec.set(channel, 'xmppSlice', "nepi")
ec.set(channel, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(channel, 'xmppPort', "5222")
ec.set(channel, 'xmppPassword', "1234")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'appid', 'Vlc#1')
ec.set(app1, 'path', "/opt/vlc-1.1.13/cvlc")
ec.set(app1, 'args', "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
#ec.set(app1, 'args', "--quiet /opt/big_buck_bunny_240p_mpeg4.ts --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts} '")
ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app1, 'xmppSlice', "nepi")
ec.set(app1, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(app1, 'xmppPort', "5222")
ec.set(app1, 'xmppPassword', "1234")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'appid', 'Vlc#2')
ec.set(app2, 'path', "/opt/vlc-1.1.13/cvlc")
ec.set(app2, 'args', "--quiet rtp://10.0.0.37:1234")
ec.set(app2, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app2, 'xmppSlice', "nepi")
ec.set(app2, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(app2, 'xmppPort', "5222")
ec.set(app2, 'xmppPassword', "1234")

app3 = ec.register_resource("OMFApplication")
ec.set(app3, 'appid', 'Kill#2')
ec.set(app3, 'path', "/usr/bin/killall")
ec.set(app3, 'args', "vlc")
ec.set(app3, 'env', " ")
ec.set(app3, 'xmppSlice', "nepi")
ec.set(app3, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(app3, 'xmppPort', "5222")
ec.set(app3, 'xmppPassword', "1234")

# Connection
ec.register_connection(app3, node1)
ec.register_connection(app1, node1)
ec.register_connection(node1, iface1)
ec.register_connection(iface1, channel)
ec.register_connection(iface2, channel)
ec.register_connection(node2, iface2)
ec.register_connection(app2, node2)

#      User Behaviour
ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "4s")
ec.register_condition([app1, app2], ResourceAction.STOP, app2, ResourceState.STARTED , "22s")
ec.register_condition(app3, ResourceAction.START, app2, ResourceState.STARTED , "25s")
ec.register_condition(app3, ResourceAction.STOP, app3, ResourceState.STARTED , "1s")

# Deploy
ec.deploy()

ec.wait_finished([app1, app2, app3])

# Stop Experiment
#time.sleep(55)
ec.shutdown()
