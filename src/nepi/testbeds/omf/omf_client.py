import logging
import sleekxmpp
from sleekxmpp.exceptions import IqError, IqTimeout
import traceback
from xml.etree import cElementTree as ET

class OMFClient(sleekxmpp.ClientXMPP):
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
    
    @property
    def ready(self):
        return self._ready

    def start(self, event):
        self.send_presence()
        self._ready = True
        self._server = "pubsub.%s" % self.boundjid.domain

    def register(self, iq):
        if self._registered:
            logging.info("%s already registered!" % self.boundjid)
            return 

        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)
            logging.info("Account created for %s!" % self.boundjid)
            self._registered = True
        except IqError as e:
            logging.error("Could not register account: %s" %
                    e.iq['error']['text'])
        except IqTimeout:
            logging.error("No response from server.")

    def unregister(self):
        try:
            self.plugin['xep_0077'].cancel_registration(
                ifrom=self.boundjid.full)
            logging.info("Account unregistered for %s!" % self.boundjid)
        except IqError as e:
            logging.error("Could not unregister account: %s" %
                    e.iq['error']['text'])
        except IqTimeout:
            logging.error("No response from server.")

    def nodes(self):
        try:
            result = self['xep_0060'].get_nodes(self._server)
            for item in result['disco_items']['items']:
                print(' - %s' % str(item))
            return result
        except:
            print traceback.format_exc()
            logging.error('Could not retrieve node list.')

    def suscriptions(self):
        try:
            result = self['xep_0060'].get_subscriptions(self._server)
                #self.boundjid.full)
            for node in result['node']:
                print(' - %s' % str(node))
            return result
        except:
            print traceback.format_exc()
            logging.error('Could not retrieve suscriptions.')


    def create(self, node):
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
            print traceback.format_exc()
            logging.error('Could not create node: %s' % node)

    def delete(self, node):
        try:
            self['xep_0060'].delete_node(self._server, node)
            print('Deleted node: %s' % node)
        except:
            print traceback.format_exc()
            logging.error('Could not delete node: %s' % node)

    
    def publish(self, data, node):
        try:
            result = self['xep_0060'].publish(self._server,node,payload=data)
            id = result['pubsub']['publish']['item']['id']
            print('Published at item id: %s' % id)
        except:
            print traceback.format_exc()
            logging.error('Could not publish to: %s' % self.boundjid)

    def get(self, data):
        try:
            result = self['xep_0060'].get_item(self._server, self.boundjid,
                data)
            for item in result['pubsub']['items']['substanzas']:
                print('Retrieved item %s: %s' % (item['id'], tostring(item['payload'])))
        except:
            print traceback.format_exc()
            logging.error('Could not retrieve item %s from node %s' % (data, self.boundjid))

    def retract(self, data):
        try:
            result = self['xep_0060'].retract(self._server, self.boundjid, data)
            print('Retracted item %s from node %s' % (data, self.boundjid))
        except:
            print traceback.format_exc()
            logging.error('Could not retract item %s from node %s' % (data, self.boundjid))

    def purge(self):
        try:
            result = self['xep_0060'].purge(self._server, self.boundjid)
            print('Purged all items from node %s' % self.boundjid)
        except:
            print traceback.format_exc()
            logging.error('Could not purge items from node %s' % self.boundjid)

    def subscribe(self, node):
        try:
            result = self['xep_0060'].subscribe(self._server, node)
            print('Subscribed %s to node %s' % (self.boundjid.bare, self.boundjid))
        except:
            print traceback.format_exc()
            logging.error('Could not subscribe %s to node %s' % (self.boundjid.bare, node))

    def unsubscribe(self, node):
        try:
            result = self['xep_0060'].unsubscribe(self._server, node)
            print('Unsubscribed %s from node %s' % (self.boundjid.bare, node))
        except:
            print traceback.format_exc()
            logging.error('Could not unsubscribe %s from node %s' % (self.boundjid.bare, node))


