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

from xml.etree import cElementTree as ET

class MessageHandler():
    """
    .. class:: Class Args :
      
        :param sliceid: Slice Name (= Xmpp Slice)
        :type expid: str
        :param expid: Experiment ID (= Xmpp User)
        :type expid: str

    .. note::

       This class is used only for OMF 5.4 Protocol and is going to become unused

    """

    def __init__(self):
        """
        
        """
        pass

    def _type_element(self, type_elt, xmlns, msg_id):
        """ Insert a markup element with an id

        """
        elt = ET.Element(type_elt)
        elt.set("xmlns", xmlns)
        elt.set("mid", msg_id)
        return elt

    

    def _attr_element(self, parent, markup, text, type_key=None, type_value = None):
        """ Insert a markup element with a text (value)

        :param parent: Parent element in an XML point of view
        :type parent: ElementTree Element
        :param markup: Name of the markup
        :type markup: str
        :param text: Value of the markup element
        :type text: str

        """
        elt = ET.SubElement(parent, markup)
        if type_key and type_value:
            elt.set(type_key, type_value)
        elt.text = text
        return elt

    def _id_element(self, parent, markup, key, value):
        """ Insert a markup element with a text (value)

        :param parent: Parent element in an XML point of view
        :type parent: ElementTree Element
        :param markup: Name of the markup
        :type markup: str
        :param text: Value of the markup element
        :type text: str

        """
        elt = ET.SubElement(parent, markup)
        elt.set(key, value)
        return elt

    def create_function(self, msg_id, src, rtype, timestamp, props = None, guards = None):
        """ Build a create message

        :param msg_id: Id of the message
        :type msg_id: str
        :param src: Src node that send the message (jabber source)
        :type src: str
        :param rtype: Type of the object
        :type rtype: str
        :param timestamp: Unix Timestamp
        :type timestamp: str
        :param props: List of properties
        :type props: list
        :param guards: list of guards (assertions for properties)
        :type guards: list
        """
        payload = self._type_element("create", "http://schema.mytestbed.net/omf/6.0/protocol", msg_id )
        self._attr_element(payload,"src",src)
        self._attr_element(payload,"ts",timestamp)
        self._attr_element(payload,"rtype",rtype)

        if props :
            if rtype == "application" :
                properties = self._id_element(payload,"props","xmlns:application",
                      "http://schema.mytestbed.net/omf/6.0/protocol/application")
            elif rtype == "wlan" :
                properties = self._id_element(payload,"props","xmlns:wlan",
                      "http://schema.mytestbed.net/omf/6.0/protocol/wlan")
            else:
                properties = self._attr_element(payload,"props","")

            for prop in props.keys():
                if isinstance(props[prop],str):
                    self._attr_element(properties,prop,props[prop],type_key="type", type_value = "string")
                elif isinstance(props[prop],dict):
                    key = self._attr_element(properties,prop,"",type_key="type", type_value = "hash")
                    for comp in props[prop].keys():
                        self._attr_element(key,comp,props[prop][comp],type_key="type", type_value = "string")

        if guards :
            guardians = self._attr_element(payload,"guard","")
            for guard in guards.keys():
                self._attr_element(guardians,guard,guards[guard],type_key="type", type_value = "string")

        return payload

    def configure_function(self, msg_id, src, timestamp, props = None, guards = None):
        """ Build a configure message

        :param msg_id: Id of the message
        :type msg_id: str
        :param src: Src node that send the message (jabber source)
        :type src: str
        :param timestamp: Unix Timestamp
        :type timestamp: str
        :param props: List of properties
        :type props: list
        :param guards: list of guards (assertions for properties)
        :type guards: list
        """
        payload = self._type_element("configure", "http://schema.mytestbed.net/omf/6.0/protocol", msg_id )
        self._attr_element(payload,"src",src)
        self._attr_element(payload,"ts",timestamp)

        if props :
            properties = self._attr_element(payload,"props","")
            for prop in props.keys():
                self._attr_element(properties,prop,props[prop],type_key="type", type_value = "symbol")
           
        if guards :
            guardians = self._attr_element(payload,"guard","")
            for guard in guards.keys():
                self._attr_element(guardians,guard,guards[guard],type_key="type", type_value = "string")

        return payload

    def request_function(self, msg_id, src, timestamp,  props = None, guards = None):
        """ Build a request message

        :param msg_id: Id of the message
        :type msg_id: str
        :param src: Src node that send the message (jabber source)
        :type src: str
        :param timestamp: Unix Timestamp
        :type timestamp: str
        :param props: List of properties
        :type props: list
        :param guards: list of guards (assertions for properties)
        :type guards: list
        """
        payload = self._type_element("request", "http://schema.mytestbed.net/omf/6.0/protocol", msg_id )
        self._attr_element(payload,"src",src)
        self._attr_element(payload,"ts",timestamp)

        if props :
            properties = self._attr_element(payload,"props","")
            for prop in props.keys():
                self._attr_element(properties,prop,props[prop])

        if guards :
            guardians = self._attr_element(payload,"guard","")
            for guard in guards.keys():
                self._attr_element(guardians,guard,guards[guard])
        return payload

#  For now, we don't need the inform message since it is ht RC that send them.

#    def inform_function(self, msg_id, src, timestamp, cid, itype):
#        """ Build an inform message

#        :param msg_id: Id of the message
#        :type msg_id: str
#        :param src: Src node that send the message (jabber source)
#        :type src: str
#        :param rtype: Type of the object
#        :type rtype: str
#        :param timestamp: Unix Timestamp
#        :type timestamp: str
#        :param cid: Id of the orignial message
#        :type cid: str
#        :param itype: type of the object created
#        :type itype: str
#        """

#        payload = self._type_element("inform", "http://schema.mytestbed.net/omf/6.0/protocol", msg_id )
#        sliceid = self._attr_element(payload,"src",src)
#        expid = self._attr_element(config,"ts",timestamp)
#        target = self._attr_element(config,"cid",cid)
#        value = self._attr_element(config,"itype",value)
#        path = self._attr_element(config,"properties",path)
#        return payload

    def release_function(self, msg_id, src, timestamp, res_id = None, props = None, guards = None):
        """ Build a release message

        :param msg_id: Id of the message
        :type msg_id: str
        :param src: Src node that send the message (jabber source)
        :type src: str
        :param timestamp: Unix Timestamp
        :type timestamp: str
        :param res_id: Id of the release resource
        :type res_id: str
        :param props: List of properties
        :type props: list
        :param guards: list of guards (assertions for properties)
        :type guards: list
        """
        payload = self._type_element("release", "http://schema.mytestbed.net/omf/6.0/protocol", msg_id )
        self._attr_element(payload,"src",src)
        self._attr_element(payload,"ts",timestamp)
        if res_id :
            self._attr_element(payload,"res_id",res_id)
 
        if props :
            properties = self._id_element(payload,"props","xmlns:frcp",
                      "http://schema.mytestbed.net/omf/6.0/protocol")
            for prop in props.keys():
                self._attr_element(properties,prop,props[prop])

        if guards :
            guardians = self._attr_element(payload,"guard","")
            for guard in guards.keys():
                self._attr_element(guardians,guard,guards[guard])

        return payload

