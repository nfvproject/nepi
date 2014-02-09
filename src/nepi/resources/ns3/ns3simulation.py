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

class NS3Simulation(object):
    @property
    def client(self):
        return self._client

    def create(self, clazzname, *args):
        return self.client.create(clazzname, *args)

    def factory(self, type_name, **kwargs):
        return self.client.factory(type_name, **kwargs)

    def invoke(self, uuid, operation, *args):
        return self.client.invoke(uuid, operation, *args)

    def set(self, uuid, name, value):
        return self.client.set(uuid, name, value)

    def get(self, uuid, name):
        return self.client.get(uuid, name)

    def enable_trace(self, *args):
        return self.client.enable_trace(*args)

    def flush(self):
        return self.client.flush()

    def start(self):
        return self.client.start()

    def stop(self, time = None):
        return self.client.stop(time)

    def shutdown(self):
        return self.client.shutdown()

