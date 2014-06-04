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
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, ResourceAction
from nepi.util.sshfuncs import ProcStatus

import os
import tempfile

@clsinit_copy
class Collector(ResourceManager):
    """ The collector is reponsible of collecting traces
    of a same type associated to RMs into a local directory.

    .. class:: Class Args :

        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

    """
    _rtype = "Collector"
    _help = "A Collector can be attached to a trace name on another " \
        "ResourceManager and will retrieve and store the trace content " \
        "in a local file at the end of the experiment"
    _backend_type = "all"

    @classmethod
    def _register_attributes(cls):
        trace_name = Attribute("traceName", 
                "Name of the trace to be collected", 
                flags = Flags.Design)

        store_dir = Attribute("storeDir", 
                "Path to local directory to store trace results", 
                default = tempfile.gettempdir(),
                flags = Flags.Design)

        user_run_id = Attribute("useRunId", 
                "If set to True stores traces into a sub directory named after "
                "the RUN ID assigned by the EC", 
                type = types.Bool,
                default = False,
                flags = Flags.Design)

        sub_dir = Attribute("subDir", 
                "Sub directory to collect traces into", 
                flags = Flags.Design)

        rename = Attribute("rename", 
                "Name to give to the collected trace file", 
                flags = Flags.Design)

        cls._register_attribute(trace_name)
        cls._register_attribute(store_dir)
        cls._register_attribute(sub_dir)
        cls._register_attribute(rename)
        cls._register_attribute(useRunId)

    def __init__(self, ec, guid):
        super(Collector, self).__init__(ec, guid)
        self._store_path =  None

    @property
    def store_path(self):
        return self._store_path
   
    def do_provision(self):
        trace_name = self.get("traceName")
        if not trace_name:
            self.fail()
            
            msg = "No traceName was specified"
            self.error(msg)
            raise RuntimeError, msg

        self._store_path = self.get("storeDir")

        if self.get("useRunId"):
            self._store_path = os.path.join(self._store_path, self.ec.run_id)

        subdir = self.get("subDir")
        if subdir:
            self._store_path = os.path.join(self._store_path, subdir)
        
        msg = "Creating local directory at %s to store %s traces " % (
            store_dir, trace_name)
        self.info(msg)

        try:
            os.makedirs(self.store_path)
        except OSError:
            pass

        super(Collector, self).do_provision()

    def do_deploy(self):
        self.do_discover()
        self.do_provision()

        super(Collector, self).do_deploy()

    def do_release(self):
        trace_name = self.get("traceName")
        rename = self.get("rename") or trace_name

        msg = "Collecting '%s' traces to local directory %s" % (
            trace_name, self.store_path)
        self.info(msg)

        rms = self.get_connected()
        for rm in rms:
            result = self.ec.trace(rm.guid, trace_name)
            fpath = os.path.join(self.store_path, "%d.%s" % (rm.guid, 
                rename))
            try:
                f = open(fpath, "w")
                f.write(result)
                f.close()
            except:
                import traceback
                err = traceback.format_exc()
                msg = "Couldn't retrieve trace %s for %d at %s " % (trace_name, 
                        rm.guid, fpath)
                self.error(msg, out = "", err = err)
                continue

        super(Collector, self).do_release()

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

