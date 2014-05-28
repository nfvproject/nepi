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
class NS3LteSimpleNetDevice(NS3BaseNetDevice):
    _rtype = "ns3::LteSimpleNetDevice"

    @classmethod
    def _register_attributes(cls):
        pass

    @classmethod
    def _register_traces(cls):
        
        phyrxdrop = Trace("PhyRxDrop", "Trace source indicating a packet has been dropped by the device during reception")

        cls._register_trace(phyrxdrop)



    def __init__(self, ec, guid):
        super(NS3LteSimpleNetDevice, self).__init__(ec, guid)
        self._home = "ns3-lte-simple-net-device-%s" % self.guid
