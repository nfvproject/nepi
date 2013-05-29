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
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

from nepi.util import guid

guid_gen = guid.GuidGenerator()

class Attributes(object):
    def __init__(self):
        super(Attributes, self).__init__()
        self._attributes = dict()

    def __getattr__(self, name):
        try:
            return self._attributes[name]
        except:
            return super(Attributes, self).__getattribute__(name)

    def __setattr__(self, name, value):
        try:
            if value == None:
                old = self._attributes[name]
                del self._attributes[name]
                return old

            self._attributes[name] = value
            return value
        except:
            return super(Attributes, self).__setattr__(name, value)

class Connections(object):
    def __init__(self):
        super(Connections, self).__init__()
        self._connections = set()

    def __getattr__(self, guid_or_label):
        try:
            for b in self._connections:
                if guid_or_label in [b.guid, b.label]:
                    return b
        except:
            return super(Connections, self).__getattribute__(guid_or_label)

class Box(object):
    def __init__(self, label = None, guid = None):
        super(Box, self).__init__()
        self._guid = guid_gen.next(guid)
        self._a = Attributes()
        self._c = Connections()
        self._tags = set()
        self.label = label or self._guid

        # Graphical information to draw box
        self.x = 0
        self.y = 0
        self.width = 4
        self.height = 4

    @property
    def tags(self):
        return self._tags

    @property
    def attributes(self):
        return self._a._attributes.keys()

    @property
    def a(self):
        return self._a

    @property
    def c(self):
        return self._c

    @property
    def guid(self):
        return self._guid

    @property
    def connections(self):
        return set(self._c._connections)

    def tadd(self, name):
        self._tags.add(name)

    def tdel(self, name):
        self._tags.remove(name)

    def thas(self, name):
        return name in self._tags

    def connect(self, box, cascade = True):
        self._c._connections.add(box)
        if cascade:
            box.connect(self, cascade = False)

    def disconnect(self, box, cascade = True):
        self._c._connections.remove(box)
        if cascade:
            box.disconnect(self, cascade = False)

    def is_connected(self, box):
        return box in self.connections

