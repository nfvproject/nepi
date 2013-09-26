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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.util.sshfuncs import ProcStatus
from nepi.util.timefuncs import tnow, tdiffsec

import os
import socket
import time

@clsinit_copy
class UdpTunnel(LinuxApplication):
    _rtype = "UdpTunnel"
    _help = "Constructs a tunnel between two Linux endpoints using a UDP connection "
    _backend = "linux"


    @classmethod
    def _register_attributes(cls):
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

        cls._register_attribute(cipher)
        cls._register_attribute(cipher_key)
        cls._register_attribute(txqueuelen)
        cls._register_attribute(bwlimit)

    def __init__(self, ec, guid):
        super(UdpTunnel, self).__init__(ec, guid)
        self._home = "udp-tunnel-%s" % self.guid
        self._pid1 = None
        self._ppid1 = None
        self._pid2 = None
        self._ppid2 = None

    def log_message(self, msg):
        return " guid %d - tunnel %s - %s - %s " % (self.guid, 
                self.endpoint1.node.get("hostname"), 
                self.endpoint2.node.get("hostname"), 
                msg)

    def get_endpoints(self):
        """ Returns the list of RM that are endpoints to the tunnel 
        """
        connected = []
        for guid in self.connections:
            rm = self.ec.get_resource(guid)
            if hasattr(rm, "udp_connect_command"):
                connected.append(rm)
        return connected

    @property
    def endpoint1(self):
        endpoints = self.get_endpoints()
        if endpoints: return endpoints[0]
        return None

    @property
    def endpoint2(self):
        endpoints = self.get_endpoints()
        if endpoints and len(endpoints) > 1: return endpoints[1]
        return None

    def app_home(self, endpoint):
        return os.path.join(endpoint.node.exp_home, self._home)

    def run_home(self, endpoint):
        return os.path.join(self.app_home(endpoint), self.ec.run_id)

    def udp_connect(self, endpoint, remote_ip):
        # Get udp connect command
        local_port_file = os.path.join(self.run_home(endpoint), 
                "local_port")
        remote_port_file = os.path.join(self.run_home(endpoint), 
                "remote_port")
        ret_file = os.path.join(self.run_home(endpoint), 
                "ret_file")
        cipher = self.get("cipher")
        cipher_key = self.get("cipherKey")
        bwlimit = self.get("bwLimit")
        txqueuelen = self.get("txQueueLen")
        udp_connect_command = endpoint.udp_connect_command(
                remote_ip, local_port_file, remote_port_file,
                ret_file, cipher, cipher_key, bwlimit, txqueuelen)

        # upload command to connect.sh script
        shfile = os.path.join(self.app_home(endpoint), "udp-connect.sh")
        endpoint.node.upload(udp_connect_command,
                shfile,
                text = True, 
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = endpoint.node.run(cmd, self.run_home(endpoint)) 
             
        # check if execution errors occurred
        msg = " Failed to connect endpoints "
        
        if proc.poll():
            self.fail()
            self.error(msg, out, err)
            raise RuntimeError, msg
    
        # Wait for pid file to be generated
        pid, ppid = endpoint.node.wait_pid(self.run_home(endpoint))
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = endpoint.node.check_errors(self.run_home(endpoint))
            # Out is what was written in the stderr file
            if err:
                self.fail()
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg

        # wait until port is written to file
        port = self.wait_local_port(endpoint)
        return (port, pid, ppid)

    def provision(self):
        # create run dir for tunnel on each node 
        self.endpoint1.node.mkdir(self.run_home(self.endpoint1))
        self.endpoint2.node.mkdir(self.run_home(self.endpoint2))

        # Invoke connect script in endpoint 1
        remote_ip1 = socket.gethostbyname(self.endpoint2.node.get("hostname"))
        (port1, self._pid1, self._ppid1) = self.udp_connect(self.endpoint1,
                remote_ip1)

        # Invoke connect script in endpoint 2
        remote_ip2 = socket.gethostbyname(self.endpoint1.node.get("hostname"))
        (port2, self._pid2, self._ppid2) = self.udp_connect(self.endpoint2,
                remote_ip2)

        # upload file with port 2 to endpoint 1
        self.upload_remote_port(self.endpoint1, port2)
        
        # upload file with port 1 to endpoint 2
        self.upload_remote_port(self.endpoint2, port1)

        # check if connection was successful on both sides
        self.wait_result(self.endpoint1)
        self.wait_result(self.endpoint2)
       
        self.info("Provisioning finished")
 
        self.set_provisioned()

    def deploy(self):
        if (not self.endpoint1 or self.endpoint1.state < ResourceState.READY) or \
            (not self.endpoint2 or self.endpoint2.state < ResourceState.READY):
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            try:
                self.discover()
                self.provision()
            except:
                self.fail()
                raise
 
            self.debug("----- READY ---- ")
            self.set_ready()

    def start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)
            
            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            self.fail()
            raise RuntimeError, msg

    def stop(self):
        """ Stops application execution
        """
        if self.state == ResourceState.STARTED:
            self.info("Stopping tunnel")
    
            # Only try to kill the process if the pid and ppid
            # were retrieved
            if self._pid1 and self._ppid1 and self._pid2 and self._ppid2:
                (out1, err1), proc1 = self.endpoint1.node.kill(self._pid1,
                        self._ppid1, sudo = True) 
                (out2, err2), proc2 = self.endpoint2.node.kill(self._pid2, 
                        self._ppid2, sudo = True) 

                if err1 or err2 or proc1.poll() or proc2.poll():
                    # check if execution errors occurred
                    msg = " Failed to STOP tunnel"
                    self.error(msg, err1, err2)
                    self.fail()

        if self.state == ResourceState.STARTED:
            self.set_stopped()

    @property
    def state(self):
        """ Returns the state of the application
        """
        if self._state == ResourceState.STARTED:
            # In order to avoid overwhelming the remote host and
            # the local processor with too many ssh queries, the state is only
            # requested every 'state_check_delay' seconds.
            state_check_delay = 0.5
            if tdiffsec(tnow(), self._last_state_check) > state_check_delay:
                if self._pid1 and self._ppid1 and self._pid2 and self._ppid2:
                    # Make sure the process is still running in background
                    # No execution errors occurred. Make sure the background
                    # process with the recorded pid is still running.
                    status1 = self.endpoint1.node.status(self._pid1, self._ppid1)
                    status2 = self.endpoint2.node.status(self._pid2, self._ppid2)

                    if status1 == ProcStatus.FINISHED and \
                            status2 == ProcStatus.FINISHED:

                        # check if execution errors occurred
                        (out1, err1), proc1 = self.endpoint1.node.check_errors(
                                self.run_home(self.endpoint1))

                        (out2, err2), proc2 = self.endpoint2.node.check_errors(
                                self.run_home(self.endpoint2))

                        if err1 or err2: 
                            msg = "Error occurred in tunnel"
                            self.error(msg, err1, err2)
                            self.fail()
                        else:
                            self.set_finished()

                self._last_state_check = tnow()

        return self._state

    def wait_local_port(self, endpoint):
        """ Waits until the local_port file for the endpoint is generated, 
        and returns the port number 
        
        """
        return self.wait_file(endpoint, "local_port")

    def wait_result(self, endpoint):
        """ Waits until the return code file for the endpoint is generated 
        
        """ 
        return self.wait_file(endpoint, "ret_file")
 
    def wait_file(self, endpoint, filename):
        """ Waits until file on endpoint is generated """
        result = None
        delay = 1.0

        for i in xrange(4):
            (out, err), proc = endpoint.node.check_output(
                    self.run_home(endpoint), filename)

            if out:
                result = out.strip()
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "Couldn't retrieve %s" % filename
            self.error(msg, out, err)
            self.fail()
            raise RuntimeError, msg

        return result

    def upload_remote_port(self, endpoint, port):
        # upload remote port number to file
        port = "%s\n" % port
        endpoint.node.upload(port,
                os.path.join(self.run_home(endpoint), "remote_port"),
                text = True, 
                overwrite = False)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

