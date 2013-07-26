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

from nepi.execution.attribute import Attribute, Flags
from nepi.execution.resource import ResourceManager, clsinit, ResourceState

@clsinit
class LinuxChannel(ResourceManager):
    _rtype = "LinuxChannel"

    def __init__(self, ec, guid):
        super(LinuxChannel, self).__init__(ec, guid)

    def log_message(self, msg):
        return " guid %d - %s " % (self.guid, msg)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True
