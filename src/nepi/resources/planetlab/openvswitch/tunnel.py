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
# Authors: Alina Quereilhac <alina.quereilhac@inria.fr>
#         Alexandros Kouvakas <alexandros.kouvakas@inria.fr>
#         Julien Tribino <julien.tribino@inria.fr>


from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, ResourceFactory, clsinit_copy, \
        ResourceState
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.planetlab.node import PlanetlabNode            
from nepi.resources.planetlab.openvswitch.ovs import OVSSwitch   
from nepi.util.timefuncs import tnow, tdiffsec    
from nepi.resources.planetlab.vroute import PlanetlabVroute
from nepi.resources.planetlab.tap import PlanetlabTap

import os
import time
import socket

reschedule_delay = "0.5s"

@clsinit_copy                 
class OVSTunnel(LinuxApplication):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm 
        :type creds: dict

    """
    
    _rtype = "OVSTunnel"
    _authorized_connections = ["OVSPort", "PlanetlabTap"]    

    @classmethod
    def _register_attributes(cls):
        """ Register the attributes of OVSTunnel RM 

        """
        network = Attribute("network", "IPv4 Network Address",
               flags = Flags.Design)

        cipher = Attribute("cipher",
               "Cipher to encript communication. "
                "One of PLAIN, AES, Blowfish, DES, DES3. ",
                default = None,
                allowed = ["PLAIN", "AES", "Blowfish", "DES", "DES3"],
                type = Types.Enumerate, 
                flags = Flags.Design)

        cipher_key = Attribute("cipherKey",
                "Specify a symmetric encryption key with which to protect "
                "packets across the tunnel. python-crypto must be installed "
                "on the system." ,
                flags = Flags.Design)

        txqueuelen = Attribute("txQueueLen",
                "Specifies the interface's transmission queue length. "
                "Defaults to 1000. ", 
                type = Types.Integer, 
                flags = Flags.Design)

        bwlimit = Attribute("bwLimit",
                "Specifies the interface's emulated bandwidth in bytes "
                "per second.",
                type = Types.Integer, 
                flags = Flags.Design)

        cls._register_attribute(network)
        cls._register_attribute(cipher)
        cls._register_attribute(cipher_key)
        cls._register_attribute(txqueuelen)
        cls._register_attribute(bwlimit)

    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
    
        """
        super(OVSTunnel, self).__init__(ec, guid)
        self._home = "tunnel-%s" % self.guid
        self.port_info_tunl = []
        self._pid = None
        self._ppid = None
        self._vroute = None
        self._node_endpoint1 = None
        self._node_endpoint2 = None

    def log_message(self, msg):
        return " guid %d - Tunnel - %s " % (self.guid, msg)

    def app_home(self, node):
        return os.path.join(node.exp_home, self._home)

    def run_home(self, node):
        return os.path.join(self.app_home(node), self.ec.run_id)

    @property
    def tap(self):
        """ Return the Tap RM if it exists """
        rclass = ResourceFactory.get_resource_type(PlanetlabTap.get_rtype())
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if isinstance(rm, rclass):
                return rm

    @property
    def ovsswitch(self):
        """ Return the 1st switch """
        for guid in self.connections:
            rm_port = self.ec.get_resource(guid)
            if hasattr(rm_port, "create_port"):
                rm_list = rm_port.get_connected(OVSSwitch.get_rtype())
                if rm_list:
                    return rm_list[0]

    @property         
    def check_switch_host_link(self):
        """ Check if the links are between switches
            or switch-host. Return False for the latter.
        """
        if self.tap :
            return True
        return False


    def endpoints(self):
        """ Return the list with the two connected elements.
        Either Switch-Switch or Switch-Host
        """
        connected = [1, 1]
        position = 0
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "create_port"):
                connected[position] = rm
                position += 1
            elif hasattr(rm, "udp_connect_command"):
                connected[1] = rm
        return connected

    def get_node(self, endpoint):
        """ Get the nodes of the endpoint
        """
        rm = []
        if hasattr(endpoint, "create_port"):
            rm_list = endpoint.get_connected(OVSSwitch.get_rtype())
            if rm_list:
                rm = rm_list[0].get_connected(PlanetlabNode.get_rtype())
        else:
            rm = endpoint.get_connected(PlanetlabNode.get_rtype())

        if rm :
            return rm[0]

    @property
    def endpoint1(self):
        """ Return the first endpoint : Always a Switch
        """
        endpoint = self.endpoints()
        return endpoint[0]

    @property
    def endpoint2(self):
        """ Return the second endpoint : Either a Switch or a TAP
        """
        endpoint = self.endpoints()
        return endpoint[1]

    def get_port_info(self, endpoint1, endpoint2):
        #TODO : Need to change it. Really bad to have method that return different type of things !!!!!
        """ Retrieve the port_info list for each port
	
        """
        if self.check_switch_host_link :
            host0, ip0, pname0, virt_ip0, pnumber0 = endpoint1.port_info
            return pnumber0

        host0, ip0, pname0, virt_ip0, pnumber0 = endpoint1.port_info
        host1, ip1, pname1, virt_ip1, pnumber1 = endpoint2.port_info

        return pname0, ip1, pnumber1
    
    def wait_local_port(self, node_endpoint):
        """ Waits until the if_name file for the command is generated, 
            and returns the if_name for the device """

        local_port = None
        delay = 1.0

        #TODO : Need to change it with reschedule to avoid the problem 
        #        of the order of connection
        for i in xrange(10):
            (out, err), proc = node_endpoint.check_output(self.run_home(node_endpoint), 'local_port')
            if out:
                local_port = int(out)
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "Couldn't retrieve local_port"
            self.error(msg, out, err)
            raise RuntimeError, msg

        return local_port

    def connection(self, local_endpoint, rm_endpoint):
        """ Create the connect command for each case : 
              - Host - Switch,  
              - Switch - Switch,  
              - Switch - Host
        """
        local_node = self.get_node(local_endpoint)
        local_node.mkdir(self.run_home(local_node))

        rm_node = self.get_node(rm_endpoint)
        rm_node.mkdir(self.run_home(rm_node))

        # Host to switch
        if self.check_switch_host_link and local_endpoint == self.endpoint2 :
        # Collect info from rem_endpoint
            remote_ip = socket.gethostbyname(rm_node.get("hostname"))

        # Collect info from endpoint
            local_port_file = os.path.join(self.run_home(local_node), "local_port")
            rem_port_file = os.path.join(self.run_home(local_node), "remote_port")
            ret_file = os.path.join(self.run_home(local_node), "ret_file")
            cipher = self.get("cipher")
            cipher_key = self.get("cipherKey")
            bwlimit = self.get("bwLimit")
            txqueuelen = self.get("txQueueLen")

            rem_port = str(self.get_port_info(rm_endpoint,local_endpoint))
   
        # Upload the remote port in a file
            local_node.upload(rem_port, rem_port_file,
                 text = True,
                 overwrite = False)
       
            connect_command = local_endpoint.udp_connect_command(
                 remote_ip, local_port_file, rem_port_file,
                 ret_file, cipher, cipher_key, bwlimit, txqueuelen) 

            self.connection_command(connect_command, local_node, rm_node)

        # Wait for pid file to be generated
            self._pid, self._ppid = local_node.wait_pid(self.run_home(local_node))

            if not self._pid or not self._ppid:
                (out, err), proc = local_node.check_errors(self.run_home(local_node))
                # Out is what was written in the stderr file
                if err:
                    msg = " Failed to start connection of the OVS Tunnel "
                    self.error(msg, out, err)
                    raise RuntimeError, msg
            return

        # Switch to Host
        if self.check_switch_host_link and local_endpoint == self.endpoint1:
            local_port_name = local_endpoint.get('port_name')
            remote_port_num = self.wait_local_port(rm_node)
            remote_ip = socket.gethostbyname(rm_node.get("hostname"))
  
        # Switch to Switch
        if not self.check_switch_host_link :
            local_port_name, remote_ip, remote_port_num = self.get_port_info(local_endpoint, rm_endpoint)

        connect_command = local_endpoint.switch_connect_command(
                    local_port_name, remote_ip, remote_port_num)

        self.connection_command(connect_command, local_node, rm_node)       

    def connection_command(self, command, node_endpoint, rm_node_endpoint):
        """ Execute the connection command on the node and check if the processus is
            correctly running on the node.
        """
        shfile = os.path.join(self.app_home(node_endpoint), "sw_connect.sh")
        node_endpoint.upload(command,
                shfile,
                text = True,
                overwrite = False)

        # Invoke connect script
        out = err= ''       
        cmd = "bash %s" % shfile
        (out, err), proc = node_endpoint.run(cmd, self.run_home(node_endpoint),
                sudo  = True,
                stdout = "sw_stdout",
                stderr = "sw_stderr")
        
        # Check if execution errors occured

        if proc.poll():
            msg = "Failed to connect endpoints"
            self.error(msg, out, err)
            raise RuntimeError, msg

        # For debugging
        msg = "Connection on port configured"
        self.debug(msg)

    def do_provision(self):
        """ Provision the tunnel
        """
        
        #TODO : The order of the connection is important for now ! 
        # Need to change the code of wait local port
        self.connection(self.endpoint2, self.endpoint1)
        self.connection(self.endpoint1, self.endpoint2)

    def configure_route(self):
        """ Configure the route for the tap device

            .. note : In case of a conection between a switch and a host, a route
                      was missing on the node with the Tap Device. This method create
                      the missing route. 
        """

        if  self.check_switch_host_link:
            self._vroute = self.ec.register_resource("PlanetlabVroute")
            self.ec.set(self._vroute, "action", "add")
            self.ec.set(self._vroute, "network", self.get("network"))

            self.ec.register_connection(self._vroute, self.tap.guid)
            self.ec.deploy(guids=[self._vroute], group = self.deployment_group)

    def do_deploy(self):
        """ Deploy the tunnel after the endpoint get ready
        """
        if (not self.endpoint1 or self.endpoint1.state < ResourceState.READY) or \
            (not self.endpoint2 or self.endpoint2.state < ResourceState.READY):
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()
        self.configure_route()

        # Cannot call the deploy of the linux application 
        #         because of a log error.
        # Need to investigate if it is right that the tunnel 
        #    inherits from the linux application
        #  super(OVSTunnel, self).do_deploy()
        self.set_ready()
 
    def do_release(self):
        """ Release the tunnel by releasing the Tap Device if exists
        """
        if self.check_switch_host_link:
            # TODO: Make more generic Release method of PLTAP
            tap_node = self.get_node(self.endpoint2)
            if self._pid and self._ppid:
                (out, err), proc = tap_node.kill(self._pid,
                        self._ppid, sudo = True)

                if err or proc.poll():
                    msg = " Failed to delete TAP device"
                    self.error(msg, out, err)

        super(OVSTunnel, self).do_release()

