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

from nepi.util.logger import Logger

import traceback
import xml.etree.ElementTree as ET

# inherit from BaseXmpp and XMLstream classes
class OMF6Parser(Logger): 
    """
    .. class:: Class Args :
      
        :param jid: Jabber Id (= Xmpp Slice + Date)
        :type jid: str
        :param password: Jabber Password (= Xmpp Password)
        :type password: str

    .. note::

       This class is an XMPP Client with customized method

    """

    def __init__(self):
        """

        :param jid: Jabber Id (= Xmpp Slice + Date)
        :type jid: str
        :param password: Jabber Password (= Xmpp Password)
        :type password: str


        """
        super(OMF6Parser, self).__init__("OMF6API")
        self.mailbox={}
        self.traces={}
        self.trace='NULL'

        self.init_mailbox()


    def init_mailbox(self):
        self.mailbox['create'] = []
        self.mailbox['started'] = []
        self.mailbox['release'] = []
  
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
                return element.text
            else : 
                return None

    def _check_for_props(self, root, namespaces):
        """  Check if an element markup is in the ElementTree

        :param root: Root of the tree
        :type root: ElementTree Element
        :param namespaces: Namespaces of the element
        :type namespaces: str

        """
        props = {}
        for properties in root.iter(namespaces+'props'):
            for element in properties.iter():
                if element.tag and element.text:
                    props[element.tag] = element.text
        return props

    def _check_for_membership(self, root, namespaces):
        """  Check if an element markup is in the ElementTree

        :param root: Root of the tree
        :type root: ElementTree Element
        :param namespaces: Namespaces of the element
        :type namespaces: str

        """
        for element in root.iter(namespaces+'membership'):
            for elt in element.iter(namespaces+'it'):
                ##XXX : change
                return elt.text


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


    def _inform_creation_ok(self, root, namespaces):
        """ Parse and Display CREATION OK message

        """
        #ET.dump(root)
        uid = self._check_for_tag(root, namespaces, "uid")
        cid = self._check_for_tag(root, namespaces, "cid")
        member = self._check_for_membership(root, namespaces)
        binary_path = self._check_for_tag(root, namespaces, "binary_path")
        msg = "CREATION OK -- "
        if binary_path :
            msg = msg + "The resource : '"+binary_path
        else :
            msg = msg + "The interface"
        if uid :
            msg = msg + "' is listening to the topics : '"+ uid
        if member :
            msg = msg + "' and '"+ member +"'"
        if cid:
            self.info(msg)
            self.mailbox['create'].append([cid, uid ])

    def _inform_creation_failed(self, root, namespaces):
        """ Parse and Display CREATION FAILED message

        """
        reason = self._check_for_tag(root, namespaces, "reason")
        cid = self._check_for_tag(root, namespaces, "cid")
        msg = "CREATION FAILED - The reason : "+reason
        if cid:
            self.error(msg)
            self.mailbox['create'].append([cid, uid ])

    def _inform_status(self, root, namespaces):
        """ Parse and Display STATUS message

        """
        props = self._check_for_props(root, namespaces)
        uid = self._check_for_tag(root, namespaces, "uid")
        event = self._check_for_tag(root, namespaces, "event")

        if event == "STDOUT":
            if not uid+'out' in self.traces:
                f = open('/tmp/'+ uid + '.out','w')
                self.traces[uid+'out'] = f
            self.trace = self.traces[uid+'out']
        elif event == "STDERR" :
            if not uid+'err' in self.traces:
                g = open('/tmp/'+ uid + '.err','w')
                self.traces[uid+'err'] = g
            self.trace = self.traces[uid+'err']
        elif event == "EXIT" :
            if uid+'out' in self.traces:
                self.traces[uid+'out'].close()
            if uid+'err' in self.traces:
                self.traces[uid+'err'].close()
            
        log = "STATUS -- "
        for elt in props.keys():
            ns, tag = elt.split('}')
            if tag == "it":
                log = log + "membership : " + props[elt]+" -- "
            elif tag == "event":
                self.mailbox['started'].append(uid)
                log = log + "event : " + props[elt]+" -- "
            elif tag == "msg":
                if event == "STDOUT" or event == "STDERR" :
                    self.trace.write(props[elt]+'\n')
                log = log + tag +" : " + props[elt]+" -- "
            else:
                log = log + tag +" : " + props[elt]+" -- "
        log = log + " STATUS "
        self.info(log)

    def _inform_released(self, root, namespaces):
        """ Parse and Display RELEASED message

        """
        #ET.dump(root)
        parent_id = self._check_for_tag(root, namespaces, "src")
        child_id = self._check_for_tag(root, namespaces, "res_id")
        cid = self._check_for_tag(root, namespaces, "cid")
        if cid :
            msg = "RELEASED - The resource : '"+child_id+ \
              "' has been released by : '"+ parent_id
            self.info(msg)
            self.mailbox['release'].append(cid)

    def _inform_error(self, root, namespaces):
        """ Parse and Display ERROR message

        """
        reason = self._check_for_tag(root, namespaces, "reason")
        msg = "The reason : "+reason
        self.error(msg)

    def _inform_warn(self, root, namespaces):
        """ Parse and Display WARN message

        """
        reason = self._check_for_tag(root, namespaces, "reason")
        msg = "The reason : "+reason
        self.warn(msg)

    def _parse_inform(self, root, namespaces):
        """ Check the significative element in the answer
            Then Parse it and display using specific method

        :param root: Root of the tree
        :type root: ElementTree Element
        :param namespaces: Namespaces of the tree
        :type namespaces: str

        """
        itype = self._check_for_tag(root, namespaces, "itype")
        if itype :
            method_name = '_inform_'+ itype.replace('.', '_').lower()
            method = getattr(self, method_name)
            if method :
                method(root, namespaces)
            else :
                msg = "There is no method to parse the response of the type " + itype
                self.info(msg)
                return
        

    def check_mailbox(self, itype, attr):
        """ Check the mail box

        :param itype: type of mail
        :type itype: str
        :param attr: value wanted
        :type attr: str

        """
        if itype == "create":
            for res in self.mailbox[itype]:
                binary, uid = res
                if binary == attr:
                    self.mailbox[itype].remove(res)
                    return uid
        else :
            for res in self.mailbox[itype]:
                if attr == res:
                    self.mailbox[itype].remove(res)
                    return res
               

    def handle(self, iq):
        """ Check the mail box

        :param iq: message received
        :type itype: iq
        """
        namespaces = "{http://schema.mytestbed.net/omf/6.0/protocol}"
        for i in iq['pubsub_event']['items']:
            root = ET.fromstring(str(i))
            #ET.dump(root)
            self._parse_inform(root, namespaces)

