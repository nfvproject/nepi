from neco.execution.resource import ResourceManager, clsinit
from neco.execution.attribute import Attribute, Flags

@clsinit
class LinuxNode(ResourceManager):
    _rtype = "LinuxNode"

    @classmethod
    def _register_attributes(cls):
        hostname = Attribute("hostname", "Hostname of the machine")
        username = Attribute("username", "Local account username", 
                flags = Flags.Credential)
        password = Attribute("pasword", "Local account password",
                flags = Flags.Credential)

        cls._register_attribute(hostname)
        cls._register_attribute(username)
        cls._register_attribute(password)

    def __init__(self, ec, guid):
        super(LinuxNode, self).__init__(ec, guid)

        self._logger = logging.getLogger("neco.linux.Node.%d" % guid)
        #elf._logger.setLevel(neco.LOGLEVEL)

    def deploy(self):
        pass

    def discover(self, filters):
        pass

    def provision(self, filters):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def deploy(self, group = None):
        pass

    def release(self):
        pass

    def _validate_connection(self, guid):
        # TODO: Validate!
        return True


