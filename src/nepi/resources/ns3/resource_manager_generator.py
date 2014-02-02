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

def select_base_class(ns3, tid): 
    rtype = tid.GetName()

    type_id = ns3.TypeId()
    appbase = type_id.LookupByName("ns3::Application")
    devicebase = type_id.LookupByName("ns3::NetDevice")
    channelbase = type_id.LookupByName("ns3::Channel")
    queuebase = type_id.LookupByName("ns3::Queue")
    lossbase = type_id.LookupByName("ns3::PropagationLossModel")
    delaybase = type_id.LookupByName("ns3::PropagationDelayModel")
    managerbase = type_id.LookupByName("ns3::WifiRemoteStationManager")

    if tid.IsChiledOf(appbase):
       base_class_import = "from nepi.resources.ns3.ns3application import NS3BaseApplication"
       base_class = "NS3BaseApplication"
    elif tid.IsChiledOf(devicebase):
       base_class_import = "from nepi.resources.ns3.ns3device import NS3BaseNetDevice"
       base_class = "NS3BaseNetDevice"
    elif tid.IsChiledOf(channelbase):
       base_class_import = "from nepi.resources.ns3.ns3channel import NS3BaseChannel"
       base_class = "NS3BaseChannel"
    elif tid.IsChiledOf(queuebase):
       base_class_import = "from nepi.resources.ns3.ns3queue import NS3BaseQueue"
       base_class = "NS3BaseQueue"
    elif tid.IsChiledOf(lossbase):
       base_class_import = "from nepi.resources.ns3.ns3loss import NS3BasePropagationLossModel"
       base_class = "NS3BasePropagationLossDelay"
    elif tid.IsChiledOf(delaybase):
       base_class_import = "from nepi.resources.ns3.ns3delay import NS3BasePropagationDelayModel"
       base_class = "NS3BasePropagationDelayModel"
    elif tid.IsChiledOf(managerbase):
       base_class_import = "from nepi.resources.ns3.ns3manager import NS3BaseWifiRemoteStationManager"
       base_class = "NS3BaseWifiRemoteStationManager"
    elif rtype == "ns3::Node":
       base_class_import = "from nepi.resources.ns3.ns3node import NS3BaseNode"
       base_class = "NS3BaseNode"
    elif rtype == "ns3::Ipv4L3Protocol":
       base_class_import = "from nepi.resources.ns3.ns3ipv4protocol import NS3BaseIpV4Protocol"
       base_class = "NS3BaseIpV4Protocol"
    else:
       base_class_import = "from nepi.resources.ns3.ns3base import NS3Base"
       base_class = "NS3Base"

    return (base_class_import, base_class)

def create_ns3_rms():
    ns3 = load_ns3_module()

    type_id = ns3.TypeId()
    
    tid_count = type_id.GetRegisteredN()
    base = type_id.LookupByName("ns3::Object")

    # Create a .py file using the ns-3 RM template for each ns-3 TypeId
    for i in xrange(tid_count):
        tid = type_id.GetRegistered(i)
        
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

        rtype = tid.GetName()
        category = tid.GetGroupName()

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

        #f = open(os.path.join(d, "classes", fname), "w")
        #print os.path.join(d, fname)
        #print template
        #f.write(template)
        #f.close()

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
            attr_flags = "Types.ExecReadOnly"

        attr_name = attr_info.name
        checker = attr_info.checker
        attr_help = attr_info.help.replace('"', '\\"').replace("'", "\\'")
        value = attr_info.initialValue
        attr_value = value.SerializeToString(checker)
        attr_allowed = "None"
        attr_range = "None"
        attr_type = "Types.STRING"

        if isinstance(value, ns3.ObjectVectorValue):
            continue
        elif isinstance(value, ns3.PointerValue):
            continue
        elif isinstance(value, ns3.WaypointValue):
            continue
        elif isinstance(value, ns3.BooleanValue):
            attr_type = "Types.BOOL"
            attr_value = "True" if attr_value == "true" else "False"
        elif isinstance(value, ns3.EnumValue):
            attr_type = "Types.ENUM"
            attr_allowed = "[%s]"% checker.GetUnderlyingTypeInformation().replace("|", ",")
        elif isinstance(value, ns3.DoubleValue):
            attr_type = "Types.DOUBLE"
            # TODO: range
        elif isinstance(value, ns3.UintegerValue):
            attr_type = "Types.INTEGER"
            # TODO: range

        attr_id = attr_name.lower()
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
