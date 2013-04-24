#!/usr/bin/env python
from neco.execution.resource import ResourceManager, clsinit
from neco.execution.attribute import Attribute, Flags 

from neco.resources.omf.omf_api import OMFAPIFactory

import neco
import logging
import time

@clsinit
class OMFNode(ResourceManager):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

    .. note::

       This class is used only by the Experiment Controller through the Resource Factory

    """
    _rtype = "OMFNode"
    _authorized_connections = ["OMFApplication" , "OMFWifiInterface"]
    _waiters = []

    @classmethod
    def _register_attributes(cls):
        """Register the attributes of an OMF Node

        """
        hostname = Attribute("hostname", "Hostname of the machine")
        cpu = Attribute("cpu", "CPU of the node")
        ram = Attribute("ram", "RAM of the node")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = Flags.Credential)
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = Flags.Credential)
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = Flags.Credential)
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = Flags.Credential)
        cls._register_attribute(hostname)
        cls._register_attribute(ram)
        cls._register_attribute(cpu)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)

    @classmethod
    def _register_filters(cls):
        """Register the filters of an OMF Node

        """
        hostname = Attribute("hostname", "Hostname of the machine")
        gateway = Attribute("gateway", "Gateway")
        granularity = Attribute("granularity", "Granularity of the reservation time")
        hardware_type = Attribute("hardware_type", "Hardware type of the machine")
        cls._register_filter(hostname)
        cls._register_filter(gateway)
        cls._register_filter(granularity)
        cls._register_filter(hardware_type)

    # XXX: We don't necessary need to have the credentials at the 
    # moment we create the RM
    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
        :param creds: Credentials to communicate with the rm (XmppClient for OMF)
        :type creds: dict

        """
        super(OMFNode, self).__init__(ec, guid)

        self._omf_api = None 

        self._logger = logging.getLogger("neco.omf.omfNode   ")

        # XXX: TO DISCUSS
        self._logger.setLevel(neco.LOGLEVEL)

    def _validate_connection(self, guid):
        """Check if the connection is available.

        :param guid: Guid of the current RM
        :type guid: int
        :rtype:  Boolean

        """
        rm = self.ec.get_resource(guid)
        if rm.rtype() in self._authorized_connections:
            self._logger.debug("Connection between %s %s and %s %s accepted" %
                (self.rtype(), self._guid, rm.rtype(), guid))
            return True
        self._logger.debug("Connection between %s %s and %s %s refused" %
            (self.rtype(), self._guid, rm.rtype(), guid))
        return False

    def deploy_action(self):
        """Deploy the RM

        """ 
        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), 
            self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))
        self._omf_api.enroll_host(self.get('hostname'))

        super(OMFNode, self).deploy_action()

    def discover(self):
        """ Discover the availables nodes

        """
        pass
     
    def provision(self):
        """ Provision some availables nodes

        """
        pass

    def start(self):
        """Send Xmpp Message Using OMF protocol to enroll the node into the experiment

        """
        super(OMFNode, self).start()


    def stop(self):
        """Send Xmpp Message Using OMF protocol to disconnect the node

        """
        super(OMFNode, self).stop()

    def release(self):
        """Clean the RM at the end of the experiment

        """
        self._omf_api.release(self.get('hostname'))
        OMFAPIFactory.release_api(self.get('xmppSlice'), 
            self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))


    def configure(self):
        #routes = self.tc._add_route.get(self.guid, [])
        #iface_guids = self.tc.get_connected(self.guid, "devs", "node")
       
        for route in routes:
            (destination, netprefix, nexthop, metric, device) = route
            netmask = ipaddr2.ipv4_mask2dot(netprefix)

            # Validate that the interface is associated to the node
            for iface_guid in iface_guids:
                iface = self.tc.elements.get(iface_guid)
                if iface.devname == device:
                    self._omf_api.execute(self.get('hostname'), 
                        "Id#%s" % str(random.getrandbits(128)), 
                        "add -net %s netmask %s dev %s" % (destination, netmask, iface.devname), 
                        "/sbin/route", # path
                        None, # env
                     )
                    break
