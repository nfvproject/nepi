#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
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
from nepi.execution.resource import clsinit_copy, ResourceState, \
    ResourceAction, reschedule_delay
from nepi.resources.linux.application import LinuxApplication
from nepi.resources.linux.ccn.ccnd import LinuxCCND
from nepi.util.timefuncs import tnow

import os

@clsinit_copy
class LinuxCCNR(LinuxApplication):
    _rtype = "LinuxCCNR"

    @classmethod
    def _register_attributes(cls):
        max_fanout = Attribute("maxFanout",
            "Sets the CCNR_BTREE_MAX_FANOUT environmental variable. ",
            flags = Flags.ExecReadOnly)

        max_leaf_entries = Attribute("maxLeafEntries",
            "Sets the CCNR_BTREE_MAX_LEAF_ENTRIES environmental variable. ",
            flags = Flags.ExecReadOnly)

        max_node_bytes = Attribute("maxNodeBytes",
            "Sets the CCNR_BTREE_MAX_NODE_BYTES environmental variable. ",
            flags = Flags.ExecReadOnly)

        max_node_pool = Attribute("maxNodePool",
            "Sets the CCNR_BTREE_MAX_NODE_POOL environmental variable. ",
            flags = Flags.ExecReadOnly)

        content_cache = Attribute("contentCache",
            "Sets the CCNR_CONTENT_CACHE environmental variable. ",
            flags = Flags.ExecReadOnly)

        debug = Attribute("debug",
            "Sets the CCNR_DEBUG environmental variable. "
            "Logging level for ccnr. Defaults to WARNING.",
            type = Types.Enumerate,
            allowed = [
                    "NONE",
                    "SEVERE",
                    "ERROR",
                    "WARNING",
                    "INFO",
                    "FINE, FINER, FINEST"],
            flags = Flags.ExecReadOnly)

        directory = Attribute("directory",
            "Sets the CCNR_DIRECTORY environmental variable. ",
            flags = Flags.ExecReadOnly)

        global_prefix = Attribute("globalPrefix",
            "Sets the CCNR_GLOBAL_PREFIX environmental variable. ",
            flags = Flags.ExecReadOnly)

        listen_on = Attribute("listenOn",
            "Sets the CCNR_LISTEN_ON environmental variable. ",
            flags = Flags.ExecReadOnly)

        min_send_bufsize = Attribute("minSendBufsize",
            "Sets the CCNR_MIN_SEND_BUFSIZE environmental variable. ",
            flags = Flags.ExecReadOnly)

        proto = Attribute("proto",
            "Sets the CCNR_PROTO environmental variable. ",
            flags = Flags.ExecReadOnly)

        status_port = Attribute("statusPort",
            "Sets the CCNR_STATUS_PORT environmental variable. ",
            flags = Flags.ExecReadOnly)

        start_write_scope_limit = Attribute("startWriteScopeLimit",
            "Sets the CCNR_START_WRITE_SCOPE_LIMIT environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_debug = Attribute("ccnsDebug",
            "Sets the CCNS_DEBUG environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_enable = Attribute("ccnsEnable",
            "Sets the CCNS_ENABLE environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_faux_error = Attribute("ccnsFauxError",
            "Sets the CCNS_FAUX_ERROR environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_heartbeat_micros = Attribute("ccnsHeartBeatMicros",
            "Sets the CCNS_HEART_BEAT_MICROS environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_max_compares_busy = Attribute("ccnsMaxComparesBusy",
            "Sets the CCNS_MAX_COMPARES_BUSY environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_max_fetch_busy = Attribute("ccnsMaxFetchBusy",
            "Sets the CCNS_MAX_FETCH_BUSY environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_node_fetch_lifetime = Attribute("ccnsNodeFetchLifetime",
            "Sets the CCNS_NODE_FETCH_LIFETIME environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_note_err = Attribute("ccnsNoteErr",
            "Sets the CCNS_NOTE_ERR environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_repo_store = Attribute("ccnsRepoStore",
            "Sets the CCNS_REPO_STORE environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_root_advise_fresh = Attribute("ccnsRootAdviseFresh",
            "Sets the CCNS_ROOT_ADVISE_FRESH environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_root_advise_lifetime = Attribute("ccnsRootAdviseLifetime",
            "Sets the CCNS_ROOT_ADVISE_LIFETIME environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_stable_enabled = Attribute("ccnsStableEnabled",
            "Sets the CCNS_STABLE_ENABLED environmental variable. ",
            flags = Flags.ExecReadOnly)

        ccns_sync_scope = Attribute("ccnsSyncScope",
            "Sets the CCNS_SYNC_SCOPE environmental variable. ",
            flags = Flags.ExecReadOnly)

        repo_file = Attribute("repoFile1",
            "The Repository uses $CCNR_DIRECTORY/repoFile1 for "
            "persistent storage of CCN Content Objects",
            flags = Flags.ExecReadOnly)

        cls._register_attribute(max_fanout)
        cls._register_attribute(max_leaf_entries)
        cls._register_attribute(max_node_bytes)
        cls._register_attribute(max_node_pool)
        cls._register_attribute(content_cache)
        cls._register_attribute(debug)
        cls._register_attribute(directory)
        cls._register_attribute(global_prefix)
        cls._register_attribute(listen_on)
        cls._register_attribute(min_send_bufsize)
        cls._register_attribute(proto)
        cls._register_attribute(status_port)
        cls._register_attribute(start_write_scope_limit)
        cls._register_attribute(ccns_debug)
        cls._register_attribute(ccns_enable)
        cls._register_attribute(ccns_faux_error)
        cls._register_attribute(ccns_heartbeat_micros)
        cls._register_attribute(ccns_max_compares_busy)
        cls._register_attribute(ccns_max_fetch_busy)
        cls._register_attribute(ccns_node_fetch_lifetime)
        cls._register_attribute(ccns_note_err)
        cls._register_attribute(ccns_repo_store)
        cls._register_attribute(ccns_root_advise_fresh)
        cls._register_attribute(ccns_root_advise_lifetime)
        cls._register_attribute(ccns_stable_enabled)
        cls._register_attribute(ccns_sync_scope)
        cls._register_attribute(repo_file)

    @classmethod
    def _register_traces(cls):
        log = Trace("log", "CCND log output")

        cls._register_trace(log)

    def __init__(self, ec, guid):
        super(LinuxCCNR, self).__init__(ec, guid)
        self._home = "ccnr-%s" % self.guid

    @property
    def ccnd(self):
        ccnd = self.get_connected(LinuxCCND.rtype())
        if ccnd: return ccnd[0]
        return None

    @property
    def node(self):
        if self.ccnd: return self.ccnd.node
        return None

    def deploy(self):
        if not self.ccnd or self.ccnd.state < ResourceState.READY:
            self.debug("---- RESCHEDULING DEPLOY ---- CCND state %s " % self.ccnd.state )
            
            # ccnr needs to wait until ccnd is deployed and running
            self.ec.schedule(reschedule_delay, self.deploy)
        else:
            try:
                if not self.get("command"):
                    self.set("command", self._start_command)

                if not self.get("env"):
                    self.set("env", self._environment)

                command = self.get("command")

                self.info("Deploying command '%s' " % command)

                self.discover()
                self.provision()
            except:
                self.fail()
                raise
 
            self.debug("----- READY ---- ")
            self.set_ready()

    def upload_start_command(self):
        command = self.get("command")
        env = self.get("env")

        if self.get("repoFile1"):
            # upload repoFile1
            local_file = self.get("repoFile1")
            remote_file = "${RUN_HOME}/repoFile1"
            remote_file = self.replace_paths(remote_file)
            self.node.upload(local_file,
                    remote_file,
                    overwrite = False)

        # We want to make sure the repository is running
        # before the experiment starts.
        # Run the command as a bash script in background,
        # in the host ( but wait until the command has
        # finished to continue )
        env = self.replace_paths(env)
        command = self.replace_paths(command)

        shfile = os.path.join(self.app_home, "start.sh")
        self.node.run_and_wait(command, self.run_home,
                shfile = shfile,
                overwrite = False,
                env = env,
                raise_on_error = True)

    def start(self):
        if self.state == ResourceState.READY:
            command = self.get("command")
            self.info("Starting command '%s'" % command)

            self.set_started()
        else:
            msg = " Failed to execute command '%s'" % command
            self.error(msg, out, err)
            self.fail()
            raise RuntimeError, msg

    @property
    def _start_command(self):
        return "ccnr &"

    @property
    def _environment(self):
        envs = dict({
            "maxFanout": "CCNR_BTREE_MAX_FANOUT",
            "maxLeafEntries": "CCNR_BTREE_MAX_LEAF_ENTRIES",
            "maxNodeBytes": "CCNR_BTREE_MAX_NODE_BYTES",
            "maxNodePool": "CCNR_BTREE_MAX_NODE_POOL",
            "contentCache": "CCNR_CONTENT_CACHE",
            "debug": "CCNR_DEBUG",
            "directory": "CCNR_DIRECTORY",
            "globalPrefix": "CCNR_GLOBAL_PREFIX",
            "listenOn": "CCNR_LISTEN_ON",
            "minSendBufsize": "CCNR_MIN_SEND_BUFSIZE",
            "proto": "CCNR_PROTO",
            "statusPort": "CCNR_STATUS_PORT",
            "startWriteScopeLimit": "CCNR_START_WRITE_SCOPE_LIMIT",
            "ccnsDebug": "CCNS_DEBUG",
            "ccnsEnable": "CCNS_ENABLE",
            "ccnsFauxError": "CCNS_FAUX_ERROR",
            "ccnsHeartBeatMicros": "CCNS_HEART_BEAT_MICROS",
            "ccnsMaxComparesBusy": "CCNS_MAX_COMPARES_BUSY",
            "ccnsMaxFetchBusy": "CCNS_MAX_FETCH_BUSY",
            "ccnsNodeFetchLifetime": "CCNS_NODE_FETCH_LIFETIME",
            "ccnsNoteErr": "CCNS_NOTE_ERR",
            "ccnsRepoStore": "CCNS_REPO_STORE",
            "ccnsRootAdviseFresh": "CCNS_ROOT_ADVISE_FRESH",
            "ccnsRootAdviseLifetime": "CCNS_ROOT_ADVISE_LIFETIME",
            "ccnsStableEnabled": "CCNS_STABLE_ENABLED",
            "ccnsSyncScope": "CCNS_SYNC_SCOPE",
            })

        env = self.ccnd.path
        env += " ".join(map(lambda k: "%s=%s" % (envs.get(k), self.get(k)) \
            if self.get(k) else "", envs.keys()))
       
        return env            
        
    def valid_connection(self, guid):
        # TODO: Validate!
        return True

