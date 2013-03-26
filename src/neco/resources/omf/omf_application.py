#!/usr/bin/env python
from neco.execution.resource import Resource, clsinit
from neco.execution.attribute import Attribute
from neco.resources.omf.omf_api import OMFAPIFactory

import neco
import logging

@clsinit
class OMFApplication(Resource):
    _rtype = "OMFApplication"
    _authorized_connections = ["OMFNode"]

    @classmethod
    def _register_attributes(cls):
        appid = Attribute("appid", "Name of the application")
        path = Attribute("path", "Path of the application")
        args = Attribute("args", "Argument of the application")
        env = Attribute("env", "Environnement variable of the application")
        xmppSlice = Attribute("xmppSlice","Name of the slice", flags = "0x02")
        xmppHost = Attribute("xmppHost", "Xmpp Server",flags = "0x02")
        xmppPort = Attribute("xmppPort", "Xmpp Port",flags = "0x02")
        xmppPassword = Attribute("xmppPassword", "Xmpp Port",flags = "0x02")
        cls._register_attribute(appid)
        cls._register_attribute(path)
        cls._register_attribute(args)
        cls._register_attribute(env)
        cls._register_attribute(xmppSlice)
        cls._register_attribute(xmppHost)
        cls._register_attribute(xmppPort)
        cls._register_attribute(xmppPassword)


    def __init__(self, ec, guid, creds):
        super(OMFApplication, self).__init__(ec, guid)
        self.set('xmppSlice', creds['xmppSlice'])
        self.set('xmppHost', creds['xmppHost'])
        self.set('xmppPort', creds['xmppPort'])
        self.set('xmppPassword', creds['xmppPassword'])

        self.set('appid', "")
        self.set('path', "")
        self.set('args', "")
        self.set('env', "")

        self._node = None

        self._omf_api = OMFAPIFactory.get_api(self.get('xmppSlice'), self.get('xmppHost'), self.get('xmppPort'), self.get('xmppPassword'))

        self._logger = logging.getLogger("neco.omf.omfApp    ")
        self._logger.setLevel(neco.LOGLEVEL)

    def _validate_connection(self, guid):
        rm = self.ec.resource(guid)
        if rm.rtype() not in self._authorized_connections:
            self._logger.debug("Connection between %s %s and %s %s refused : An Application can be connected only to a Node" % (self.rtype(), self._guid, rm.rtype(), guid))
            return False
        elif len(self.connections) != 0 :
            self._logger.debug("Connection between %s %s and %s %s refused : Already Connected" % (self.rtype(), self._guid, rm.rtype(), guid))
            return False
        else :
            self._logger.debug("Connection between %s %s and %s %s accepted" % (self.rtype(), self._guid, rm.rtype(), guid))
            return True

    def _get_nodes(self, conn_set):
        for elt in conn_set:
            rm = self.ec.resource(elt)
            if rm.rtype() == "OMFNode":
                return rm
        return None

    def start(self):
        self._logger.debug(" " + self.rtype() + " ( Guid : " + str(self._guid) +") : " + self.get('appid') + " : " + self.get('path') + " : " + self.get('args') + " : " + self.get('env'))
        #try:
        if self.get('appid') and self.get('path') and self.get('args') and self.get('env'):
            rm_node = self._get_nodes(self._connections)
            self._omf_api.execute(rm_node.get('hostname'),self.get('appid'), self.get('args'), self.get('path'), self.get('env'))

    def stop(self):
        rm_node = self._get_nodes(self._connections)
        self._omf_api.exit(rm_node.get('hostname'),self.get('appid'))



