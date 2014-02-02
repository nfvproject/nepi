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

from nepi.execute.attributes import Flags
from nepi.resources.ns3.ns3simulator import NS3Simulator
from nepi.resources.ns3.ns3node import NS3BaseNode

@clsinit_copy
class NS3Base(ResourceManager):
    _rtype = "ns3::Object"

    def __init__(self):
        super(NS3Base, self).__init__()
        self._uuid = None
        self._connected = set()

    @property
    def connected(self):
        return self._connected

    @property
    def uuid(self):
        return self._uuid

    @property
    def simulator(self):
        simulators = self.get_connected(NS3Simulator.get_rtype())
        if simulators: return simulators[0]
        # if the object is not directly connected to the simulator,
        # it should be connected to a node
        node = self.node
        if node: return node.simulator
        return None
         
    @property
    def node(self):
        nodes = self.get_connected(NS3BaseNode.get_rtype())
        if nodes: return nodes[0]
        return None

    @property
    def others_to_wait(self):
        others = set()
        node = self.node
        if node: others.add(node)
        return others

    def _instantiate_object(self):
        if self.uuid:
            return 

        kwargs = dict()
        for attr in self._attrs:
            if not attr.value or attr.has_flag(Flags.ReadOnly):
                continue

            kwargs[attr.name] = attr.value

        self.uuid = self.simulator.factory(self.get_rtype(), **kwargs)

    def _configure_object(self):
        pass

    def _connect_object(self):
        node = self.node
        if node and node.uuid not in self.connected:
            self.simulator.invoke(node.uuid, "AggregateObject", self.uuid)
            self._connected.add(node.uuid)

    def _wait_others(self):
        """ Returns the collection of ns-3 RMs that this RM needs to
        wait for before start

        This method should be overriden to wait for other ns-3
        objects to be deployed before proceeding with the deployment

        """
        for other in self.others_to_wait:
            if other and other.state < ResourceState.READY:
                return True
        return False

    def do_provision(self):
        # create run dir for ns3 object
        # self.simulator.node.mkdir(self.run_home)

        self._instantiate_object()
        self._configure_object()
        self._connect_object()
      
        self.info("Provisioning finished")

        super(NS3Base, self).do_provision()

    def do_deploy(self):
        if not self.simulator or self.simulator.state < ResourceState.READY or \
                self._wait_others():
            self.debug("---- RESCHEDULING DEPLOY ----" )
            
            # ccnd needs to wait until node is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            # TODO: CREATE AND CONFIGURE NS-3 C++ OBJECT
            self.do_discover()
            self.do_provision()

            self.debug("----- READY ---- ")
            self.set_ready()

    def do_start(self):
        if self.state == ResourceState.READY:
            # No need to do anything, simulator.Run() will start every object
            self.info("Starting")
            self.set_started()
        else:
            msg = " Failed "
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        if self.state == ResourceState.STARTED:
            # No need to do anything, simulator.Destroy() will stop every object
            self.info("Stopping command '%s'" % command)
            self.set_stopped()
    
    @property
    def state(self):
        return self._state

