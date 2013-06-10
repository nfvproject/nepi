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

class TraceAttr:
    """ Class representing the different attributes 
    that can characterized a trace.

    """
    ALL = 'all'
    STREAM = 'stream'
    PATH = 'path'
    SIZE = 'size'

class Trace(object):
    """
    .. class:: Class Args :
      
        :param name: Name of the trace
        :type name: str
        :param help: Help about the trace
        :type help: str

    """

    def __init__(self, name, help):
        self._name = name
        self._help = help
        self.enabled = False

    @property
    def name(self):
    """ Returns the name of the trace """
        return self._name

    @property
    def help(self):
    """ Returns the help of the trace """
        return self._help
