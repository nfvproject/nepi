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
from nepi.resources.planetlab.node import PlanetlabNode
from nepi.util.timefuncs import tnow, tdiffsec

import os
import socket
import time

PYTHON_VSYS_VERSION = "1.0"

@clsinit_copy
class PlanetlabTap(LinuxApplication):
    _rtype = "PlanetlabTap"
    _help = "Creates a TAP device on a PlanetLab host"
    _backend = "planetlab"

    @classmethod
    def _register_attributes(cls):
        ip4 = Attribute("ip4", "IPv4 Address",
              flags = Flags.Design)

        mac = Attribute("mac", "MAC Address",
                flags = Flags.Design)

        prefix4 = Attribute("prefix4", "IPv4 network prefix",
                type = Types.Integer,
                flags = Flags.Design)

        mtu = Attribute("mtu", "Maximum transmition unit for device",
                type = Types.Integer)

        devname = Attribute("deviceName", 
                "Name of the network interface (e.g. eth0, wlan0, etc)",
                flags = Flags.NoWrite)

        up = Attribute("up", "Link up", 
                type = Types.Bool)
        
        snat = Attribute("snat", "Set SNAT=1", 
                type = Types.Bool,
                flags = Flags.Design)
        
        pointopoint = Attribute("pointopoint", "Peer IP address", 
                flags = Flags.Design)

        txqueuelen = Attribute("txqueuelen", "Length of transmission queue", 
                flags = Flags.Design)

        txqueuelen = Attribute("txqueuelen", "Length of transmission queue", 
                flags = Flags.Design)

        gre_key = Attribute("greKey", 
                "GRE key to be used to configure GRE tunnel", 
                default = "1",
                flags = Flags.Design)

        gre_remote = Attribute("greRemote", 
                "Public IP of remote endpoint for GRE tunnel", 
                flags = Flags.Design)

        tear_down = Attribute("tearDown", 
                "Bash script to be executed before releasing the resource",
                flags = Flags.Design)

        cls._register_attribute(ip4)
        cls._register_attribute(mac)
        cls._register_attribute(prefix4)
        cls._register_attribute(mtu)
        cls._register_attribute(devname)
        cls._register_attribute(up)
        cls._register_attribute(snat)
        cls._register_attribute(pointopoint)
        cls._register_attribute(txqueuelen)
        cls._register_attribute(gre_key)
        cls._register_attribute(gre_remote)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(PlanetlabTap, self).__init__(ec, guid)
        self._home = "tap-%s" % self.guid
        self._gre_enabled = False

    @property
    def node(self):
        node = self.get_connected(PlanetlabNode.get_rtype())
        if node: return node[0]
        return None

    @property
    def gre_enabled(self):
        if not self._gre_enabled:
            from nepi.resources.linux.gretunnel import LinuxGRETunnel
            gre = self.get_connected(LinuxGRETunnel.get_rtype())
            if gre: self._gre_enabled = True

        return self._gre_enabled

    def upload_sources(self):
        scripts = []

        # vif-creation python script
        pl_vif_create = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-vif-create.py")

        scripts.append(pl_vif_create)
        
        # vif-up python script
        pl_vif_up = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-vif-up.py")
        
        scripts.append(pl_vif_up)

        # vif-down python script
        pl_vif_down = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-vif-down.py")
        
        scripts.append(pl_vif_down)

        # udp-connect python script
        pl_vif_connect = os.path.join(os.path.dirname(__file__), "scripts",
                "pl-vif-udp-connect.py")
        
        scripts.append(pl_vif_connect)

        # tunnel creation python script
        tunchannel = os.path.join(os.path.dirname(__file__), "..", "linux",
                "scripts", "tunchannel.py")

        scripts.append(tunchannel)

        # Upload scripts
        scripts = ";".join(scripts)

        self.node.upload(scripts,
                os.path.join(self.node.src_dir),
                overwrite = False)

        # upload stop.sh script
        stop_command = self.replace_paths(self._stop_command)

        self.node.upload(stop_command,
                os.path.join(self.app_home, "stop.sh"),
                text = True,
                # Overwrite file every time. 
                # The stop.sh has the path to the socket, which should change
                # on every experiment run.
                overwrite = True)

    def upload_start_command(self):
        # If GRE mode is enabled, TAP creation is delayed until the
        # tunnel is established
        if not self.gre_enabled:
            # Overwrite file every time. 
            # The start.sh has the path to the socket, wich should change
            # on every experiment run.
            super(PlanetlabTap, self).upload_start_command(overwrite = True)

            # We want to make sure the device is up and running
            # before the deploy finishes, so we execute now the 
            # start script. We run it in background, because the 
            # TAP will live for as long as the process that 
            # created it is running, and wait until the TAP  
            # is created. 
            self._run_in_background()
            
            # After creating the TAP, the pl-vif-create.py script
            # will write the name of the TAP to a file. We wait until
            # we can read the interface name from the file.
            vif_name = self.wait_vif_name()
            self.set("deviceName", vif_name) 

    def do_deploy(self):
        if not self.node or self.node.state < ResourceState.PROVISIONED:
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("command"):
                self.set("command", self._start_command)

            if not self.get("depends"):
                self.set("depends", self._dependencies)

            if not self.get("install"):
                self.set("install", self._install)

            self.do_discover()
            self.do_provision()

            self.set_ready()

    def do_start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        command = self.get('command') or ''
        
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)

            command = "bash %s" % os.path.join(self.app_home, "stop.sh")
            (out, err), proc = self.execute_command(command,
                    blocking = True)

            if err:
                msg = " Failed to stop command '%s' " % command
                self.error(msg, out, err)

            self.set_stopped()

    @property
    def state(self):
        state_check_delay = 0.5
        if self._state == ResourceState.STARTED and \
                tdiffsec(tnow(), self._last_state_check) > state_check_delay:

            if self.get("deviceName"):
                (out, err), proc = self.node.execute("ifconfig")

                if out.strip().find(self.get("deviceName")) == -1: 
                    # tap is not running is not running (socket not found)
                    self.set_stopped()

            self._last_state_check = tnow()

        return self._state

    def do_release(self):
        # Node needs to wait until all associated RMs are released
        # to be released
        from nepi.resources.linux.tunnel import LinuxTunnel
        rms = self.get_connected(LinuxTunnel.get_rtype())

        for rm in rms:
            if rm.state < ResourceState.STOPPED:
                self.ec.schedule(reschedule_delay, self.release)
                return 

        super(PlanetlabTap, self).do_release()

    def wait_vif_name(self):
        """ Waits until the vif_name file for the command is generated, 
            and returns the vif_name for the device """
        vif_name = None
        delay = 0.5

        for i in xrange(20):
            (out, err), proc = self.node.check_output(self.run_home, "vif_name")

            if proc.poll() > 0:
                (out, err), proc = self.node.check_errors(self.run_home)
                
                if err.strip():
                    raise RuntimeError, err

            if out:
                vif_name = out.strip()
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "Couldn't retrieve vif_name"
            self.error(msg, out, err)
            raise RuntimeError, msg

        return vif_name

    def gre_connect(self, remote_endpoint, connection_app_home,
            connection_run_home):
        gre_connect_command = self._gre_connect_command(
                remote_endpoint, connection_run_home)

        # upload command to connect.sh script
        shfile = os.path.join(connection_app_home, "gre-connect.sh")
        self.node.upload(gre_connect_command,
                shfile,
                text = True, 
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, connection_run_home) 
             
        # check if execution errors occurred
        msg = " Failed to connect endpoints "
        
        if proc.poll() or err:
            self.error(msg, out, err)
            raise RuntimeError, msg
    
        # Wait for pid file to be generated
        pid, ppid = self.node.wait_pid(connection_run_home)
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = self.node.check_errors(connection_run_home)
            # Out is what was written in the stderr file
            if err:
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg
        
        # After creating the TAP, the pl-vif-create.py script
        # will write the name of the TAP to a file. We wait until
        # we can read the interface name from the file.
        vif_name = self.wait_vif_name()
        self.set("deviceName", vif_name) 

        return True

    def udp_connect(self, remote_endpoint, connection_app_home, 
            connection_run_home, cipher, cipher_key, bwlimit, txqueuelen):
        udp_connect_command = self._udp_connect_command(
                remote_endpoint, connection_run_home,
                cipher, cipher_key, bwlimit, txqueuelen)

        # upload command to connect.sh script
        shfile = os.path.join(connection_app_home, "udp-connect.sh")
        self.node.upload(udp_connect_command,
                shfile,
                text = True, 
                overwrite = False)

        # invoke connect script
        cmd = "bash %s" % shfile
        (out, err), proc = self.node.run(cmd, connection_run_home) 
             
        # check if execution errors occurred
        msg = "Failed to connect endpoints "
        
        if proc.poll():
            self.error(msg, out, err)
            raise RuntimeError, msg
    
        # Wait for pid file to be generated
        pid, ppid = self.node.wait_pid(connection_run_home)
        
        # If the process is not running, check for error information
        # on the remote machine
        if not pid or not ppid:
            (out, err), proc = self.node.check_errors(connection_run_home)
            # Out is what was written in the stderr file
            if err:
                msg = " Failed to start command '%s' " % command
                self.error(msg, out, err)
                raise RuntimeError, msg

        return pid, ppid

    def _udp_connect_command(self, remote_endpoint, connection_run_home, 
            cipher, cipher_key, bwlimit, txqueuelen):

        # Set the remote endpoint
        self.set("pointopoint", remote_endpoint.get("ip4"))

        remote_ip = socket.gethostbyname(
                remote_endpoint.node.get("hostname"))

        local_port_file = os.path.join(connection_run_home, 
                "local_port")

        remote_port_file = os.path.join(connection_run_home, 
                "remote_port")

        ret_file = os.path.join(connection_run_home, 
                "ret_file")

        # Generate UDP connect command
        # Use pl-vif-up.py script to configure TAP with peer info
        vif_up_command = self._vif_up_command
        
        command = ["( "]
        command.append(vif_up_command)

        # Use pl-vid-udp-connect.py to stablish the tunnel between endpoints
        command.append(") & (")
        command.append("sudo -S")
        command.append("PYTHONPATH=$PYTHONPATH:${SRC}")
        command.append("python ${SRC}/pl-vif-udp-connect.py")
        command.append("-t %s" % self.vif_type)
        command.append("-S %s " % self.sock_name)
        command.append("-l %s " % local_port_file)
        command.append("-r %s " % remote_port_file)
        command.append("-H %s " % remote_ip)
        command.append("-R %s " % ret_file)
        if cipher:
            command.append("-c %s " % cipher)
        if cipher_key:
            command.append("-k %s " % cipher_key)
        if txqueuelen:
            command.append("-q %s " % txqueuelen)
        if bwlimit:
            command.append("-b %s " % bwlimit)

        command.append(")")

        command = " ".join(command)
        command = self.replace_paths(command)

        return command

    def _gre_connect_command(self, remote_endpoint, connection_run_home): 
        # Set the remote endpoint
        self.set("pointopoint", remote_endpoint.get("ip4"))
        self.set("greRemote", socket.gethostbyname(
            remote_endpoint.node.get("hostname")))

        # Generate GRE connect command

        # Use vif_down command to first kill existing TAP in GRE mode
        vif_down_command = self._vif_down_command

        # Use pl-vif-up.py script to configure TAP with peer info
        vif_up_command = self._vif_up_command
        
        command = ["("]
        command.append(vif_down_command)
        command.append(") ; (")
        command.append(vif_up_command)
        command.append(")")

        command = " ".join(command)
        command = self.replace_paths(command)

        return command

    @property
    def _start_command(self):
        if self.gre_enabled:
            command = []
        else:
            command = ["sudo -S python ${SRC}/pl-vif-create.py"]
            
            command.append("-t %s" % self.vif_type)
            command.append("-a %s" % self.get("ip4"))
            command.append("-n %d" % self.get("prefix4"))
            command.append("-f %s " % self.vif_name_file)
            command.append("-S %s " % self.sock_name)

            if self.get("snat") == True:
                command.append("-s")

            if self.get("pointopoint"):
                command.append("-p %s" % self.get("pointopoint"))
            
            if self.get("txqueuelen"):
                command.append("-q %s" % self.get("txqueuelen"))

        return " ".join(command)

    @property
    def _stop_command(self):
        if self.gre_enabled:
            command = self._vif_down_command
        else:
            command = ["sudo -S "]
            command.append("PYTHONPATH=$PYTHONPATH:${SRC}")
            command.append("python ${SRC}/pl-vif-down.py")
            command.append("-S %s " % self.sock_name)
            command = " ".join(command)

        return command

    @property
    def _vif_up_command(self):
        if self.gre_enabled:
            device_name = "%s" % self.guid
        else:
            device_name = self.get("deviceName")

        # Use pl-vif-up.py script to configure TAP
        command = ["sudo -S "]
        command.append("PYTHONPATH=$PYTHONPATH:${SRC}")
        command.append("python ${SRC}/pl-vif-up.py")
        command.append("-u %s" % self.node.get("username"))
        command.append("-N %s" % device_name)
        command.append("-t %s" % self.vif_type)
        command.append("-a %s" % self.get("ip4"))
        command.append("-n %d" % self.get("prefix4"))

        if self.get("snat") == True:
            command.append("-s")

        if self.get("pointopoint"):
            command.append("-p %s" % self.get("pointopoint"))
        
        if self.get("txqueuelen"):
            command.append("-q %s" % self.get("txqueuelen"))

        if self.gre_enabled:
            command.append("-g %s" % self.get("greKey"))
            command.append("-G %s" % self.get("greRemote"))
        
        command.append("-f %s " % self.vif_name_file)

        return " ".join(command)

    @property
    def _vif_down_command(self):
        if self.gre_enabled:
            device_name = "%s" % self.guid
        else:
            device_name = self.get("deviceName")

        command = ["sudo -S "]
        command.append("PYTHONPATH=$PYTHONPATH:${SRC}")
        command.append("python ${SRC}/pl-vif-down.py")
        command.append("-N %s " % device_name)
        
        if self.gre_enabled:
            command.append("-u %s" % self.node.get("username"))
            command.append("-t %s" % self.vif_type)
            command.append("-D")

        return " ".join(command)

    @property
    def vif_type(self):
        return "IFF_TAP"

    @property
    def vif_name_file(self):
        return os.path.join(self.run_home, "vif_name")

    @property
    def sock_name(self):
        return os.path.join(self.run_home, "tap.sock")

    @property
    def _dependencies(self):
        return "mercurial make gcc"

    @property
    def _install(self):
        # Install python-vsys and python-passfd
        install_vsys = ( " ( "
                    "   python -c 'import vsys, os;  vsys.__version__ == \"%(version)s\" or os._exit(1)' "
                    " ) "
                    " || "
                    " ( "
                    "   cd ${SRC} ; "
                    "   hg clone http://nepi.inria.fr/code/python-vsys ; "
                    "   cd python-vsys ; "
                    "   make all ; "
                    "   sudo -S make install "
                    " )" ) % ({
                        "version": PYTHON_VSYS_VERSION
                        })

        install_passfd = ( " ( python -c 'import passfd' ) "
                    " || "
                    " ( "
                    "   cd ${SRC} ; "
                    "   hg clone http://nepi.inria.fr/code/python-passfd ; "
                    "   cd python-passfd ; "
                    "   make all ; "
                    "   sudo -S make install "
                    " )" )

        return "%s ; %s" % ( install_vsys, install_passfd )

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

