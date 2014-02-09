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

class NS3Client(object):
    """ Common Interface for NS3 client classes """
    def __init__(self):
        super(NS3Client, self).__init__()

    def create(self, clazzname, *args):
        pass

    def factory(self, type_name, **kwargs):
        pass

    def invoke(self, uuid, operation, *args):
        pass

    def set(self, uuid, name, value):
        pass

    def get(self, uuid, name):
        pass

    def trace(self, *args):
        pass

    def flush(self):
        pass

    def start(self):
        pass

    def stop(self, time = None):
        pass

    def shutdown(self):
        pass

