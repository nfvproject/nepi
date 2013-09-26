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


from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState
from nepi.execution.attribute import Attribute, Flags
from nepi.resources.planetlab.node import PlanetlabNode        
from nepi.resources.linux.application import LinuxApplication
import os

reschedule_delay = "0.5s"

@clsinit_copy                    
class OVSWitch(LinuxApplication):
    
    _rtype = "OVSWitch"
    _help = "Runs an OpenVSwitch on a PlanetLab host"
    _backend = "planetlab"

    _authorized_connections = ["PlanetlabNode", "OVSPort", "LinuxNode"]       

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of OVSWitch RM 

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
        super(OVSWitch, self).__init__(ec, guid)
        self._pid = None
        self._ppid = None
        self._home = "ovswitch-%s" % self.guid
        self._checks = "ovsChecks-%s" % self.guid

    @property
    def node(self):
        node = self.get_connected(PlanetlabNode.rtype())
        if node: return node[0]
        return None

    @property
    def ovs_home(self):
        return os.path.join(self.node.exp_home, self._home)

    @property
    def ovs_checks(self):
        return os.path.join(self.ovs_home, self._checks)

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        return self._ppid

#    def valid_connection(self, guid):
#        """ Check if the connection with the guid in parameter is possible. Only meaningful connections are allowed.

#        :param guid: Guid of the current RM
#        :type guid: int
#        :rtype:  Boolean

#        """
#        rm = self.ec.get_resource(guid)
#        if rm.rtype() in self._authorized_connections:
#            msg = "Connection between %s %s and %s %s accepted" % \
#                (self.rtype(), self._guid, rm.rtype(), guid)
#            self.debug(msg)
#            return True
#        msg = "Connection between %s %s and %s %s refused" % \
#             (self.rtype(), self._guid, rm.rtype(), guid)
#        self.debug(msg)
#        return False

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

    def provision(self):
        # create home dir for ovs
        self.node.mkdir(self.ovs_home)
        # create dir for ovs checks
        self.node.mkdir(self.ovs_checks)

    def check_sliver_ovs(self):  
        """ Check if sliver-ovs exists. If it does not exist, we interrupt
        the execution immediately. 
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

    def deploy(self):
        """ Wait until node is associated and deployed
        """
        node = self.node
        if not node or node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            self.ec.schedule(reschedule_delay, self.deploy)

        else:
            try:
                self.discover()
                self.provision()
                self.check_sliver_ovs()
                self.servers_on()
                self.create_bridge()
                self.assign_contr()
                self.ovs_status()
            except:
                self._state = ResourceState.FAILED
                raise
                
            self._state = ResourceState.READY

    def servers_on(self):
        """ Start the openvswitch servers and also checking 
            if they started successfully 
        """
        self.info("Starting the OVSWitch servers")
        command = ("sliver-ovs start") 
                   		
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
            self.debug("Servers have not started")
            raise RuntimeError, msg	
				
        cmd = "ps -A | grep ovsdb-server"
        out = err = ""
        (out, err), proc = self.node.run_and_wait(cmd, self.ovs_checks, 
                shfile = "status_srv.sh",
                pidfile = "status_srv_pidfile",
                ecodefile = "status_srv_exitcode", 
                sudo = True, 
                stdout = "status_srv_stdout", 
                stderr = "status_srv_stderr")

        # Check if the servers are running or not
        (out, err), proc = self.node.check_output(self.ovs_checks, 'status_srv_exitcode')
        if out != "0\n":
            self.debug("Servers are not running")
            raise RuntimeError, msg
        self.info("Servers started")  

    def del_old_br(self):
        # TODO: Delete old bridges that might exist maybe by adding atribute
        """ With ovs-vsctl list-br
        """
        pass

    def create_bridge(self):
        """ Create the bridge/switch and we check if we have any 
            error during the SSH connection         
        """
        # TODO: Add check for virtual_ip belonging to vsys_tag
        self.del_old_br()
	
        if self.get("bridge_name") and self.get("virtual_ip_pref"):	
            bridge_name = self.get("bridge_name")
            virtual_ip_pref = self.get("virtual_ip_pref")
            self.info(" Creating the bridge %s and assigning %s" %\
                (bridge_name, virtual_ip_pref) )
            cmd = "sliver-ovs create-bridge '%s' '%s'" %\
                (bridge_name, virtual_ip_pref) 
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
                self.debug("Check again the virtual IP")			
                raise RuntimeError, msg
            self.info("Bridge %s created" % bridge_name)
          
        else: 	
            msg = "No assignment in one or both attributes"
            self.error(msg)
            self.debug("Bridge name is %s and virtual_ip_pref is %s" %\
                (self.get("bridge_name"), self.get("virtual_ip_pref")) )
            raise AttributeError, msg

    def assign_contr(self):
        """ Set the controller IP
        """
        if self.get("controller_ip") and self.get("controller_port"):
            controller_ip = self.get("controller_ip")
            controller_port = self.get("controller_port")
            self.info("Assigning the controller to the %s" % self.get("bridge_name"))
            cmd = "ovs-vsctl set-controller %s tcp:%s:%s" %\
                (self.get("bridge_name"), controller_ip, controller_port)
            out = err = ""
            (out, err), proc = self.node.run(cmd, self.ovs_checks,
                    sudo = True, 
                    stdout = "stdout", 
                    stderr = "stderr")
            if err != "":
                self.debug("SSH connection refusing in assign_contr")
                raise RuntimeError, msg
            self.info("Controller assigned")
	    
    def ovs_status(self):
        """ Print the status of the created bridge					
        """
        cmd = "sliver-ovs show | tail -n +2"
        out = err = ""
        (out, err), proc = self.node.run_and_wait(cmd, self.ovs_home,
                sudo = True, 
                stdout = "show_stdout", 
                stderr = "show_stderr") 
        (out, err), proc = self.node.check_output(self.ovs_home, 'show_stdout')
        self.info(out)

    def start(self):
        """ Start the RM. It means nothing special for 
            ovswitch for now.	
        """
        pass

    def stop(self):
        """ Stop the RM.It means nothing 
            for ovswitch for now.
        """
        pass

    def release(self):
        """ Delete the bridge and 
            close the servers
        """
        # Node needs to wait until all associated RMs are released
        # to be released
        from nepi.resources.planetlab.openvswitch.ovsport import OVSPort
        rm = self.get_connected(OVSPort.rtype())

        if rm[0].state < ResourceState.FINISHED:
            self.ec.schedule(reschedule_delay, self.release)
            return 
            
        msg = "Deleting the bridge %s" % self.get('bridge_name')
        self.info(msg)
        cmd = "sliver-ovs del-bridge %s" % self.get('bridge_name')
        (out, err), proc = self.node.run(cmd, self.ovs_checks,
                sudo = True)
        cmd = "sliver-ovs stop"
        (out, err), proc = self.node.run(cmd, self.ovs_checks,
                sudo = True)
        
        if proc.poll():
            self.fail()
            self.error(msg, out, err)
            raise RuntimeError, msg
     
        self._state = ResourceState.RELEASED
        
