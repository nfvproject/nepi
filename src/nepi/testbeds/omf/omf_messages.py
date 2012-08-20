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
    SliceID = ""
    ExpID = ""

    def __init__(self, sliceid, expid ):
        self.SliceID = sliceid
        self.ExpID = expid
        print "init" + self.ExpID +"  "+ self.SliceID
        pass


    def Mid(self, parent, keyword):
        mid = ET.SubElement(parent, keyword)
        mid.set("id", "\'omf-payload\'")
        return mid

    def Mtext(self, parent, keyword, text):
        mtext = ET.SubElement(parent, keyword)
        mtext.text = text
        return mtext


    def executefunction(self, target, appid, cmdlineargs, path):
        payload = ET.Element("omf-message")
        execute = self.Mid(payload,"EXECUTE")
        env = self.Mtext(execute, "ENV", "")
        sliceid = self.Mtext(execute,"SLICEID",self.SliceID)
        expid = self.Mtext(execute,"EXPID",self.ExpID)
        target = self.Mtext(execute,"TARGET",target)
        appid = self.Mtext(execute,"APPID",appid)
        cmdlineargs = self.Mtext(execute,"CMDLINEARGS",cmdlineargs)
        path = self.Mtext(execute,"PATH",path)
        return payload

    def configurefunction(self, target, value, path):
        payload = ET.Element("omf-message")
        config = self.Mid(payload, "CONFIGURE")
        sliceid = self.Mtext(config,"SLICEID",self.SliceID)
        expid = self.Mtext(config,"EXPID",self.ExpID)
        target = self.Mtext(config,"TARGET",target)
        value = self.Mtext(config,"VALUE",value)
        path = self.Mtext(config,"PATH",path)
        return payload

    def logfunction(self,level, logger, level_name, data):
        payload = ET.Element("omf-message")
        log = self.Mid(payload, "LOGGING")
        level = self.Mtext(log,"LEVEL",level)
        sliceid = self.Mtext(log,"SLICEID",self.SliceID)
        logger = self.Mtext(log,"LOGGER",logger)
        expid = self.Mtext(log,"EXPID",self.ExpID)
        level_name = self.Mtext(log,"LEVEL_NAME",level_name)
        data = self.Mtext(log,"DATA",data)
        return payload

    def aliasfunction(self, name, target):
        payload = ET.Element("omf-message")
        alias = self.Mid(payload,"ALIAS")
        sliceid = self.Mtext(alias,"SLICEID",self.SliceID)
        expid = self.Mtext(alias,"EXPID",self.ExpID)
        name = self.Mtext(alias,"NAME",name)
        target = self.Mtext(alias,"TARGET",target)
        return payload

    def enrollfunction(self, enrollkey, image, index, target ):
        payload = ET.Element("omf-message")
        enroll = self.Mid(payload,"ENROLL")
        enrollkey = self.Mtext(enroll,"ENROLLKEY",enrollkey)
        sliceid = self.Mtext(enroll,"SLICEID",self.SliceID)
        image = self.Mtext(enroll,"IMAGE",image)
        expid = self.Mtext(enroll,"EXPID",self.ExpID)
        index = self.Mtext(enroll,"INDEX",index)
        target = self.Mtext(enroll,"TARGET",target)
        return payload

    def noopfunction(self,target):
        payload = ET.Element("omf-message")
        noop = self.Mid(payload,"NOOP")
        sliceid = self.Mtext(noop,"SLICEID",self.SliceID)
        expid = self.Mtext(noop,"EXPID",self.ExpID)
        target = self.Mtext(noop,"TARGET",target)
        return payload

    def enrollfunction(self, enrollkey, image, index, target ):
        payload = ET.Element("omf-message")
        enroll = self.Mid(payload,"ENROLL")
        enrollkey = self.Mtext(enroll,"ENROLLKEY",enrollkey)
        sliceid = self.Mtext(enroll,"SLICEID",self.SliceID)
        image = self.Mtext(enroll,"IMAGE",image)
        expid = self.Mtext(enroll,"EXPID",self.ExpID)
        index = self.Mtext(enroll,"INDEX",index)
        target = self.Mtext(enroll,"TARGET",target)
        return payload

    def newexpfunction(self, experimentid, address):
        payload = ET.Element("omf-message")
        newexp = self.Mid(payload,"EXPERIMENT_NEW")
        experimentid = self.Mtext(newexp,"EXPERIMENT_ID",experimentid)
        sliceid = self.Mtext(newexp,"SLICEID",self.SliceID)
        expid = self.Mtext(newexp,"EXPID",self.ExpID)
        address = self.Mtext(newexp,"ADDRESS",address)
        return payload

    def handle_message(self, msg):
        # Do something!!!
        return msg
