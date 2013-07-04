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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit, ResourceState, \
        ResourceAction
from nepi.util.sshfuncs import ProcStatus

import os
import tempfile

@clsinit
class Collector(ResourceManager):
    """ The collector is reponsible of collecting traces
    of a same type associated to RMs into a local directory.

    .. class:: Class Args :

        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient)
        :type creds: dict

    """
    _rtype = "Collector"

    @classmethod
    def _register_attributes(cls):
        trace_name = Attribute("traceName", "Name of the trace to be collected", 
                flags = Flags.ExecReadOnly)
        store_dir = Attribute("storeDir", "Path to local directory to store trace results", 
                default = tempfile.gettempdir(),
                flags = Flags.ExecReadOnly)

        cls._register_attribute(trace_name)
        cls._register_attribute(store_dir)

    def __init__(self, ec, guid):
        super(Collector, self).__init__(ec, guid)
        self._store_path =  None

    @property
    def store_path(self):
        return self._store_path
    
    def provision(self):
        trace_name = self.get("traceName")
        if not trace_name:
            self.fail()
            
            msg = "No traceName was specified"
            self.error(msg)
            raise RuntimeError, msg

        store_dir = self.get("storeDir")
        self._store_path = os.path.join(store_dir, self.ec.exp_id, self.ec.run_id)
        
        msg = "Creating local directory at %s to store %s traces " % (
            store_dir, trace_name)
        self.info(msg)

        try:
            os.makedirs(self.store_path)
        except OSError:
            pass

        super(Collector, self).provision()

    def deploy(self):
        try:
            self.discover()
            self.provision()
        except:
            self.fail()
            raise

        super(Collector, self).deploy()

    def release(self):
        trace_name = self.get("traceName")

        msg = "Collecting '%s' traces to local directory %s" % (
            trace_name, self.store_path)
        self.info(msg)

        rms = self.get_connected()
        for rm in rms:
            result = self.ec.trace(rm.guid, trace_name)
            fpath = os.path.join(self.store_path, "%d.%s" % (rm.guid, 
                trace_name))
            f = open(fpath, "w")
            f.write(result)
            f.close()

        super(Collector, self).release()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

