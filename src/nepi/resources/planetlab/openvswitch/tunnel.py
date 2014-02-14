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
from nepi.execution.resource import ResourceManager, ResourceFactory, clsinit_copy, \
        ResourceState
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.planetlab.node import PlanetlabNode            
from nepi.resources.planetlab.openvswitch.ovs import OVSWitch   
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
        """ Register the attributes of Connection RM 

        """
        network = Attribute("network", "IPv4 Network Address",
               flags = Flags.ExecReadOnly)

        cipher = Attribute("cipher",
               "Cipher to encript communication. "
                "One of PLAIN, AES, Blowfish, DES, DES3. ",
                default = None,
                allowed = ["PLAIN", "AES", "Blowfish", "DES", "DES3"],
                type = Types.Enumerate, 
                flags = Flags.ExecReadOnly)

        cipher_key = Attribute("cipherKey",
                "Specify a symmetric encryption key with which to protect "
                "packets across the tunnel. python-crypto must be installed "
                "on the system." ,
                flags = Flags.ExecReadOnly)

        txqueuelen = Attribute("txQueueLen",
                "Specifies the interface's transmission queue length. "
                "Defaults to 1000. ", 
                type = Types.Integer, 
                flags = Flags.ExecReadOnly)

        bwlimit = Attribute("bwLimit",
                "Specifies the interface's emulated bandwidth in bytes "
                "per second.",
                type = Types.Integer, 
                flags = Flags.ExecReadOnly)

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
        ''' Return the Tap RM if it exists '''
        rclass = ResourceFactory.get_resource_type(PlanetlabTap.get_rtype())
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if isinstance(rm, rclass):
                return rm

    @property
    def ovswitch(self):
        ''' Return the 1st switch '''
        for guid in self.connections:
            rm_port = self.ec.get_resource(guid)
            if hasattr(rm_port, "create_port"):
                rm_list = rm_port.get_connected(OVSWitch.get_rtype())
                if rm_list:
                    return rm_list[0]

    @property         
    def check_switch_host_link(self):
        ''' Check if the links are between switches
            or switch-host. Return False for latter.
        '''
        if self.tap :
            return True
        return False


    def endpoints(self):
        ''' Return the list with the two connected elements.
        Either Switch-Switch or Switch-Host
        '''
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

#    def port_endpoints(self):
#        # Switch-Switch connection
#        connected = []
#        for guid in self.connections:
#            rm = self.ec.get_resource(guid)
#            if hasattr(rm, "create_port"):
#                connected.append(rm)
#        return connected

#    
#    def mixed_endpoints(self):
#        # Switch-Host connection
#        connected = [1, 2]
#        for guid in self.connections:
#            rm = self.ec.get_resource(guid)
#            if hasattr(rm, "create_port"):
#                connected[0] = rm
#            elif hasattr(rm, "udp_connect_command"):
#                connected[1] = rm
#        return connected

    def get_node(self, endpoint):
        # Get connected to the nodes
        rm = []
        if hasattr(endpoint, "create_port"):
            rm_list = endpoint.get_connected(OVSWitch.get_rtype())
            if rm_list:
                rm = rm_list[0].get_connected(PlanetlabNode.get_rtype())
        else:
            rm = endpoint.get_connected(PlanetlabNode.get_rtype())

        if rm :
            return rm[0]

    @property
    def endpoint1(self):
            endpoint = self.endpoints()
            return endpoint[0]

    @property
    def endpoint2(self):
            endpoint = self.endpoints()
            return endpoint[1]

#    @property          
#    def check_endpoints(self):
#        """ Check if the links are between switches
#            or switch-host. Return False for latter.
#        """
#        port_endpoints = self.port_endpoints()
#        if len(port_endpoints) == 2:
#            return True
#        return False

    def get_port_info(self, endpoint1, endpoint2):
        # Need to change it. Not good to have method that return different type of things !!!!!
        """ Retrieve the port_info list for each port
	
        """
        if self.check_switch_host_link :
            host0, ip0, pname0, virt_ip0, pnumber0 = endpoint1.port_info
            return pnumber0

        host0, ip0, pname0, virt_ip0, pnumber0 = endpoint1.port_info
        host1, ip1, pname1, virt_ip1, pnumber1 = endpoint2.port_info

        return pname0, ip1, pnumber1
    
    def host_to_switch_connect(self, tap_endpoint, sw_endpoint):     
        # Collect info from rem_endpoint
        remote_ip = socket.gethostbyname(self.node_endpoint1.get("hostname"))

        # Collect info from endpoint
        local_port_file = os.path.join(self.run_home(self.node_endpoint2), "local_port")
        rem_port_file = os.path.join(self.run_home(self.node_endpoint2), "remote_port")
        ret_file = os.path.join(self.run_home(self.node_endpoint2), "ret_file")
        cipher = self.get("cipher")
        cipher_key = self.get("cipherKey")
        bwlimit = self.get("bwLimit")
        txqueuelen = self.get("txQueueLen")

        rem_port = str(self.get_port_info( sw_endpoint,tap_endpoint))

        # Upload the remote port in a file
        self.node_endpoint2.upload(rem_port, rem_port_file,
                text = True,
                overwrite = False)
       
        udp_connect_command = tap_endpoint.udp_connect_command(
                remote_ip, local_port_file, rem_port_file,
                ret_file, cipher, cipher_key, bwlimit, txqueuelen) 

        # upload command to host_connect.sh script
        shfile = os.path.join(self.app_home(self.node_endpoint2), "host_connect.sh")
        self.node_endpoint2.upload(udp_connect_command, shfile,
                text = True,
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node_endpoint2.run(cmd, self.run_home(self.node_endpoint2),
                sudo  = True,
                stdout = "udp_stdout",
                stderr = "udp_stderr")

        # check if execution errors
        if proc.poll():
            msg = "Failed to connect endpoints"
            self.error(msg, out, err)
            raise RuntimeError, msg

        msg = "Connection on host %s configured" % self.node_endpoint2.get("hostname")
        self.debug(msg)
         
        # Wait for pid file to be generated
        pid, ppid = self.node_endpoint2.wait_pid(self.run_home(self.node_endpoint2))
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = self.node_endpoint2.check_errors(self.run_home(self.node_endpoint2))
            # Out is what was written in the stderr file
            if err:
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
                
        return (pid, ppid)

    def switch_to_switch_connect(self, endpoint, rem_endpoint):
        """ Get switch connect command
        """
        # Get and configure switch connection command

        local_port_name, remote_ip, remote_port_num = self.get_port_info(endpoint, rem_endpoint)


        switch_connect_command = endpoint.switch_connect_command(
                local_port_name, remote_ip, remote_port_num)
        node_endpoint = self.get_node(endpoint)        

        # Upload command to the file sw_connect.sh
        shfile = os.path.join(self.app_home(node_endpoint), "sw_connect.sh")
        node_endpoint.upload(switch_connect_command,
                shfile,
                text = True,
                overwrite = False)

        #invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = node_endpoint.run(cmd, self.run_home(node_endpoint),
                sudo  = True,
                stdout = "sw_stdout",
                stderr = "sw_stderr")
        
        # check if execution errors occured
        if proc.poll():
            msg = "Failed to connect endpoints"
            self.error(msg, out, err)
            raise RuntimeError, msg

        # For debugging
        msg = "Connection on port %s configured" % local_port_name
        self.info(msg)

    def wait_local_port(self):
        """ Waits until the if_name file for the command is generated, 
            and returns the if_name for the device """
        local_port = None
        delay = 1.0

        for i in xrange(10):
            (out, err), proc = self.node_endpoint2.check_output(self.run_home(self.node_endpoint2), 'local_port')
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

    def switch_to_host_connect(self, sw_endpoint, host_endpoint):
        """Link switch--> host
        """
        # Retrieve remote port number from sw_endpoint
        local_port_name = sw_endpoint.get('port_name')

        out = err= ''
        remote_port_num = self.wait_local_port()
        remote_ip = socket.gethostbyname(self.node_endpoint2.get("hostname"))
        switch_connect_command = sw_endpoint.switch_connect_command(
                local_port_name, remote_ip, remote_port_num)

        # Upload command to the file sw_connect.sh
        shfile = os.path.join(self.app_home(self.node_endpoint1), "sw_connect.sh")
        self.node_endpoint1.upload(switch_connect_command,
                shfile,
                text = True,
                overwrite = False)

        # Invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node_endpoint1.run(cmd, self.run_home(self.node_endpoint1),
                sudo  = True,
                stdout = "sw_stdout",
                stderr = "sw_stderr")
        
        # Check if execution errors occured

        if proc.poll():
            msg = "Failed to connect endpoints"
            self.error(msg, out, err)
            raise RuntimeError, msg

        # For debugging
        msg = "Connection on port %s configured" % local_port_name
        self.debug(msg)                                                   

    def do_provision(self):
        """ Provision the tunnel

           ..note : Endpoint 1 is always a OVSPort. 
                    Endpoint 2 can be either a OVSPort or a Tap
                     
        """
        self.node_endpoint1 = self.get_node(self.endpoint1)
        self.node_endpoint1.mkdir(self.run_home(self.node_endpoint1))

        self.node_endpoint2 = self.get_node(self.endpoint2)
        self.node_endpoint2.mkdir(self.run_home(self.node_endpoint2))

        if not self.check_switch_host_link:
            # Invoke connect script between switches
            self.switch_to_switch_connect(self.endpoint1, self.endpoint2)
            self.switch_to_switch_connect(self.endpoint2, self.endpoint1)
        else: 
            # Invoke connect script between switch & host
            (self._pid, self._ppid) = self.host_to_switch_connect(self.endpoint2, self.endpoint1)
            self.switch_to_host_connect(self.endpoint1, self.endpoint2)

        #super(OVSTunnel, self).do_provision()

    def configure(self):
        if  self.check_switch_host_link:
            self._vroute = self.ec.register_resource("PlanetlabVroute")
            self.ec.set(self._vroute, "action", "add")
            self.ec.set(self._vroute, "network", self.get("network"))

            self.ec.register_connection(self._vroute, self.tap.guid)
            # schedule deploy
            self.ec.deploy(guids=[self._vroute], group = self.deployment_group)

    def do_deploy(self):
        if (not self.endpoint1 or self.endpoint1.state < ResourceState.READY) or \
            (not self.endpoint2 or self.endpoint2.state < ResourceState.READY):
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()
        self.configure()

        self.set_ready()
        #super(OVSTunnel, self).do_deploy()
 
    def do_release(self):
        """ Release the udp_tunnel on endpoint2.
            On endpoint1 means nothing special.        
        """
        if not self.check_switch_host_link:
            # Kill the TAP devices
            # TODO: Make more generic Release method of PLTAP
            if self._pid and self._ppid:
                (out, err), proc = self.node_enpoint2.kill(self._pid,
                        self._ppid, sudo = True)

                if err or proc.poll():
                    msg = " Failed to delete TAP device"
                    self.error(msg, out, err)

        super(OVSTunnel, self).do_release()

