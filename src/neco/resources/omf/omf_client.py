import logging
import sleekxmpp
from sleekxmpp.exceptions import IqError, IqTimeout
import traceback
import xml.etree.ElementTree as ET

import neco

class OMFClient(sleekxmpp.ClientXMPP):
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
        
        self._logger = logging.getLogger("neco.omf.xmppClient")
        self._logger.setLevel(neco.LOGLEVEL)

    @property
    def ready(self):
        return self._ready

    def start(self, event):
        self.send_presence()
        self._ready = True
        self._server = "pubsub.%s" % self.boundjid.domain

    def register(self, iq):
        if self._registered:
            self._logger.info("%s already registered!" % self.boundjid)
            return 

        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)
            self._logger.info("Account created for %s!" % self.boundjid)
            self._registered = True
        except IqError as e:
            self._logger.error("Could not register account: %s" %
                    e.iq['error']['text'])
        except IqTimeout:
            self._logger.error("No response from server.")

    def unregister(self):
        try:
            self.plugin['xep_0077'].cancel_registration(
                ifrom=self.boundjid.full)
            self._logger.info("Account unregistered for %s!" % self.boundjid)
        except IqError as e:
            self._logger.error("Could not unregister account: %s" %
                    e.iq['error']['text'])
        except IqTimeout:
            self._logger.error("No response from server.")

    def nodes(self):
        try:
            result = self['xep_0060'].get_nodes(self._server)
            for item in result['disco_items']['items']:
                self._logger.info(' - %s' % str(item))
            return result
        except:
            error = traceback.format_exc()
            self._logger.error('Could not retrieve node list.\ntraceback:\n%s', error)

    def subscriptions(self):
        try:
            result = self['xep_0060'].get_subscriptions(self._server)
                #self.boundjid.full)
            for node in result['node']:
                self._logger.info(' - %s' % str(node))
            return result
        except:
            error = traceback.format_exc()
            self._logger.error('Could not retrieve subscriptions.\ntraceback:\n%s', error)

    def create(self, node):
        self._logger.debug(" Create Topic : " + node)
   
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
            self._logger.error('Could not create topic: %s\ntraceback:\n%s' % (node, error))

    def delete(self, node):
        try:
            self['xep_0060'].delete_node(self._server, node)
            self._logger.info('Deleted node: %s' % node)
        except:
            error = traceback.format_exc()
            self._logger.error('Could not delete topic: %s\ntraceback:\n%s' % (node, error))
    
    def publish(self, data, node):
        self._logger.debug(" Publish to Topic :" + node)
        try:
            result = self['xep_0060'].publish(self._server,node,payload=data)
            # id = result['pubsub']['publish']['item']['id']
            # print('Published at item id: %s' % id)
        except:
            error = traceback.format_exc()
            self._logger.error('Could not publish to: %s\ntraceback:\n%s' \
                    % (node, error))

    def get(self, data):
        try:
            result = self['xep_0060'].get_item(self._server, self.boundjid,
                data)
            for item in result['pubsub']['items']['substanzas']:
                self._logger.info('Retrieved item %s: %s' % (item['id'], 
                    tostring(item['payload'])))
        except:
            error = traceback.format_exc()
            self._logger.error('Could not retrieve item %s from topic %s\ntraceback:\n%s' \
                    % (data, self.boundjid, error))

    def retract(self, data):
        try:
            result = self['xep_0060'].retract(self._server, self.boundjid, data)
            self._logger.info('Retracted item %s from topic %s' % (data, self.boundjid))
        except:
            error = traceback.format_exc()
            self._logger.error('Could not retract item %s from topic %s\ntraceback:\n%s' \
                    % (data, self.boundjid, error))

    def purge(self):
        try:
            result = self['xep_0060'].purge(self._server, self.boundjid)
            self._logger.info('Purged all items from topic %s' % self.boundjid)
        except:
            error = traceback.format_exc()
            self._logger.error('Could not purge items from topic %s\ntraceback:\n%s' \
                    % (self.boundjid, error))

    def subscribe(self, node):
        try:
            result = self['xep_0060'].subscribe(self._server, node)
            #self._logger.debug('Subscribed %s to node %s' \
                    #% (self.boundjid.bare, node))
            self._logger.info(' Subscribed %s to topic %s' \
                    % (self.boundjid.user, node))
        except:
            error = traceback.format_exc()
            self._logger.error(' Could not subscribe %s to topic %s\ntraceback:\n%s' \
                    % (self.boundjid.bare, node, error))

    def unsubscribe(self, node):
        try:
            result = self['xep_0060'].unsubscribe(self._server, node)
            self._logger.info(' Unsubscribed %s from topic %s' % (self.boundjid.bare, node))
        except:
            error = traceback.format_exc()
            self._logger.error(' Could not unsubscribe %s from topic %s\ntraceback:\n%s' \
                    % (self.boundjid.bare, node, error))

    def _check_for_tag(self, treeroot, namespaces, tag):
        for element in treeroot.iter(namespaces+tag):
            if element.text:
                return element
            else : 
                return None    

    def _check_output(self, treeroot, namespaces):
        output_param = ["TARGET", "REASON", "PATH", "APPID", "VALUE"]
        response = ""
        for elt in output_param:
            msg = self._check_for_tag(treeroot, namespaces, elt)
            if msg is not None:
                response = response + " " + msg.text + " :"
        deb = self._check_for_tag(treeroot, namespaces, "MESSAGE")
        if deb is not None:
            self._logger.debug(response + " " + deb.text)
        else :
            self._logger.info(response)

    def handle_omf_message(self, iq):
        namespaces = "{http://jabber.org/protocol/pubsub}"
        for i in iq['pubsub_event']['items']:
            root = ET.fromstring(str(i))
            self._check_output(root, namespaces)


