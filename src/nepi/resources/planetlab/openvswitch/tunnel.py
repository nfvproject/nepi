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
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.planetlab.node import PlanetlabNode            
from nepi.resources.planetlab.openvswitch.ovs import OVSWitch   
from nepi.util.timefuncs import tnow, tdiffsec     

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
        self._nodes = []
        self._pid = None
        self._ppid = None


    def log_message(self, msg):
        return " guid %d - Tunnel - %s " % (self.guid, msg)

    @property
    def node(self):
        if self._nodes:
            return self._nodes[0]

    def app_home(self, node):
        return os.path.join(node.exp_home, self._home)

    def run_home(self, node):
        return os.path.join(self.app_home(node), self.ec.run_id)

    def port_endpoints(self):
        # Switch-Switch connection
        connected = []
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "create_port"):
                connected.append(rm)
        return connected

    def mixed_endpoints(self):
        # Switch-Host connection
        connected = [1, 2]
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "create_port"):
                connected[0] = rm
            elif hasattr(rm, "udp_connect_command"):
                connected[1] = rm
        return connected

    def get_node(self, endpoint):
        # Get connected to the nodes
        res = []
        if hasattr(endpoint, "create_port"):
            rm_list = endpoint.get_connected(OVSWitch.get_rtype())
            if rm_list:
                rm = rm_list[0].get_connected(PlanetlabNode.get_rtype())
        else:
            rm = endpoint.get_connected(PlanetlabNode.get_rtype())

        if rm :
            res.append(rm[0])
        return res

    @property
    def endpoint1(self):
        if self.check_endpoints():
            port_endpoints = self.port_endpoints()
            if port_endpoints: return port_endpoints[0]
        else:
            mixed_endpoints = self.mixed_endpoints()
            if mixed_endpoints: return mixed_endpoints[0]

    @property
    def endpoint2(self):
        if self.check_endpoints():
            port_endpoints = self.port_endpoints()
            if port_endpoints: return port_endpoints[1]
        else:
            mixed_endpoints = self.mixed_endpoints()
            if mixed_endpoints: return mixed_endpoints[1]
                
    def check_endpoints(self):
        """ Check if the links are between switches
            or switch-host. Return False for latter.
        """
        port_endpoints = self.port_endpoints()
        if len(port_endpoints) == 2:
            return True
        return False

    def get_port_info(self, endpoint, rem_endpoint):
        """ Retrieve the port_info list for each port
	
            :param port_info_tunl: [hostname, publ_IP_addr, port_name,
                virtual_ip, local_port_Numb]
            :type port_info_tunl: list
        """
        self.port_info_tunl = []
        if self.check_endpoints():
            # Use for the link switch-->switch
            self.port_info_tunl.append(endpoint.port_info)
            host0, ip0, pname0, virt_ip0, pnumber0 = self.port_info_tunl[0]
            self.port_info_tunl.append(rem_endpoint.port_info)
            host1, ip1, pname1, virt_ip1, pnumber1 = self.port_info_tunl[1]
            return (pname0, ip1, pnumber1)      
         
        # Use for the link host-->switch
        self.port_info_tunl.append(endpoint.port_info)
        host0, ip0, pname0, virt_ip0, pnumber0 = self.port_info_tunl[0]
        return pnumber0
    
    def udp_connect(self, endpoint, rem_endpoint):     
        # Collect info from rem_endpoint
        self._nodes = self.get_node(rem_endpoint)
        remote_ip = socket.gethostbyname(self.node.get("hostname"))
        # Collect info from endpoint
        self._nodes = self.get_node(endpoint) 
        local_port_file = os.path.join(self.run_home(self.node), 
                "local_port")
        remote_port_file = os.path.join(self.run_home(self.node), 
                "remote_port")
        ret_file = os.path.join(self.run_home(self.node), 
                "ret_file")
        cipher = self.get("cipher")
        cipher_key = self.get("cipherKey")
        bwlimit = self.get("bwLimit")
        txqueuelen = self.get("txQueueLen")

        rem_port = str(self.get_port_info(rem_endpoint, endpoint))           
        # Upload the remote port in a file
        self.node.upload(rem_port,
                remote_port_file,
                text = True,
                overwrite = False)
       
        udp_connect_command = endpoint.udp_connect_command(
                remote_ip, local_port_file, remote_port_file,
                ret_file, cipher, cipher_key, bwlimit, txqueuelen) 

        # upload command to host_connect.sh script
        shfile = os.path.join(self.app_home(self.node), "host_connect.sh")
        self.node.upload(udp_connect_command,
                shfile,
                text = True,
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, self.run_home(self.node),
                sudo  = True,
                stdout = "udp_stdout",
                stderr = "udp_stderr")

        # check if execution errors
        msg = "Failed to connect endpoints"

        if proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg

        msg = "Connection on host %s configured" \
            % self.node.get("hostname")
        self.debug(msg)
         
        # Wait for pid file to be generated
        self._nodes = self.get_node(endpoint) 
        pid, ppid = self.node.wait_pid(self.run_home(self.node))
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = self.node.check_errors(self.run_home(self.node))
            # Out is what was written in the stderr file
            if err:
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
                
        return (pid, ppid)

    def switch_connect(self, endpoint, rem_endpoint):
        """ Get switch connect command
        """
        # Get and configure switch connection command
        (local_port_name, remote_ip, remote_port_num) = self.get_port_info(
                endpoint, rem_endpoint)
        switch_connect_command = endpoint.switch_connect_command(
                local_port_name, remote_ip, remote_port_num)
        self._nodes = self.get_node(endpoint) 

        # Upload command to the file sw_connect.sh
        shfile = os.path.join(self.app_home(self.node), "sw_connect.sh")
        self.node.upload(switch_connect_command,
                shfile,
                text = True,
                overwrite = False)

        #invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, self.run_home(self.node),
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

    def sw_host_connect(self, endpoint, rem_endpoint):
        """Link switch--> host
        """
        # Retrieve remote port number from rem_endpoint
        local_port_name = endpoint.get('port_name')
        self._nodes = self.get_node(rem_endpoint)
        time.sleep(2) # Without this, sometimes I get nothing in remote_port_num
        remote_port_num = ''
        (out, err), proc = self.node.check_output(self.run_home(self.node), 'local_port')
        remote_port_num = int(out)
        remote_ip = socket.gethostbyname(self.node.get("hostname"))
        switch_connect_command = endpoint.switch_connect_command(
                local_port_name, remote_ip, remote_port_num)

        # Upload command to the file sw_connect.sh
        self._nodes = self.get_node(endpoint) 
        shfile = os.path.join(self.app_home(self.node), "sw_connect.sh")
        self.node.upload(switch_connect_command,
                shfile,
                text = True,
                overwrite = False)

        # Invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, self.run_home(self.node),
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
        """
        # Create folders
        self._nodes = self.get_node(self.endpoint1)
        self.node.mkdir(self.run_home(self.node))
        self._nodes = self.get_node(self.endpoint2)
        self.node.mkdir(self.run_home(self.node))

        if self.check_endpoints():
            #Invoke connect script between switches
            self.switch_connect(self.endpoint1, self.endpoint2)
            self.switch_connect(self.endpoint2, self.endpoint1)

        else: 
            # Invoke connect script between switch & host
            (self._pid, self._ppid) = self.udp_connect(self.endpoint2, self.endpoint1)
            self.sw_host_connect(self.endpoint1, self.endpoint2)

        super(OVSTunnel, self).do_provision()

    def do_deploy(self):
        if (not self.endpoint1 or self.endpoint1.state < ResourceState.READY) or \
            (not self.endpoint2 or self.endpoint2.state < ResourceState.READY):
            self.ec.schedule(reschedule_delay, self.deploy)
            return

        self.do_discover()
        self.do_provision()

        super(OVSTunnel, self).do_deploy()
 
    def do_release(self):
        """ Release the udp_tunnel on endpoint2.
            On endpoint1 means nothing special.        
        """
        if not self.check_endpoints():
            # Kill the TAP devices
            # TODO: Make more generic Release method of PLTAP
            if self._pid and self._ppid:
                self._nodes = self.get_node(self.endpoint2) 
                (out, err), proc = self.node.kill(self._pid,
                        self._ppid, sudo = True)
                if err or proc.poll():
                    # check if execution errors occurred
                    msg = " Failed to delete TAP device"
                    self.error(msg, err, err)

        super(OVSTunnel, self).do_release()

