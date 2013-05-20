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

from nepi.execution.resource import ResourceManager, clsinit
from nepi.execution.attribute import Attribute

from nepi.resources.omf.omf_api import OMFAPIFactory

@clsinit
class OMFResource(ResourceManager):
    _rtype = "OMFResource"

    @classmethod
    def _register_attributes(cls):
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = "0x02")
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = "0x02")
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = "0x02")
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = "0x02")
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)

    def __init__(self, ec, guid, creds):
        super(OMFNode, self).__init__(ec, guid)
        self.set('xmppSlice', creds['xmppSlice'])
        self.set('xmppHost', creds['xmppHost'])
        self.set('xmppPort', creds['xmppPort'])
        self.set('xmppPassword', creds['xmppPassword'])

        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

    def discover(self):
        pass
     
    def provision(self, credential):
        pass


