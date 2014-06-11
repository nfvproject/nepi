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
# Authors: Alina Quereilhac <alina.quereilhac@inria.fr>
#          Julien Tribino <julien.tribino@inria.fr>



from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay

#import time
#import threading

#clsinit_copy is used to copy the attirbute from parent class
@clsinit_copy
class RMName(ResourceManager):
        
    _rtype = "RMName" # Name that will be used in the Experiment Description Script 
    _help = "Help that describe the RM"
    _backend_type = "backend" # Name of the platform this RM is attached. 
    _authorized_connections = ["RMName1" , "RMName2"] # list of valid connection for this RM


    @classmethod
    def _register_attributes(cls):
    '''
        This method is used to register all the attribute of this RM. Check the
        file src/execution/attribute.py to see all the fields of this class
    '''

        attribute1 = Attribute("nameOfAttribute1", "Description of the Attribute 1",
                flags = Flags.Design)

        attribute2 = Attribute("nameOfAttribute2", "Description of the Attribute 2",
                flags = Flags.Design)

        cls._register_attribute(attribute1)
        cls._register_attribute(attribute2)

    def __init__(self, ec, guid):
    '''
        In the init, we usually intialize the variable of the RM that are not attribute
    '''

        super(RMName, self).__init__(ec, guid)

        self.var1 = None

    
    def log_message(self, msg):
    '''
        In some particular cases, it is required to redefined the log of the RM.
        The default log require the name of the node, but sometimes, 
        it does not mean something.
    '''
        return " guid %d - host %s - %s " % (self.guid, 
                self.get("hostname"), msg)


    def valid_connection(self, guid):
    '''
        Check if the connection is valide or not, depending on the list povided in the parameter
        _authorized_connection described above
    '''
        return True

    # This one is not mandatory
    def do_discover(self):
    '''
        Do anything required to discover the resource.The meaning of discover
        is different for each RM 
    '''
        super(RMName, self).do_discover()

    # This one is not mandatory
    def do_provision(self):
    '''
        Do anything required to provision the resource.The meaning of provision
        is different for each RM 
    '''
        super(RMName, self).do_provision()

    def do_deploy(self):
    '''
        Do anything required to deploy the resource.The meaning of deploy 
        is different for each RM 
    '''
        super(RMName, self).do_deploy()


    def do_start(self):
    '''
        Do anything required to start the resource.The meaning of start 
        is different for each RM 
    '''
        super(RMName, self).do_release()


    def do_stop(self):
    '''
        Do anything required to stop the resource.The meaning of stop 
        is different for each RM 
    '''
        super(RMName, self).do_release()

    def do_release(self):
    '''
        Do anything required to release the resource.The meaning of release 
        is different for each RM 
    '''
        super(RMName, self).do_release()


