from xml.etree import cElementTree as ET

EXECUTE = "EXECUTE"
KILL = "KILL"
STDIN = "STDIN"
NOOP = "NOOP"
PM_INSTALL = "PM_INSTALL"
APT_INSTALL = "APT_INSTALL"
RPM_INSTALL = "RPM_INSTALL"
RESET = "RESET"
REBOOT = "REBOOT"
MODPROBE = "MODPROBE"
CONFIGURE = "CONFIGURE"
LOAD_IMAGE = "LOAD_IMAGE"
SAVE_IMAGE = "SAVE_IMAGE"
LOAD_DATA = "LOAD_DATA"
SET_LINK = "SET_LINK"
ALIAS = "ALIAS"
SET_DISCONNECTION = "SET_DISCONNECTION"
RESTART = "RESTART"
ENROLL = "ENROLL"
EXIT = "EXIT" 

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
        self._slice_id = sliceid
        self._exp_id = expid
        print "init" + self._exp_id +"  "+ self._slice_id
        pass

    def Mid(self, parent, keyword):
        mid = ET.SubElement(parent, keyword)
        mid.set("id", "\'omf-payload\'")
        return mid

    def Mtext(self, parent, keyword, text):
        mtext = ET.SubElement(parent, keyword)
        mtext.text = text
        return mtext

    def executefunction(self, target, appid, cmdlineargs, path, env):
        payload = ET.Element("omf-message")
        execute = self.Mid(payload,"EXECUTE")
        env = self.Mtext(execute, "ENV", env)
        sliceid = self.Mtext(execute,"SLICEID",self._slice_id)
        expid = self.Mtext(execute,"EXPID",self._exp_id)
        target = self.Mtext(execute,"TARGET",target)
        appid = self.Mtext(execute,"APPID",appid)
        cmdlineargs = self.Mtext(execute,"CMDLINEARGS",cmdlineargs)
        path = self.Mtext(execute,"PATH",path)
        return payload

    def exitfunction(self, target, appid):
        payload = ET.Element("omf-message")
        execute = self.Mid(payload,"EXIT")
        sliceid = self.Mtext(execute,"SLICEID",self._slice_id)
        expid = self.Mtext(execute,"EXPID",self._exp_id)
        target = self.Mtext(execute,"TARGET",target)
        appid = self.Mtext(execute,"APPID",appid)
        return payload

    def configurefunction(self, target, value, path):
        payload = ET.Element("omf-message")
        config = self.Mid(payload, "CONFIGURE")
        sliceid = self.Mtext(config,"SLICEID",self._slice_id)
        expid = self.Mtext(config,"EXPID",self._exp_id)
        target = self.Mtext(config,"TARGET",target)
        value = self.Mtext(config,"VALUE",value)
        path = self.Mtext(config,"PATH",path)
        return payload

    def logfunction(self,level, logger, level_name, data):
        payload = ET.Element("omf-message")
        log = self.Mid(payload, "LOGGING")
        level = self.Mtext(log,"LEVEL",level)
        sliceid = self.Mtext(log,"SLICEID",self._slice_id)
        logger = self.Mtext(log,"LOGGER",logger)
        expid = self.Mtext(log,"EXPID",self._exp_id)
        level_name = self.Mtext(log,"LEVEL_NAME",level_name)
        data = self.Mtext(log,"DATA",data)
        return payload

    def aliasfunction(self, name, target):
        payload = ET.Element("omf-message")
        alias = self.Mid(payload,"ALIAS")
        sliceid = self.Mtext(alias,"SLICEID",self._slice_id)
        expid = self.Mtext(alias,"EXPID",self._exp_id)
        name = self.Mtext(alias,"NAME",name)
        target = self.Mtext(alias,"TARGET",target)
        return payload

    def enrollfunction(self, enrollkey, image, index, target ):
        payload = ET.Element("omf-message")
        enroll = self.Mid(payload,"ENROLL")
        enrollkey = self.Mtext(enroll,"ENROLLKEY",enrollkey)
        sliceid = self.Mtext(enroll,"SLICEID",self._slice_id)
        image = self.Mtext(enroll,"IMAGE",image)
        expid = self.Mtext(enroll,"EXPID",self._exp_id)
        index = self.Mtext(enroll,"INDEX",index)
        target = self.Mtext(enroll,"TARGET",target)
        return payload

    def noopfunction(self,target):
        payload = ET.Element("omf-message")
        noop = self.Mid(payload,"NOOP")
        sliceid = self.Mtext(noop,"SLICEID",self._slice_id)
        expid = self.Mtext(noop,"EXPID",self._exp_id)
        target = self.Mtext(noop,"TARGET",target)
        return payload

    def newexpfunction(self, experimentid, address):
        payload = ET.Element("omf-message")
        newexp = self.Mid(payload,"EXPERIMENT_NEW")
        experimentid = self.Mtext(newexp,"EXPERIMENT_ID",experimentid)
        sliceid = self.Mtext(newexp,"SLICEID",self._slice_id)
        expid = self.Mtext(newexp,"EXPID",self._exp_id)
        address = self.Mtext(newexp,"ADDRESS",address)
        return payload

    def handle_message(self, msg):
        # Do something!!!
        return msg
