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
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>
#         Alexandros Kouvakas <alexandros.kouvakas@inria.fr>


from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState
from nepi.execution.attribute import Attribute, Flags
from nepi.resources.planetlab.node import PlanetlabNode        
from nepi.resources.linux.application import LinuxApplication
import os

reschedule_delay = "0.5s"

@clsinit_copy                    
class OVSSwitch(LinuxApplication):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """

    _rtype = "OVSSwitch"
    _help = "Runs an OpenVSwitch on a PlanetLab host"
    _backend = "planetlab"

    _authorized_connections = ["PlanetlabNode", "OVSPort", "LinuxNode"]       

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of OVSSwitch RM 

        """
        bridge_name = Attribute("bridge_name", "Name of the switch/bridge",
                flags = Flags.ExecReadOnly)	
        virtual_ip_pref = Attribute("virtual_ip_pref", "Virtual IP/PREFIX of the switch",
                flags = Flags.ExecReadOnly)       
        controller_ip = Attribute("controller_ip", "IP of the controller",
                flags = Flags.ExecReadOnly)
        controller_port = Attribute("controller_port", "Port of the controller",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(bridge_name)
        cls._register_attribute(virtual_ip_pref)
        cls._register_attribute(controller_ip)
        cls._register_attribute(controller_port)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
    
        """
        super(OVSSwitch, self).__init__(ec, guid)
        self._home = "ovsswitch-%s" % self.guid
        self._checks = "ovsChecks-%s" % self.guid

    @property
    def node(self):
        """ Node wthat run the switch
        """
        node = self.get_connected(PlanetlabNode.get_rtype())
        if node: return node[0]
        return None

    def log_message(self, msg):
        return " guid %d - OVSSwitch - %s " % (self.guid, msg)

    @property
    def ovs_home(self):
        return os.path.join(self.node.exp_home, self._home)

    @property
    def ovs_checks(self):
        return os.path.join(self.ovs_home, self._checks)

    def valid_connection(self, guid):
        """ Check if the connection with the guid in parameter is possible. Only meaningful connections are allowed.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.get_rtype() in self._authorized_connections:
            msg = "Connection between %s %s and %s %s accepted" % \
                (self.get_rtype(), self._guid, rm.get_rtype(), guid)
            self.debug(msg)
            return True
        msg = "Connection between %s %s and %s %s refused" % \
             (self.get_rtype(), self._guid, rm.get_rtype(), guid)
        self.debug(msg)
        return False

    def do_provision(self):
        """ Create the different OVS folder.
        """

        # create home dir for ovs
        self.node.mkdir(self.ovs_home)
        # create dir for ovs checks
        self.node.mkdir(self.ovs_checks)
        
        super(OVSSwitch, self).do_provision()
				
    def do_deploy(self):
        """ Deploy the OVS Switch : Turn on the server, create the bridges
            and assign the controller
        """

        if not self.node or self.node.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()

        self.check_sliver_ovs()
        self.servers_on()
        self.create_bridge()
        self.assign_controller()
        self.ovs_status()
            
        super(OVSSwitch, self).do_deploy()

    def check_sliver_ovs(self):  
        """ Check if sliver-ovs exists. If it does not exist, the execution is stopped
        """

        cmd = "compgen -c | grep sliver-ovs"			
        out = err = ""

        (out,err), proc = self.node.run_and_wait(cmd, self.ovs_checks, 
	            shfile = "check_cmd.sh",
                pidfile = "check_cmd_pidfile",
                ecodefile = "check_cmd_exitcode", 
                sudo = True, 
                stdout = "check_cmd_stdout", 
                stderr = "check_cmd_stderr")

        (out, err), proc = self.node.check_output(self.ovs_checks, 'check_cmd_exitcode')
        
        if out != "0\n":
            msg = "Command sliver-ovs does not exist on the VM"    	 
            self.debug(msg)
            raise RuntimeError, msg

        msg = "Command sliver-ovs exists" 
        self.debug(msg)

    def servers_on(self):
        """ Start the openvswitch servers and check it
        """

        # Start the server
        command = "sliver-ovs start"   		
        out = err = ""									
        (out, err), proc = self.node.run_and_wait(command, self.ovs_checks,   
                shfile = "start_srv.sh",
                pidfile = "start_srv_pidfile",
                ecodefile = "start_srv_exitcode", 
                sudo = True, 
                raise_on_error = True,
                stdout = "start_srv_stdout", 
                stderr = "start_srv_stderr")
        (out, err), proc = self.node.check_output(self.ovs_checks, 'start_srv_exitcode')

        if out != "0\n":
            self.error("Servers have not started")
            raise RuntimeError, msg	
				
        # Check if the servers are running or not
        cmd = "ps -A | grep ovsdb-server"
        out = err = ""
        (out, err), proc = self.node.run_and_wait(cmd, self.ovs_checks, 
                shfile = "status_srv.sh",
                pidfile = "status_srv_pidfile",
                ecodefile = "status_srv_exitcode", 
                sudo = True, 
                stdout = "status_srv_stdout", 
                stderr = "status_srv_stderr")
        (out, err), proc = self.node.check_output(self.ovs_checks, 'status_srv_exitcode')
        
        if out != "0\n":
            msg = "Servers are not running"
            self.error(msg)
            raise RuntimeError, msg
        
        self.info("Server OVS Started Correctly")  

    def create_bridge(self):
        """ Create the bridge/switch and check error during SSH connection
        """
        # TODO: Check if previous bridge exist and delete them. Use ovs-vsctl list-br
        # TODO: Add check for virtual_ip belonging to vsys_tag

	
        if not (self.get("bridge_name") and self.get("virtual_ip_pref")):
            msg = "No assignment in one or both attributes"
            self.error(msg)
            raise AttributeError, msg

        cmd = "sliver-ovs create-bridge '%s' '%s'" %\
            (self.get("bridge_name"), self.get("virtual_ip_pref")) 
        out = err = ""
        (out, err), proc = self.node.run_and_wait(cmd, self.ovs_checks,
                shfile = "create_br.sh",
                pidfile = "create_br_pidfile",
                ecodefile = "create_br_exitcode", 
                sudo = True, 
                stdout = "create_br_stdout", 
                stderr = "create_br_stderr") 
        (out, err), proc = self.node.check_output(self.ovs_checks, 'create_br_exitcode')

        if out != "0\n":
            msg = "No such pltap netdev\novs-appctl: ovs-vswitchd: server returned an error"
            self.error(msg)			
            raise RuntimeError, msg

        self.info(" Bridge %s Created and Assigned to %s" %\
            (self.get("bridge_name"), self.get("virtual_ip_pref")) )
          

    def assign_controller(self):
        """ Set the controller IP
        """

        if not (self.get("controller_ip") and self.get("controller_port")):
            msg = "No assignment in one or both attributes"
            self.error(msg)
            raise AttributeError, msg

        cmd = "ovs-vsctl set-controller %s tcp:%s:%s" %\
            (self.get("bridge_name"), self.get("controller_ip"), self.get("controller_port"))
        out = err = ""
        (out, err), proc = self.node.run(cmd, self.ovs_checks,
                sudo = True, 
                stdout = "stdout", 
                stderr = "stderr")

        if err != "":
            msg = "SSH connection in the method assign_controller"
            self.error(msg)
            raise RuntimeError, msg

        self.info("Controller assigned to the bridge %s" % self.get("bridge_name"))
	    
    def ovs_status(self):
        """ Print the status of the bridge				
        """

        cmd = "sliver-ovs show | tail -n +2"
        out = err = ""
        (out, err), proc = self.node.run_and_wait(cmd, self.ovs_home,
                sudo = True, 
                stdout = "show_stdout", 
                stderr = "show_stderr") 
        (out, err), proc = self.node.check_output(self.ovs_home, 'show_stdout')
        
        if out == "":
            msg = "Error when checking the status of the OpenVswitch"
            self.error(msg)
            raise RuntimeError, msg
        
        self.debug(out)

    def do_release(self):
        """ Delete the bridge and close the server.  

          .. note : It need to wait for the others RM (OVSPort and OVSTunnel)
        to be released before releasing itself

        """

        from nepi.resources.planetlab.openvswitch.ovsport import OVSPort
        rm = self.get_connected(OVSPort.get_rtype())

        if rm[0].state < ResourceState.RELEASED:
            self.ec.schedule(reschedule_delay, self.release)
            return 
            
        cmd = "sliver-ovs del-bridge %s" % self.get('bridge_name')
        (out, err), proc = self.node.run(cmd, self.ovs_checks,
                sudo = True)

        cmd = "sliver-ovs stop"
        (out, err), proc = self.node.run(cmd, self.ovs_checks,
                sudo = True)

        msg = "Deleting the bridge %s" % self.get('bridge_name')
        self.info(msg)
        
        if proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg

        super(OVSSwitch, self).do_release()

