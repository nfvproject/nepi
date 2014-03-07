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
#         Julien Tribino <julien.tribino@inria.fr>

import ssl
import sys
import time
import hashlib
import threading

from nepi.util.timefuncs import tsformat 
import os

from nepi.util.logger import Logger

from nepi.resources.omf.omf_client import OMFClient
from nepi.resources.omf.messages_6 import MessageHandler

class OMF6API(Logger):
    """
    .. class:: Class Args :
      
        :param slice: Xmpp Slice
        :type slice: str
        :param host: Xmpp Server
        :type host: str
        :param port: Xmpp Port
        :type port: str
        :param password: Xmpp password
        :type password: str
        :param xmpp_root: Root of the Xmpp Topic Architecture
        :type xmpp_root: str

    .. note::

       This class is the implementation of an OMF 5.4 API. 
       Since the version 5.4.1, the Topic Architecture start with OMF_5.4 
       instead of OMF used for OMF5.3

    """
    def __init__(self, host, user = "nepi", port="5222", password="1234",
            exp_id = None):
        """
    
        :param slice: Xmpp Slice
        :type slice: str
        :param host: Xmpp Server
        :type host: str
        :param port: Xmpp Port
        :type port: str
        :param password: Xmpp password
        :type password: str
        :param xmpp_root: Root of the Xmpp Topic Architecture
        :type xmpp_root: str

        """
        super(OMF6API, self).__init__("OMF6API")
        self._exp_id = exp_id
        self._user = user # name of the machine that run Nepi
        self._host = host # name of the xmpp server
        self._port = port # port of the xmpp server
        self._password = password # password to connect to xmpp
        self._jid = "%s-%s@%s" % (self._user, self._exp_id, self._host)
        self._src = "xmpp://" + self._jid
        
        self._topics = []

        # OMF xmpp client
        self._client = None

        # message handler
        self._message = None

        if sys.version_info < (3, 0):
            reload(sys)
            sys.setdefaultencoding('utf8')

        # instantiate the xmpp client
        self._init_client()

        # register nepi topic
        self._enroll_nepi()


    def _init_client(self):
        """ Initialize XMPP Client

        """
        xmpp = OMFClient(self._jid, self._password)
        # PROTOCOL_SSLv3 required for compatibility with OpenFire
        xmpp.ssl_version = ssl.PROTOCOL_SSLv3

        if xmpp.connect((self._host, self._port)):
            xmpp.process(block=False)
            self.check_ready(xmpp)
            self._client = xmpp
            self._message = MessageHandler()
        else:
            msg = "Unable to connect to the XMPP server."
            self.error(msg)
            raise RuntimeError(msg)

    def check_ready(self, xmpp):
        delay = 1.0
        for i in xrange(4):
            if xmpp.ready:
                break
            else:
                time.sleep(delay)
                delay = delay * 1.5
        else:
            msg = "XMPP Client is not ready after long time"
            self.error(msg, out, err)
            raise RuntimeError, msg

    @property
    def _nepi_topic(self):
        msg = "nepi-" + self._exp_id
        self.debug(msg)
        return msg

    def _enroll_nepi(self):
        """ Create and Subscribe to the Session Topic

        """
        nepi_topic = self._nepi_topic
        self._client.create(nepi_topic)
        self._client.subscribe(nepi_topic)


    def enroll_topic(self, topic):
        """ Create and Subscribe to the session topic and the resources
            corresponding to the hostname

        :param hostname: Full hrn of the node
        :type hostname: str

        """
        if topic in self._topics:
            return 

        self._topics.append(topic)

#        try :
        self._client.create(topic)
#        except:
#            msg = "Topic already existing"
#            self.info(msg)
        self._client.subscribe(topic)

    def frcp_inform(self, topic, cid, itype):
        """ Configure attribute on the node

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.inform_function(msg_id, self._src, timestamp, props = props ,guards = guards) 
        
        self._client.publish(payload, xmpp_node)

    def frcp_configure(self, topic, props = None, guards = None ):
        """ Configure attribute on the node

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.configure_function(msg_id, self._src, timestamp ,props = props ,guards = guards) 
        self._client.publish(payload, topic)

    
    def frcp_create(self, topic, rtype, props = None, guards = None ):
        """ Send to the stdin of the application the value

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.create_function(msg_id, self._src, rtype, timestamp , props = props ,guards = guards) 
        self._client.publish(payload, topic)


    def frcp_request(self, topic, props = None, guards = None ):
        """ Execute command on the node

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.request_function(msg_id, self._src, timestamp, props = props ,guards = guards) 
        self._client.publish(payload, xmpp_node)

    def frcp_release(self, parent, child, res_id = None, props = None, guards = None ):
        """ Delete the session and logger topics. Then disconnect 

        """
        msg_id = os.urandom(16).encode('hex')
        timestamp = tsformat()
        payload = self._message.release_function(msg_id, self._src, timestamp, res_id = res_id, props = props ,guards = guards) 
        self._client.publish(payload, parent)

        if child in self._topics:
            self._topics.remove(child)

        self._client.delete(child)

    def disconnect(self) :
        """ Delete the session and logger topics. Then disconnect 

        """
        self._client.delete(self._nepi_topic)

        #XXX Why there is a sleep there ?
        time.sleep(1)
        
        # Wait the send queue to be empty before disconnect
        self._client.disconnect(wait=True)
        msg = " Disconnected from XMPP Server"
        self.debug(msg)


class OMF6APIFactory(object):
    """ 
    .. note::

        It allows the different RM to use the same xmpp client if they use 
        the same credentials.  For the moment, it is focused on XMPP.

    """
    # use lock to avoid concurrent access to the Api list at the same times by 2 
    # different threads
    lock = threading.Lock()
    _apis = dict()

    @classmethod 
    def get_api(cls, host, user, port, password, exp_id = None):
        """ Get an OMF Api

        :param slice: Xmpp Slice Name
        :type slice: str
        :param host: Xmpp Server Adress
        :type host: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str

        """
        if host and user and port and password:
            key = cls._make_key(host, user, port, password, exp_id)
            cls.lock.acquire()
            if key in cls._apis:
                #print "Api Counter : " + str(cls._apis[key]['cnt'])
                cls._apis[key]['cnt'] += 1
                cls.lock.release()
                return cls._apis[key]['api']
            else :
                omf_api = cls.create_api(host, user, port, password, exp_id)
                cls.lock.release()
                return omf_api
        return None

    @classmethod 
    def create_api(cls, host, user, port, password, exp_id):
        """ Create an OMF API if this one doesn't exist yet with this credentials

        :param slice: Xmpp Slice Name
        :type slice: str
        :param host: Xmpp Server Adress
        :type host: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str

        """
        omf_api = OMF6API(host, user = user, port = port, password = password, exp_id = exp_id)
        key = cls._make_key(host, user, port, password, exp_id)
        cls._apis[key] = {}
        cls._apis[key]['api'] = omf_api
        cls._apis[key]['cnt'] = 1
        return omf_api

    @classmethod 
    def release_api(cls, host, user, port, password, exp_id = None):
        """ Release an OMF API with this credentials

        :param slice: Xmpp Slice Name
        :type slice: str
        :param host: Xmpp Server Adress
        :type host: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str

        """
        if host and user and port and password:
            key = cls._make_key(host, user, port, password, exp_id)
            if key in cls._apis:
                cls._apis[key]['cnt'] -= 1
                #print "Api Counter : " + str(cls._apis[key]['cnt'])
                if cls._apis[key]['cnt'] == 0:
                    omf_api = cls._apis[key]['api']
                    omf_api.disconnect()


    @classmethod 
    def _make_key(cls, *args):
        """ Hash the credentials in order to create a key

        :param args: list of arguments used to create the hash (user, host, port, ...)
        :type args: list of args

        """
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()



