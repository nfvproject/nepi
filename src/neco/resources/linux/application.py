from neco.execution.attribute import Attribute, Flags
from neco.execution.resource import ResourceManager, clsinit, ResourceState
from neco.resources.linux.ssh_api import SSHApiFactory

import logging

@clsinit
class LinuxApplication(ResourceManager):
    _rtype = "LinuxApplication"

    @classmethod
    def _register_attributes(cls):
        command = Attribute("command", "Command to execute", 
                flags = Flags.ReadOnly)
        env = Attribute("env", "Environment variables string for command execution",
                flags = Flags.ReadOnly)
        sudo = Attribute("sudo", "Run with root privileges", 
                flags = Flags.ReadOnly)
        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.ReadOnly)
        sources = Attribute("sources", 
                "Space-separated list of regular files to be deployed in the working "
                "path prior to building. Archives won't be expanded automatically.",
                flags = Flags.ReadOnly)
        build = Attribute("build", 
                "Build commands to execute after deploying the sources. "
                "Sources will be in the ${SOURCES} folder. "
                "Example: tar xzf ${SOURCES}/my-app.tgz && cd my-app && ./configure && make && make clean.\n"
                "Try to make the commands return with a nonzero exit code on error.\n"
                "Also, do not install any programs here, use the 'install' attribute. This will "
                "help keep the built files constrained to the build folder (which may "
                "not be the home folder), and will result in faster deployment. Also, "
                "make sure to clean up temporary files, to reduce bandwidth usage between "
                "nodes when transferring built packages.",
                flags = Flags.ReadOnly)
        install = Attribute("install", 
                "Commands to transfer built files to their final destinations. "
                "Sources will be in the initial working folder, and a special "
                "tag ${SOURCES} can be used to reference the experiment's "
                "home folder (where the application commands will run).\n"
                "ALL sources and targets needed for execution must be copied there, "
                "if building has been enabled.\n"
                "That is, 'slave' nodes will not automatically get any source files. "
                "'slave' nodes don't get build dependencies either, so if you need "
                "make and other tools to install, be sure to provide them as "
                "actual dependencies instead.",
                flags = Flags.ReadOnly)
        stdin = Attribute("stdin", "Standard input", flags = Flags.ReadOnly)
        stdout = Attribute("stdout", "Standard output", flags = Flags.ReadOnly)
        stderr = Attribute("stderr", "Standard error", flags = Flags.ReadOnly)

        tear_down = Attribute("tearDown", "Bash script to be executed before
                releasing the resource", flags = Flags.ReadOnly)

        cls._register_attribute(command)
        cls._register_attribute(env)
        cls._register_attribute(sudo)
        cls._register_attribute(depends)
        cls._register_attribute(sources)
        cls._register_attribute(build)
        cls._register_attribute(install)
        cls._register_attribute(stdin)
        cls._register_attribute(stdout)
        cls._register_attribute(stderr)
        cls._register_attribute(tear_down)

    def __init__(self, ec, guid):
        super(LinuxApplication, self).__init__(ec, guid)
        self._pid = None
        self._ppid = None
        self._home = "${HOME}/app-%s" % self.box.guid
        self._node = None

        self._logger = logging.getLogger("neco.linux.Application.%d" % guid)

    @property
    def api(self):
        return self.node.api

    @property
    def node(self):
        self._node

    @property
    def home(self):
        return self._home

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        return self._ppid

    def provision(self, filters = None):
        # clean home
        # upload
        # build  
        # Install stuff!!
        pass

    def start(self):
        dst = os.path.join(self.home, "app.sh")
        
        # Create shell script with the command
        # This way, complex commands and scripts can be ran seamlessly
        # sync files
        cmd = ""
        env = self.get("env")
        if env:
            for envkey, envvals in env.iteritems():
                for envval in envvals:
                    cmd += 'export %s=%s\n' % (envkey, envval)

        cmd += self.get("command")
        self.api.upload(cmd, dst)

        command = 'bash ./app.sh'
        stdin = 'stdin' if self.get("stdin") else None
        self.api.run(command, self.home, stdin = stdin)
        self._pid, self._ppid = self.api.checkpid(self.app_home)

    def stop(self):
        self._state = ResourceState.STOPPED

    def release(self):
        tear_down = self.get("tearDown")
        if tear_down:
            self.api.execute(tear_down)

        return self.api.kill(self.pid, self.ppid)

    def status(self):
        return self.api.status(self.pid, self.ppid)

    def make_app_home(self):
        self.api.mkdir(self.home)

        stdin = self.get("stdin")
        if stdin:
            self.api.upload(stdin, os.path.join(self.home, 'stdin'))

    def _validate_connection(self, guid):
        # TODO: Validate!
        return True
        # XXX: What if it is connected to more than one node?
        resources = self.find_resources(exact_tags = [tags.NODE])
        self._node = resources[0] if len(resources) == 1 else None
        return self._node



