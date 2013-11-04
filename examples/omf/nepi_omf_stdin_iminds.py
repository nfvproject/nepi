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
      - Testbed : iMinds
      - Explanation :

       Test the STDIN Message
                   
     Node Zotack
     node0.nepi-robot.nepi.wilab2.ilabt.iminds.be
     0 
     |
     |
     0
     Application RobotCTRLComm.rb
   
      - Experiment:
        - t0 : Deployment
        - t1 : After the application started, send the message START_DRIVE
        - t2 (t1 + 83s) : Open Left eye of robot 1
        - t3 (t2 + 2s) : Open Left eye of robot 2

"""

from nepi.execution.resource import ResourceFactory, ResourceAction, ResourceState
from nepi.execution.ec import ExperimentController

import time

# Create the EC
ec = ExperimentController()

# Create and Configure the Node
node1 = ec.register_resource("OMFNode")
    # If the hostname is not declared, Nepi will take SFA to provision one.
ec.set(node1, 'hostname', 'node0.nepi-robot.nepi.wilab2.ilabt.iminds.be')
    # XMPP credentials
ec.set(node1, 'xmppSlice', "default_slice_iminds")
ec.set(node1, 'xmppHost', "am.wilab2.ilabt.iminds.be")
ec.set(node1, 'xmppPort', "5222")
ec.set(node1, 'xmppPassword', "1234")

# Create and Configure the Application
app1 = ec.register_resource("OMFRobotApplication")
ec.set(app1, 'appid', "robot")
ec.set(app1, 'path', "/users/jtribino/RobotCTRLComm.rb") # /users/username/RobotCTRLComm.rb
ec.set(app1, 'args', "/users/jtribino/coordinate.csv")   #/users/username/coordinate.csv
ec.set(app1, 'env', " ")
ec.set(app1, 'sources', "/home/wlab18/Desktop/coordinate.csv")  # local path
ec.set(app1, 'sshUser', "jtribino")  # username

# Connection
ec.register_connection(app1, node1)

# The Application should run during 350sec
ec.register_condition(app1, ResourceAction.STOP, app1, ResourceState.STARTED , "350s")

# Deploy
ec.deploy()

ec.wait_started([app1])

ec.set(app1, 'stdin', "START_DRIVE")

time.sleep(83)
ec.set(app1, 'stdin', "1;openlefteye")

time.sleep(2)
ec.set(app1, 'stdin', "2;openlefteye")

ec.wait_finished([app1])

# Stop Experiment
ec.shutdown()
