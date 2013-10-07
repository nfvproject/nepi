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

from nepi.execution.attribute import Attribute, Types, Flags
from nepi.execution.resource import ResourceManager, clsinit, ResourceState, \
        reschedule_delay
from nepi.resources.linux.node import LinuxNode
from nepi.resources.linux.channel import LinuxChannel

import collections
import os
import random
import re
import tempfile
import time

# TODO: UP, MTU attributes!


@clsinit
class LinuxInterface(ResourceManager):
    _rtype = "LinuxInterface"
    _help = "Controls network devices on Linux hosts through the ifconfig tool"
    _backend = "linux"

    @classmethod
    def _register_attributes(cls):
        ip4 = Attribute("ip4", "IPv4 Address",
              flags = Flags.ExecReadOnly)

        ip6 = Attribute("ip6", "IPv6 Address",
                flags = Flags.ExecReadOnly)

        mac = Attribute("mac", "MAC Address",
                flags = Flags.ExecReadOnly)

        mask4 = Attribute("mask4", "IPv4 network mask",
                flags = Flags.ExecReadOnly)

        mask6 = Attribute("mask6", "IPv6 network mask",
                type = Types.Integer,
                flags = Flags.ExecReadOnly)

        mtu = Attribute("mtu", "Maximum transmition unit for device",
                type = Types.Integer)

        devname = Attribute("deviceName", 
                "Name of the network interface (e.g. eth0, wlan0, etc)",
                flags = Flags.ExecReadOnly)

        up = Attribute("up", "Link up", type = Types.Bool)

        tear_down = Attribute("tearDown", "Bash script to be executed before " + \
                "releasing the resource",
                flags = Flags.ExecReadOnly)

        cls._register_attribute(ip4)
        cls._register_attribute(ip6)
        cls._register_attribute(mac)
        cls._register_attribute(mask4)
        cls._register_attribute(mask6)
        cls._register_attribute(mtu)
        cls._register_attribute(devname)
        cls._register_attribute(up)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxInterface, self).__init__(ec, guid)
        self._configured = False
        
        self.add_set_hooks()

    def log_message(self, msg):
        return " guid %d - host %s - %s " % (self.guid, 
                self.node.get("hostname"), msg)

    @property
    def node(self):
        node = self.get_connected(LinuxNode.rtype())
        if node: return node[0]
        return None

    @property
    def channel(self):
        chan = self.get_connected(LinuxChannel.rtype())
        if chan: return chan[0]
        return None

    def discover(self):
        devname = self.get("deviceName")
        ip4 = self.get("ip4")
        ip6 = self.get("ip4")
        mac = self.get("mac")
        mask4 = self.get("mask4")
        mask6 = self.get("mask6")
        mtu = self.get("mtu")

        # Get current interfaces information
        (out, err), proc = self.node.execute("ifconfig", sudo = True, tty = True)

        if err and proc.poll():
            msg = " Error retrieving interface information "
            self.error(msg, out, err)
            raise RuntimeError, "%s - %s - %s" % (msg, out, err)
        
        # Check if an interface is found matching the RM attributes
        ifaces = out.split("\n\n")

        for i in ifaces:
            m = re.findall("(\w+)\s+Link\s+encap:\w+(\s+HWaddr\s+(([0-9a-fA-F]{2}:?){6}))?(\s+inet\s+addr:((\d+\.?){4}).+Mask:(\d+\.\d+\.\d+\.\d+))?(.+inet6\s+addr:\s+([0-9a-fA-F:.]+)/(\d+))?(.+(UP))?(.+MTU:(\d+))?", i, re.DOTALL)
            
            m = m[0]
            dn = m[0]
            mc = m[2]
            i4 = m[5]
            msk4 = m[7]
            i6 = m[9]
            msk6 = m[10]
            up = True if m[12] else False
            mu = m[14]

            self.debug("Found interface %(devname)s with MAC %(mac)s,"
                    "IPv4 %(ipv4)s %(mask4)s IPv6 %(ipv6)s/%(mask6)s %(up)s %(mtu)s" % ({
                'devname': dn,
                'mac': mc,
                'ipv4': i4,
                'mask4': msk4,
                'ipv6': i6,
                'mask6': msk6,
                'up': up,
                'mtu': mu
                }) )

            # If the user didn't provide information we take the first 
            # interface that is UP
            if not devname and not ip4 and not ip6 and up:
                self._configured = True
                self.load_configuration(dn, mc, i4, msk4, i6, msk6, mu, up)
                break

            # If the user provided ipv4 or ipv6 matching that of an interface
            # load the interface info
            if (ip4 and ip4 == i4) or (ip6 and ip6 == i6):
                self._configured = True
                self.load_configuration(dn, mc, i4, msk4, i6, msk6, mu, up)
                break

            # If the user provided the device name we load the associated info
            if devname and devname == dn:
                if ((ip4 and ip4 == i4) and (ipv6 and ip6 == i6)) or \
                        not (ip4 or ip6):
                    self._configured = True
               
                # If the user gave a different ip than the existing, asume ip 
                # needs to be changed
                i4 = ip4 or i4
                i6 = ip6 or i6
                mu = mtu or mu 

                self.load_configuration(dn, mc, i4, msk4, i6, msk6, mu, up)
                break
       
        if not self.get("deviceName"):
            msg = "Unable to resolve interface "
            self.error(msg)
            raise RuntimeError, msg

        super(LinuxInterface, self).discover()

    def provision(self):
        devname = self.get("deviceName")
        ip4 = self.get("ip4")
        ip6 = self.get("ip4")
        mac = self.get("mac")
        mask4 = self.get("mask4")
        mask6 = self.get("mask6")
        mtu = self.get("mtu")

        # Must configure interface if configuration is required
        if not self._configured:
            cmd = "ifconfig %s" % devname

            if ip4 and mask4:
                cmd += " %(ip4)s netmask %(mask4)s broadcast %(bcast)s up" % ({
                    'ip4': ip4,
                    'mask4': mask4,
                    'bcast': bcast})
            if mtu:
                cmd += " mtu %d " % mtu

            (out, err), proc = self.node.execute(cmd, sudo = True)

            if err and proc.poll():
                msg = "Error configuring interface with command '%s'" % cmd
                self.error(msg, out, err)
                raise RuntimeError, "%s - %s - %s" % (msg, out, err)

            if ip6 and mask6:
                cmd = "ifconfig %(devname)s inet6 add %(ip6)s/%(mask6)d" % ({
                        'devname': devname,
                        'ip6': ip6,
                        'mask6': mask6})

            (out, err), proc = self.node.execute(cmd, sudo = True)

            if err and proc.poll():
                msg = "Error seting ipv6 for interface using command '%s' " % cmd
                self.error(msg, out, err)
                raise RuntimeError, "%s - %s - %s" % (msg, out, err)

        super(LinuxInterface, self).provision()

    def deploy(self):
        # Wait until node is provisioned
        node = self.node
        chan = self.channel

        if not node or node.state < ResourceState.PROVISIONED:
            self.ec.schedule(reschedule_delay, self.deploy)
        elif not chan or chan.state < ResourceState.READY:
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            # Verify if the interface exists in node. If not, configue
            # if yes, load existing configuration
            try:
                self.discover()
                self.provision()
            except:
                self.fail()
                return 

            super(LinuxInterface, self).deploy()

    def release(self):
        tear_down = self.get("tearDown")
        if tear_down:
            self.execute(tear_down)

        super(LinuxInterface, self).release()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

    def load_configuration(self, devname, mac, ip4, mask4, ip6, mask6, mtu, up):
        self.set("deviceName", devname)
        self.set("mac", mac)
        self.set("ip4", ip4)
        self.set("mask4", mask4)
        self.set("ip6", ip6)
        self.set("mask6", mask6)

        # set the following without validating or triggering hooks
        attr = self._attrs["up"]
        attr._value = up
        attr = self._attrs["mtu"]

    def add_set_hooks(self):
        attrup = self._attrs["up"]
        attrup.set_hook = self.set_hook_up

        attrmtu = self._attrs["mtu"]
        attrmtu.set_hook = self.set_hook_mtu

    def set_hook_up(self, oldval, newval):
        if oldval == newval:
            return oldval

        # configure interface up
        if newval == True:
            cmd = "ifup %s" % self.get("deviceName")
        elif newval == False:
            cmd = "ifdown %s" % self.get("deviceName")

        (out, err), proc = self.node.execute(cmd, sudo = True)

        if err and proc.poll():
            msg = "Error setting interface up/down using command '%s' " % cmd
            self.error(msg, err, out)
            return oldval
        
        return newval

    def set_hook_mtu(self, oldval, newval):
        if oldval == newval:
            return oldval

        cmd = "ifconfig %s mtu %d" % (self.get("deviceName"), newval)

        (out, err), proc = self.node.execute(cmd, sudo = True)

        if err and proc.poll():
            msg = "Error setting interface MTU using command '%s' " % cmd
            self.error(msg, err, out)
            return  oldval
        
        return newval

