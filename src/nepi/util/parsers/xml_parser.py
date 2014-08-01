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

from xml.dom import minidom

import sys
import os

STRING = "string"
BOOL = "bool"
INTEGER = "integer"
DOUBLE = "float"

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

def from_type(value):
    if value == None:
        return str("None")

    if isinstance(value, str):
        return STRING
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INTEGER
    if isinstance(value, float):
        return DOUBLE

def to_type(type, value):
    if type == STRING:
        if value == "None":
            return None
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
        doc.appendChild(ecnode)

        for guid, rm in ec._resources.iteritems():
            self._rm_to_xml(doc, ecnode, ec, guid, rm)

        return doc

    def _rm_to_xml(self, doc, ecnode, ec, guid, rm):
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
        ecnode.appendChild(rmnode)

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
                cnnode = doc.createElement("condition")
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
                exp_id = ecnode.getAttribute("exp_id")
                run_id = ecnode.getAttribute("run_id")
                nthreads = int(ecnode.getAttribute("nthreads"))
            
                os.environ["NEPI_NTHREADS"] = str(nthreads)
                ec = ExperimentController(exp_id = exp_id)

                connections = set()

                rmnode_list = ecnode.getElementsByTagName("rm")
                for rmnode in rmnode_list:
                    if rmnode.nodeType == doc.ELEMENT_NODE:
                        self._rm_from_xml(doc, rmnode, ec, connections)

                for (guid1, guid2) in connections:
                    ec.register_connection(guid1, guid2)

                break

        return ec

    def _rm_from_xml(self, doc, rmnode, ec, connections):
        start_time = None
        stop_time = None
        discover_time = None
        provision_time = None
        ready_time = None
        release_time = None
        failed_time = None

        guid = int(rmnode.getAttribute("guid"))
        rtype = xmldecode(rmnode.getAttribute("rtype"))
        state = int(rmnode.getAttribute("state"))

        if rmnode.hasAttribute("start_time"):
            start_time = xmldecode(rmnode.getAttribute("start_time"))
        if rmnode.hasAttribute("stop_time"):
            stop_time = xmldecode(rmnode.getAttribute("stop_time"))
        if rmnode.hasAttribute("discover_time"):
            dicover_time = xmldecode(rmnode.getAttribute("discover_time"))
        if rmnode.hasAttribute("provision_time"):
            provision_time = xmldecode(rmnode.getAttribute("provision_time"))
        if rmnode.hasAttribute("ready_time"):
            ready_time = xmldecode(rmnode.getAttribute("ready_time"))
        if rmnode.hasAttribute("release_time"):
            release_time = xmldecode(rmnode.getAttribute("release_time"))
        if rmnode.hasAttribute("failed_time"):
            failed_time = xmldecode(rmnode.getAttribute("failed_time"))

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
                type = xmldecode(aanode.getAttribute("type"))
                value = to_type(type, value)
                rm.set(name, value)

        cnode_list = rmnode.getElementsByTagName("connections")
        if cnode_list:
            ccnode_list = cnode_list[0].getElementsByTagName("connection") 
            for ccnode in ccnode_list:
                guid2 = int(ccnode.getAttribute("guid"))
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
                action = int(ccnnode.getAttribute("action"))
                group = int(ccnnode.getAttribute("group"))
                state = int(ccnnode.getAttribute("state"))
                time = ccnnode.getAttribute("time")
                ec.register_condition(guid, action, group, state, time = time)
                 
