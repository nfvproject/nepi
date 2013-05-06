from neco.execution.attribute import Attribute, Flags, Types
from neco.execution.trace import Trace, TraceAttr
from neco.execution.resource import ResourceManager, clsinit, ResourceState
from neco.resources.linux.node import LinuxNode
from neco.util import sshfuncs 

import logging
import os

DELAY ="1s"

# TODO: Resolve wildcards in commands!! 

@clsinit
class LinuxApplication(ResourceManager):
    _rtype = "LinuxApplication"

    @classmethod
    def _register_attributes(cls):
        command = Attribute("command", "Command to execute", 
                flags = Flags.ExecReadOnly)
        forward_x11 = Attribute("forwardX11", " Enables X11 forwarding for SSH connections", 
                flags = Flags.ExecReadOnly)
        env = Attribute("env", "Environment variables string for command execution",
                flags = Flags.ExecReadOnly)
        sudo = Attribute("sudo", "Run with root privileges", 
                flags = Flags.ExecReadOnly)
        depends = Attribute("depends", 
                "Space-separated list of packages required to run the application",
                flags = Flags.ExecReadOnly)
        sources = Attribute("sources", 
                "Space-separated list of regular files to be deployed in the working "
                "path prior to building. Archives won't be expanded automatically.",
                flags = Flags.ExecReadOnly)
        code = Attribute("code", 
                "Plain text source code to be uploaded to the server. It will be stored "
                "under ${SOURCES}/code",
                flags = Flags.ExecReadOnly)
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
        stdin = Attribute("stdin", "Standard input", flags = Flags.ExecReadOnly)
        stdout = Attribute("stdout", "Standard output", flags = Flags.ExecReadOnly)
        stderr = Attribute("stderr", "Standard error", flags = Flags.ExecReadOnly)
        update_home = Attribute("updateHome", "If application hash has changed remove old directory and"
                "re-upload before starting experiment. If not keep the same directory", 
                default = True,
                type = Types.Bool, 
                flags = Flags.ExecReadOnly)

        tear_down = Attribute("tearDown", "Bash script to be executed before "
                "releasing the resource", 
                flags = Flags.ReadOnly)

        cls._register_attribute(command)
        cls._register_attribute(forward_x11)
        cls._register_attribute(env)
        cls._register_attribute(sudo)
        cls._register_attribute(depends)
        cls._register_attribute(sources)
        cls._register_attribute(code)
        cls._register_attribute(build)
        cls._register_attribute(install)
        cls._register_attribute(stdin)
        cls._register_attribute(stdout)
        cls._register_attribute(stderr)
        cls._register_attribute(update_home)
        cls._register_attribute(tear_down)

    @classmethod
    def _register_traces(cls):
        stdout = Trace("stdout", "Standard output stream")
        stderr = Trace("stderr", "Standard error stream")
        buildlog = Trace("buildlog", "Output of the build process")

        cls._register_trace(stdout)
        cls._register_trace(stderr)
        cls._register_trace(buildlog)

    def __init__(self, ec, guid):
        super(LinuxApplication, self).__init__(ec, guid)
        self._pid = None
        self._ppid = None
        self._home = "app-%s" % self.guid

        self._logger = logging.getLogger("LinuxApplication")
    
    def log_message(self, msg):
        return " guid %d - host %s - %s " % (self.guid, 
                self.node.get("hostname"), msg)

    @property
    def node(self):
        node = self.get_connected(LinuxNode.rtype())
        if node: return node[0]
        return None

    @property
    def home(self):
        return os.path.join(self.node.exp_dir, self._home)

    @property
    def src_dir(self):
        return os.path.join(self.home, 'src')

    @property
    def build_dir(self):
        return os.path.join(self.home, 'build')

    @property
    def pid(self):
        return self._pid

    @property
    def ppid(self):
        return self._ppid

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        path = os.path.join(self.home, name)
        
        cmd = "(test -f %s && echo 'success') || echo 'error'" % path
        (out, err), proc = self.node.execute(cmd)

        if (err and proc.poll()) or out.find("error") != -1:
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
    
        if attr == TraceAttr.PATH:
            return path

        if attr == TraceAttr.ALL:
            (out, err), proc = self.node.check_output(self.home, name)
            
            if err and proc.poll():
                msg = " Couldn't read trace %s " % name
                self.error(msg, out, err)
                return None

            return out

        if attr == TraceAttr.STREAM:
            cmd = "dd if=%s bs=%d count=1 skip=%d" % (path, block, offset)
        elif attr == TraceAttr.SIZE:
            cmd = "stat -c%%s %s " % path

        (out, err), proc = self.node.execute(cmd)

        if err and proc.poll():
            msg = " Couldn't find trace %s " % name
            self.error(msg, out, err)
            return None
        
        if attr == TraceAttr.SIZE:
            out = int(out.strip())

        return out
            
    def provision(self, filters = None):
        # TODO: verify home hash or clean home

        # create home dir for application
        self.node.mkdir(self.home)

        # upload sources
        self.upload_sources()

        # upload code
        self.upload_code()

        # install dependencies
        self.install_dependencies()

        # build
        self.build()

        # Install
        self.install()

        super(LinuxApplication, self).provision()

    def upload_sources(self):
        # check if sources need to be uploaded and upload them
        sources = self.get("sources")
        if sources:
            self.info(" Uploading sources ")

            # create dir for sources
            self.node.mkdir(self.src_dir)

            sources = self.sources.split(' ')

            http_sources = list()
            for source in list(sources):
                if source.startswith("http") or source.startswith("https"):
                    http_sources.append(source)
                    sources.remove(source)

            # Download http sources
            for source in http_sources:
                dst = os.path.join(self.src_dir, source.split("/")[-1])
                command = "wget -o %s %s" % (dst, source)
                self.node.execute(command)

            self.node.upload(sources, self.src_dir)

    def upload_code(self):
        code = self.get("code")
        if code:
            # create dir for sources
            self.node.mkdir(self.src_dir)

            self.info(" Uploading code ")

            dst = os.path.join(self.src_dir, "code")
            self.node.upload(sources, dst, text = True)

    def install_dependencies(self):
        depends = self.get("depends")
        if depends:
            self.info(" Installing dependencies %s" % depends)
            self.node.install_packages(depends, home = self.home)

    def build(self):
        build = self.get("build")
        if build:
            self.info(" Building sources ")
            
            # create dir for build
            self.node.mkdir(self.build_dir)

            cmd = self.replace_paths(build)

            (out, err), proc = self.run_and_wait(cmd, self.home,
                pidfile = "build_pid",
                stdout = "build_log", 
                stderr = "build_err", 
                raise_on_error = True)
 
    def install(self):
        install = self.get("install")
        if install:
            self.info(" Installing sources ")

            cmd = self.replace_paths(install)

            (out, err), proc = self.run_and_wait(cmd, self.home, 
                pidfile = "install_pid",
                stdout = "install_log", 
                stderr = "install_err", 
                raise_on_error = True)

    def deploy(self):
        # Wait until node is associated and deployed
        node = self.node
        if not node or node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            self.ec.schedule(DELAY, self.deploy)
        else:
            try:
                self.discover()
                self.provision()
            except:
                self._state = ResourceState.FAILED
                raise

            super(LinuxApplication, self).deploy()

    def start(self):
        command = self.replace_paths(self.get("command"))
        env = self.get("env")
        stdin = 'stdin' if self.get("stdin") else None
        sudo = self.get('sudo') or False
        x11 = self.get("forwardX11") or False
        failed = False

        super(LinuxApplication, self).start()

        self.info("Starting command %s" % command)

        if x11:
            (out, err), proc = self.node.execute(command,
                    sudo = sudo,
                    stdin = stdin,
                    stdout = 'stdout',
                    stderr = 'stderr',
                    env = env,
                    forward_x11 = x11)

            if proc.poll() and err:
                failed = True
        else:
            (out, err), proc = self.node.run(command, self.home, 
                stdin = stdin, 
                sudo = sudo)

            if proc.poll() and err:
                failed = True
        
            if not failed:
                pid, ppid = self.node.wait_pid(home = self.home)
                if pid: self._pid = int(pid)
                if ppid: self._ppid = int(ppid)

            if not self.pid or not self.ppid:
                failed = True
 
        (out, chkerr), proc = self.node.check_output(self.home, 'stderr')

        if failed or out or chkerr:
            # check if execution errors occurred
            msg = " Failed to start command '%s' " % command
            out = out
            if err:
                err = err
            elif chkerr:
                err = chkerr

            self.error(msg, out, err)

            msg2 = " Setting state to Failed"
            self.debug(msg2)
            self._state = ResourceState.FAILED

            raise RuntimeError, msg

    def stop(self):
        state = self.state
        if state == ResourceState.STARTED:
            self.info("Stopping command %s" % command)

            (out, err), proc = self.node.kill(self.pid, self.ppid)

            if out or err:
                # check if execution errors occurred
                msg = " Failed to STOP command '%s' " % self.get("command")
                self.error(msg, out, err)
                self._state = ResourceState.FAILED
                stopped = False
            else:
                super(LinuxApplication, self).stop()

    def release(self):
        self.info("Releasing resource")

        tear_down = self.get("tearDown")
        if tear_down:
            self.node.execute(tear_down)

        self.stop()
        if self.state == ResourceState.STOPPED:
            super(LinuxApplication, self).release()
    
    @property
    def state(self):
        if self._state == ResourceState.STARTED:
            (out, err), proc = self.node.check_output(self.home, 'stderr')

            if out or err:
                if err.find("No such file or directory") >= 0 :
                    # The resource is marked as started, but the
                    # command was not yet executed
                    return ResourceState.READY

                # check if execution errors occurred
                msg = " Failed to execute command '%s'" % self.get("command")
                self.error(msg, out, err)
                self._state = ResourceState.FAILED

            elif self.pid and self.ppid:
                status = self.node.status(self.pid, self.ppid)

                if status == sshfuncs.FINISHED:
                    self._state = ResourceState.FINISHED

        return self._state

    def valid_connection(self, guid):
        # TODO: Validate!
        return True
        # XXX: What if it is connected to more than one node?
        resources = self.find_resources(exact_tags = [tags.NODE])
        self._node = resources[0] if len(resources) == 1 else None
        return self._node

    def hash_app(self):
        """ Generates a hash representing univokely the application.
        Is used to determine whether the home directory should be cleaned
        or not.

        """
        command = self.get("command")
        forwards_x11 = self.get("forwardX11")
        env = self.get("env")
        sudo = self.get("sudo")
        depends = self.get("depends")
        sources = self.get("sources")
        cls._register_attribute(sources)
        cls._register_attribute(build)
        cls._register_attribute(install)
        cls._register_attribute(stdin)
        cls._register_attribute(stdout)
        cls._register_attribute(stderr)
        cls._register_attribute(tear_down)
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()

    def replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        return ( command
            .replace("${SOURCES}", self.src_dir)
            .replace("${BUILD}", self.build_dir) 
            .replace("${APPHOME}", self.home) 
            .replace("${NODEHOME}", self.node.home) )


