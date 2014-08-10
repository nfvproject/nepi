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

from nepi.util.netgraph import NetGraph, TopologyType 
from nepi.util.timefuncs import stformat, tsformat

from xml.dom import minidom

import datetime
import sys
import os

STRING = "string"
BOOL = "bool"
INTEGER = "integer"
DOUBLE = "float"

def xmlencode(s):
    if isinstance(s, str):
        rv = s.decode("latin1")
    if isinstance(s, datetime.datetime):
        rv = tsformat(s)
    elif not isinstance(s, unicode):
        rv = unicode(s)
    else:
        rv = s
    return rv.replace(u'\x00',u'&#0000;')

def xmldecode(s, cast = str):
    ret = s.replace(u'&#0000',u'\x00').encode("ascii")
    ret = cast(ret)
    if s == "None":
        return None
    return ret

def from_type(value):
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INTEGER
    if isinstance(value, float):
        return DOUBLE

    return STRING

def to_type(type, value):
    if not value:
        return value

    if type == STRING:
        return str(value)
    if type == BOOL:
        return value == "True"
    if type == INTEGER:
        return int(value)
    if type == DOUBLE:
        return float(value)

class ECXMLParser(object):
    def to_xml(self, ec):
        
        doc = minidom.Document()
        
        self._ec_to_xml(doc, ec)
       
        try:
            xml = doc.toprettyxml(indent="    ", encoding="UTF-8")
        except:
            print >>sys.stderr, "Oops: generating XML from %s" % (data,)
            raise
        
        return xml

    def _ec_to_xml(self, doc, ec):
        ecnode = doc.createElement("experiment")
        ecnode.setAttribute("exp_id", xmlencode(ec.exp_id))
        ecnode.setAttribute("run_id", xmlencode(ec.run_id))
        ecnode.setAttribute("nthreads", xmlencode(ec.nthreads))
        ecnode.setAttribute("local_dir", xmlencode(ec.local_dir))
        doc.appendChild(ecnode)

        if ec.netgraph != None:
            self._netgraph_to_xml(doc, ecnode, ec)

        rmsnode = doc.createElement("rms")
        ecnode.appendChild(rmsnode)

        for guid, rm in ec._resources.iteritems():
            self._rm_to_xml(doc, rmsnode, ec, guid, rm)

        return doc
    
    def _netgraph_to_xml(self, doc, ecnode, ec):
        ngnode = doc.createElement("topology")
        ngnode.setAttribute("topo-type", xmlencode(ec.netgraph.topo_type))
        ecnode.appendChild(ngnode)
        
        self. _netgraph_nodes_to_xml(doc, ngnode, ec)
        self. _netgraph_edges_to_xml(doc, ngnode, ec)
        
    def _netgraph_nodes_to_xml(self, doc, ngnode, ec):
        ngnsnode = doc.createElement("nodes")
        ngnode.appendChild(ngnsnode)

        for nid in ec.netgraph.nodes():
            ngnnode = doc.createElement("node")
            ngnnode.setAttribute("nid", xmlencode(nid))
            ngnsnode.appendChild(ngnnode)

            # Mark ources and targets
            if ec.netgraph.is_source(nid):
                ngnnode.setAttribute("source", xmlencode(True))

            if ec.netgraph.is_target(nid):
                ngnnode.setAttribute("target", xmlencode(True))

            # Node annotations
            annosnode = doc.createElement("node-annotations")
            add_annotations = False
            for name in ec.netgraph.node_annotations(nid):
                add_annotations = True
                value = ec.netgraph.node_annotation(nid, name)
                annonode = doc.createElement("node-annotation")
                annonode.setAttribute("name", xmlencode(name))
                annonode.setAttribute("value", xmlencode(value))
                annonode.setAttribute("type", from_type(value))
                annosnode.appendChild(annonode)

            if add_annotations:
                ngnnode.appendChild(annosnode)

    def _netgraph_edges_to_xml(self, doc, ngnode, ec):
        ngesnode = doc.createElement("edges")
        ngnode.appendChild(ngesnode)

        for nid1, nid2 in ec.netgraph.edges():
            ngenode = doc.createElement("edge")
            ngenode.setAttribute("nid1", xmlencode(nid1))
            ngenode.setAttribute("nid2", xmlencode(nid2))
            ngesnode.appendChild(ngenode)

            # Edge annotations
            annosnode = doc.createElement("edge-annotations")
            add_annotations = False
            for name in ec.netgraph.edge_annotations(nid1, nid2):
                add_annotations = True
                value = ec.netgraph.edge_annotation(nid1, nid2, name)
                annonode = doc.createElement("edge-annotation")
                annonode.setAttribute("name", xmlencode(name))
                annonode.setAttribute("value", xmlencode(value))
                annonode.setAttribute("type", from_type(value))
                annosnode.appendChild(annonode)

            if add_annotations:
                ngenode.appendChild(annosnode)

    def _rm_to_xml(self, doc, rmsnode, ec, guid, rm):
        rmnode = doc.createElement("rm")
        rmnode.setAttribute("guid", xmlencode(guid))
        rmnode.setAttribute("rtype", xmlencode(rm._rtype))
        rmnode.setAttribute("state", xmlencode(rm._state))
        if rm._start_time:
            rmnode.setAttribute("start_time", xmlencode(rm._start_time))
        if rm._stop_time:
            rmnode.setAttribute("stop_time", xmlencode(rm._stop_time))
        if rm._discover_time:
            rmnode.setAttribute("discover_time", xmlencode(rm._discover_time))
        if rm._provision_time:    
            rmnode.setAttribute("provision_time", xmlencode(rm._provision_time))
        if rm._ready_time:
            rmnode.setAttribute("ready_time", xmlencode(rm._ready_time))
        if rm._release_time:
            rmnode.setAttribute("release_time", xmlencode(rm._release_time))
        if rm._failed_time:
            rmnode.setAttribute("failed_time", xmlencode(rm._failed_time))
        rmsnode.appendChild(rmnode)

        anode = doc.createElement("attributes")
        attributes = False

        for attr in rm._attrs.values():
            if attr.has_changed:
                attributes = True
                aanode = doc.createElement("attribute")
                aanode.setAttribute("name", xmlencode(attr.name))
                aanode.setAttribute("value", xmlencode(attr.value))
                aanode.setAttribute("type", from_type(attr.value))
                anode.appendChild(aanode)
    
        if attributes: 
            rmnode.appendChild(anode)

        cnode = doc.createElement("connections")
        connections = False
        
        for guid in rm._connections:
            connections = True
            ccnode = doc.createElement("connection")
            ccnode.setAttribute("guid", xmlencode(guid))
            cnode.appendChild(ccnode)
        
        if connections:
           rmnode.appendChild(cnode)

        cnnode = doc.createElement("conditions")
        conditions = False

        for action, conds in rm._conditions.iteritems():
            conditions = True
            for (group, state, time) in conds:
                ccnnode = doc.createElement("condition")
                ccnnode.setAttribute("action", xmlencode(action))
                ccnnode.setAttribute("group", xmlencode(group))
                ccnnode.setAttribute("state", xmlencode(state))
                ccnnode.setAttribute("time", xmlencode(time))
                cnnode.appendChild(ccnnode)
        
        if conditions:
           rmnode.appendChild(cnnode)

        tnode = doc.createElement("traces")
        traces = False

        for trace in rm._trcs.values():
            if trace.enabled:
                traces = True
                ttnode = doc.createElement("trace")
                ttnode.setAttribute("name", xmlencode(trace.name))
                tnode.appendChild(ttnode)
    
        if traces: 
            rmnode.appendChild(tnode)

    def from_xml(self, xml):
        doc = minidom.parseString(xml)
        return self._ec_from_xml(doc)

    def _ec_from_xml(self, doc):
        from nepi.execution.ec import ExperimentController
        ec = None
        
        ecnode_list = doc.getElementsByTagName("experiment")
        for ecnode in ecnode_list:
            if ecnode.nodeType == doc.ELEMENT_NODE:
                exp_id = xmldecode(ecnode.getAttribute("exp_id"))
                run_id = xmldecode(ecnode.getAttribute("run_id"))
                local_dir = xmldecode(ecnode.getAttribute("local_dir"))

                # Configure number of preocessing threads
                nthreads = xmldecode(ecnode.getAttribute("nthreads"))
                os.environ["NEPI_NTHREADS"] = nthreads

                # Deserialize netgraph
                netgraph = self._netgraph_from_xml(doc, ecnode)
                topo_type = netgraph.topo_type if netgraph else None

                # Instantiate EC
                ec = ExperimentController(exp_id = exp_id, local_dir = local_dir, 
                        topology = netgraph.topology, topo_type = topo_type)

                connections = set()

                rmsnode_list = ecnode.getElementsByTagName("rms")
                if rmsnode_list:
                    rmnode_list = rmsnode_list[0].getElementsByTagName("rm") 
                    for rmnode in rmnode_list:
                        if rmnode.nodeType == doc.ELEMENT_NODE:
                            self._rm_from_xml(doc, rmnode, ec, connections)

                for (guid1, guid2) in connections:
                    ec.register_connection(guid1, guid2)

                break

        return ec

    def _netgraph_from_xml(self, doc, ecnode):
        netgraph = None

        topology = ecnode.getElementsByTagName("topology")
        if topology:
            topology = topology[0]
            topo_type = xmldecode(topology.getAttribute("topo-type"))

            netgraph = NetGraph(topo_type = topo_type)

            ngnsnode_list = topology.getElementsByTagName("nodes")
            if ngnsnode_list:
                ngnsnode = ngnsnode_list[0].getElementsByTagName("node") 
                for ngnnode in ngnsnode:
                    nid = xmldecode(ngnnode.getAttribute("nid"))
                    netgraph.add_node(nid)

                    if ngnnode.hasAttribute("source"):
                        netgraph.set_source(nid)
                    if ngnnode.hasAttribute("target"):
                        netgraph.set_target(nid)

                    annosnode_list = ngnnode.getElementsByTagName("node-annotations")
                    
                    if annosnode_list:
                        annosnode = annosnode_list[0].getElementsByTagName("node-annotation") 
                        for annonode in annosnode:
                            name = xmldecode(annonode.getAttribute("name"))

                            if name == "ips":
                                ips = xmldecode(annonode.getAttribute("value"), eval) # list
                                for ip in ips:
                                    netgraph.annotate_node_ip(nid, ip)
                            else:
                                value = xmldecode(annonode.getAttribute("value"))
                                tipe = xmldecode(annonode.getAttribute("type"))
                                value = to_type(tipe, value)
                                netgraph.annotate_node(nid, name, value)

            ngesnode_list = topology.getElementsByTagName("edges") 
            if ngesnode_list:
                ngesnode = ngesnode_list[0].getElementsByTagName("edge") 
                for ngenode in ngesnode:
                    nid1 = xmldecode(ngenode.getAttribute("nid1"))
                    nid2 = xmldecode(ngenode.getAttribute("nid2"))
                    netgraph.add_edge(nid1, nid2)

                    annosnode_list = ngenode.getElementsByTagName("edge-annotations")
                    if annosnode_list:
                        annosnode = annosnode_list[0].getElementsByTagName("edge-annotation") 
                        for annonode in annosnode:
                            name = xmldecode(annonode.getAttribute("name"))

                            if name == "net":
                                net = xmldecode(annonode.getAttribute("value"), eval) # dict
                                netgraph.annotate_edge_net(nid1, nid2, net[nid1], net[nid2], 
                                        net["mask"], net["network"], net["prefix"])
                            else:
                                value = xmldecode(annonode.getAttribute("value"))
                                tipe = xmldecode(annonode.getAttribute("type"))
                                value = to_type(tipe, value)
                                netgraph.annotate_edge(nid1, nid2, name, value)
        return netgraph

    def _rm_from_xml(self, doc, rmnode, ec, connections):
        start_time = None
        stop_time = None
        discover_time = None
        provision_time = None
        ready_time = None
        release_time = None
        failed_time = None

        guid = xmldecode(rmnode.getAttribute("guid"), int)
        rtype = xmldecode(rmnode.getAttribute("rtype"))

        # FOR NOW ONLY STATE NEW IS ALLOWED
        state = 0
        """
        state = xmldecode(rmnode.getAttribute("state"), int)

        if rmnode.hasAttribute("start_time"):
            start_time = xmldecode(rmnode.getAttribute("start_time"), 
                    datetime.datetime)
        if rmnode.hasAttribute("stop_time"):
            stop_time = xmldecode(rmnode.getAttribute("stop_time"), 
                    datetime.datetime)
        if rmnode.hasAttribute("discover_time"):
            dicover_time = xmldecode(rmnode.getAttribute("discover_time"), 
                    datetime.datetime)
        if rmnode.hasAttribute("provision_time"):
            provision_time = xmldecode(rmnode.getAttribute("provision_time"),
                    datetime.datetime)
        if rmnode.hasAttribute("ready_time"):
            ready_time = xmldecode(rmnode.getAttribute("ready_time"),
                    datetime.datetime)
        if rmnode.hasAttribute("release_time"):
            release_time = xmldecode(rmnode.getAttribute("release_time"),
                    datetime.datetime)
        if rmnode.hasAttribute("failed_time"):
            failed_time = xmldecode(rmnode.getAttribute("failed_time"),
                    datetime.datetime)
        """

        ec.register_resource(rtype, guid = guid)
        rm = ec.get_resource(guid)
        rm.set_state_time(state, "_start_time", start_time)
        rm.set_state_time(state, "_stop_time", stop_time)
        rm.set_state_time(state, "_discover_time", discover_time)
        rm.set_state_time(state, "_provision_time", provision_time)
        rm.set_state_time(state, "_ready_time", ready_time)
        rm.set_state_time(state, "_release_time", release_time)
        rm.set_state_time(state, "_failed_time", failed_time)
        
        anode_list = rmnode.getElementsByTagName("attributes")
        if anode_list:
            aanode_list = anode_list[0].getElementsByTagName("attribute") 
            for aanode in aanode_list:
                name = xmldecode(aanode.getAttribute("name"))
                value = xmldecode(aanode.getAttribute("value"))
                tipe = xmldecode(aanode.getAttribute("type"))
                value = to_type(tipe, value)
                rm.set(name, value)

        cnode_list = rmnode.getElementsByTagName("connections")
        if cnode_list:
            ccnode_list = cnode_list[0].getElementsByTagName("connection") 
            for ccnode in ccnode_list:
                guid2 = xmldecode(ccnode.getAttribute("guid"), int)
                connections.add((guid, guid2))

        tnode_list = rmnode.getElementsByTagName("traces")
        if tnode_list:
            ttnode_list = tnode_list[0].getElementsByTagName("trace") 
            for ttnode in ttnode_list:
                name = xmldecode(ttnode.getAttribute("name"))
                ec.enable_trace(guid, name)

        cnnode_list = rmnode.getElementsByTagName("conditions")
        if cnnode_list:
            ccnnode_list = cnnode_list[0].getElementsByTagName("condition") 
            for ccnnode in ccnnode_list:
                action = xmldecode(ccnnode.getAttribute("action"), int)
                group = xmldecode(ccnnode.getAttribute("group"), eval) # list
                state = xmldecode(ccnnode.getAttribute("state"), int)
                time = xmldecode(ccnnode.getAttribute("time"))
                time = to_type('STRING', time)
                ec.register_condition(guid, action, group, state, time = time)
                 
