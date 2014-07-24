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
ec.set(node1, 'hostname', 'servernode.nepivlcexperiment.nepi.wilab2.ilabt.iminds.be')
ec.set(node1, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node1, 'xmppUser', "nepi")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")

iface1 = ec.register_resource("OMFWifiInterface")
ec.set(iface1, 'name', 'wlan0')
ec.set(iface1, 'mode', "adhoc")
ec.set(iface1, 'hw_mode', "g")
ec.set(iface1, 'essid', "vlc")
ec.set(iface1, 'ip', "192.168.0.1/24")

node2 = ec.register_resource("OMFNode")
ec.set(node2, 'hostname', 'client1node.nepivlcexperiment.nepi.wilab2.ilabt.iminds.be')
ec.set(node2, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node2, 'xmppUser', "nepi")
ec.set(node2, 'xmppPort', "5222")
ec.set(node2, 'xmppPassword', "1234")

iface2 = ec.register_resource("OMFWifiInterface")
ec.set(iface2, 'name', 'wlan0')
ec.set(iface2, 'mode', "adhoc")
ec.set(iface2, 'hw_mode', "g")
ec.set(iface2, 'essid', "vlc")
ec.set(iface2, 'ip', "192.168.0.2/24")

node3 = ec.register_resource("OMFNode")
ec.set(node3, 'hostname', 'client2node.nepivlcexperiment.nepi.wilab2.ilabt.iminds.be')
ec.set(node3, 'xmppServer', "xmpp.ilabt.iminds.be")
ec.set(node3, 'xmppUser', "nepi")
ec.set(node3, 'xmppPort', "5222")
ec.set(node3, 'xmppPassword', "1234")

iface3 = ec.register_resource("OMFWifiInterface")
ec.set(iface3, 'name', 'wlan0')
ec.set(iface3, 'mode', "adhoc")
ec.set(iface3, 'hw_mode', "g")
ec.set(iface3, 'essid', "vlc")
ec.set(iface3, 'ip', "192.168.0.3/24")

chan = ec.register_resource("OMFChannel")
ec.set(chan, 'channel', "6")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'command', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority /root/vlc/vlc-1.1.13/cvlc /root/10-by-p0d.avi --sout '#duplicate{dst=rtp{dst=192.168.0.2,port=1234,mux=ts},dst=rtp{dst=192.168.0.3,port=1234,mux=ts}}'")

app2 = ec.register_resource("OMFApplication")
ec.set(app2, 'command', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority /root/vlc/vlc-1.1.13/cvlc rtp://192.168.0.2:1234")

app3 = ec.register_resource("OMFApplication")
ec.set(app3, 'command', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority /root/vlc/vlc-1.1.13/cvlc rtp://192.168.0.3:1234")


       "echo -e 'new TEST broadcast enabled loop\\n"\
       "setup TEST input %s\\n"\
       "setup TEST output #rtp{mux=ts,sdp=rtsp://0.0.0.0:8554/TEST}\\n\\n"\
       "new test_sched schedule enabled\\n"\
       "setup test_sched append control TEST play' > ${SOURCES}/VOD.vlm" % mv)



# Connection
ec.register_connection(iface1, node1)
ec.register_connection(iface2, node2)
ec.register_connection(iface3, node3)
ec.register_connection(iface1, chan)
ec.register_connection(iface2, chan)
ec.register_connection(iface3, chan)
ec.register_connection(app1, node1)
ec.register_connection(app2, node2)
ec.register_connection(app3, node3)

ec.register_condition([app2,app3], ResourceAction.START, app1, ResourceState.STARTED , "4s")
ec.register_condition([app1,app2,app3], ResourceAction.STOP, [app2,app3], ResourceState.STARTED , "30s")


# Deploy
ec.deploy()

ec.wait_finished([app1,app2,app3])

# Stop Experiment
ec.shutdown()

