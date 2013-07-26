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
from nepi.execution.resource import ResourceManager, clsinit_copy, ResourceState, \
        reschedule_delay
from nepi.resources.linux.node import LinuxNode
from nepi.resources.planetlab.plcapi import PLCAPIFactory 
from nepi.util.timefuncs import tnow, tdiff, tdiffsec, stabsformat


@clsinit_copy
class PlanetlabNode(LinuxNode):
    _rtype = "PlanetlabNode"

    @classmethod
    def _register_attributes(cls):
        ip = Attribute("ip", "PlanetLab host public IP address",
                flags = Flags.ReadOnly)

        pl_url = Attribute("plcApiUrl", "URL of PlanetLab PLCAPI host (e.g. www.planet-lab.eu or www.planet-lab.org) ",
                default = "www.planet-lab.eu",
                flags = Flags.Credential)

        pl_ptn = Attribute("plcApiPattern", "PLC API service regexp pattern (e.g. https://%(hostname)s:443/PLCAPI/ ) ",
                default = "https://%(hostname)s:443/PLCAPI/",
                flags = Flags.ExecReadOnly)
    
        pl_user = Attribute("pluser", "PlanetLab account user, as the one to authenticate in the website) ",
                flags = Flags.Credential)

        pl_password = Attribute("password", "PlanetLab account password, as the one to authenticate in the website) ",
                flags = Flags.Credential)

        city = Attribute("city",
                "Constrain location (city) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        country = Attribute("country",
                "Constrain location (country) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        region = Attribute("region",
                "Constrain location (region) during resource discovery. May use wildcards.",
                flags = Flags.Filter)

        architecture = Attribute("architecture",
                "Constrain architecture during resource discovery.",
                type = Types.Enumerate,
                allowed = ["x86_64",
                            "i386"],
                flags = Flags.Filter)

        operating_system = Attribute("operatingSystem",
                "Constrain operating system during resource discovery.",
                type = Types.Enumerate,
                allowed =  ["f8",
                            "f12",
                            "f14",
                            "centos",
                            "other"],
                flags = Flags.Filter)

        site = Attribute("site",
                "Constrain the PlanetLab site this node should reside on.",
                type = Types.Enumerate,
                allowed = ["PLE",
                            "PLC",
                            "PLJ"],
                flags = Flags.Filter)

        min_reliability = Attribute("minReliability",
                "Constrain reliability while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (1, 100),
                flags = Flags.Filter)

        max_reliability = Attribute("maxReliability",
                "Constrain reliability while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (1, 100),
                flags = Flags.Filter)

        min_bandwidth = Attribute("minBandwidth",
                "Constrain available bandwidth while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        max_bandwidth = Attribute("maxBandwidth",
                "Constrain available bandwidth while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        min_load = Attribute("minLoad",
                "Constrain node load average while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        max_load = Attribute("maxLoad",
                "Constrain node load average while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 2**31),
                flags = Flags.Filter)

        min_cpu = Attribute("minCpu",
                "Constrain available cpu time while picking PlanetLab nodes. Specifies a lower acceptable bound.",
                type = Types.Double,
                range = (0, 100),
                flags = Flags.Filter)

        max_cpu = Attribute("maxCpu",
                "Constrain available cpu time while picking PlanetLab nodes. Specifies an upper acceptable bound.",
                type = Types.Double,
                range = (0, 100),
                flags = Flags.Filter)

        timeframe = Attribute("timeframe",
                "Past time period in which to check information about the node. Values are year,month, week, latest",
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

    #def discover(self):
    #    hostname = self.get("hostname")
    #    if hostname: 
    #        node_id = self.check_alive_and_active(hostname=hostname)
    #    else:
    #        from random import choice
    #        nodes = self.filter_based_on_attributes()
    #        nodes_alive = self.check_alive_and_active(nodes)
    #        while in_blkl:
    #            node_id = choice(nodes_alive)
                

    #    self._discover_time = tnow()
    #    self._state = ResourceState.DISCOVERED
    #    return node_id

    #def provision(self):

    def filter_based_on_attributes(self):
        # Map attributes with tagnames of PL
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
            print nodes_id
            if attr_value is not None and attr_obj.flags == 8 and not 'min' in attr_name \
                and not 'max' in attr_name and attr_name != 'timeframe':
                attr_tag = attr_to_tags[attr_name]
                filters['tagname'] = attr_tag
                filters['value'] = attr_value
                node_tags = self.plapi.get_node_tags(filters)
                if node_tags is not None:
                    if len(nodes_id) == 0:
                        for node_tag in node_tags:
                            nodes_id.append(node_tag['node_id'])
                    else:
                        nodes_id_tmp = []
                        for node_tag in node_tags:
                            if node_tag['node_id'] in nodes_id:
                                nodes_id_tmp.append(node_tag['node_id'])
                        if len(nodes_id_tmp):
                            nodes_id = set(nodes_id) & set(nodes_id_tmp)
                        else:
                            self.fail()
                else:
                    self.fail()
            elif attr_value is not None and attr_obj.flags == 8 and ('min' or 'max') in attr_name:
                attr_tag = attr_to_tags[attr_name]
                filters['tagname'] = attr_tag
                node_tags = self.plapi.get_node_tags(filters)
                if node_tags is not None:
                    if len(nodes_id) == 0:
                        for node_tag in node_tags:
                            if 'min' in attr_name and node_tag['value'] != 'n/a' and \
                                float(node_tag['value']) > attr_value:
                                nodes_id.append(node_tag['node_id'])
                            elif 'max' in attr_name and node_tag['value'] != 'n/a' and \
                                float(node_tag['value']) < attr_value:
                                nodes_id.append(node_tag['node_id'])
                    else:
                        nodes_id_tmp = []
                        for node_tag in node_tags:
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
                            self.fail()

        return nodes_id
                    
    def check_alive_and_active(self, nodes_id=None, hostname=None):
        if nodes_id is None and hostname is None:
            msg = "Specify nodes_id or hostname"
            raise RuntimeError, msg
        if nodes_id is not None and hostname is not None:
            msg = "Specify either nodes_id or hostname"
            raise RuntimeError, msg

        # check node alive
        import time
        filters = dict()
        filters['run_level'] = 'boot'
        filters['boot_state'] = 'boot'
        filters['node_type'] = 'regular' 
        filters['>last_contact'] =  int(time.time()) - 2*3600
        if nodes_id:
            filters['node_id'] = list(nodes_id)
            alive_nodes_id = self.plapi.get_nodes(filters, fields=['node_id'])
        elif hostname:
            filters['hostname'] = hostname
            alive_nodes_id = self.plapi.get_nodes(filters, fields=['node_id'])
        if len(alive_nodes_id) == 0:
            self.fail()
        else:
            nodes_id = list()
            for node_id in alive_nodes_id:
                nid = node_id['node_id']
                nodes_id.append(nid)
            return nodes_id

# ip = self.plapi.get_interfaces({'node_id':nid}, fields=['ip'])
# self.set('ip', ip[0]['ip'])
#de hostname para que provision haga add_node_slice, check que ip coincide con hostname


    def fail(self):
        msg = "Discovery failed. No candidates found for node"
        self.error(msg)
        raise RuntimeError, msg
           
                        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

#    def blacklist(self):
#        # TODO!!!!
#        self.warn(" Blacklisting malfunctioning node ")
#        #import util
#        #util.appendBlacklist(self.hostname)

