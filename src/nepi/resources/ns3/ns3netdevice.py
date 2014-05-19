#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
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

from nepi.execution.attribute import Attribute, Flags
from nepi.execution.resource import clsinit_copy
from nepi.execution.trace import Trace
from nepi.resources.ns3.ns3base import NS3Base

import ipaddr

@clsinit_copy
class NS3BaseNetDevice(NS3Base):
    _rtype = "abstract::ns3::NetDevice"

    @classmethod
    def _register_attributes(cls):
        mac = Attribute("mac", "MAC address for device",
                flags = Flags.Design)

        ip = Attribute("ip", "IP address for device",
                flags = Flags.Design)

        prefix = Attribute("prefix", "Network prefix for device",
                flags = Flags.Design)

        cls._register_attribute(mac)
        cls._register_attribute(ip)
        cls._register_attribute(prefix)

    @classmethod
    def _register_traces(cls):
        pcap = Trace("pcap", "Dump traffic sniffed on the network device in Pcap format")
        promisc_pcap = Trace("promiscPcap", "Dump traffic sniffed in promiscuous mode on the network device in Pcap format")
        ascii = Trace("ascii", "Dump traffic sniffed on the network device in Ascii format")

        cls._register_trace(pcap)
        cls._register_trace(promisc_pcap)
        cls._register_trace(ascii)

    def __init__(self, ec, guid):
        super(NS3BaseNetDevice, self).__init__(ec, guid)
        self._ascii_helper_uuid = None
        self._device_helper_uuid = None

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())

        if not nodes: 
            msg = "Device not connected to node"
            self.error(msg)
            raise RuntimeError, msg

        return nodes[0]

    @property
    def channel(self):
        from nepi.resources.ns3.ns3channel import NS3BaseChannel
        channels = self.get_connected(NS3BaseChannel.get_rtype())

        if not channels: 
            msg = "Device not connected to channel"
            self.error(msg)
            raise RuntimeError, msg

        return channels[0]

    @property
    def queue(self):
        from nepi.resources.ns3.ns3queue import NS3BaseQueue
        queue = self.get_connected(NS3BaseQueue.get_rtype())

        if not queue: 
            msg = "Device not connected to queue"
            self.error(msg)
            raise RuntimeError, msg

        return queue[0]

    @property
    def ascii_helper_uuid(self):
        if not self._ascii_helper_uuid:
            self._ascii_helper_uuid = self.simulation.create("AsciiTraceHelper")
        return self._ascii_helper_uuid

    @property
    def device_helper_uuid(self):
        if not self._device_helper_uuid:
            rtype = self.get_rtype()
            if rtype == "ns3::PointToPointNetDevice":
                classname = "PointToPointHelper"
            elif rtype == "ns3::CsmaNetDevice":
                classname = "CsmaHelper"
            elif rtype == "ns3::EmuNetDevice":
                classname = "EmuHelper"
            elif rtype == "ns3::FdNetDevice":
                classname = "FdNetDeviceHelper"
            elif rtype in [ "ns3::BaseStationNetDevice", "SubscriberStationNetDevice" ]:
                classname = "WimaxHelper"
            elif rtype == "ns3::WifiNetDevice":
                classname = "YansWifiPhyHelper"

            self._device_helper_uuid = self.simulation.create(classname)

        return self._device_helper_uuid

    @property
    def _rms_to_wait(self):
        rms = set()
        
        node = self.node
        rms.add(node)

        ipv4 = node.ipv4
        if node.ipv4:
            rms.add(ipv4)

        rms.add(self.channel)
        return rms

    def _configure_object(self):
        # Set Mac
        self._configure_mac_address()

        # Set IP address
        self._configure_ip_address()
        
        # Enable traces
        self._configure_traces()

    def _configure_mac_address(self):
        mac = self.get("mac")
        if mac:
            mac_uuid = self.simulation.create("Mac48Address", mac)
        else:
            mac_uuid = self.simulation.invoke("singleton::Mac48Address", "Allocate")

        self.simulation.invoke(self.uuid, "SetAddress", mac_uuid)

    def _configure_ip_address(self):
        ip = self.get("ip")
        prefix = self.get("prefix")

        i = ipaddr.IPAddress(ip)
        if i.version == 4:
            # IPv4
            ipv4 = self.node.ipv4
            ifindex_uuid = self.simulation.invoke(ipv4.uuid, "AddInterface", 
                    self.uuid)
            ipv4_addr_uuid = self.simulation.create("Ipv4Address", ip)
            ipv4_mask_uuid = self.simulation.create("Ipv4Mask", "/%s" % str(prefix))
            inaddr_uuid = self.simulation.create("Ipv4InterfaceAddress", 
                    ipv4_addr_uuid, ipv4_mask_uuid)
            self.simulation.invoke(ipv4.uuid, "AddAddress", ifindex_uuid, 
                    inaddr_uuid)
            self.simulation.invoke(ipv4.uuid, "SetMetric", ifindex_uuid, 1)
            self.simulation.invoke(ipv4.uuid, "SetUp", ifindex_uuid)
        else:
            # IPv6
            # TODO!
            pass

    def _configure_traces(self):
        if self.trace_enabled("pcap"):
            helper_uuid = self.device_helper_uuid

            filename = "trace-pcap-netdev-%d.pcap" % self.guid
            self._trace_filename["pcap"] = filename

            filepath = self.simulation.trace_filepath(filename)

            self.simulation.invoke(helper_uuid, "EnablePcap", filepath, 
                    self.uuid, promiscuous = False, explicitFilename = True)

        if self.trace_enabled("promiscPcap"):
            helper_uuid = self.device_helper_uuid

            filename = "trace-promisc-pcap-netdev-%d.pcap" % self.guid
            self._trace_filename["promiscPcap"] = filename

            filepath = self.simulation.trace_filepath(filename)

            self.simulation.invoke(helper_uuid, "EnablePcap", filepath, 
                    self.uuid, promiscuous = True, explicitFilename = True)

        if self.trace_enabled("ascii"):
            helper_uuid = self.device_helper_uuid
            ascii_helper_uuid = self.ascii_helper_uuid

            filename = "trace-ascii-netdev-%d.tr" % self.guid
            self._trace_filename["ascii"] = filename

            filepath = self.simulation.trace_filepath(filename)
            stream_uuid = self.simulation.invoke(ascii_helper_uuid, 
                    "CreateFileStream", filepath) 
            self.simulation.invoke(helper_uuid, "EnableAscii", stream_uuid,
                    self.uuid)

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self.simulation.invoke(node.uuid, "AddDevice", self.uuid)
            self._connected.add(node.uuid)

        channel = self.channel
        if channel and channel.uuid not in self.connected:
            self.simulation.invoke(self.uuid, "Attach", channel.uuid)
            self._connected.add(channel.uuid)
        
        queue = self.queue
        # Verify that the device has a queue. If no queue is added a segfault 
        # error occurs
        if queue and queue.uuid not in self.connected:
            self._connected.add(queue.uuid)
