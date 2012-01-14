# -*- coding: utf-8 -*-

from xml.dom import minidom

import sys

def xmlencode(s):
    if isinstance(s, str):
        rv = s.decode("latin1")
    elif not isinstance(s, unicode):
        rv = unicode(s)
    else:
        rv = s
    return rv.replace(u'\x00',u'&#0000;')

def xmldecode(s):
    return s.replace(u'&#0000',u'\x00').encode("utf8")

def get_child_text(tag, name):
    tags = tag.getElementsByTagName(name)
    if not tags:
        return ""
    return get_text(tags[0])

def get_name(tag):
    return xmldecode(tag.tagName)

def get_text(tag):
    text = ''.join(t.nodeValue for t in tag.childNodes if t.nodeType == t.TEXT_NODE)
    return xmldecode(text)

def set_text(doc, tag, text):
    ttag = doc.createTextNode(text)
    tag.appendChild(ttag)

def get_attribute(p_tag, name):
    return xmldecode(p_tag.getAttribute(name))

def has_sliver(node_tag):
    sliver_tag = node_tag.getElementsByTagName("sliver")
    return len(sliver_tag) > 0 

class SFAResourcesParser(object):
    def resources_from_xml(self, xml):
        data = dict()
        doc = minidom.parseString(xml)
        rspec_tag = doc.getElementsByTagName("RSpec")[0]
        network_tags = rspec_tag.getElementsByTagName("network")
        for network_tag in network_tags:
            if network_tag.nodeType == doc.ELEMENT_NODE:
                node_data = self.nodes_from_xml(doc, network_tag)
                data.update(node_data)
        return data

    def slice_info_from_xml(self, xml):
        nodes_data = dict()
        doc = minidom.parseString(xml)
        rspec_tag = doc.getElementsByTagName("RSpec")[0]
        network_tags = rspec_tag.getElementsByTagName("network")
        for network_tag in network_tags:
            if network_tag.nodeType == doc.ELEMENT_NODE:
                node_data = self.nodes_from_xml(doc, network_tag, in_sliver = True)
                nodes_data.update(node_data)
        nodes_data = set(nodes_data.keys())
        tags_data = self.slice_tags_from_xml(doc, rspec_tag)
        return tags_data, nodes_data

    def nodes_from_xml(self, doc, network_tag, in_sliver = False):
        nodes_data = dict()
        network_name = get_attribute(network_tag, 'name')
        node_tags = network_tag.getElementsByTagName('node')
        for node_tag in node_tags:
            if node_tag.nodeType == doc.ELEMENT_NODE:
                if in_sliver and not has_sliver(node_tag):
                    continue
                node_data = dict()
                node_data['network_name'] = network_name
                node_name = get_attribute(node_tag, 'component_name')
                nodes_data[node_name] = node_data
                for name in ['component_id', 'component_manager_id',
                        'boot_state', 'component_name', 'site_id']:
                    node_data[name] = get_attribute(node_tag, name)
                location_tag = node_tag.getElementsByTagName('location')
                if location_tag:
                    for name in ['longitud' , 'latitude']:
                        node_data[name] = get_attribute(location_tag[0], name)
                for name in ['hostname', 'pldistro', 'arch', 'fcdistro',
                        'stype', 'reliabilityw', 'loadm', 'cpuy', 'cpum', 
                        'slicesm', 'slicesw', 'cpuw', 'loady', 'memy',
                        'memw', 'reliabilityy', 'reliability', 'reliabilitym', 
                        'responsey', 'bww', 'memem', 'bwm', 'slicey', 'responsem', 
                        'response', 'loadw', 'country', 'load', 'mem', 'slices',
                        'region', 'asnumber', 'bw', 'hrn', 'city', 'responsew', 
                        'bwy', 'cpu']:
                    node_data[name] = get_child_text(node_tag, name)
                iface_tags =  node_tag.getElementsByTagName('interface')
                ifaces_data = dict()
                iface_ids = list()
                for iface_tag in iface_tags: 
                    if iface_tag.nodeType == doc.ELEMENT_NODE:
                        for name in ['component_id', 'ipv4']:
                            value = get_attribute(iface_tag, name)
                            ifaces_data[name] = value
                            if name == 'component_id':
                                iface_ids.append(value)
                node_data['interfaces'] = ifaces_data
                node_data['interface_ids'] = iface_ids
        return nodes_data

    def slice_tags_from_xml(self, doc, rspec_tag):
        tags_data = dict()
        sliver_tag = rspec_tag.getElementsByTagName('sliver_defaults')
        if len(sliver_tag) == 0:
            return tags_data
        for child_tag in sliver_tag[0].childNodes:
            if child_tag.nodeType == doc.ELEMENT_NODE:
                name = get_name(child_tag)
                value = get_text(child_tag)
                tags_data[name] = value
        return tags_data

    def create_slice_xml(self, node_data, slice_tags):
        doc = minidom.Document()
        rspec_tag = doc.createElement("RSpec")
        doc.appendChild(rspec_tag)
        rspec_tag.setAttribute("type", "SFA")
        slice_defaults_tag = self.slice_defaults_xml(doc, slice_tags)
        
        networks = dict()
        for k, data in node_data.iteritems():
            network_name = data["network_name"]
            if network_name not in networks:
                networks[network_name] = dict()
            networks[network_name][k] = data

        for n, netdata in networks.iteritems():
            network_tag = doc.createElement("testbeds")
            network_tag.setAttribute("name", n)
            rspec_tag.appendChild(network_tag)
            for k, data in netdata.iteritems():
                node_tag = doc.createElement("node")
                node_tag.setAttribute("component_manager_id", data["component_manager_id"])
                node_tag.setAttribute("component_id", data["component_id"])
                node_tag.setAttribute("component_name", data["component_name"])
                node_tag.setAttribute("boot_state", data["boot_state"])
                node_tag.setAttribute("site_id", data["site_id"])
                hostname_tag = doc.createElement("hostname")
                set_text(doc, hostname_tag, data["hostname"])
                node_tag.appendChild(hostname_tag)
                sliver_tag = doc.createElement("sliver")
                node_tag.appendChild(sliver_tag)
                network_tag.appendChild(node_tag)
            network_tag.appendChild(slice_defaults_tag)
        return doc.toxml()

    def slice_defaults_xml(self, doc, slice_tags):
        slice_defaults_tag = doc.createElement("sliver_defaults")
        for name, value in slice_tags.iteritems():
            tag = doc.createElement(name)
            set_text(doc, tag, value)
            slice_defaults_tag.appendChild(tag)
        return slice_defaults_tag

"""
if __name__ == "__main__":
    path = sys.argv[1]
    fd = open(path, 'r')
    xml = fd.read()
    fd.close()
    p = SFAResourcesParser()
    tags, nodes = p.slice_info_from_xml(xml)
    print tags, nodes
"""
