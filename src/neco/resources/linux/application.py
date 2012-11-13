from neco.execution import tags
from neco.execution.resource import Resource

import cStringIO
import logging

class Application(Resource):
    def __init__(self, box, ec):
        super(Application, self).__init__(box, ec)
        self.command = None
        self.pid = None
        self.ppid = None
        self.stdin = None
        self.del_app_home = True
        self.env = None
        
        self.app_home = "${HOME}/app-%s" % self.box.guid
        self._node = None
       
        # Logging
        loglevel = "debug"
        self._logger = logging.getLogger("neco.resources.base.Application.%s" % self.guid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    @property
    def node(self):
        if self._node:
            return self._node

        # XXX: What if it is connected to more than one node?
        resources = self.find_resources(exact_tags = [tags.NODE])
        self._node = resources[0] is len(resources) == 1 else None
        return self._node

    def make_app_home(self):
        self.node.mkdir(self.app_home)

        if self.stdin:
            self.node.upload(self.stdin, os.path.join(self.app_home, 'stdin'))

    def cleanup(self):
        self.kill()

    def run(self):
        dst = os.path.join(self.app_home, "app.sh")
        
        # Create shell script with the command
        # This way, complex commands and scripts can be ran seamlessly
        # sync files
        cmd = ""
        if self.env:
            for envkey, envvals in env.iteritems():
                for envval in envvals:
                    cmd += 'export %s=%s\n' % (envkey, envval)

        cmd += self.command
        self.node.upload(cmd, dst)

        command = 'bash ./app.sh'
        stdin = 'stdin' if self.stdin else None
        self.node.run(command, self.app_home, stdin = stdin)
        self.pid, self.ppid = self.node.checkpid(self.app_home)

    def status(self):
        return self.node.status(self.pid, self.ppid)

    def kill(self):
        return self.node.kill(self.pid, self.ppid)

