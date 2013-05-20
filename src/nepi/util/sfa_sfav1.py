"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from lxml import etree
#import collections
import sys

class SFAResourcesParser(object):
    # Maybe this init method is not necessary, it was aim to check that the
    # aggregate was supported by nepi

    def __init__(self, aggr_pattern):
        if not isinstance(aggr_pattern, list):
            self._aggr_pattern = [aggr_pattern]
        else:
            self._aggr_pattern = aggr_pattern
    
    def resources_from_xml(self, xml, sliver = False, resources = False):
        rdata = dict()
        ldata = dict()
        stags = dict()
        RSpec = etree.fromstring(xml)
        RSpec_attr = dict(RSpec.attrib)
        network = RSpec.findall('.//network')
        for net in network:
            aggr = net.get('name') 
            if aggr == 'ple' and resources:
                node_tree = net.iterfind('node')
                for node in list(node_tree): 
                    if isinstance(node.tag, basestring):
                        data_ple = dict(node.attrib)
                        data_ple['aggregate'] = aggr
                        data_ple['resource_type'] = 'node'
                        data_ple = self._get_node_info(node, data_ple)
                        hostname = node.find('hostname')
                        rdata[hostname.text] = data_ple
                if sliver:
                    sliver_defaults = net.find('sliver_defaults')
                    if len(sliver_defaults):
                        stags = self._get_sliver_tags(sliver_defaults, stags)
            elif aggr == 'omf' and resources:
                node_tree = net.iterfind('node')
                for node in node_tree:
                    if isinstance(node.tag, basestring):
                        data_omf = dict(node.attrib)
                        data_omf['aggregate'] = aggr
                        data_omf['resource_type'] = 'node'
                        data_omf = self._get_node_info(node, data_omf)
                        hostname = node.find('hostname')
                        rdata[hostname.text] = data_omf
                spectrum = net.find('spectrum')
                for channel in list(spectrum):
                    if isinstance(channel.tag, basestring):
                        data_omf = dict(channel.attrib)
                        data_omf['aggregate'] = aggr
                        data_omf['resource_type'] = 'channel'
                        channelnum = data_omf['channel_num']
                        rdata[channelnum] = data_omf
                leases = net.iterfind('lease')
                for lease in list(leases):
                    if isinstance(lease.tag, basestring):
                        (st, duration) = lease.attrib['start_time'], lease.attrib['duration']
                        data_lease = dict(lease.attrib)
                        data_lease['aggregate'] = aggr
                        data_lease['resource_type'] = 'lease'
                        data_lease = self._get_leases_info(lease, data_lease)
                        ldata[(st, duration)] = data_lease
            elif aggr == 'omf' and not resources:
                leases = net.iterfind('lease')
                for lease in list(leases):
                    if isinstance(lease.tag, basestring):
                        (st, duration) = lease.attrib['start_time'], lease.attrib['duration']
                        data_lease = dict(lease.attrib)
                        data_lease['aggregate'] = aggr
                        data_lease['resource_type'] = 'lease'
                        data_lease = self._get_leases_info(lease, data_lease)
                        ldata[(st, duration)] = data_lease
            else:
                pass
        if sliver:
            return rdata, ldata, stags
        elif resources:
            return rdata, ldata
        elif not resources:
            return ldata

    def _get_node_info(self, node_tag, data_dict):
        for n in list(node_tag):
            if isinstance(n.tag, basestring):
                if n.attrib:
                    data_dict[n.tag] = dict(n.attrib)
                else:
                    data_dict[n.tag] = n.text
        return data_dict

    def _get_leases_info(self, lease_tag, data_dict):
        nodes = list()
        channels = list()
        for l in list(lease_tag):
            if l.tag == 'node':
                node = l.attrib['component_id'].split('+').pop()
                nodes.append(node)
            if l.tag == 'channel':
                #TODO: find out key when channel reservation
                #channels.append(l.attrib['averiguar']) channel_num
                pass
            data_dict['nodes'] = nodes
            data_dict['channels'] = channels
        return data_dict

    def _get_sliver_tags(self, sliverdefaults_tag, sliver_tag_dict):
        vsys = list()
        for info in list(sliverdefaults_tag):
            if info.tag == 'vsys_vnet':
                sliver_tag_dict['vsys_vnet'] = info.text
            elif info.tag == 'vsys':
                vsys.append(info.text)
        sliver_tag_dict['vsys'] = vsys
        return sliver_tag_dict
            
    def create_reservation_xml(self, xml, slice_hrn, new_resource, start_time, duration, aggregate):
        aggrs = []
        RSpec = etree.fromstring(xml)
        network = RSpec.findall('.//network')
        for net in network:
            aggr = net.get('name')
            aggrs.append(aggr)
            if aggr == aggregate:
                new_xml = self._create_tags(RSpec, net, slice_hrn, new_resource, start_time, duration)
        if aggregate not in aggrs:
            new_net = etree.SubElement(RSpec, 'network', name = aggregate)
            new_xml = self._create_tags(RSpec, new_net, slice_hrn, new_resource, start_time, duration)
        return new_xml

    def _create_tags(self, RSpec, net, slice_hrn, new_resource, start_time, duration):
        resource = new_resource.keys()[0]
        res_type = new_resource[resource]['resource_type']
        if res_type == 'node':
            node = etree.SubElement(net, res_type, \
            component_manager_id = new_resource[resource]['component_manager_id'],\
            component_id = new_resource[resource]['component_id'],\
            component_name = new_resource[resource]['component_name'], \
            site_id = new_resource[resource]['site_id'])
            sliver_tag = etree.SubElement(node, 'sliver')
        elif res_type == 'channel':
            spectrum = etree.SubElement(net, spectrum)
            channel = etree.SubElement(spectrum, channel,\
            channel_num = new_resource[resource]['channel_num'],\
            frequency = new_resource[resource]['frequency'],\
            standard = new_resource[resource]['standard'])
        if start_time is not None and duration is not None:
            slice_id = "urn:publicid:IDN+" + slice_hrn.split('.')[0] + ':' + slice_hrn.split('.')[1]\
            + '+slice+' + slice_hrn.split('.')[2]
            lease = etree.SubElement(net, 'lease', slice_id = slice_id,\
            start_time = str(start_time), duration = str(duration))
            if res_type == 'node':
                res = etree.SubElement(lease, res_type,\
                component_id = new_resource[resource]['component_id'])
            elif res_type == 'channel':
                res = etree.SubElement(lease, res_type,\
                channel_num = new_resource[resource]['channel_num'])
        new_xml = etree.tostring(RSpec, xml_declaration=True)
        return new_xml
                
    def verify_reservation_xml(self, xml, slice_hrn, new_resource, start_time, duration, aggregate):
        slice_id = "urn:publicid:IDN+" + slice_hrn.split('.')[0] + ':' + slice_hrn.split('.')[1]\
        + '+slice+' + slice_hrn.split('.')[2]
        rdata, ldata, stags = self.resources_from_xml(xml, sliver = True, resources = True)
        res_name = new_resource.keys()[0]
        if res_name in rdata.keys():
            if start_time and duration:
                if ldata[(start_time, duration)]:
                    nodes = ldata[(start_time, duration)]['nodes']
                    sliceid = ldata[(start_time, duration)]['slice_id']
                    if res_name in nodes and sliceid == slice_id:
                        return True
                    else: return False
                else: return False
            else: return True
        else: return False

    def release_reservation_xml(self, xml, slice_hrn, resource, start_time, duration, aggregate):
        RSpec = etree.fromstring(xml)
        network = RSpec.findall('.//network')
        for net in network:
            aggr = net.get('name')
            if aggr == aggregate:
                new_xml = self._delete_tag(RSpec, net, slice_hrn, resource, start_time, duration)
                return new_xml

    def _delete_tag(self, RSpec, net, slice_hrn, resource, start_time, duration):
        resource_name = resource.keys()[0]
        res_type = resource[resource_name]['resource_type']
        if res_type == 'node':
            node_tree = net.iterfind('node')
            for node in list(node_tree):
                if isinstance(node.tag, basestring):
                    data_node = dict(node.attrib)
                    if data_node['component_name'] == resource_name:
                        net.remove(node)
        elif res_type == 'channel':
            spectrum = net.find('spectrum')
            for channel in list(spectrum):
                if isinstance(channel.tag, basestring):
                    data_channel = dict(channel.attrib)
                    if data_channel['channel_num'] == resource_name:
                        spectrum.remove(channel)
        if start_time is not None and duration is not None:
            slice_id = "urn:publicid:IDN+" + slice_hrn.split('.')[0] + ':' + slice_hrn.split('.')[1]\
            + '+slice+' + slice_hrn.split('.')[2]
            leases = net.iterfind('lease')
            for lease in list(leases):
                if isinstance(lease.tag, basestring):
                    (st, duration) = lease.attrib['start_time'], lease.attrib['duration']
                    sliceid = lease.attrib['slice_id']
                    if st == str(start_time) and duration == str(duration) and sliceid == slice_id:
                        for l in list(lease):
                            if l.tag == 'node' and res_type == 'node':
                                if l.attrib['component_id'].split('+').pop() == resource_name:
                                    lease.remove(l)
                            elif l.tag == 'channel' and res_type == 'channel':
                                if l.attrib['channel_num'] == resource_name:
                                    lease.remove(l)
        new_xml = etree.tostring(RSpec, xml_declaration=True)
        return new_xml


