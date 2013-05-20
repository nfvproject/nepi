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

from xml.etree import cElementTree as ET

class MessageHandler():
    """
    .. class:: Class Args :
      
        :param sliceid: Slice Name (= Xmpp Slice)
        :type expid: Str
        :param expid: Experiment ID (= Xmpp User)
        :type expid: Str

    .. note::

       This class is used only for OMF 5.4 Protocol and is going to become unused

    """

    def __init__(self, sliceid, expid ):
        """

        :param sliceid: Slice Name (= Xmpp Slice)
        :type expid: Str
        :param expid: Experiment ID (= Xmpp User)
        :type expid: Str

        """
        self._slice_id = sliceid
        self._exp_id = expid


    def _id_element(self, parent, markup):
        """ Insert a markup element with an id

        :param parent: Parent element in an XML point of view
        :type parent: ElementTree Element
        :param markup: Name of the markup
        :type markup: str

        """
        elt = ET.SubElement(parent, markup)
        elt.set("id", "\'omf-payload\'")
        return elt

    def _attr_element(self, parent, markup, text):
        """ Insert a markup element with a text (value)

        :param parent: Parent element in an XML point of view
        :type parent: ElementTree Element
        :param markup: Name of the markup
        :type markup: str
        :param text: Value of the markup element
        :type text: str

        """
        elt = ET.SubElement(parent, markup)
        elt.text = text
        return elt

    def execute_function(self, target, appid, cmdlineargs, path, env):
        """ Build an Execute Message

        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str
        :param appid: Application id
        :type appid: str
        :param cmdlineargs: Arguments of the application
        :type cmdlineargs: str
        :param path: Path of the application
        :type path: str
        :param env: Environment variables
        :type env: str

        """
        payload = ET.Element("omf-message")
        execute = self._id_element(payload,"EXECUTE")
        env = self._attr_element(execute, "ENV", env)
        sliceid = self._attr_element(execute,"SLICEID",self._slice_id)
        expid = self._attr_element(execute,"EXPID",self._exp_id)
        target = self._attr_element(execute,"TARGET",target)
        appid = self._attr_element(execute,"APPID",appid)
        cmdlineargs = self._attr_element(execute,"CMDLINEARGS",cmdlineargs)
        path = self._attr_element(execute,"PATH",path)
        return payload

    def exit_function(self, target, appid):
        """ Build an Exit Message

        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str
        :param appid: Application id (ex : vlc#1)
        :type appid: str

        """
        payload = ET.Element("omf-message")
        execute = self._id_element(payload,"EXIT")
        sliceid = self._attr_element(execute,"SLICEID",self._slice_id)
        expid = self._attr_element(execute,"EXPID",self._exp_id)
        target = self._attr_element(execute,"TARGET",target)
        appid = self._attr_element(execute,"APPID",appid)
        return payload

    def configure_function(self, target, value, path):
        """ Build a Configure Message

        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str
        :param value: guid of the RM
        :type value: int
        :param path: Path of the element to configure (ex : net/w0/channel)
        :type path: dict

        """
        payload = ET.Element("omf-message")
        config = self._id_element(payload, "CONFIGURE")
        sliceid = self._attr_element(config,"SLICEID",self._slice_id)
        expid = self._attr_element(config,"EXPID",self._exp_id)
        target = self._attr_element(config,"TARGET",target)
        value = self._attr_element(config,"VALUE",value)
        path = self._attr_element(config,"PATH",path)
        return payload

    def log_function(self,level, logger, level_name, data):
        """ Build a Log Message

        :param level: Level of logging
        :type level: str
        :param logger: Element publishing the log
        :type logger: str
        :param level_name: Name of the level (ex : INFO)
        :type level_name: str
        :param data: Content to publish
        :type data: str

        """
        payload = ET.Element("omf-message")
        log = self._id_element(payload, "LOGGING")
        level = self._attr_element(log,"LEVEL",level)
        sliceid = self._attr_element(log,"SLICEID",self._slice_id)
        logger = self._attr_element(log,"LOGGER",logger)
        expid = self._attr_element(log,"EXPID",self._exp_id)
        level_name = self._attr_element(log,"LEVEL_NAME",level_name)
        data = self._attr_element(log,"DATA",data)
        return payload

    def alias_function(self, name, target):
        """ Build a Alias Message

        :param name: Name of the new alias
        :type name: str
        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str

        """
        payload = ET.Element("omf-message")
        alias = self._id_element(payload,"ALIAS")
        sliceid = self._attr_element(alias,"SLICEID",self._slice_id)
        expid = self._attr_element(alias,"EXPID",self._exp_id)
        name = self._attr_element(alias,"NAME",name)
        target = self._attr_element(alias,"TARGET",target)
        return payload

    def enroll_function(self, enrollkey, image, index, target ):
        """ Build an Enroll Message

        :param enrollkey: Type of enrollment (= 1)
        :type enrollkey: str
        :param image: Image (= * when all the nodes are concerned)
        :type image: str
        :param index: Index (= 1 in general)
        :type index: str
        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str

        """
        payload = ET.Element("omf-message")
        enroll = self._id_element(payload,"ENROLL")
        enrollkey = self._attr_element(enroll,"ENROLLKEY",enrollkey)
        sliceid = self._attr_element(enroll,"SLICEID",self._slice_id)
        image = self._attr_element(enroll,"IMAGE",image)
        expid = self._attr_element(enroll,"EXPID",self._exp_id)
        index = self._attr_element(enroll,"INDEX",index)
        target = self._attr_element(enroll,"TARGET",target)
        return payload

    def noop_function(self,target):
        """ Build a Noop Message

        :param target: Hrn of the target node (ex : omf.plexus.wlab17)
        :type target: str

        """
        payload = ET.Element("omf-message")
        noop = self._id_element(payload,"NOOP")
        sliceid = self._attr_element(noop,"SLICEID",self._slice_id)
        expid = self._attr_element(noop,"EXPID",self._exp_id)
        target = self._attr_element(noop,"TARGET",target)
        return payload

    def newexp_function(self, experimentid, address):
        """ Build a NewExp Message

        :param experimentid: Id of the new experiment
        :type experimentid: str
        :param address: Adress of the destination set of nodes
        :type address: str

        """
        payload = ET.Element("omf-message")
        newexp = self._id_element(payload,"EXPERIMENT_NEW")
        experimentid = self._attr_element(newexp,"EXPERIMENT_ID",experimentid)
        sliceid = self._attr_element(newexp,"SLICEID",self._slice_id)
        expid = self._attr_element(newexp,"EXPID",self._exp_id)
        address = self._attr_element(newexp,"ADDRESS",address)
        return payload

