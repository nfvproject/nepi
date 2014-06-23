from nepi.execution.resource import ResourceManager, clsinit_copy
from nepi.execution.attribute import Attribute, Flags
from nepi.resources.iotlab.iotlab_api_factory import IOTLABAPIFactory


@clsinit_copy
class IOTLABNode(ResourceManager):
    """
    .. class:: Class Args :
      
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int
    """
    _rtype = "IOTLABNode"
    _authorized_connections = ["IOTLABApplication"]

	
    @classmethod
    def _register_attributes(cls):
        hostname = Attribute("hostname", "Hostname of the node",
                flags = Flags.Design)
        username = Attribute("user","REST API login", 
            flags = Flags.Credential)
        password = Attribute("password", "REST API password",
                flags = Flags.Credential)
        cls._register_attribute(username)
        cls._register_attribute(password)
        cls._register_attribute(hostname)

    # XXX: We don't necessary need to have the credentials at the 
    # moment we create the RM
    def __init__(self, ec, guid):
        """
        :param ec: The Experiment controller
        :type ec: ExperimentController
        :param guid: guid of the RM
        :type guid: int

        """
        super(IOTLABNode, self).__init__(ec, guid)
        self._rest_api = None 

    @property
    def exp_id(self):
        return self.ec.exp_id


    def do_deploy(self):
        """ Deploy the RM. 
        """
        if not (self.get('username') or self.get('password')):
            msg = "Credentials are not all initialzed."
            self.error(msg)
            raise RuntimeError, msg

        if not self.get('hostname') :
            msg = "Hostname's value is not initialized"
            self.error(msg)
            raise RuntimeError, msg

        if not self._rest_api :
            self._rest_api = IOTLABAPIFactory.get_api(self.get('username'), 
            self.get('password'), self.get('hostname'),
            exp_id = self.exp_id)

        super(IOTLABNode, self).do_deploy()

    def do_release(self):
        """ Clean the RM at the end of the experiment 
        """
        if self._rest_api:
            IOTLABAPIFactory.release_api(self.get('username'), 
            self.get('password'), self.get('hostname'),
            exp_id = self.exp_id)

        super(IOTLABNode, self).do_release()