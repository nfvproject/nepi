#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
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

from nepi.execution.attribute import Attribute, Flags, Types
from nepi.execution.trace import Trace, TraceAttr
from nepi.execution.resource import ResourceManager, clsinit_copy, \
        ResourceState, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow, tdiffsec
from nepi.resources.ns3.ns3simulation import NS3Simulation
from nepi.resources.ns3.ns3wrapper import GLOBAL_VALUE_UUID
from nepi.resources.linux.ns3.ns3client import LinuxNS3Client

import os
import time

@clsinit_copy
class LinuxNS3Simulation(LinuxApplication, NS3Simulation):
    _rtype = "LinuxNS3Simulation"

    @classmethod
    def _register_attributes(cls):
        impl_type = Attribute("simulatorImplementationType",
                "The object class to use as the simulator implementation",
            allowed = ["ns3::DefaultSimulatorImpl", "ns3::RealtimeSimulatorImpl"],
            default = "ns3::DefaultSimulatorImpl",
            type = Types.Enumerate,
            flags = Flags.Design)

        sched_type = Attribute("schedulerType",
                "The object class to use as the scheduler implementation",
                allowed = ["ns3::MapScheduler",
                            "ns3::ListScheduler",
                            "ns3::HeapScheduler",
                            "ns3::MapScheduler",
                            "ns3::CalendarScheduler"
                    ],
            default = "ns3::MapScheduler",
            type = Types.Enumerate,
            flags = Flags.Design)

        check_sum = Attribute("checksumEnabled",
                "A global switch to enable all checksums for all protocols",
            default = False,
            type = Types.Bool,
            flags = Flags.Design)

        stop_time = Attribute("stopTime",
                "Time to stop the simulation",
            flags = Flags.Design)

        ns_log = Attribute("nsLog",
            "NS_LOG environment variable. " \
                    " Will only generate output if ns-3 is compiled in DEBUG mode. ",
            flags = Flags.Design)

        verbose = Attribute("verbose",
            "True to output debugging info from the ns3 client-server communication",
            type = Types.Bool,
            flags = Flags.Design)

        cls._register_attribute(impl_type)
        cls._register_attribute(sched_type)
        cls._register_attribute(check_sum)
        cls._register_attribute(stop_time)
        cls._register_attribute(ns_log)
        cls._register_attribute(verbose)

    def __init__(self, ec, guid):
        LinuxApplication.__init__(self, ec, guid)
        NS3Simulation.__init__(self)

        self._client = None
        self._home = "ns3-simu-%s" % self.guid
        self._socket_name = "ns3simu-%s" % os.urandom(8).encode('hex')

    @property
    def socket_name(self):
        return self._socket_name

    @property
    def remote_socket(self):
        return os.path.join(self.run_home, self.socket_name)

    @property
    def local_socket(self):
        if self.node.get('hostname') in ['localhost', '127.0.0.01']:
            return self.remote_socket

        return os.path.join("/", "tmp", self.socket_name)

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        self._client.flush() 
        return LinuxApplication.trace(self, name, attr, block, offset)

    def upload_sources(self):
        self.node.mkdir(os.path.join(self.node.src_dir, "ns3wrapper"))

        # upload ns3 wrapper python script
        ns3_wrapper = os.path.join(os.path.dirname(__file__), "..", "..", "ns3", 
                "ns3wrapper.py")

        self.node.upload(ns3_wrapper,
                os.path.join(self.node.src_dir, "ns3wrapper", "ns3wrapper.py"),
                overwrite = False)

        # upload ns3_server python script
        ns3_server = os.path.join(os.path.dirname(__file__), "..", "..", "ns3",
                "ns3server.py")

        self.node.upload(ns3_server,
                os.path.join(self.node.src_dir, "ns3wrapper", "ns3server.py"),
                overwrite = False)

        if self.node.use_rpm:
            # upload pygccxml sources
            pygccxml_tar = os.path.join(os.path.dirname(__file__), "dependencies",
                    "%s.tar.gz" % self.pygccxml_version)

            self.node.upload(pygccxml_tar,
                    os.path.join(self.node.src_dir, "%s.tar.gz" % self.pygccxml_version),
                    overwrite = False)

    def upload_start_command(self):
        command = self.get("command")
        env = self.get("env")

        # We want to make sure the ccnd is running
        # before the experiment starts.
        # Run the command as a bash script in background,
        # in the host ( but wait until the command has
        # finished to continue )
        env = self.replace_paths(env)
        command = self.replace_paths(command)

        shfile = os.path.join(self.app_home, "start.sh")
        self.node.upload_command(command, 
                    shfile = shfile,
                    env = env,
                    overwrite = True)

        # Run the ns3wrapper 
        self._run_in_background()

    def configure(self):
        if self._attrs.get("simulatorImplementationType").has_changed():
            simu_type = self.get("simulatorImplementationType")
            stype = self.create("StringValue", simu_type)
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "SimulatorImplementationType", stype)

        if self._attrs.get("checksumEnabled").has_changed():
            check_sum = self.get("checksumEnabled")
            btrue = self.create("BooleanValue", check_sum)    
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "ChecksumEnabled", btrue)
        
        if self._attrs.get("schedulerType").has_changed():
            sched_type = self.get("schedulerType")
            stype = self.create("StringValue", sched_type)
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "SchedulerType", btrue)
        
        if self._attrs.get("stopTime").has_changed():
            stop_time = self.get("stopTime")
            self.stop(time = stop_time)

    def do_deploy(self):
        if not self.node or self.node.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- node state %s " % self.node.state )
            
            # ccnd needs to wait until node is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            if not self.get("command"):
                self.set("command", self._start_command)
            
            if not self.get("depends"):
                self.set("depends", self._dependencies)

            if not self.get("build"):
                self.set("build", self._build)

            if not self.get("install"):
                self.set("install", self._install)

            if not self.get("env"):
                self.set("env", self._environment)

            self.do_discover()
            self.do_provision()

            # Create client
            self._client = LinuxNS3Client(self)
           
            # Wait until local socket is created
            for i in [1, 5, 15, 30, 60]:
                if os.path.exists(self.local_socket):
                    break
                time.sleep(i)

            if not os.path.exists(self.local_socket):
                raise RuntimeError("Problem starting socat")

            self.configure()
            
            self.set_ready()

    def do_start(self):
        """ Starts simulation execution

        """
        self.info("Starting")

        if self.state == ResourceState.READY:
            self._client.start() 

            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            raise RuntimeError, msg

    def do_stop(self):
        """ Stops simulation execution

        """
        if self.state == ResourceState.STARTED:
            self._client.stop() 
            self._client.shutdown()
            LinuxApplication.do_stop(self)

    def do_release(self):
        self.info("Releasing resource")

        tear_down = self.get("tearDown")
        if tear_down:
            self.node.execute(tear_down)

        self.do_stop()
        
        super(LinuxApplication, self).do_release()

    @property
    def state(self):
        """ Returns the state of the application
        """
        state = super(LinuxApplication, self).state
        if state == ResourceState.STARTED:
            # Check simulator
            is_finished = self.invoke(SIMULATOR_UUID, "IsFinished")
            if is_finished:
                self.do_stop()

        return self._state

    @property
    def _start_command(self):
        command = [] 
        command.append("PYTHONPATH=$PYTHONPATH:${SRC}/ns3wrapper/")

        command.append("python ${SRC}/ns3wrapper/ns3server.py -S %s" % self.remote_socket )

        ns_log = self.get("nsLog")
        if ns_log:
            command.append("-L %s" % ns_log)

        if self.get("verbose"):
            command.append("-v")

        command = " ".join(command)
        return command

    @property
    def _dependencies(self):
        if self.node.use_rpm:
            return ( " gcc gcc-c++ python python-devel mercurial bzr tcpdump socat gccxml")
        elif self.node.use_deb:
            return ( " gcc g++ python python-dev mercurial bzr tcpdump socat gccxml python-pygccxml")
        return ""

    @property
    def ns3_repo(self):
       return "http://code.nsnam.org"

    @property
    def ns3_version(self):
       return "ns-3.19"

    @property
    def pybindgen_version(self):
       return "834"

    @property
    def pygccxml_version(self):
       return "pygccxml-1.0.0"

    @property
    def _build(self):
        return (
                # Test if ns-3 is alredy installed
                " ( "
                " (( "
                "  ( test -d ${SRC}/%(ns3_version)s ) || (test -d ${NS3BINDINGS:='None'} && test -d ${NS3LIBRARIES:='None'}) ) && "
                "  echo 'binaries found, nothing to do' )"
                " ) "
                "  || " 
                # If not, install ns-3 and its dependencies
                " (   "
                # Install pygccxml
                "   (   "
                "     ( "
                "       python -c 'import pygccxml' && "
                "       echo 'pygccxml not found' "
                "     ) "
                "      || "
                "     ( "
                "       tar xf ${SRC}/%(pygccxml_version)s.tar.gz -C ${SRC} && "
                "       cd ${SRC}/%(pygccxml_version)s && "
                "       sudo -S python setup.py install "
                "     ) "
                "   ) " 
                # Install pybindgen
                "  && "
                "   (   "
                "     ( "
                "       test -d ${BIN}/pybindgen && "
                "       echo 'binaries found, nothing to do' "
                "     ) "
                "      || "
                # If not, clone and build
                "      ( cd ${SRC} && "
                "        bzr checkout lp:pybindgen -r %(pybindgen_version)s && "
                "        cd ${SRC}/pybindgen && "
                "        ./waf configure && "
                "        ./waf "
                "      ) "
                "   ) " 
               "  && "
                # Clone and build ns-3
                "  ( "
                "    hg clone %(ns3_repo)s/%(ns3_version)s ${SRC}/%(ns3_version)s && "
                "    cd ${SRC}/%(ns3_version)s && "
                "    ./waf configure -d optimized  && "
                "    ./waf "
                "   ) "
                " ) "
             ) % ({ 
                    'ns3_repo':  self.ns3_repo,       
                    'ns3_version': self.ns3_version,
                    'pybindgen_version': self.pybindgen_version,
                    'pygccxml_version': self.pygccxml_version
                 })

    @property
    def _install(self):
        return (
                 # Test if ns-3 is alredy cloned
                " ( "
                "  ( ( (test -d ${BIN}/%(ns3_version)s/build ) || "
                "    (test -d ${NS3BINDINGS:='None'} && test -d ${NS3LIBRARIES:='None'}) ) && "
                "    echo 'binaries found, nothing to do' )"
                " ) "
                " ||" 
                " (   "
                 # If not, copy ns-3 build to bin
                "  mkdir -p ${BIN}/%(ns3_version)s && "
                "  mv ${SRC}/%(ns3_version)s/build ${BIN}/%(ns3_version)s/build "
                " )"
             ) % ({ 
                    'ns3_version': self.ns3_version
                 })

    @property
    def _environment(self):
        env = []
        env.append("NS3BINDINGS=${NS3BINDINGS:=${BIN}/%(ns3_version)s/build/bindings/python/}" % ({ 
                    'ns3_version': self.ns3_version,
                 }))
        env.append("NS3LIBRARIES=${NS3LIBRARIES:=${BIN}/%(ns3_version)s/build/}" % ({ 
                    'ns3_version': self.ns3_version,
                 }))

        return " ".join(env) 

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

