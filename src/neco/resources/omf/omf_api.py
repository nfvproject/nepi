import datetime
import logging
import ssl
import sys
import time

from neco.resources.omf.omf_client import OMFClient
from neco.resources.omf.omf_messages_5_4 import MessageHandler

class OMFAPI(object):
    def __init__(self, slice, host, port, password, xmpp_root = None):
        date = datetime.datetime.now().strftime("%Y-%m-%dt%H.%M.%S")
        tz = -time.altzone if time.daylight != 0 else -time.timezone
        date += "%+06.2f" % (tz / 3600) # timezone difference is in seconds
        self._user = "%s-%s" % (slice, date)
        self._slice = slice
        self._host = host
        self._port = port
        self._password = password
        self._hostnames = []
        self._xmpp_root = xmpp_root or "OMF_5.4"

        self._logger = logging.getLogger("neco.resources.omf")

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
        self._enroll_newexperiment()

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
        #print "Create experiment sesion id topics !!" 
        self._client.subscribe(xmpp_node)
        #print "Subscribe to experiment sesion id topics !!" 


    def _enroll_newexperiment(self):
        address = "/%s/%s/%s/%s" % (self._host, self._xmpp_root, self._slice, self._user)
        print address
        payload = self._message.newexpfunction(self._user, address)
        slice_sid = "/%s/%s" % (self._xmpp_root, self._slice)
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
        return "/%s/%s/%s/%s" % (self._xmpp_root, self._slice, self._user, hostname)

    def _host_resource_id(self, hostname):
        return "/%s/%s/resources/%s" % (self._xmpp_root, self._slice, hostname)

    @property
    def _exp_session_id(self):
        return "/%s/%s/%s" % (self._xmpp_root, self._slice, self._user)

    @property
    def _logger_session_id(self):
        return "/%s/%s/%s/LOGGER" % (self._xmpp_root, self._slice, self._user)

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

    def execute(self, hostname, app_id, arguments, path, env):
        payload = self._message.executefunction(hostname, app_id, arguments, path, env)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def exit(self, hostname, app_id):
        payload = self._message.exitfunction(hostname, app_id)
        xmpp_node =  self._host_session_id(hostname)
        self._client.publish(payload, xmpp_node)

    def disconnect(self):
        self._client.delete(self._exp_session_id)
        self._client.delete(self._logger_session_id)

        for hostname in self._hostnames[:]:
            self.delete(hostname)

        time.sleep(1)
        self._client.disconnect()


class OMFAPIFactory(object):
    _Api = dict()

    @classmethod 
    def get_api(cls, slice, host, port, password):
        if slice and host and port and password:
            key = cls._hash_api(slice, host, port)
            if key in cls._Api:
                return cls._Api[key]
            else :
                return cls.create_api(slice, host, port, password)
        return None

    @classmethod 
    def create_api(cls, slice, host, port, password):
        OmfApi = OMFAPI(slice, host, port, password)
        key = cls._hash_api(slice, host, port)      
        cls._Api[key] = OmfApi
        return OmfApi

    @classmethod 
    def _hash_api(cls, slice, host, port):
        res = slice + "_" + host + "_" + port
        return res





