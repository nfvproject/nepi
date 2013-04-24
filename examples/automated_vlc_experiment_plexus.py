#!/usr/bin/env python
from neco.execution.resource import ResourceFactory, ResourceAction, ResourceState
from neco.execution.ec import ExperimentController

from neco.resources.omf.omf_node import OMFNode
from neco.resources.omf.omf_application import OMFApplication
from neco.resources.omf.omf_interface import OMFWifiInterface
from neco.resources.omf.omf_channel import OMFChannel

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
node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'omf.plexus.wlab17')
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
ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app1, 'xmppSlice', "nepi")
ec.set(app1, 'xmppHost', "xmpp-plexus.onelab.eu")
ec.set(app1, 'xmppPort', "5222")
ec.set(app1, 'xmppPassword', "1234")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'appid', 'Vlc#2')
ec.set(app2, 'path', "/opt/vlc-1.1.13/cvlc")
ec.set(app2, 'args', "rtp://10.0.0.37:1234")
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

# Condition
#      Topology behaviour : It should not be done by the user, but ....
#ec.register_condition([iface1, iface2, channel], ResourceAction.START, [node1, node2], ResourceState.STARTED , 2)
#ec.register_condition(channel, ResourceAction.START, [iface1, iface2], ResourceState.STARTED , 1)
#ec.register_condition(app1, ResourceAction.START, channel, ResourceState.STARTED , 1)

#      User Behaviour
ec.register_condition(app2, ResourceAction.START, app1, ResourceState.STARTED , "4s")
ec.register_condition([app1, app2], ResourceAction.STOP, app2, ResourceState.STARTED , "20s")
ec.register_condition(app3, ResourceAction.START, app2, ResourceState.STARTED , "25s")

# Deploy
ec.deploy()

# Stop Experiment
time.sleep(50)
ec.shutdown()
