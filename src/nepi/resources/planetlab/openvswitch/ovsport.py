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
#	      Alexandros Kouvakas <alexandros.kouvakas@gmail.com>

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState
from nepi.resources.planetlab.openvswitch.ovs import OVSWitch        
from nepi.resources.planetlab.node import PlanetlabNode        
from nepi.resources.linux.application import LinuxApplication

reschedule_delay = "0.5s"

@clsinit_copy                 
class OVSPort(LinuxApplication):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """
    
    _rtype = "OVSPort"
    _help = "Runs an OpenVSwitch on a PlanetLab host"
    _backend = "planetlab"

    _authorized_connections = ["OVSWitch", "Tunnel"]      

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of OVSPort RM 

        """
        port_name = Attribute("port_name", "Name of the port",
            flags = Flags.ExecReadOnly)			

        cls._register_attribute(port_name)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
    
        """
        super(OVSPort, self).__init__(ec, guid)
        self._port_number = None
        self.port_info = []	     

    @property
    def node(self):
        rm_list = self.get_connected(OVSWitch.get_rtype())
        if rm_list:
            for elt in rm_list:
                node = elt.get_connected(PlanetlabNode.get_rtype())
                if node: return node[0]
        return node[0]

    @property
    def ovswitch(self):
        ovswitch = self.get_connected(OVSWitch.get_rtype())
        if ovswitch: return ovswitch[0]
        return None
        
    @property
    def port_number(self):
        return self._port_number

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

#    def valid_connection(self, guid):
#        """ Check if the connection is available.

#        :param guid: Guid of the current RM
#        :type guid: int
#        :rtype:  Boolean

#        """
#        rm = self.ec.get_resource(guid)
#        if rm.get_rtype() in self._authorized_connections:
#            msg = "Connection between %s %s and %s %s accepted" % (self.get_rtype(), self._guid, rm.get_rtype(), guid)
#            self.debug(msg)
#            return True
#        msg = "Connection between %s %s and %s %s refused" % (self.get_rtype(), self._guid, rm.get_rtype(), guid)
#        self.debug(msg)

    def get_ip(self):
        """ Return the ip of the node. This data is necessary to
        create the tunnel.
        """

        import socket
        return socket.gethostbyname(self.node.get('hostname'))
    
    def create_port(self):
        """ Create the desired port
        """
        msg = "Creating the port %s" % self.get('port_name')
        self.debug(msg)

        if not self.get('port_name'):
            msg = "The port name is not assigned"
            self.error(msg)
            raise AttributeError, msg

        if not self.ovswitch:
            msg = "The OVSwitch RM is not running"
            self.error(msg)
            raise AttributeError, msg

        cmd = "sliver-ovs create-port %s %s" % (self.ovswitch.get('bridge_name'),
                                                self.get('port_name'))   
        self.node.run(cmd, self.ovswitch.ovs_checks, 
                stderr = "stdout-%s" % self.get('port_name'), 
                stdout = "stderr-%s" % self.get('port_name'),
                sudo = True)

        self.info("Created the port %s on switch %s" % (self.get('port_name'),
                                             self.ovswitch.get('bridge_name')))     
	    
    def get_local_end(self):
        """ Get the local_endpoint of the port
        """

        msg = "Discovering the number of the port %s" % self.get('port_name')
        self.debug(msg)

        command = "sliver-ovs get-local-endpoint %s" % self.get('port_name')
        out = err = ""
        (out, err), proc = self.node.run_and_wait(command, 
                self.ovswitch.ovs_checks,
                shfile = "port_number-%s.sh" % self.get('port_name'),
                pidfile = "port_number_pidfile-%s" % self.get('port_name'),
                ecodefile = "port_number_exitcode-%s" % self.get('port_name'), 
                sudo = True, 
                stdout = "stdout-%s" % self.get('port_name'),    
                stderr = "stderr-%s" % self.get('port_name'))

        if err != "":
            msg = "Error retrieving the local endpoint of the port"
            self.error(msg)
            raise AttributeError, msg

        if out:
            self._port_number = int(out)

        self.info("The number of the %s is %s" % (self.get('port_name'), 
           self.port_number))
   
    def set_port_info(self, ip):
        info = []
        info.append(self.node.get('hostname'))
        info.append(ip)
        info.append(self.get('port_name'))
        info.append(self.ovswitch.get('virtual_ip_pref'))
        info.append(self.port_number)
        return info

    def switch_connect_command(self, local_port_name, 
            remote_ip, remote_port_num):
        """ Script for switch links
        """
        command = ["sliver-ovs"]
        command.append("set-remote-endpoint ")
        command.append("%s " % local_port_name)
        command.append("%s " % remote_ip)
        command.append("%s " % remote_port_num)
        command = " ".join(command)
        command = self.replace_paths(command)
        return command
        
    def do_deploy(self):
        """ Wait until ovswitch is started
        """

        if not self.ovswitch or self.ovswitch.state < ResourceState.READY:       
            self.debug("---- RESCHEDULING DEPLOY ---- OVSwitch state %s " % self.ovswitch.state )  
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()
        ip = self.get_ip()
        self.create_port()
        self.get_local_end()
        self.ovswitch.ovs_status()

        self.port_info = self.set_port_info(ip)

        super(OVSPort, self).do_deploy()

    def do_release(self):
        """ Delete the port on the OVSwitch. It needs to wait for the tunnel
        to be released.
        """

        from nepi.resources.planetlab.openvswitch.tunnel import OVSTunnel
        rm = self.get_connected(OVSTunnel.get_rtype())

        if rm and rm[0].state < ResourceState.RELEASED:
            self.ec.schedule(reschedule_delay, self.release)
            return 
            
        cmd = "sliver-ovs del_port %s" % self.get('port_name')
        (out, err), proc = self.node.run(cmd, self.ovswitch.ovs_checks,
                sudo = True)

        msg = "Deleting the port %s" % self.get('port_name')
        self.info(msg)

        if proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg

        super(OVSPort, self).do_release()

