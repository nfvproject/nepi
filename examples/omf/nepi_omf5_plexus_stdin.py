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

    Author: Julien Tribino <julien.tribino@inria.fr>

    Example :
      - Testbed : Plexus
      - Explanation :

       Test the STDIN Message
                   
     Node 
     wlab17
     0 
     |
     |
     0
     Application CTRL_test.rb
   
      - Experiment:
        * t0 : Deployment
        * t1 : After the application started, one stdin message is sent
        * t2 (t1 + 5s) : An other message is send

"""

#!/usr/bin/env python
from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

import time

# Create the EC
ec = ExperimentController()

# Create and Configure the Nodes
node1 = ec.register_resource("OMFNode")
ec.set(node1, 'hostname', 'omf.plexus.wlab17')
ec.set(node1, 'xmppServer', "nepi")
ec.set(node1, 'xmppUser', "xmpp-plexus.onelab.eu")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")
ec.set(node1, 'version', "5")

# Create and Configure the Application
app1 = ec.register_resource("OMFApplication")
ec.set(app1, 'appid', "robot")
ec.set(app1, 'command', "/root/CTRL_test.rb coord.csv")
ec.set(app1, 'env', "DISPLAY=localhost:10.0 XAUTHORITY=/root/.Xauthority")
ec.set(app1, 'version', "5")

# Connection
ec.register_connection(app1, node1)

ec.register_condition(app1, ResourceAction.STOP, app1, ResourceState.STARTED , "20s")

# Deploy
ec.deploy()

ec.wait_started([app1])
ec.set(app1, 'stdin', "xxxxxxxxxxxxxxxxx")

time.sleep(5)
ec.set(app1, 'stdin', "xxxxxxxxxxxxxxxxx")

ec.wait_finished([app1])

# Stop Experiment
ec.shutdown()
