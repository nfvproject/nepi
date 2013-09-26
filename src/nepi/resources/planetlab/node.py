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
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.node import LinuxNode
from nepi.resources.planetlab.plcapi import PLCAPIFactory 
from nepi.util.execfuncs import lexec

from random import randint
import time
import threading

@clsinit_copy
class PlanetlabNode(LinuxNode):
    _rtype = "PlanetlabNode"
    _help = "Controls a PlanetLab host accessible using a SSH key " \
            "associated to a PlanetLab user account"
    _backend = "planetlab"

    blacklist = list()
    provisionlist = list()

    lock_blist = threading.Lock()
    lock_plist = threading.Lock()

    lock_slice = threading.Lock()


    @classmethod
    def _register_attributes(cls):
        ip = Attribute("ip", "PlanetLab host public IP address",
                flags = Flags.ReadOnly)

        pl_url = Attribute("plcApiUrl", "URL of PlanetLab PLCAPI host \
                    (e.g. www.planet-lab.eu or www.planet-lab.org) ",
                    default = "www.planet-lab.eu",
                    flags = Flags.Credential)

        pl_ptn = Attribute("plcApiPattern", "PLC API service regexp pattern \
                    (e.g. https://%(hostname)s:443/PLCAPI/ ) ",
                    default = "https://%(hostname)s:443/PLCAPI/",
                    flags = Flags.ExecReadOnly)
    
        pl_user = Attribute("pluser", "PlanetLab account user, as the one to \
                    authenticate in the website) ",
                    flags = Flags.Credential)

        pl_password = Attribute("password", 
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

        site = Attribute("site", "Constrain the PlanetLab site this node \
                should reside on.",
                type = Types.Enumerate,
                allowed = ["PLE",
                            "PLC",
                            "PLJ"],
                flags = Flags.Filter)

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

        cls._register_attribute(ip)
        cls._register_attribute(pl_url)
        cls._register_attribute(pl_ptn)
        cls._register_attribute(pl_user)
        cls._register_attribute(pl_password)
        cls._register_attribute(site)
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
    
    @property
    def plapi(self):
        if not self._plapi:
            pl_user = self.get("pluser")
            pl_pass = self.get("password")
            pl_url = self.get("plcApiUrl")
            pl_ptn = self.get("plcApiPattern")

            self._plapi =  PLCAPIFactory.get_api(pl_user, pl_pass, pl_url,
                    pl_ptn)
            
        return self._plapi

    def discoverl(self):
        """
        Based on the attributes defined by the user, discover the suitable nodes
        """
        hostname = self.get("hostname")
        if hostname:
            # the user specified one particular node to be provisioned
            # check with PLCAPI if it is alvive
            node_id = self._query_if_alive(hostname=hostname)
            node_id = node_id.pop()

            # check that the node is not blacklisted or already being provision 
            # by other RM
            blist = PlanetlabNode.blacklist
            plist = PlanetlabNode.provisionlist
            if node_id not in blist and node_id not in plist:
                
                # check that is really alive, by performing ping
                ping_ok = self._do_ping(node_id)
                if not ping_ok:
                    self._blacklist_node(node_id)
                    self.fail_node_not_alive(hostname)
                else:
                    self._node_to_provision = node_id
                    self._put_node_in_provision(node_id)
                    super(PlanetlabNode, self).discover()
                
            else:
                self.fail_node_not_available(hostname)                
        
        else:
            # the user specifies constraints based on attributes, zero, one or 
            # more nodes can match these constraints 
            nodes = self._filter_based_on_attributes()
            nodes_alive = self._query_if_alive(nodes)
    
            # nodes that are already part of user's slice have the priority to
            # provisioned
            nodes_inslice = self._check_if_in_slice(nodes_alive)
            nodes_not_inslice = list(set(nodes_alive) - set(nodes_inslice))
            
            node_id = None
            if nodes_inslice:
                node_id = self._choose_random_node(nodes_inslice)
                
            if not node_id and nodes_not_inslice:
                # Either there were no matching nodes in the user's slice, or
                # the nodes in the slice  were blacklisted or being provisioned
                # by other RM. Note nodes_not_inslice is never empty
                node_id = self._choose_random_node(nodes_not_inslice)
            if not node_id:
                self.fail_not_enough_nodes()

            self._node_to_provision = node_id
            super(PlanetlabNode, self).discover()
            
    def provisionl(self):
        """
        Add node to user's slice after verifing that the node is functioning
        correctly
        """
        provision_ok = False
        ssh_ok = False
        proc_ok = False
        timeout = 1200

        while not provision_ok:
            node = self._node_to_provision
            self._set_hostname_attr(node)
            self._add_node_to_slice(node)
            
            # check ssh connection
            t = 0 
            while t < timeout and not ssh_ok:

                cmd = 'echo \'GOOD NODE\''
                ((out, err), proc) = self.execute(cmd)
                if out.find("GOOD NODE") < 0:
                    t = t + 60
                    time.sleep(60)
                    continue
                else:
                    ssh_ok = True
                    continue

            if not ssh_ok:
                # the timeout was reach without establishing ssh connection
                # the node is blacklisted, deleted from the slice, and a new
                # node to provision is discovered
                self._blacklist_node(node)
                self._delete_node_from_slice(node)
                self.discover()
                continue
            
            # check /proc directory is mounted (ssh_ok = True)
            else:
                cmd = 'mount |grep proc'
                ((out, err), proc) = self.execute(cmd)
                if out.find("/proc type proc") < 0:
                    self._blacklist_node(node)
                    self._delete_node_from_slice(node)
                    self.discover()
                    continue
            
                else:
                    provision_ok = True
                    # set IP attribute
                    ip = self._get_ip(node)
                    self.set("ip", ip)
            
        super(PlanetlabNode, self).provision()

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
            
            if attr_value is not None and attr_obj.flags == 8 and \
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
        if node_tags is not None:
            
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
        
    def _query_if_alive(self, nodes_id=None, hostname=None):
        """
        Query PLCAPI for nodes that register activity recently, using filters 
        related to the state of the node, e.g. last time it was contacted
        """
        if nodes_id is None and hostname is None:
            msg = "Specify nodes_id or hostname"
            raise RuntimeError, msg

        if nodes_id is not None and hostname is not None:
            msg = "Specify either nodes_id or hostname"
            raise RuntimeError, msg

        # define PL filters to check the node is alive
        filters = dict()
        filters['run_level'] = 'boot'
        filters['boot_state'] = 'boot'
        filters['node_type'] = 'regular' 
        filters['>last_contact'] =  int(time.time()) - 2*3600

        # adding node_id or hostname to the filters to check for the particular
        # node
        if nodes_id:
            filters['node_id'] = list(nodes_id)
            alive_nodes_id = self._get_nodes_id(filters)
        elif hostname:
            filters['hostname'] = hostname
            alive_nodes_id = self._get_nodes_id(filters)

        if len(alive_nodes_id) == 0:
            self.fail_discovery()
        else:
            nodes_id = list()
            for node_id in alive_nodes_id:
                nid = node_id['node_id']
                nodes_id.append(nid)

            return nodes_id

    def _choose_random_node(self, nodes):
        """
        From the possible nodes for provision, choose randomly to decrese the
        probability of different RMs choosing the same node for provision
        """
        blist = PlanetlabNode.blacklist
        plist = PlanetlabNode.provisionlist

        size = len(nodes)
        while size:
            size = size - 1
            index = randint(0, size)
            node_id = nodes[index]
            nodes[index] = nodes[size]

            # check the node is not blacklisted or being provision by other RM
            # and perform ping to check that is really alive
            if node_id not in blist and node_id not in plist:
                ping_ok = self._do_ping(node_id)
                if not ping_ok:
                    self._blacklist_node(node_id)
                else:
                    # discovered node for provision, added to provision list
                    self._put_node_in_provision(node_id)
                    return node_id

    def _get_nodes_id(self, filters):
        return self.plapi.get_nodes(filters, fields=['node_id'])

    def _add_node_to_slice(self, node_id):
        self.warn(" Adding node to slice ")
        slicename = self.get("username")
        with PlanetlabNode.lock_slice:
            slice_nodes = self.plapi.get_slice_nodes(slicename)
            slice_nodes.append(node_id)
            self.plapi.add_slice_nodes(slicename, slice_nodes)

    def _delete_node_from_slice(self, node):
        self.warn(" Deleting node from slice ")
        slicename = self.get("username")
        self.plapi.delete_slice_node(slicename, [node])

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
        command = "ping -c2 %s | echo \"PING OK\"" % ip

        (out, err) = lexec(command)
        if not out.find("PING OK") < 0:
            ping_ok = True

        return ping_ok 

    def _blacklist_node(self, node):
        """
        Add node mal functioning node to blacklist
        """
        blist = PlanetlabNode.blacklist

        self.warn(" Blacklisting malfunctioning node ")
        with PlanetlabNode.lock_blist:
            blist.append(node)

    def _put_node_in_provision(self, node):
        """
        Add node to the list of nodes being provisioned, in order for other RMs
        to not try to provision the same one again
        """
        plist = PlanetlabNode.provisionlist

        self.warn(" Provisioning node ")
        with PlanetlabNode.lock_plist:
            plist.append(node)

    def _get_ip(self, node_id):
        """
        Query PLCAPI for the IP of a node with certain node id
        """
        ip = self.plapi.get_interfaces({'node_id':node_id}, fields=['ip'])
        ip = ip[0]['ip']
        return ip

    def fail_discovery(self):
        self.fail()
        msg = "Discovery failed. No candidates found for node"
        self.error(msg)
        raise RuntimeError, msg

    def fail_node_not_alive(self, hostname):
        msg = "Node %s not alive, pick another node" % hostname
        raise RuntimeError, msg
    
    def fail_node_not_available(self, hostname):
        msg = "Node %s not available for provisioning, pick another \
                node" % hostname
        raise RuntimeError, msg

    def fail_not_enough_nodes(self):
        msg = "Not enough nodes available for provisioning"
        raise RuntimeError, msg

    def valid_connection(self, guid):
        # TODO: Validate!
        return True


