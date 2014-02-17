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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.ns3.ns3netdevice import NS3BaseNetDevice 

@clsinit_copy
class NS3FdNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::FdNetDevice"

    @classmethod
    def _register_attributes(cls):
        
        attr_address = Attribute("Address",
            "The MAC address of this device.",
            type = Types.String,
            default = "ff:ff:ff:ff:ff:ff",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_address)

        attr_start = Attribute("Start",
            "The simulation time at which to spin up the device thread.",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_start)

        attr_stop = Attribute("Stop",
            "The simulation time at which to tear down the device thread.",
            type = Types.String,
            default = "+0.0ns",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_stop)

        attr_encapsulationmode = Attribute("EncapsulationMode",
            "The link-layer encapsulation type to use.",
            type = Types.Enumerate,
            default = "Dix",  
            allowed = ["Dix","Llc","DixPi"],
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_encapsulationmode)

        attr_rxqueuesize = Attribute("RxQueueSize",
            "Maximum size of the read queue.  This value limits number of packets that have been read from the network into a memory buffer but have not yet been processed by the simulator.",
            type = Types.Integer,
            default = "1000",  
            allowed = None,
            range = None,    
            flags = Flags.Reserved | Flags.Construct)

        cls._register_attribute(attr_rxqueuesize)



    @classmethod
    def _register_traces(cls):
        
        mactx = Trace("MacTx", "Trace source indicating a packet has arrived for transmission by this device")

        cls._register_trace(mactx)

        mactxdrop = Trace("MacTxDrop", "Trace source indicating a packet has been dropped by the device before transmission")

        cls._register_trace(mactxdrop)

        macpromiscrx = Trace("MacPromiscRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a promiscuous trace,")

        cls._register_trace(macpromiscrx)

        macrx = Trace("MacRx", "A packet has been received by this device, has been passed up from the physical layer and is being forwarded up the local protocol stack.  This is a non-promiscuous trace,")

        cls._register_trace(macrx)

        sniffer = Trace("Sniffer", "Trace source simulating a non-promiscuous packet sniffer attached to the device")

        cls._register_trace(sniffer)

        promiscsniffer = Trace("PromiscSniffer", "Trace source simulating a promiscuous packet sniffer attached to the device")

        cls._register_trace(promiscsniffer)



    def __init__(self, ec, guid):
        super(NS3FdNetDevice, self).__init__(ec, guid)
        self._home = "ns3-fd-net-device-%s" % self.guid
