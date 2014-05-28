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
# Author: Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay 
from nepi.resources.linux.node import LinuxNode
from nepi.util.sfaapi import SFAAPIFactory 
from nepi.util.execfuncs import lexec
from nepi.util import sshfuncs

from random import randint
import time
import re
import weakref
import socket
import threading
import datetime

@clsinit_copy
class WilabtSfaNode(LinuxNode):
    _rtype = "WilabtSfaNode"
    _help = "Controls a Wilabt host accessible using a SSH key " \
            "and provisioned using SFA"
    _backend = "omf"

    @classmethod
    def _register_attributes(cls):

        sfa_user = Attribute("sfauser", "SFA user",
                    flags = Flags.Credential)

        sfa_private_key = Attribute("sfaPrivateKey", "SFA path to the private key \
                            used to generate the user credential",
                            flags = Flags.Credential)

        slicename = Attribute("slicename", "SFA slice for the experiment",
                    flags = Flags.Credential)

        gateway_user = Attribute("gatewayUser", "Gateway account username",
                flags = Flags.Design)

        gateway = Attribute("gateway", "Hostname of the gateway machine",
                flags = Flags.Design)

        cls._register_attribute(sfa_user)
        cls._register_attribute(sfa_private_key)
        cls._register_attribute(slicename)
        cls._register_attribute(gateway_user)
        cls._register_attribute(gateway)

    def __init__(self, ec, guid):
        super(WilabtSfaNode, self).__init__(ec, guid)

        self._ecobj = weakref.ref(ec)
        self._sfaapi = None
        self._node_to_provision = None
        self._slicenode = False
        self._hostname = False
        self._username = None

    def _skip_provision(self):
        sfa_user = self.get("sfauser")
        if not sfa_user:
            return True
        else: return False
    
    @property
    def sfaapi(self):
        """
        Property to instanciate the SFA API based in sfi client.
        For each SFA method called this instance is used.
        """
        if not self._sfaapi:
            sfa_user = self.get("sfauser")
            sfa_sm = "http://www.wilab2.ilabt.iminds.be:12369/protogeni/xmlrpc/am/3.0"
            sfa_auth = '.'.join(sfa_user.split('.')[:2])
            sfa_registry = "http://sfa3.planet-lab.eu:12345/"
            sfa_private_key = self.get("sfaPrivateKey")
            batch = True

            _sfaapi = SFAAPIFactory.get_api(sfa_user, sfa_auth, 
                sfa_registry, sfa_sm, sfa_private_key, self._ecobj(), batch, WilabtSfaNode._rtype)
            
            if not _sfaapi:
                self.fail_sfaapi()

            self._sfaapi = weakref.ref(_sfaapi)

        return self._sfaapi()

    def do_discover(self):
        """
        Based on the attributes defined by the user, discover the suitable 
        node for provision.
        """
        if self._skip_provision():
            super(WilabtSfaNode, self).do_discover()
            return

        nodes = self.sfaapi.get_resources_hrn()

        hostname = self._get_hostname()
        if hostname:
            # the user specified one particular node to be provisioned
            self._hostname = True
            host_hrn = nodes[hostname]

            # check that the node is not blacklisted or being provisioned
            # by other RM
            if not self._blacklisted(host_hrn):
                if not self._reserved(host_hrn):
                    if self._check_if_in_slice([host_hrn]):
                        self.debug("Node already in slice %s" % host_hrn)
                        self._slicenode = True
                    hostname = hostname + '.wilab2.ilabt.iminds.be'
                    self.set('hostname', hostname)
                    self._node_to_provision = host_hrn
                    super(WilabtSfaNode, self).do_discover()

    def do_provision(self):
        """
        Add node to user's slice and verifing that the node is functioning
        correctly. Check ssh, omf rc running, hostname, file system.
        """
        if self._skip_provision():
            super(WilabtSfaNode, self).do_provision()
            return

        provision_ok = False
        ssh_ok = False
        proc_ok = False
        timeout = 300

        while not provision_ok:
            node = self._node_to_provision
            if self._slicenode:
                self._delete_from_slice()
                self.debug("Waiting 300 seg for re-adding to slice")
                time.sleep(300) # Timout for the testbed to allow a new reservation
            self._add_node_to_slice(node)
            t = 0
            while not self._check_if_in_slice([node]) and t < timeout \
                and not self._ecobj().abort:
                t = t + 5
                time.sleep(t)
                self.debug("Waiting 5 seg for resources to be added")
                continue

            if not self._check_if_in_slice([node]):
                self.debug("Couldn't add node %s to slice" % node)
                self.fail_node_not_available(node)

            self._get_username()
            ssh_ok = self._check_ssh_loop()          

            if not ssh_ok:
                # the timeout was reach without establishing ssh connection
                # the node is blacklisted, and a new
                # node to provision is discovered
                self._blacklist_node(node)
                self.do_discover()
                continue
            
            # check /proc directory is mounted (ssh_ok = True)
            # file system is not read only, hostname is correct
            # and omf_rc process is up
            else:
                if not self._check_fs():
                    self.do_discover()
                    continue
                if not self._check_omf():
                    self.do_discover()
                    continue
                if not self._check_hostname():
                    self.do_discover()
                    continue
            
                else:
                    provision_ok = True
                    if not self.get('hostname'):
                        self._set_hostname_attr(node)            
                    self.info(" Node provisioned ")            
            
        super(WilabtSfaNode, self).do_provision()

    def _blacklisted(self, host_hrn):
        """
        Check in the SFA API that the node is not in the blacklist.
        """
        if self.sfaapi.blacklisted(host_hrn):
           self.fail_node_not_available(host_hrn)
        return False

    def _reserved(self, host_hrn):
        """
        Check in the SFA API that the node is not in the reserved
        list.
        """
        if self.sfaapi.reserved(host_hrn):
            self.fail_node_not_available(host_hrn)
        return False

    def _get_username(self):
        """
        Get the username for login in to the nodes from RSpec.
        Wilabt username is not made out of any convention, it
        has to be retrived from the manifest RSpec.
        """
        slicename = self.get("slicename")
        if self._username is None:
            slice_info = self.sfaapi.get_slice_resources(slicename)
            username = slice_info['resource'][0]['services'][0]['login'][0]['username']
            self.set('username', username)
            self.debug("Retriving username information from RSpec %s" % username)
            self._username = username
            
    def _check_ssh_loop(self):
        """
        Check that the ssh login is possible. In wilabt is done
        through the gateway because is private testbed.
        """
        t = 0
        timeout = 10
        ssh_ok = False
        while t < timeout and not ssh_ok:
            cmd = 'echo \'GOOD NODE\''
            ((out, err), proc) = self.execute(cmd)
            if out.find("GOOD NODE") < 0:
                self.debug( "No SSH connection, waiting 60s" )
                t = t + 5
                time.sleep(5)
                continue
            else:
                self.debug( "SSH OK" )
                ssh_ok = True
                continue
        return ssh_ok

    def _check_fs(self):
        """
        Check file system, /proc well mounted.
        """
        cmd = 'mount |grep proc'
        ((out, err), proc) = self.execute(cmd)
        if out.find("/proc type proc") < 0:
            self.warning(" Corrupted file system ")
            self._blacklist_node(node)
            return False
        return True

    def _check_omfrc(self):
        """
        Check that OMF 6 resource controller is running.
        """
        cmd = 'ps aux|grep omf'
        ((out, err), proc) = self.execute(cmd)
        if out.find("/usr/local/rvm/gems/ruby-1.9.3-p286@omf/bin/omf_rc") < 0:
            return False
        return True

    def _check_hostname(self):
        """
        Check that the hostname in the image is not set to localhost.
        """
        cmd = 'hostname'
        ((out, err), proc) = self.execute(cmd)
        if 'localhost' in out.lower():
            return False
        return True 

    def _add_node_to_slice(self, host_hrn):
        """
        Add node to slice, using SFA API. Actually Wilabt testbed
        doesn't allow adding nodes, in fact in the API there is method
        to group all the nodes instanciated as WilabtSfaNodes and the
        Allocate and Provision is done with the last call at 
        sfaapi.add_resource_to_slice_batch.
        """
        self.info(" Adding node to slice ")
        slicename = self.get("slicename")
        self.sfaapi.add_resource_to_slice_batch(slicename, host_hrn)

    def _delete_from_slice(self):
        """
        Delete every node from slice, using SFA API.
        Wilabt doesn't allow to remove one sliver so this method 
        remove every slice from the slice.
        """

        self.warning(" Deleting all slivers from slice ")
        slicename = self.get("slicename")
        self.sfaapi.remove_all_from_slice(slicename)

    def _get_hostname(self):
        """
        Get the attribute hostname.
        """
        hostname = self.get("hostname")
        if hostname:
            return hostname
        else:
            return None

    def _set_hostname_attr(self, node):
        """
        Query SFAAPI for the hostname of a certain host hrn and sets the
        attribute hostname, it will over write the previous value.
        """
        hosts_hrn = self.sfaapi.get_resources_hrn()
        for hostname, hrn  in hosts_hrn.iteritems():
            if hrn == node:
                hostname = hostname + '.wilab2.ilabt.iminds.be'
                self.set("hostname", hostname)

    def _check_if_in_slice(self, hosts_hrn):
        """
        Check using SFA API if any host hrn from hosts_hrn is in the user's
        slice.
        """
        slicename = self.get("slicename")
        slice_nodes = self.sfaapi.get_slice_resources(slicename)['resource']
        if slice_nodes:
            if len(slice_nodes[0]['services']) != 0:
                slice_nodes_hrn = self.sfaapi.get_resources_hrn(slice_nodes).values()
        else: slice_nodes_hrn = []
        nodes_inslice = list(set(hosts_hrn) & set(slice_nodes_hrn))
        return nodes_inslice

    def _do_ping(self, hostname):
        """
        Perform ping command on node's IP matching hostname.
        """
        ping_ok = False
        guser = self.get("gatewayUser")
        gw = self.get("gateway")
        host = hostname + ".wilab2.ilabt.iminds.be"
        command = "ssh %s@%s 'ping -c4 %s'" % (guser, gw, host)
        (out, err) = lexec(command)
        m = re.search("(\d+)% packet loss", str(out))
        if m and int(m.groups()[0]) < 50:
            ping_ok = True

        return ping_ok

    def _blacklist_node(self, host_hrn):
        """
        Add mal functioning node to blacklist (in SFA API).
        """
        self.warning(" Blacklisting malfunctioning node ")
        self.sfaapi.blacklist_resource(host_hrn)
        if not self._hostname:
            self.set('hostname', None)
        else:
            self.set('hostname', host_hrn.split('.').pop())

    def _put_node_in_provision(self, host_hrn):
        """
        Add node to the list of nodes being provisioned, in order for other RMs
        to not try to provision the same one again.
        """
        self.sfaapi.reserve_resource(host_hrn)

    def _get_ip(self, hostname):
        """
        Query cache for the IP of a node with certain hostname
        """
        try:
            ip = sshfuncs.gethostbyname(hostname)
        except:
            # Fail while trying to find the IP
            return None
        return ip

    def fail_discovery(self):
        msg = "Discovery failed. No candidates found for node"
        self.error(msg)
        raise RuntimeError, msg

    def fail_node_not_alive(self, hostname=None):
        msg = "Node %s not alive" % hostname
        raise RuntimeError, msg
    
    def fail_node_not_available(self, hostname):
        msg = "Node %s not available for provisioning" % hostname
        raise RuntimeError, msg

    def fail_not_enough_nodes(self):
        msg = "Not enough nodes available for provisioning"
        raise RuntimeError, msg

    def fail_plapi(self):
        msg = "Failing while trying to instanciate the PLC API.\nSet the" + \
            " attributes pluser and plpassword."
        raise RuntimeError, msg

    def valid_connection(self, guid):
        # TODO: Validate!
        return True


