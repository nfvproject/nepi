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

    def get_host_ip(self):
        """ Get the hostname of the node that
        the port belongs to. We use it for tunnel.
        """
        get_host_ip = self.node
        if not get_host_ip: 
            msg = "info_list is empty"
            self.debug(msg)
            raise RuntimeError, msg

        import socket
        self.port_info.append(get_host_ip.get('hostname'))
        self.port_info.append(socket.gethostbyname(self.port_info[0]))   
    
    def create_port(self):
        """ Create the desired port
        """
        port_name = self.get('port_name')

        if not (port_name or self.ovswitch):
            msg = "The rm_list is empty or the port name is not assigned\n Failed to create port"
            self.error(msg)
            self.debug("ovswitch_list = %s and port_name = %s" % (self.ovswitch, port_name) )
            raise AttributeError, msg

        self.info("Create the port %s on switch %s" % (port_name, self.ovswitch.get('bridge_name')))     
        self.port_info.append(port_name)
        self.port_info.append(self.ovswitch.get('virtual_ip_pref'))
        cmd = "sliver-ovs create-port %s %s" % (self.ovswitch.get('bridge_name'), port_name)   
        self.node.run(cmd, self.ovswitch.ovs_checks, 
                stderr = "stdout-%s" % port_name, 
                stdout = "stderr-%s" % port_name,
                sudo = True)
	    
    def get_local_end(self):
        """ Get the local_endpoint of the port
        """
        msg = "Discovering the number of the port %s"\
            % self.get('port_name')
        self.info(msg)

        command = "sliver-ovs get-local-endpoint %s"\
            % self.get('port_name')
        out = err = ""
        (out, err), proc = self.node.run_and_wait(command, self.ovswitch.ovs_checks, 
                shfile = "port_number-%s.sh" % self.get('port_name'),
                pidfile = "port_number_pidfile-%s" % self.get('port_name'),
                ecodefile = "port_number_exitcode-%s" % self.get('port_name'), 
                sudo = True, 
                stdout = "stdout-%s" % self.get('port_name'),    
                stderr = "stderr-%s" % self.get('port_name'))

        if err != "":
            msg = "No assignment in attribute port_name"
            self.error(msg)
            self.debug("You are in the method get_local_end and the port_name = %s" % self.get('port_name'))
            raise AttributeError, msg

        self._port_number = None
        self._port_number = int(out)
        self.port_info.append(self._port_number)				
        self.info("The number of the %s is %s" % (self.get('port_name'), self._port_number))
   
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
        ovswitch = self.ovswitch

        if not ovswitch or ovswitch.state < ResourceState.READY:       
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.ovswitch.state )  
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()
        self.get_host_ip()
        self.create_port()
        self.get_local_end()
        self.ovswitch.ovs_status()

        super(OVSPort, self).do_deploy()

    def do_release(self):
        """ Release the port RM means delete the ports
        """
        # OVS needs to wait until all associated RMs are released
        # to be released
        from nepi.resources.planetlab.openvswitch.tunnel import OVSTunnel
        rm = self.get_connected(OVSTunnel.get_rtype())

        if rm and rm[0].state < ResourceState.FINISHED:
            self.ec.schedule(reschedule_delay, self.release)
            return 
            
        msg = "Deleting the port %s" % self.get('port_name')
        self.info(msg)
        cmd = "sliver-ovs del_port %s" % self.get('port_name')
        (out, err), proc = self.node.run(cmd, self.ovswitch.ovs_checks,
                sudo = True)

        if proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg

        super(OVSPort, self).do_release()

