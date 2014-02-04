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

# Force the load of ns3 libraries
from nepi.resources.ns3.ns3wrapper import load_ns3_module

import os
import re

base_types = ["ns3::Node",
        "ns3::Application", 
        "ns3::NetDevice",
        "ns3::Channel",
        "ns3::Queue",
        "ns3::Icmpv4L4Protocol",
        "ns3::ArpL3Protocol",
        "ns3::Ipv4L3Protocol",
        "ns3::PropagationLossModel",
        "ns3::PropagationDelayModel",
        "ns3::WifiRemoteStationManager",
        "ns3::WifiPhy",
        "ns3::WifiMac",
        "ns3::ErrorModel",
        "ns3::ErrorRateModel"]

def discard(ns3, tid):
    rtype = tid.GetName()
    type_id = ns3.TypeId()

    for type_name in base_types:
        tid_base = type_id.LookupByName(type_name)
        if type_name == rtype or tid.IsChildOf(tid_base):
            return False

    return True

def select_base_class(ns3, tid): 
    base_class_import = "from nepi.resources.ns3.ns3base import NS3Base"
    base_class = "NS3Base"
   
    rtype = tid.GetName()

    type_id = ns3.TypeId()

    for type_name in base_types:
        tid_base = type_id.LookupByName(type_name)
        if type_name == rtype or tid.IsChildOf(tid_base):
            base_class = "NS3Base" + type_name.replace("ns3::", "")
            base_module = "ns3" + type_name.replace("ns3::", "").lower()
            base_class_import = "from nepi.resources.ns3.%s import %s " % (
                    base_module, base_class)

    return (base_class_import, base_class)

def create_ns3_rms():
    ns3 = load_ns3_module()

    type_id = ns3.TypeId()
    
    tid_count = type_id.GetRegisteredN()
    base = type_id.LookupByName("ns3::Object")

    # Create a .py file using the ns-3 RM template for each ns-3 TypeId
    for i in xrange(tid_count):
        tid = type_id.GetRegistered(i)
        
        if discard(ns3, tid):
            continue
        
        if tid.MustHideFromDocumentation() or \
                not tid.HasConstructor() or \
                not tid.IsChildOf(base): 
            continue
       
        attributes = template_attributes(ns3, tid)
        traces = template_traces(ns3, tid)
        ptid = tid
        while ptid.HasParent():
            ptid = ptid.GetParent()
            attributes += template_attributes(ns3, ptid)
            traces += template_traces(ns3, ptid)

        attributes = "\n" + attributes if attributes else "pass"
        traces = "\n" + traces if traces else "pass"

        (base_class_import, base_class) = select_base_class(ns3, tid)

        category = tid.GetGroupName()

        rtype = tid.GetName()
        classname = rtype.replace("ns3::", "NS3").replace("::","")
        uncamm_rtype = re.sub('([a-z])([A-Z])', r'\1-\2', rtype).lower()
        short_rtype = uncamm_rtype.replace("::","-")

        d = os.path.dirname(os.path.realpath(__file__))
        ftemp = open(os.path.join(d, "templates", "resource_manager_template.txt"), "r")
        template = ftemp.read()
        ftemp.close()

        template = template. \
                replace("<CLASS_NAME>", classname). \
                replace("<RTYPE>", rtype). \
                replace("<ATTRIBUTES>", attributes). \
                replace("<TRACES>", traces). \
                replace("<BASE_CLASS_IMPORT>", base_class_import). \
                replace("<BASE_CLASS>", base_class). \
                replace("<SHORT-RTYPE>", short_rtype)

        fname = uncamm_rtype.replace('ns3::', ''). \
                replace('::', ''). \
                replace("-","_").lower() + ".py"

        f = open(os.path.join(d, "classes", fname), "w")
        print os.path.join(d, fname)
        print template
        f.write(template)
        f.close()

def template_attributes(ns3, tid): 
    d = os.path.dirname(os.path.realpath(__file__))
    ftemp = open(os.path.join(d, "templates", "attribute_template.txt"), "r")
    template = ftemp.read()
    ftemp.close()

    attributes = ""

    attr_count = tid.GetAttributeN()
    for i in xrange(attr_count):
        attr_info = tid.GetAttribute(i)
        if not attr_info.accessor.HasGetter():
            continue

        attr_flags = "None"
        flags = attr_info.flags
        if (flags & ns3.TypeId.ATTR_SET) != ns3.TypeId.ATTR_SET:
            attr_flags = "Flags.Design"
        elif (flags & ns3.TypeId.ATTR_CONSTRUCT) == ns3.TypeId.ATTR_CONSTRUCT:
            attr_flags = "Flags.Construct"

        attr_name = attr_info.name
        checker = attr_info.checker
        attr_help = attr_info.help.replace('"', '\\"').replace("'", "\\'")
        value = attr_info.initialValue
        attr_value = value.SerializeToString(checker)
        attr_allowed = "None"
        attr_range = "None"
        attr_type = "Types.String"

        if isinstance(value, ns3.ObjectVectorValue):
            continue
        elif isinstance(value, ns3.PointerValue):
            continue
        elif isinstance(value, ns3.WaypointValue):
            continue
        elif isinstance(value, ns3.BooleanValue):
            attr_type = "Types.Bool"
            attr_value = "True" if attr_value == "true" else "False"
        elif isinstance(value, ns3.EnumValue):
            attr_type = "Types.Enumerate"
            allowed = checker.GetUnderlyingTypeInformation().split("|")
            attr_allowed = "[%s]" % ",".join(map(lambda x: "\"%s\"" % x, allowed))
        elif isinstance(value, ns3.DoubleValue):
            attr_type = "Types.Double"
            # TODO: range
        elif isinstance(value, ns3.UintegerValue):
            attr_type = "Types.Integer"
            # TODO: range

        attr_id = "attr_" + attr_name.lower().replace("-", "_")
        attributes += template.replace("<ATTR_ID>", attr_id) \
                .replace("<ATTR_NAME>", attr_name) \
                .replace("<ATTR_HELP>", attr_help) \
                .replace("<ATTR_TYPE>", attr_type) \
                .replace("<ATTR_DEFAULT>", attr_value) \
                .replace("<ATTR_ALLOWED>", attr_allowed) \
                .replace("<ATTR_RANGE>", attr_range) \
                .replace("<ATTR_FLAGS>", attr_flags) 

    return attributes

def template_traces(ns3, tid): 
    d = os.path.dirname(os.path.realpath(__file__))
    ftemp = open(os.path.join(d, "templates", "trace_template.txt"), "r")
    template = ftemp.read()
    ftemp.close()

    traces = ""

    trace_count = tid.GetTraceSourceN()
    for i in xrange(trace_count):
        trace_info = tid.GetTraceSource(i)
        trace_name = trace_info.name
        trace_help = trace_info.help.replace('"', '\\"').replace("'", "\\'")

        trace_id = trace_name.lower()
        traces += template.replace("<TRACE_ID>", trace_id) \
                .replace("<TRACE_NAME>", trace_name) \
                .replace("<TRACE_HELP>", trace_help) 

    return traces

if __name__ == "__main__":
    create_ns3_rms()
