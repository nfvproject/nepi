# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import testbed_impl
from nepi.util.constants import TIME_NOW

import datetime
import logging
import os
import sys
import ssl
import time

from nepi.testbeds.omf.omf_client import OMFClient
from nepi.testbeds.omf.omf_messages import MessageHandler


class TestbedController(testbed_impl.TestbedController):
    def __init__(self):
        super(TestbedController, self).__init__(TESTBED_ID, TESTBED_VERSION)
        self._slice = None
        self._user = None
        self._host = None
        self._xmpp = None
        self._message = None
        self._home = None
        
        self._logger = logging.getLogger('nepi.testbeds.omf')
 
    def do_setup(self):
        if self._attributes.get_attribute_value("enableDebug") == True:
            self._logger.setLevel(logging.DEBUG)

        # create home
        self._home = self._attributes.\
            get_attribute_value("homeDirectory")
        home = os.path.normpath(self._home)
        if not os.path.exists(home):
            os.makedirs(home, 0755)
    
        # instantiate the xmpp client
        self._init_client()
        # register xmpp nodes for the experiment
        self._publish_and_enroll_experiment()
        # register xmpp logger for the experiment
        self._publish_and_enroll_logger()

        super(TestbedController, self).do_setup()

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        pass

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        return "MISS"

    def shutdown(self):
        node_sid = "/OMF/%s/%s" % (self._slice, self._user)
        self._clean_up(node_sid)
        logger = "/OMF/%s/%s/LOGGER" % (self._slice, self._user)
        self._clean_up(logger)

        for hostname in self._elements.values():
            if not hostname:
                continue
            node_sid = self._host_sid(hostname)
            self._clean_up(node_sid)
            #node_res = self._host_res(hostname)
            #self._clean_up(node_res)

        time.sleep(5)
        self._xmpp.disconnect()

    def _host_sid(self, hostname):
        return "/OMF/%s/%s/%s" % (self._slice, self._user, hostname)

    def _host_res(self, hostname):
        return "/OMF/%s/resources/%s" % (self._slice, hostname)

    def _init_client(self):
        self._slice = self._attributes.get_attribute_value("xmppSlice")
        self._host = self._attributes.get_attribute_value("xmppHost")
        port = self._attributes.get_attribute_value("xmppPort")
        password = self._attributes.get_attribute_value("xmppPassword")
       
        #date = "2012-04-18t16.06.34+02.00"
        date = datetime.datetime.now().strftime("%Y-%m-%dt%H.%M.%S+02.00")
        self._user = "%s-%s" % (self._slice, date)
        jid = "%s@%s" % (self._user, self._host)

        xmpp = OMFClient(jid, password)
        # PROTOCOL_SSLv3 required for compatibility with OpenFire
        xmpp.ssl_version = ssl.PROTOCOL_SSLv3

        if xmpp.connect((self._host, port)):
            xmpp.process(threaded=True)
            while not xmpp.ready:
                time.sleep(1)
            self._xmpp = xmpp
            self._message = MessageHandler(self._slice, self._user)
        else:
            msg = "Unable to connect to the XMPP server."
            self._logger.error(msg)
            raise RuntimeError(msg)

    def _publish_and_enroll_experiment(self):
        node_sid = "/OMF/%s/%s" % (self._slice, self._user)
        self._create_and_subscribe(node_sid)  

        node_slice = "/OMF/%s" % (self._slice)
        address = "/%s/OMF/%s/%s" % (self._host, self._slice, self._user)
        payload = self._message.newexpfunction(self._user, address)
        self._xmpp.publish(payload, node_slice)
   
    def _publish_and_enroll_logger(self):
        logger = "/OMF/%s/%s/LOGGER" % (self._slice, self._user)
        self._create_and_subscribe(logger)

        payload = self._message.logfunction("2", 
                "nodeHandler::NodeHandler", 
                "INFO", 
                "OMF Experiment Controller 5.4 (git 529a626)")
        self._xmpp.publish(payload, logger)

    def _clean_up(self, xmpp_node):
        self._xmpp.delete(xmpp_node)

        if sys.version_info < (3, 0):
            reload(sys)
            sys.setdefaultencoding('utf8')

    def _create_and_subscribe(self, xmpp_node):
        self._xmpp.suscriptions()
        self._xmpp.create(xmpp_node)
        self._xmpp.subscribe(xmpp_node)
        self._xmpp.nodes()

    def _publish_and_enroll_host(self, hostname):
        node_sid =  self._host_sid(hostname)
        self._create_and_subscribe(node_sid)  
        
        node_res =  self._host_res(hostname)
        self._create_and_subscribe(node_res)  

        payload = self._message.enrollfunction("1", "*", "1", hostname)
        self._xmpp.publish(payload, node_res)

    def _publish_configure(self, hostname, attribute, value): 
        payload = self._message.configurefunction(hostname, value, attribute)
        node_sid =  self._host_sid(hostname)
        self._xmpp.publish(payload, node_sid)

    def _publish_execute(self, hostname, app_id, arguments, path):
        payload = self._message.executefunction(hostname, app_id, arguments, path)
        node_sid =  self._host_sid(hostname)
        self._xmpp.publish(payload, node_sid)



