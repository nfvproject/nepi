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

from nepi.execution.resource import ResourceFactory
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

# Register the different RM that will be used
ResourceFactory.register_type(OMFNode)
ResourceFactory.register_type(OMFWifiInterface)
ResourceFactory.register_type(OMFChannel)
ResourceFactory.register_type(OMFApplication)

# Create and Configure the Nodes
guid = ec.register_resource("OMFNode")
node1 = ec.get_resource(guid)
node1.set('hostname', 'omf.plexus.wlab17')
node1.set('xmppSlice', "nepi")
node1.set('xmppHost', "xmpp-plexus.onelab.eu")
node1.set('xmppPort', "5222")
node1.set('xmppPassword', "1234")

guid = ec.register_resource("OMFNode")
node2 = ec.get_resource(guid)
node2.set('hostname', "omf.plexus.wlab37")
node2.set('xmppSlice', "nepi")
node2.set('xmppHost', "xmpp-plexus.onelab.eu")
node2.set('xmppPort', "5222")
node2.set('xmppPassword', "1234")

# Create and Configure the Interfaces
guid = ec.register_resource("OMFWifiInterface")
iface1 = ec.get_resource(guid)
iface1.set('alias', "w0")
iface1.set('mode', "adhoc")
iface1.set('type', "g")
iface1.set('essid', "helloworld")
iface1.set('ip', "10.0.0.17")
iface1.set('xmppSlice', "nepi")
iface1.set('xmppHost', "xmpp-plexus.onelab.eu")
iface1.set('xmppPort', "5222")
iface1.set('xmppPassword', "1234")

guid = ec.register_resource("OMFWifiInterface")
iface2 = ec.get_resource(guid)
iface2.set('alias', "w0")
iface2.set('mode', "adhoc")
iface2.set('type', 'g')
iface2.set('essid', "helloworld")
iface2.set('ip', "10.0.0.37")
iface2.set('xmppSlice', "nepi")
iface2.set('xmppHost', "xmpp-plexus.onelab.eu")
iface2.set('xmppPort', "5222")
iface2.set('xmppPassword', "1234")

# Create and Configure the Channel
guid = ec.register_resource("OMFChannel")
channel = ec.get_resource(guid)
channel.set('channel', "6")
channel.set('xmppSlice', "nepi")
channel.set('xmppHost', "xmpp-plexus.onelab.eu")
channel.set('xmppPort', "5222")
channel.set('xmppPassword', "1234")

# Create and Configure the Application
guid = ec.register_resource("OMFApplication")
app1 = ec.get_resource(guid)
app1.set('appid', 'Vlc#1')
app1.set('path', "/opt/vlc-1.1.13/cvlc")
app1.set('args', "/opt/10-by-p0d.avi --sout '#rtp{dst=10.0.0.37,port=1234,mux=ts}'")
app1.set('env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
app1.set('xmppSlice', "nepi")
app1.set('xmppHost', "xmpp-plexus.onelab.eu")
app1.set('xmppPort', "5222")
app1.set('xmppPassword', "1234")

guid = ec.register_resource("OMFApplication")
app2 = ec.get_resource(guid)
app2.set('appid', 'Vlc#2')
app2.set('path', "/opt/vlc-1.1.13/cvlc")
app2.set('args', "rtp://10.0.0.37:1234")
app2.set('env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
app2.set('xmppSlice', "nepi")
app2.set('xmppHost', "xmpp-plexus.onelab.eu")
app2.set('xmppPort', "5222")
app2.set('xmppPassword', "1234")

guid = ec.register_resource("OMFApplication")
app3 = ec.get_resource(guid)
app3.set('appid', 'Kill#2')
app3.set('path', "/usr/bin/killall")
app3.set('args', "vlc")
app3.set('env', " ")
app3.set('xmppSlice', "nepi")
app3.set('xmppHost', "xmpp-plexus.onelab.eu")
app3.set('xmppPort', "5222")
app3.set('xmppPassword', "1234")

# Connection
app3.connect(node1.guid)
node1.connect(app3.guid)

app1.connect(node1.guid)
node1.connect(app1.guid)

node1.connect(iface1.guid)
iface1.connect(node1.guid)

iface1.connect(channel.guid)
channel.connect(iface1.guid)

channel.connect(iface2.guid)
iface2.connect(channel.guid)

iface2.connect(node2.guid)
node2.connect(iface2.guid)

node2.connect(app2.guid)
app2.connect(node2.guid)

# Local Deploy
node1.deploy()
node2.deploy()
iface1.deploy()
iface2.deploy()
channel.deploy()
app1.deploy()
app2.deploy()
app3.deploy()

# Start the Nodes
node1.start()
node2.start()
time.sleep(2)

# Start the Interfaces
iface1.start()
iface2.start()

# Start the Channel
time.sleep(2)
channel.start()
time.sleep(2)

# Start the Application
app1.start()
time.sleep(2)
app2.start()

time.sleep(20)

# Stop the Application
app1.stop()
app2.stop()
time.sleep(1)
app3.start()
time.sleep(2)

# Stop Experiment
ec.shutdown()
