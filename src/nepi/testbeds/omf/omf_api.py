import datetime
import logging
import ssl
import sys
import time

from nepi.testbeds.omf.omf_client import OMFClient
from nepi.testbeds.omf.omf_messages import MessageHandler

class OmfAPI(object):
    def __init__(self, slice, host, port, password, debug):
        date = datetime.datetime.now().strftime("%Y-%m-%dt%H.%M.%S")
        tz = -time.altzone if time.daylight != 0 else -time.timezone
        date += "%+06.2f" % (tz / 3600) # timezone difference is in seconds
        self._user = "%s-%s" % (slice, date)
        self._slice = slice
        self._host = host
        self._port = port
        self._password = password
        self._hostnames = []

        self._logger = logging.getLogger('nepi.testbeds.omfapi')
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # OMF xmpp client
        self._client = None
        # message handler
        self._message = None

        if sys.version_info < (3, 0):
            reload(sys)
            sys.setdefaultencoding('utf8')

        # instantiate the xmpp client
        self._init_client()

        # register xmpp nodes for the experiment
        self._enroll_experiment()

        # register xmpp logger for the experiment
        self._enroll_logger()

    def _init_client(self):
        jid = "%s@%s" % (self._user, self._host)
        xmpp = OMFClient(jid, self._password)
        # PROTOCOL_SSLv3 required for compatibility with OpenFire
        xmpp.ssl_version = ssl.PROTOCOL_SSLv3

        if xmpp.connect((self._host, self._port)):
            xmpp.process(threaded=True)
            while not xmpp.ready:
                time.sleep(1)
            self._client = xmpp
            self._message = MessageHandler(self._slice, self._user)
        else:
            msg = "Unable to connect to the XMPP server."
            self._logger.error(msg)
            raise RuntimeError(msg)

    def _enroll_experiment(self):
        xmpp_node = self._exp_session_id
        self._client.create(xmpp_node)
        self._client.subscribe(xmpp_node)

        address = "/%s/OMF/%s/%s" % (self._host, self._slice, self._user)
        payload = self._message.newexpfunction(self._user, address)
        slice_sid = "/OMF/%s" % (self._slice)
        self._client.publish(payload, slice_sid)

    def _enroll_logger(self):
        xmpp_node = self._logger_session_id
        self._client.create(xmpp_node)
        self._client.subscribe(xmpp_node)

        payload = self._message.logfunction("2", 
                "nodeHandler::NodeHandler", 
                "INFO", 
                "OMF Experiment Controller 5.4 (git 529a626)")
        self._client.publish(payload, xmpp_node)

    def _host_session_id(self, hostname):
        return "/OMF/%s/%s/%s" % (self._slice, self._user, hostname)

    def _host_resource_id(self, hostname):
        return "/OMF/%s/resources/%s" % (self._slice, hostname)

    @property
    def _exp_session_id(self):
        return "/OMF/%s/%s" % (self._slice, self._user)

    @property
    def _logger_session_id(self):
        return "/OMF/%s/%s/LOGGER" % (self._slice, self._user)

    def delete(self, hostname):
        if not hostname in self._hostnames:
            return

        self._hostnames.remove(hostname)

        xmpp_node = self._host_session_id(hostname)
        self._client.delete(xmpp_node)

    def enroll_host(self, hostname):
        if hostname in self._hostnames:
            return 

        self._hostnames.append(hostname)

        xmpp_node =  self._host_session_id(hostname)
        self._client.create(xmpp_node)
        self._client.subscribe(xmpp_node)

        xmpp_node =  self._host_resource_id(hostname)
        self._client.subscribe(xmpp_node)

        payload = self._message.enrollfunction("1", "*", "1", hostname)
        self._client.publish(payload, xmpp_node)

    def configure(self, hostname, attribute, value): 
        payload = self._message.configurefunction(hostname, value, attribute)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def execute(self, hostname, app_id, arguments, path):
        payload = self._message.executefunction(hostname, app_id, arguments, path)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def disconnect(self):
        self._client.delete(self._exp_session_id)
        self._client.delete(self._logger_session_id)

        for hostname in self._hostnames[:]:
            self.delete(hostname)

        time.sleep(5)
        self._client.disconnect()

