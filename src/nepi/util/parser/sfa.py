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

def get_text(p_tag, name):
    tags = p_tag.getElementsByTagName(name)
    if not tags:
        return ""
    return xmldecode(tags[0].childNodes[0].nodeValue)

def get_attribute(p_tag, name):
    return xmldecode(p_tag.getAttribute(name))


class SFAResourcesParser(object):
    def from_xml(self, xml):
        data = dict()
        doc = minidom.parseString(xml)
        rspec_tag = doc.getElementsByTagName("RSpec")[0]
        network_tags = rspec_tag.getElementsByTagName("network")
        for network_tag in network_tags:
            if network_tag.nodeType == doc.ELEMENT_NODE:
                node_data = self.nodes_from_xml(doc, network_tag)
                data.update(node_data)
        return data

    def nodes_from_xml(self, doc, network_tag):
        nodes_data = dict()
        network_name = get_attribute(network_tag, "name")
        node_tags = network_tag.getElementsByTagName('node')
        for node_tag in node_tags:
            if node_tag.nodeType == doc.ELEMENT_NODE:
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
                    node_data[name] = get_text(node_tag, name)
                iface_tags =  node_tag.getElementsByTagName('interface')
                ifaces_data = dict()
                for iface_tag in iface_tags: 
                    if iface_tag.nodeType == doc.ELEMENT_NODE:
                        for name in ['component_id', 'ipv4']:
                            ifaces_data[name] = get_attribute(iface_tag, name)
                node_data['interfaces'] = ifaces_data           
        return nodes_data

"""
if __name__ == "__main__":
    path = sys.argv[1]
    fd = open(path, 'r')
    xml = fd.read()
    fd.close()
    p = SFAResourcesParser()
    data = p.from_xml(xml)
    print data.keys()
"""
