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

from nepi.resources.ns3.simulator import NS3Simulator

@clsinit_copy
class NS3Base(ResourceManager):
    _rtype = "NS3Base"

    @property
    def simulator(self):
        simulator = self.get_connected(NS3Simulator.get_rtype())
        if simulator: return simulator[0]
        return None

    def do_deploy(self):
        if not self.simulator or self.simulator.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.simulator.state )
            
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
            ## TODO!!!
            self.info("Starting ...")

            self.set_started()
        else:
            msg = " Failed "
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        if self.state == ResourceState.STARTED:
            self.info("Stopping command '%s'" % command)
            ## TODO!!!

            self.set_stopped()
    
    @property
    def state(self):
        # First check if the ccnd has failed
        # TODO!!!
        return self._state

