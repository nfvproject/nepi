from neco.execution.attribute import Attribute, Flags
from neco.execution.resource import ResourceManager, clsinit, ResourceState
from neco.resources.linux.ssh_api import SSHApiFactory

import logging

@clsinit
class LinuxNode(ResourceManager):
    _rtype = "LinuxNode"

    @classmethod
    def _register_attributes(cls):
        hostname = Attribute("hostname", "Hostname of the machine")
        username = Attribute("username", "Local account username", 
                flags = Flags.Credential)
        identity = Attribute("identity", "SSH identity file",
                flags = Flags.Credential)
        clean_home = Attribute("cleanHome", "Remove all files and directories 
                from home folder before starting experiment", 
                flags = Flags.ReadOnly)
        clean_processes = Attribute("cleanProcesses", 
                "Kill all running processes before starting experiment", 
                flags = Flags.ReadOnly)
        tear_down = Attribute("tearDown", "Bash script to be executed before
                releasing the resource", flags = Flags.ReadOnly)

        cls._register_attribute(hostname)
        cls._register_attribute(username)
        cls._register_attribute(identity)
        cls._register_attribute(clean_home)
        cls._register_attribute(clean_processes)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxNode, self).__init__(ec, guid)

        self._logger = logging.getLogger("neco.linux.Node.%d" % guid)

    def provision(self, filters = None):
        if not self.api.is_alive():
            self._state = ResourceState.FAILED
            self.logger.error("Deploy failed. Unresponsive node")
            return
        
        if self.get("cleanProcesses"):
            self._clean_processes()

        if self.get("cleanHome"):
            # self._clean_home() -> this is dangerous
            pass

    def deploy(self):
        self.provision()
        super(LinuxNode, self).deploy()

    def release(self):
        tear_down = self.get("tearDown")
        if tear_down:
            self.api.execute(tear_down)

        super(LinuxNode, self).release()

    def _validate_connection(self, guid):
        # TODO: Validate!
        return True

    @property
    def api(self):
        host = self.get("host")
        user = self.get("user")
        identity = self.get("identity")
        return SSHApiFactory.get_api(host, user, identity)

    def _clean_processes(self):
        hostname = self.get("hostname")
        self.logger.info("Cleaning up processes on %s", hostname)
        
        cmds = [
            "sudo -S killall python tcpdump || /bin/true ; "
            "sudo -S killall python tcpdump || /bin/true ; "
            "sudo -S kill $(ps -N -T -o pid --no-heading | grep -v $PPID | sort) || /bin/true ",
            "sudo -S killall -u root || /bin/true ",
            "sudo -S killall -u root || /bin/true ",
        ]

        api = self.api
        for cmd in cmds:
            out, err = api.execute(cmd)
            if err:
                self.logger.error(err)
            
    def _clean_home(self):
        hostname = self.get("hostname")
        self.logger.info("Cleaning up home on %s", hostname)

         cmds = [
            "find . -maxdepth 1 ! -name '.bash*' ! -name '.' -execdir rm -rf {} + "
        ]

        api = self.api
        for cmd in cmds:
            out, err = api.execute(cmd)
            if err:
                self.logger.error(err)

