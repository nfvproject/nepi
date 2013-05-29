"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

from nepi.util.logger import Logger

import sleekxmpp
from sleekxmpp.exceptions import IqError, IqTimeout
import traceback
import xml.etree.ElementTree as ET

# inherit from BaseXmpp and XMLStream classes
class OMFClient(sleekxmpp.ClientXMPP, Logger): 
    """
    .. class:: Class Args :
      
        :param jid: Jabber Id (= Xmpp Slice + Date)
        :type jid: Str
        :param password: Jabber Password (= Xmpp Password)
        :type password: Str

    .. note::

       This class is an XMPP Client with customized method

    """

    def __init__(self, jid, password):
        """

        :param jid: Jabber Id (= Xmpp Slice + Date)
        :type jid: Str
        :param password: Jabber Password (= Xmpp Password)
        :type password: Str


        """
        Logger.__init__(self, "OMFClient")

        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self._ready = False
        self._registered = False
        self._server = None

        self.register_plugin('xep_0077') # In-band registration
        self.register_plugin('xep_0030')
        self.register_plugin('xep_0059')
        self.register_plugin('xep_0060') # PubSub 

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("register", self.register)
        self.add_event_handler("pubsub_publish", self.handle_omf_message)
        
    @property
    def ready(self):
        """ Check if the client is ready

        """
        return self._ready

    def start(self, event):
        """ Send presence to the Xmppp Server. This function is called directly by the sleekXmpp library

        """
        self.send_presence()
        self._ready = True
        self._server = "pubsub.%s" % self.boundjid.domain

    def register(self, iq):
        """  Register to the Xmppp Server. This function is called directly by the sleekXmpp library

        """
        if self._registered:
            msg = " %s already registered!" % self.boundjid
            self.info(msg)
            return 

        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)
            msg = " Account created for %s!" % self.boundjid
            self.info(msg)
            self._registered = True
        except IqError as e:
            msg = " Could not register account: %s" % e.iq['error']['text']
            self.error(msg)
        except IqTimeout:
            msg = " No response from server."
            self.error(msg)

    def unregister(self):
        """  Unregister from the Xmppp Server.

        """
        try:
            self.plugin['xep_0077'].cancel_registration(
                ifrom=self.boundjid.full)
            msg = " Account unregistered for %s!" % self.boundjid
            self.info(msg)
        except IqError as e:
            msg = " Could not unregister account: %s" % e.iq['error']['text']
            self.error(msg)
        except IqTimeout:
            msg = " No response from server."
            self.error(msg)

    def nodes(self):
        """  Get all the nodes of the Xmppp Server.

        """
        try:
            result = self['xep_0060'].get_nodes(self._server)
            for item in result['disco_items']['items']:
                msg = ' - %s' % str(item)
                self.debug(msg)
            return result
        except:
            error = traceback.format_exc()
            msg = 'Could not retrieve node list.\ntraceback:\n%s' % error
            self.error(msg)

    def subscriptions(self):
        """  Get all the subscriptions of the Xmppp Server.

        """
        try:
            result = self['xep_0060'].get_subscriptions(self._server)
                #self.boundjid.full)
            for node in result['node']:
                msg = ' - %s' % str(node)
                self.debug(msg)
            return result
        except:
            error = traceback.format_exc()
            msg = ' Could not retrieve subscriptions.\ntraceback:\n%s' % error
            self.error(msg)

    def create(self, node):
        """  Create the topic corresponding to the node

        :param node: Name of the topic, corresponding to the node (ex : omf.plexus.wlab17)
        :type node: str

        """
        msg = " Create Topic : " + node
        self.info(msg)
   
        config = self['xep_0004'].makeForm('submit')
        config.add_field(var='pubsub#node_type', value='leaf')
        config.add_field(var='pubsub#notify_retract', value='0')
        config.add_field(var='pubsub#publish_model', value='open')
        config.add_field(var='pubsub#persist_items', value='1')
        config.add_field(var='pubsub#max_items', value='1')
        config.add_field(var='pubsub#title', value=node)

        try:
            self['xep_0060'].create_node(self._server, node, config = config)
        except:
            error = traceback.format_exc()
            msg = ' Could not create topic: %s\ntraceback:\n%s' % (node, error)
            self.error(msg)

    def delete(self, node):
        """  Delete the topic corresponding to the node

        :param node: Name of the topic, corresponding to the node (ex : omf.plexus.wlab17)
        :type node: str

        """
        # To check if the queue are well empty at the end
        #print " length of the queue : " + str(self.send_queue.qsize())
        #print " length of the queue : " + str(self.event_queue.qsize())
        try:
            self['xep_0060'].delete_node(self._server, node)
            msg = ' Deleted node: %s' % node
            self.info(msg)
        except:
            error = traceback.format_exc()
            msg = ' Could not delete topic: %s\ntraceback:\n%s' % (node, error)
            self.error(msg)
    
    def publish(self, data, node):
        """  Publish the data to the corresponding topic

        :param data: Data that will be published
        :type data: str
        :param node: Name of the topic
        :type node: str

        """ 

        msg = " Publish to Topic : " + node
        self.info(msg)
        try:
            result = self['xep_0060'].publish(self._server,node,payload=data)
            # id = result['pubsub']['publish']['item']['id']
            # print('Published at item id: %s' % id)
        except:
            error = traceback.format_exc()
            msg = ' Could not publish to: %s\ntraceback:\n%s' % (node, error)
            self.error(msg)

    def get(self, data):
        """  Get the item

        :param data: data from which the items will be get back
        :type data: str


        """
        try:
            result = self['xep_0060'].get_item(self._server, self.boundjid,
                data)
            for item in result['pubsub']['items']['substanzas']:
                msg = 'Retrieved item %s: %s' % (item['id'], tostring(item['payload']))
                self.debug(msg)
        except:
            error = traceback.format_exc()
            msg = ' Could not retrieve item %s from topic %s\ntraceback:\n%s' \
                    % (data, self.boundjid, error)
            self.error(msg)

    def retract(self, data):
        """  Retract the item

        :param data: data from which the item will be retracted
        :type data: str

        """
        try:
            result = self['xep_0060'].retract(self._server, self.boundjid, data)
            msg = ' Retracted item %s from topic %s' % (data, self.boundjid)
            self.debug(msg)
        except:
            error = traceback.format_exc()
            msg = 'Could not retract item %s from topic %s\ntraceback:\n%s' \
                    % (data, self.boundjid, error)
            self.error(msg)

    def purge(self):
        """  Purge the information in the server

        """
        try:
            result = self['xep_0060'].purge(self._server, self.boundjid)
            msg = ' Purged all items from topic %s' % self.boundjid
            self.debug(msg)
        except:
            error = traceback.format_exc()
            msg = ' Could not purge items from topic %s\ntraceback:\n%s' \
                    % (self.boundjid, error)
            self.error(msg)

    def subscribe(self, node):
        """ Subscribe to a topic

        :param node: Name of the topic
        :type node: str

        """
        try:
            result = self['xep_0060'].subscribe(self._server, node)
            msg = ' Subscribed %s to topic %s' \
                    % (self.boundjid.user, node)
            #self.info(msg)
            self.debug(msg)
        except:
            error = traceback.format_exc()
            msg = ' Could not subscribe %s to topic %s\ntraceback:\n%s' \
                    % (self.boundjid.bare, node, error)
            self.error(msg)

    def unsubscribe(self, node):
        """ Unsubscribe to a topic

        :param node: Name of the topic
        :type node: str

        """
        try:
            result = self['xep_0060'].unsubscribe(self._server, node)
            msg = ' Unsubscribed %s from topic %s' % (self.boundjid.bare, node)
            self.debug(msg)
        except:
            error = traceback.format_exc()
            msg = ' Could not unsubscribe %s from topic %s\ntraceback:\n%s' \
                    % (self.boundjid.bare, node, error)
            self.error(msg)

    def _check_for_tag(self, root, namespaces, tag):
        """  Check if an element markup is in the ElementTree

        :param root: Root of the tree
        :type root: ElementTree Element
        :param namespaces: Namespaces of the element
        :type namespaces: str
        :param tag: Tag that will search in the tree
        :type tag: str

        """
        for element in root.iter(namespaces+tag):
            if element.text:
                return element
            else : 
                return None    

    def _check_output(self, root, namespaces):
        """ Check the significative element in the answer and display it

        :param root: Root of the tree
        :type root: ElementTree Element
        :param namespaces: Namespaces of the tree
        :type namespaces: str

        """
        fields = ["TARGET", "REASON", "PATH", "APPID", "VALUE"]
        response = ""
        for elt in fields:
            msg = self._check_for_tag(root, namespaces, elt)
            if msg is not None:
                response = response + " " + msg.text + " :"
        deb = self._check_for_tag(root, namespaces, "MESSAGE")
        if deb is not None:
            msg = response + " " + deb.text
            self.debug(msg)
        else :
            self.info(response)

    def handle_omf_message(self, iq):
        """ Handle published/received message 

        :param iq: Stanzas that is currently published/received
        :type iq: Iq Stanza

        """
        namespaces = "{http://jabber.org/protocol/pubsub}"
        for i in iq['pubsub_event']['items']:
            root = ET.fromstring(str(i))
            self._check_output(root, namespaces)


