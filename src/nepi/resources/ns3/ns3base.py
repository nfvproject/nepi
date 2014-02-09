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

from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay

from nepi.execution.attribute import Flags

reschedule_delay = "2s"

@clsinit_copy
class NS3Base(ResourceManager):
    _rtype = "abstract::ns3::Object"
    _backend_type = "ns3"

    SIMULATOR_UUID = "singleton::Simulator"

    def __init__(self, ec, guid):
        super(NS3Base, self).__init__(ec, guid)
        self._uuid = None
        self._connected = set()

    @property
    def connected(self):
        return self._connected

    @property
    def uuid(self):
        return self._uuid

    @property
    def simulation(self):
        return self.node.simulation

    @property
    def node(self):
        from nepi.resources.ns3.ns3node import NS3BaseNode
        nodes = self.get_connected(NS3BaseNode.get_rtype())
        if nodes: return nodes[0]
        return None

    @property
    def _rms_to_wait(self):
        """ Returns the collection of ns-3 RMs that this RM needs to
        wait for before start

        This method should be overriden to wait for other ns-3
        objects to be deployed before proceeding with the deployment

        """
        rms = set()
        node = self.node
        if node: rms.add(node)
        return rms

    def _instantiate_object(self):
        if self.uuid:
            return 

        kwargs = dict()
        for attr in self._attrs.values():
            if not (attr.has_changed() and attr.has_flag(Flags.Construct)):
                continue

            kwargs[attr.name] = attr.value

        self._uuid = self.simulation.factory(self.get_rtype(), **kwargs)

    def _configure_object(self):
        pass

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self.simulation.invoke(node.uuid, "AggregateObject", self.uuid)
            self._connected.add(node.uuid)

    def _wait_rms(self):
        """ Returns True if dependent RMs are not yer READY, False otherwise"""
        for rm in self._rms_to_wait:
            if rm and rm.state < ResourceState.READY:
                return True
        return False

    def do_provision(self):
        # TODO: create run dir for ns3 object !!!!
        # self.simulation.node.mkdir(self.run_home)

        self._instantiate_object()
        self._connect_object()
        self._configure_object()
      
        self.info("Provisioning finished")

        super(NS3Base, self).do_provision()

    def do_deploy(self):
        if self._wait_rms():
            self.debug("---- RESCHEDULING DEPLOY ----" )
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            self.info("Entering deploy")
            self.do_discover()
            self.do_provision()

            self.set_ready()

    def do_start(self):
        if self.state == ResourceState.READY:
            # No need to do anything, simulation.Run() will start every object
            self.info("Starting")
            self.set_started()
        else:
            msg = " Failed "
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        if self.state == ResourceState.STARTED:
            # No need to do anything, simulation.Destroy() will stop every object
            self.info("Stopping command '%s'" % command)
            self.set_stopped()
    
    @property
    def state(self):
        return self._state

