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
        ResourceState, ResourceFactory, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.util.timefuncs import tnow, tdiffsec
from nepi.resources.ns3.ns3simulation import NS3Simulation
from nepi.resources.ns3.ns3wrapper import SIMULATOR_UUID, GLOBAL_VALUE_UUID, \
        IPV4_GLOBAL_ROUTING_HELPER_UUID
from nepi.resources.linux.ns3.ns3client import LinuxNS3Client

import os
import time
import threading

## TODO: Clean up DCE part. All that is DCE specific should go
##       in the linux ns3dceapplication.py

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

        ns_log = Attribute("nsLog",
            "NS_LOG environment variable. " \
                    " Will only generate output if ns-3 is compiled in DEBUG mode. ",
            flags = Flags.Design)

        verbose = Attribute("verbose",
            "True to output debugging info from the ns3 client-server communication",
            type = Types.Bool,
            flags = Flags.Design)

        enable_dump = Attribute("enableDump",
            "Enable dumping the remote executed ns-3 commands to a script "
            "in order to later reproduce and debug the experiment",
            type = Types.Bool,
            default = False,
            flags = Flags.Design)

        build_mode = Attribute("buildMode",
            "Mode used to build ns-3 with waf. One if: debug, release, oprimized ",
            default = "optimized", 
            allowed = ["debug", "release", "optimized"],
            type = Types.Enumerate,
            flags = Flags.Design)

        ns3_version = Attribute("ns3Version",
            "Version of ns-3 to install from nsam repo",
            #default = "ns-3.19", 
            default = "ns-3.20", 
            #default = "ns-3-dev", 
            flags = Flags.Design)

        pybindgen_version = Attribute("pybindgenVersion",
            "Version of pybindgen to install from bazar repo",
            #default = "864", 
            default = "868", 
            #default = "876", 
            flags = Flags.Design)

        dce_version = Attribute("dceVersion",
            "Version of dce to install from nsam repo (tag branch for repo)",
            default = "dce-1.3", 
            #default = "dce-dev", 
            flags = Flags.Design)

        populate_routing_tables = Attribute("populateRoutingTables",
            "Invokes  Ipv4GlobalRoutingHelper.PopulateRoutingTables() ",
            default = False,
            type = Types.Bool,
            flags = Flags.Design)

        stoptime = Attribute("stopTime",
            "Time at which the simulation will stop",
            flags = Flags.Design)

        cls._register_attribute(impl_type)
        cls._register_attribute(sched_type)
        cls._register_attribute(check_sum)
        cls._register_attribute(ns_log)
        cls._register_attribute(enable_dump)
        cls._register_attribute(verbose)
        cls._register_attribute(build_mode)
        cls._register_attribute(ns3_version)
        cls._register_attribute(pybindgen_version)
        cls._register_attribute(dce_version)
        cls._register_attribute(populate_routing_tables)
        cls._register_attribute(stoptime)

    def __init__(self, ec, guid):
        LinuxApplication.__init__(self, ec, guid)
        NS3Simulation.__init__(self)

        self._client = None
        self._home = "ns3-simu-%s" % self.guid
        self._socket_name = "ns3-%s.sock" % os.urandom(4).encode('hex')
        self._dce_manager_helper_uuid = None
        self._dce_application_helper_uuid = None
        self._enable_dce = None

    @property
    def socket_name(self):
        return self._socket_name

    @property
    def remote_socket(self):
        return os.path.join(self.run_home, self.socket_name)

    def trace(self, name, attr = TraceAttr.ALL, block = 512, offset = 0):
        # stout needs to get flushed on the ns-3 server side, else we will 
        # get an empty stream. We try twice to retrieve the stream
        # if we get empty stdout since the stream might not be
        # flushed immediately.
        if name.endswith("stdout"):
            self._client.flush() 
            result = LinuxApplication.trace(self, name, attr, block, offset)
            if result:
                return result
            # Let the stream be flushed
            time.sleep(1)

        return LinuxApplication.trace(self, name, attr, block, offset)

    def upload_sources(self):
        self.node.mkdir(os.path.join(self.node.src_dir, "ns3wrapper"))

        # upload ns3 wrapper python script
        ns3_wrapper = os.path.join(os.path.dirname(__file__), "..", "..", "ns3", 
                "ns3wrapper.py")

        self.node.upload(ns3_wrapper,
                os.path.join(self.node.src_dir, "ns3wrapper", "ns3wrapper.py"),
                overwrite = False)

        # upload ns3 wrapper debug python script
        ns3_wrapper_debug = os.path.join(os.path.dirname(__file__), "..", "..", "ns3", 
                "ns3wrapper_debug.py")

        self.node.upload(ns3_wrapper_debug,
                os.path.join(self.node.src_dir, "ns3wrapper", "ns3wrapper_debug.py"),
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

        # Upload user defined ns-3 sources
        self.node.mkdir(os.path.join(self.node.src_dir, "ns-3"))
        src_dir = os.path.join(self.node.src_dir, "ns-3")

        super(LinuxNS3Simulation, self).upload_sources(src_dir = src_dir)
    
    def upload_extra_sources(self, sources = None, src_dir = None):
        return super(LinuxNS3Simulation, self).upload_sources(
                sources = sources, 
                src_dir = src_dir)

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

        # Wait until the remote socket is created
        self.wait_remote_socket()

    def configure(self):
        if self.has_changed("simulatorImplementationType"):
            simu_type = self.get("simulatorImplementationType")
            stype = self.create("StringValue", simu_type)
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "SimulatorImplementationType", stype)

        if self.has_changed("checksumEnabled"):
            check_sum = self.get("checksumEnabled")
            btrue = self.create("BooleanValue", check_sum)    
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "ChecksumEnabled", btrue)
        
        if self.has_changed("schedulerType"):
            sched_type = self.get("schedulerType")
            stype = self.create("StringValue", sched_type)
            self.invoke(GLOBAL_VALUE_UUID, "Bind", "SchedulerType", btrue)
        
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

            if self.get("sources"):
                sources = self.get("sources")
                source = sources.split(" ")[0]
                basename = os.path.basename(source)
                version = ( basename.strip().replace(".tar.gz", "")
                    .replace(".tar","")
                    .replace(".gz","")
                    .replace(".zip","") )

                self.set("ns3Version", version)
                self.set("sources", source)

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

            self.configure()
            
            self.set_ready()

    def do_start(self):
        """ Starts simulation execution

        """
        self.info("Starting")

        if self.state == ResourceState.READY:
            if self.get("populateRoutingTables") == True:
                self.invoke(IPV4_GLOBAL_ROUTING_HELPER_UUID, "PopulateRoutingTables")

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
            time = None
            if self.get("stopTime"):
                time = self.get("stopTime")

            self._client.stop(time=time) 
            self.set_stopped()

    def do_release(self):
        self.info("Releasing resource")

        tear_down = self.get("tearDown")
        if tear_down:
            self.node.execute(tear_down)

        self.do_stop()
        self._client.shutdown()
        LinuxApplication.do_stop(self)
        
        super(LinuxApplication, self).do_release()

    @property
    def enable_dce(self):
        if self._enable_dce is None:
            from nepi.resources.ns3.ns3dceapplication import NS3BaseDceApplication
            rclass = ResourceFactory.get_resource_type(
                    NS3BaseDceApplication.get_rtype())
            
            self._enable_dce = False
            for guid in self.ec.resources:
                rm = self.ec.get_resource(guid)
                if isinstance(rm, rclass):
                    self._enable_dce = True
                    break

        return self._enable_dce

    @property
    def _start_command(self):
        command = [] 

        command.append("PYTHONPATH=$PYTHONPATH:${SRC}/ns3wrapper/")
        
        command.append("python ${SRC}/ns3wrapper/ns3server.py -S %s" % \
                os.path.basename(self.remote_socket) )

        ns_log = self.get("nsLog")
        if ns_log:
            command.append("-L '%s'" % ns_log)

        if self.get("enableDump"):
            command.append("-D")

        if self.get("verbose"):
            command.append("-v")

        command = " ".join(command)
        return command

    @property
    def _dependencies(self):
        if self.node.use_rpm:
            return ( " gcc gcc-c++ python python-devel mercurial bzr tcpdump socat gccxml unzip")
        elif self.node.use_deb:
            return ( " gcc g++ python python-dev mercurial bzr tcpdump socat gccxml python-pygccxml unzip")
        return ""

    @property
    def ns3_repo(self):
        return "http://code.nsnam.org"

    @property
    def pygccxml_version(self):
        return "pygccxml-1.0.0"

    @property
    def dce_repo(self):
        return "http://code.nsnam.org/ns-3-dce"
        #eturn "http://code.nsnam.org/epmancini/ns-3-dce"

    @property
    def dce_version(self):
        dce_version = self.get("dceVersion")
        return dce_version or "dce-dev"

    @property
    def ns3_build_location(self):
        location = "${BIN}/ns-3/%(ns3_version)s%(dce_version)s/%(build_mode)s/build" \
                    % {
                        "ns3_version": self.get("ns3Version"),
                        "dce_version": "-%s" % self.get("dceVersion") \
                                if self.enable_dce else "", 
                        "build_mode": self.get("buildMode"),
                      }

        return location
 

    @property
    def ns3_src_location(self):
        location = "${SRC}/ns-3/%(ns3_version)s" \
                    % {
                        "ns3_version": self.get("ns3Version"),
                      }

        return location
 
    @property
    def dce_src_location(self):
        location = "${SRC}/ns-3-dce/%(dce_version)s" \
                   % {
                        "dce_version": self.get("dceVersion"),
                     }

        return location

    @property
    def _clone_ns3_command(self):
        source = self.get("sources")
        
        if not source:
            clone_ns3_cmd = "hg clone %(ns3_repo)s/%(ns3_version)s %(ns3_src)s" \
                    % {
                        "ns3_version": self.get("ns3Version"),
                        "ns3_repo": self.ns3_repo,  
                        "ns3_src": self.ns3_src_location,
                      }
        else:
            if source.find(".tar.gz") > -1:
                clone_ns3_cmd = ( 
                            "tar xzf ${SRC}/ns-3/%(basename)s " 
                            " --strip-components=1 -C %(ns3_src)s"
                            ) % {
                                "basename": os.path.basename(source),
                                "ns3_src": self.ns3_src_location,
                                }
            elif source.find(".tar") > -1:
                clone_ns3_cmd = ( 
                            "tar xf ${SRC}/ns-3/%(basename)s " 
                            " --strip-components=1 -C %(ns3_src)s"
                            ) % {
                                "basename": os.path.basename(source),
                                "ns3_src": self.ns3_src_location,
                                }
            elif source.find(".zip") > -1:
                basename = os.path.basename(source)
                bare_basename = basename.replace(".zip", "") 

                clone_ns3_cmd = ( 
                            "unzip ${SRC}/ns-3/%(basename)s && "
                            "mv ${SRC}/ns-3/%(bare_basename)s %(ns3_src)s"
                            ) % {
                                "bare_basename": basename_name,
                                "basename": basename,
                                "ns3_src": self.ns3_src_location,
                                }

        return clone_ns3_cmd

    @property
    def _clone_dce_command(self):
        clone_dce_cmd = " echo 'DCE will not be built' "

        if self.enable_dce:
            dce_version = self.dce_version
            dce_tag = ""
            if dce_version != "dce-dev":
                dce_tag = "-r %s" % dce_version

            clone_dce_cmd = (
                        # DCE installation
                        # Test if dce is alredy cloned
                        " ( "
                        "  ( "
                        "    ( test -d %(dce_src)s ) "
                        "   && echo 'dce binaries found, nothing to do'"
                        "  ) "
                        " ) "
                        "  || " 
                        # Get dce source code
                        " ( "
                        "   mkdir -p %(dce_src)s && "
                        "   hg clone %(dce_repo)s %(dce_tag)s %(dce_src)s"
                        " ) "
                     ) % {
                            "dce_repo": self.dce_repo,
                            "dce_tag": dce_tag,
                            "dce_src": self.dce_src_location,
                         }

        return clone_dce_cmd

    @property
    def _build(self):
        # If the user defined local sources for ns-3, we uncompress the sources
        # on the remote sources directory. Else we clone ns-3 from the official repo.
        clone_ns3_cmd = self._clone_ns3_command
        clone_dce_cmd = self._clone_dce_command

        ns3_build_cmd = (
                # NS3 installation
                "( "
                " ( "
                # Test if ns-3 is alredy cloned
                "  ((( test -d %(ns3_src)s ) || "
                "    ( test -d ${NS3BINDINGS:='None'} && test -d ${NS3LIBRARIES:='None'})) "
                "  && echo 'ns-3 binaries found, nothing to do' )"
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
                "       python setup.py build && "
                "       sudo -S python setup.py install "
                "     ) "
                "   ) " 
                # Install pybindgen
                "  && "
                "   (   "
                "     ( "
                "       test -d ${SRC}/pybindgen/%(pybindgen_version)s && "
                "       echo 'binaries found, nothing to do' "
                "     ) "
                "      || "
                # If not, clone and build
                "      ( cd ${SRC} && "
                "        mkdir -p ${SRC}/pybindgen && "
                "        bzr checkout lp:pybindgen -r %(pybindgen_version)s ${SRC}/pybindgen/%(pybindgen_version)s && "
                "        cd ${SRC}/pybindgen/%(pybindgen_version)s && "
                "        ./waf configure && "
                "        ./waf "
                "      ) "
                "   ) " 
                " && "
                # Get ns-3 source code
                "  ( "
                "     mkdir -p %(ns3_src)s && "
                "     %(clone_ns3_cmd)s "
                "  ) "
                " ) "
                ") "
                " && "
                "( "
                "   %(clone_dce_cmd)s "
                ") "
             ) % { 
                    "ns3_src": self.ns3_src_location,
                    "pybindgen_version": self.get("pybindgenVersion"),
                    "pygccxml_version": self.pygccxml_version,
                    "clone_ns3_cmd": clone_ns3_cmd,
                    "clone_dce_cmd": clone_dce_cmd,
                 }

        return ns3_build_cmd

    @property
    def _install_dce_command(self):
        install_dce_cmd = " echo 'DCE will not be installed'"

        if self.enable_dce:
            install_dce_cmd = (
                        " ( "
                        "   ((test -d %(ns3_build)s/bin_dce ) && "
                        "    echo 'dce binaries found, nothing to do' )"
                        " ) "
                        " ||" 
                        " (   "
                         # If not, copy build to dce
                        "  cd %(dce_src)s && "
                        "  rm -rf %(dce_src)s/build && "
                        "  ./waf configure %(enable_opt)s --with-pybindgen=${SRC}/pybindgen/%(pybindgen_version)s "
                        "  --prefix=%(ns3_build)s --with-ns3=%(ns3_build)s && "
                        "  ./waf build && "
                        "  ./waf install && "
                        "  [ ! -e %(ns3_build)s/lib/python/site-packages/ns/dce.so ] && "
                        "   mv %(ns3_build)s/lib*/python*/site-packages/ns/dce.so %(ns3_build)s/lib/python/site-packages/ns/ "
                        " )"
                ) % { 
                    "pybindgen_version": self.get("pybindgenVersion"),
                    "enable_opt": "--enable-opt" if  self.get("buildMode") == "optimized" else "",
                    "ns3_build": self.ns3_build_location,
                    "dce_src": self.dce_src_location,
                     }

        return install_dce_cmd

    @property
    def _install(self):
        install_dce_cmd = self._install_dce_command

        install_ns3_cmd = (
                 # Test if ns-3 is alredy installed
                "("
                " ( "
                "  ( ( (test -d %(ns3_build)s/lib ) || "
                "    (test -d ${NS3BINDINGS:='None'} && test -d ${NS3LIBRARIES:='None'}) ) && "
                "    echo 'binaries found, nothing to do' )"
                " ) "
                " ||" 
                " (   "
                 # If not, copy ns-3 build to bin
                "  mkdir -p %(ns3_build)s && "
                "  cd %(ns3_src)s && "
                "  rm -rf %(ns3_src)s/build && "
                "  ./waf configure -d %(build_mode)s --with-pybindgen=${SRC}/pybindgen/%(pybindgen_version)s "
                "  --prefix=%(ns3_build)s && "
                "  ./waf build && "
                "  ./waf install && "
                "  mv %(ns3_build)s/lib*/python* %(ns3_build)s/lib/python "
                " )"
                ") "
                " && "
                "( "
                "   %(install_dce_cmd)s "
                ") "
              ) % { 
                    "pybindgen_version": self.get("pybindgenVersion"),
                    "build_mode": self.get("buildMode"),
                    "install_dce_cmd": install_dce_cmd,
                    "ns3_build": self.ns3_build_location,
                    "ns3_src": self.ns3_src_location,
                 }

        return install_ns3_cmd

    @property
    def _environment(self):
        env = []
        env.append("PYTHONPATH=$PYTHONPATH:${NS3BINDINGS:=%(ns3_build)s/lib/python/site-packages}" % { 
                    "ns3_build": self.ns3_build_location
                 })
        # If NS3LIBRARIES is defined and not empty, assign its value, 
        # if not assign ns3_build_home/lib/ to NS3LIBRARIES and LD_LIBARY_PATH
        env.append("LD_LIBRARY_PATH=${NS3LIBRARIES:=%(ns3_build)s/lib}" % { 
                    "ns3_build": self.ns3_build_location
                 })
        env.append("DCE_PATH=$NS3LIBRARIES/../bin_dce")
        env.append("DCE_ROOT=$NS3LIBRARIES/..")

        return " ".join(env) 

    def replace_paths(self, command):
        """
        Replace all special path tags with shell-escaped actual paths.
        """
        return ( command
            .replace("${USR}", self.node.usr_dir)
            .replace("${LIB}", self.node.lib_dir)
            .replace("${BIN}", self.node.bin_dir)
            .replace("${SRC}", self.node.src_dir)
            .replace("${SHARE}", self.node.share_dir)
            .replace("${EXP}", self.node.exp_dir)
            .replace("${EXP_HOME}", self.node.exp_home)
            .replace("${APP_HOME}", self.app_home)
            .replace("${RUN_HOME}", self.run_home)
            .replace("${NODE_HOME}", self.node.node_home)
            .replace("${HOME}", self.node.home_dir)
            # If NS3LIBRARIES is defined and not empty, use that value, 
            # if not use ns3_build_home/lib/
            .replace("${BIN_DCE}", "${NS3LIBRARIES-%s/lib}/../bin_dce" % \
                    self.ns3_build_location)
            )

    def valid_connection(self, guid):
        # TODO: Validate!
        return True

    def wait_remote_socket(self):
        """ Waits until the remote socket is created
        """
        command = " [ -e %s ] && echo 'DONE' " % self.remote_socket

        for i in xrange(200):
            (out, err), proc = self.node.execute(command, retry = 1, 
                    with_lock = True)

            if out.find("DONE") > -1:
                break
        else:
            raise RuntimeError("Remote socket not found at %s" % \
                    self.remote_socket)
    

