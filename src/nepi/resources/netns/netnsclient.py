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

class NetNSClient(object):
    """ Common Interface for NS3 client classes """
    def __init__(self):
        super(NetNSClient, self).__init__()

    def create(self, *args, **kwargs):
        pass

    def invoke(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass

    def shutdown(self, *args, **kwargs):
        pass

