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
#         Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay 
from nepi.resources.linux.node import LinuxNode
from nepi.resources.planetlab.plcapi import PLCAPIFactory 
from nepi.util.execfuncs import lexec
from nepi.util import sshfuncs

from random import randint
import time
import socket
import threading
import datetime

@clsinit_copy
class PlanetlabNode(LinuxNode):
    _rtype = "PlanetlabNode"
    _help = "Controls a PlanetLab host accessible using a SSH key " \
            "associated to a PlanetLab user account"
    _backend = "planetlab"

    lock = threading.Lock()

    @classmethod
    def _register_attributes(cls):
        ip = Attribute("ip", "PlanetLab host public IP address",
                    flags = Flags.Design)

        pl_url = Attribute("plcApiUrl", "URL of PlanetLab PLCAPI host \
                    (e.g. www.planet-lab.eu or www.planet-lab.org) ",
                    default = "www.planet-lab.eu",
                    flags = Flags.Credential)

        pl_ptn = Attribute("plcApiPattern", "PLC API service regexp pattern \
                    (e.g. https://%(hostname)s:443/PLCAPI/ ) ",
                    default = "https://%(hostname)s:443/PLCAPI/",
                    flags = Flags.Design)
    
        pl_user = Attribute("pluser", "PlanetLab account user, as the one to \
                    authenticate in the website) ",
                    flags = Flags.Credential)

        pl_password = Attribute("plpassword", 
                        "PlanetLab account password, as \
                        the one to authenticate in the website) ",
                        flags = Flags.Credential)

        city = Attribute("city", "Constrain location (city) during resource \
                discovery. May use wildcards.",
                flags = Flags.Filter)

        country = Attribute("country", "Constrain location (country) during \
                    resource discovery. May use wildcards.",
                    flags = Flags.Filter)

        region = Attribute("region", "Constrain location (region) during \
                    resource discovery. May use wildcards.",
                    flags = Flags.Filter)

        architecture = Attribute("architecture", "Constrain architecture \
                        during resource discovery.",
                        type = Types.Enumerate,
                        allowed = ["x86_64", 
                                    "i386"],
                        flags = Flags.Filter)

        operating_system = Attribute("operatingSystem", "Constrain operating \
                            system during resource discovery.",
                            type = Types.Enumerate,
                            allowed =  ["f8",
                                        "f12",
                                        "f14",
                                        "centos",
                                        "other"],
                            flags = Flags.Filter)

        #site = Attribute("site", "Constrain the PlanetLab site this node \
        #        should reside on.",
        #        type = Types.Enumerate,
        #        allowed = ["PLE",
        #                    "PLC",
        #                    "PLJ"],
        #        flags = Flags.Filter)

        min_reliability = Attribute("minReliability", "Constrain reliability \
                            while picking PlanetLab nodes. Specifies a lower \
                            acceptable bound.",
                            type = Types.Double,
                            range = (1, 100),
                            flags = Flags.Filter)

        max_reliability = Attribute("maxReliability", "Constrain reliability \
                            while picking PlanetLab nodes. Specifies an upper \
                            acceptable bound.",
                            type = Types.Double,
                            range = (1, 100),
                            flags = Flags.Filter)

        min_bandwidth = Attribute("minBandwidth", "Constrain available \
                            bandwidth while picking PlanetLab nodes. \
                            Specifies a lower acceptable bound.",
                            type = Types.Double,
                            range = (0, 2**31),
                            flags = Flags.Filter)

        max_bandwidth = Attribute("maxBandwidth", "Constrain available \
                            bandwidth while picking PlanetLab nodes. \
                            Specifies an upper acceptable bound.",
                            type = Types.Double,
                            range = (0, 2**31),
                            flags = Flags.Filter)

        min_load = Attribute("minLoad", "Constrain node load average while \
                    picking PlanetLab nodes. Specifies a lower acceptable \
                    bound.",
                    type = Types.Double,
                    range = (0, 2**31),
                    flags = Flags.Filter)

        max_load = Attribute("maxLoad", "Constrain node load average while \
                    picking PlanetLab nodes. Specifies an upper acceptable \
                    bound.",
                    type = Types.Double,
                    range = (0, 2**31),
                    flags = Flags.Filter)

        min_cpu = Attribute("minCpu", "Constrain available cpu time while \
                    picking PlanetLab nodes. Specifies a lower acceptable \
                    bound.",
                    type = Types.Double,
                    range = (0, 100),
                    flags = Flags.Filter)

        max_cpu = Attribute("maxCpu", "Constrain available cpu time while \
                    picking PlanetLab nodes. Specifies an upper acceptable \
                    bound.",
                    type = Types.Double,
                    range = (0, 100),
                    flags = Flags.Filter)

        timeframe = Attribute("timeframe", "Past time period in which to check\
                        information about the node. Values are year,month, \
                        week, latest",
                        default = "week",
                        type = Types.Enumerate,
                        allowed = ["latest",
                                    "week",
                                    "month",
                                    "year"],
                        flags = Flags.Filter)

#        plblacklist = Attribute("blacklist", "Take into account the file plblacklist \
#                        in the user's home directory under .nepi directory. This file \
#                        contains a list of PL nodes to blacklist, and at the end \
#                        of the experiment execution the new blacklisted nodes are added.",
#                    type = Types.Bool,
#                    default = True,
#                    flags = Flags.ReadOnly)
#

        cls._register_attribute(ip)
        cls._register_attribute(pl_url)
        cls._register_attribute(pl_ptn)
        cls._register_attribute(pl_user)
        cls._register_attribute(pl_password)
        #cls._register_attribute(site)
        cls._register_attribute(city)
        cls._register_attribute(country)
        cls._register_attribute(region)
        cls._register_attribute(architecture)
        cls._register_attribute(operating_system)
        cls._register_attribute(min_reliability)
        cls._register_attribute(max_reliability)
        cls._register_attribute(min_bandwidth)
        cls._register_attribute(max_bandwidth)
        cls._register_attribute(min_load)
        cls._register_attribute(max_load)
        cls._register_attribute(min_cpu)
        cls._register_attribute(max_cpu)
        cls._register_attribute(timeframe)

    def __init__(self, ec, guid):
        super(PlanetlabNode, self).__init__(ec, guid)

        self._plapi = None
        self._node_to_provision = None
        self._slicenode = False
        self._hostname = False

        if self.get("gateway") or self.get("gatewayUser"):
            self.set("gateway", None)
            self.set("gatewayUser", None)

    def _skip_provision(self):
        pl_user = self.get("pluser")
        pl_pass = self.get("plpassword")
        if not pl_user and not pl_pass:
            return True
        else: return False
    
    @property
    def plapi(self):
        if not self._plapi:
            pl_user = self.get("pluser")
            pl_pass = self.get("plpassword")
            pl_url = self.get("plcApiUrl")
            pl_ptn = self.get("plcApiPattern")

            self._plapi =  PLCAPIFactory.get_api(pl_user, pl_pass, pl_url,
                pl_ptn)
            
            if not self._plapi:
                self.fail_plapi()

        return self._plapi

    def do_discover(self):
        """
        Based on the attributes defined by the user, discover the suitable 
        nodes for provision.
        """
        if self._skip_provision():
            super(PlanetlabNode, self).do_discover()
            return

        hostname = self._get_hostname()
        if hostname:
            # the user specified one particular node to be provisioned
            self._hostname = True
            node_id = self._get_nodes_id({'hostname':hostname})
            node_id = node_id.pop()['node_id']

            # check that the node is not blacklisted or being provisioned
            # by other RM
            with PlanetlabNode.lock:
                plist = self.plapi.reserved()
                blist = self.plapi.blacklisted()
                if node_id not in blist and node_id not in plist:
                
                    # check that is really alive, by performing ping
                    ping_ok = self._do_ping(node_id)
                    if not ping_ok:
                        self._blacklist_node(node_id)
                        self.fail_node_not_alive(hostname)
                    else:
                        if self._check_if_in_slice([node_id]):
                            self._slicenode = True
                        self._put_node_in_provision(node_id)
                        self._node_to_provision = node_id
                else:
                    self.fail_node_not_available(hostname)
            super(PlanetlabNode, self).do_discover()
        
        else:
            # the user specifies constraints based on attributes, zero, one or 
            # more nodes can match these constraints 
            nodes = self._filter_based_on_attributes()

            # nodes that are already part of user's slice have the priority to
            # provisioned
            nodes_inslice = self._check_if_in_slice(nodes)
            nodes_not_inslice = list(set(nodes) - set(nodes_inslice))
            
            node_id = None
            if nodes_inslice:
                node_id = self._choose_random_node(nodes_inslice)
                self._slicenode = True                
                
            if not node_id:
                # Either there were no matching nodes in the user's slice, or
                # the nodes in the slice  were blacklisted or being provisioned
                # by other RM. Note nodes_not_inslice is never empty
                node_id = self._choose_random_node(nodes_not_inslice)
                self._slicenode = False

            if node_id:
                self._node_to_provision = node_id
                try:
                    self._set_hostname_attr(node_id)
                    self.info(" Selected node to provision ")
                    super(PlanetlabNode, self).do_discover()
                except:
                    with PlanetlabNode.lock:
                        self._blacklist_node(node_id)
                    self.do_discover()
            else:
               self.fail_not_enough_nodes() 
            
    def do_provision(self):
        """
        Add node to user's slice after verifing that the node is functioning
        correctly
        """
        if self._skip_provision():
            super(PlanetlabNode, self).do_provision()
            return

        provision_ok = False
        ssh_ok = False
        proc_ok = False
        timeout = 3600

        while not provision_ok:
            node = self._node_to_provision
            if not self._slicenode:
                self._add_node_to_slice(node)
                self.info( " Node added to slice ")
            
                # check ssh connection
                t = 0 
                while t < timeout and not ssh_ok:

                    cmd = 'echo \'GOOD NODE\''
                    ((out, err), proc) = self.execute(cmd)
                    if out.find("GOOD NODE") < 0:
                        self.info(" No SSH login, sleeping for 60 seconds ")
                        t = t + 60
                        time.sleep(60)
                        continue
                    else:
                        self.info(" SSH login OK ")
                        ssh_ok = True
                        continue
            else:
                cmd = 'echo \'GOOD NODE\''
                ((out, err), proc) = self.execute(cmd)
                if not out.find("GOOD NODE") < 0:
                    ssh_ok = True

            if not ssh_ok:
                # the timeout was reach without establishing ssh connection
                # the node is blacklisted, deleted from the slice, and a new
                # node to provision is discovered
                with PlanetlabNode.lock:
                    self.warning(" Could not SSH login ")
                    self._blacklist_node(node)
                    #self._delete_node_from_slice(node)
                self.do_discover()
                continue
            
            # check /proc directory is mounted (ssh_ok = True)
            # and file system is not read only
            else:
                cmd = 'mount |grep proc'
                ((out1, err1), proc1) = self.execute(cmd)
                cmd = 'touch /tmp/tmpfile; rm /tmp/tmpfile'
                ((out2, err2), proc2) = self.execute(cmd)
                if out1.find("/proc type proc") < 0 or \
                    "Read-only file system".lower() in err2.lower():
                    with PlanetlabNode.lock:
                        self.warning(" Corrupted file system ")
                        self._blacklist_node(node)
                        #self._delete_node_from_slice(node)
                    self.do_discover()
                    continue
            
                else:
                    provision_ok = True
                    if not self.get('hostname'):
                        self._set_hostname_attr(node)            
                    # set IP attribute
                    ip = self._get_ip(node)
                    self.set("ip", ip)
                    self.info(" Node provisioned ")            
            
        super(PlanetlabNode, self).do_provision()

    def _filter_based_on_attributes(self):
        """
        Retrive the list of nodes ids that match user's constraints 
        """
        # Map user's defined attributes with tagnames of PlanetLab
        timeframe = self.get("timeframe")[0]
        attr_to_tags = {
            'city' : 'city',
            'country' : 'country',
            'region' : 'region',
            'architecture' : 'arch',
            'operatingSystem' : 'fcdistro',
            #'site' : 'pldistro',
            'minReliability' : 'reliability%s' % timeframe,
            'maxReliability' : 'reliability%s' % timeframe,
            'minBandwidth' : 'bw%s' % timeframe,
            'maxBandwidth' : 'bw%s' % timeframe,
            'minLoad' : 'load%s' % timeframe,
            'maxLoad' : 'load%s' % timeframe,
            'minCpu' : 'cpu%s' % timeframe,
            'maxCpu' : 'cpu%s' % timeframe,
        }
        
        nodes_id = []
        filters = {}

        for attr_name, attr_obj in self._attrs.iteritems():
            attr_value = self.get(attr_name)
            
            if attr_value is not None and attr_obj.has_flag(Flags.Filter) and \
                attr_name != 'timeframe':
        
                attr_tag = attr_to_tags[attr_name]
                filters['tagname'] = attr_tag

                # filter nodes by fixed constraints e.g. operating system
                if not 'min' in attr_name and not 'max' in attr_name:
                    filters['value'] = attr_value
                    nodes_id = self._filter_by_fixed_attr(filters, nodes_id)

                # filter nodes by range constraints e.g. max bandwidth
                elif ('min' or 'max') in attr_name:
                    nodes_id = self._filter_by_range_attr(attr_name, attr_value, filters, nodes_id)

        if not filters:
            nodes = self._get_nodes_id()
            for node in nodes:
                nodes_id.append(node['node_id'])
        return nodes_id
                    
    def _filter_by_fixed_attr(self, filters, nodes_id):
        """
        Query PLCAPI for nodes ids matching fixed attributes defined by the
        user
        """
        node_tags = self.plapi.get_node_tags(filters)
        if node_tags is not None:

            if len(nodes_id) == 0:
                # first attribute being matched
                for node_tag in node_tags:
                    nodes_id.append(node_tag['node_id'])
            else:
                # remove the nodes ids that don't match the new attribute
                # that is being match

                nodes_id_tmp = []
                for node_tag in node_tags:
                    if node_tag['node_id'] in nodes_id:
                        nodes_id_tmp.append(node_tag['node_id'])

                if len(nodes_id_tmp):
                    nodes_id = set(nodes_id) & set(nodes_id_tmp)
                else:
                    # no node from before match the new constraint
                    self.fail_discovery()
        else:
            # no nodes match the filter applied
            self.fail_discovery()

        return nodes_id

    def _filter_by_range_attr(self, attr_name, attr_value, filters, nodes_id):
        """
        Query PLCAPI for nodes ids matching attributes defined in a certain
        range, by the user
        """
        node_tags = self.plapi.get_node_tags(filters)
        if node_tags:
            
            if len(nodes_id) == 0:
                # first attribute being matched
                for node_tag in node_tags:
 
                   # check that matches the min or max restriction
                    if 'min' in attr_name and node_tag['value'] != 'n/a' and \
                        float(node_tag['value']) > attr_value:
                        nodes_id.append(node_tag['node_id'])

                    elif 'max' in attr_name and node_tag['value'] != 'n/a' and \
                        float(node_tag['value']) < attr_value:
                        nodes_id.append(node_tag['node_id'])
            else:

                # remove the nodes ids that don't match the new attribute
                # that is being match
                nodes_id_tmp = []
                for node_tag in node_tags:

                    # check that matches the min or max restriction and was a
                    # matching previous filters
                    if 'min' in attr_name and node_tag['value'] != 'n/a' and \
                        float(node_tag['value']) > attr_value and \
                        node_tag['node_id'] in nodes_id:
                        nodes_id_tmp.append(node_tag['node_id'])

                    elif 'max' in attr_name and node_tag['value'] != 'n/a' and \
                        float(node_tag['value']) < attr_value and \
                        node_tag['node_id'] in nodes_id:
                        nodes_id_tmp.append(node_tag['node_id'])

                if len(nodes_id_tmp):
                    nodes_id = set(nodes_id) & set(nodes_id_tmp)
                else:
                    # no node from before match the new constraint
                    self.fail_discovery()

        else: #TODO CHECK
            # no nodes match the filter applied
            self.fail_discovery()

        return nodes_id
        
    def _choose_random_node(self, nodes):
        """
        From the possible nodes for provision, choose randomly to decrese the
        probability of different RMs choosing the same node for provision
        """
        size = len(nodes)
        while size:
            size = size - 1
            index = randint(0, size)
            node_id = nodes[index]
            nodes[index] = nodes[size]

            # check the node is not blacklisted or being provision by other RM
            # and perform ping to check that is really alive
            with PlanetlabNode.lock:

                blist = self.plapi.blacklisted()
                plist = self.plapi.reserved()
                if node_id not in blist and node_id not in plist:
                    ping_ok = self._do_ping(node_id)
                    if not ping_ok:
                        self._set_hostname_attr(node_id)
                        self.warning(" Node not responding PING ")
                        self._blacklist_node(node_id)
                    else:
                        # discovered node for provision, added to provision list
                        self._put_node_in_provision(node_id)
                        return node_id

    def _get_nodes_id(self, filters=None):
        return self.plapi.get_nodes(filters, fields=['node_id'])

    def _add_node_to_slice(self, node_id):
        self.info(" Adding node to slice ")
        slicename = self.get("username")
        with PlanetlabNode.lock:
            slice_nodes = self.plapi.get_slice_nodes(slicename)
            slice_nodes.append(node_id)
            self.plapi.add_slice_nodes(slicename, slice_nodes)

    def _delete_node_from_slice(self, node):
        self.warning(" Deleting node from slice ")
        slicename = self.get("username")
        self.plapi.delete_slice_node(slicename, [node])

    def _get_hostname(self):
        hostname = self.get("hostname")
        if hostname:
            return hostname
        ip = self.get("ip")
        if ip:
            hostname = socket.gethostbyaddr(ip)[0]
            self.set('hostname', hostname)
            return hostname
        else:
            return None

    def _set_hostname_attr(self, node):
        """
        Query PLCAPI for the hostname of a certain node id and sets the
        attribute hostname, it will over write the previous value
        """
        hostname = self.plapi.get_nodes(node, ['hostname'])
        self.set("hostname", hostname[0]['hostname'])

    def _check_if_in_slice(self, nodes_id):
        """
        Query PLCAPI to find out if any node id from nodes_id is in the user's
        slice
        """
        slicename = self.get("username")
        slice_nodes = self.plapi.get_slice_nodes(slicename)
        nodes_inslice = list(set(nodes_id) & set(slice_nodes))
        return nodes_inslice

    def _do_ping(self, node_id):
        """
        Perform ping command on node's IP matching node id
        """
        ping_ok = False
        ip = self._get_ip(node_id)
        if not ip: return ping_ok

        command = "ping -c4 %s" % ip

        (out, err) = lexec(command)
        if not str(out).find("2 received") < 0 or not str(out).find("3 received") < 0 or not \
            str(out).find("4 received") < 0:
            ping_ok = True
       
        return ping_ok 

    def _blacklist_node(self, node):
        """
        Add node mal functioning node to blacklist
        """
        self.warning(" Blacklisting malfunctioning node ")
        self.plapi.blacklist_host(node)
        if not self._hostname:
            self.set('hostname', None)

    def _put_node_in_provision(self, node):
        """
        Add node to the list of nodes being provisioned, in order for other RMs
        to not try to provision the same one again
        """
        self.plapi.reserve_host(node)

    def _get_ip(self, node_id):
        """
        Query PLCAPI for the IP of a node with certain node id
        """
        hostname = self.get("hostname") or \
            self.plapi.get_nodes(node_id, ['hostname'])[0]['hostname']
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


