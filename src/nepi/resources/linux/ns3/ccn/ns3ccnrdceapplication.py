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
from nepi.execution.resource import clsinit_copy, ResourceState, reschedule_delay
from nepi.resources.linux.ns3.ccn.ns3ccndceapplication import LinuxNS3CCNDceApplication

@clsinit_copy
class LinuxNS3DceCCNR(LinuxNS3CCNDceApplication):
    _rtype = "ns3::LinuxDceCCNR"

    @classmethod
    def _register_attributes(cls):
        max_fanout = Attribute("maxFanout",
            "Sets the CCNR_BTREE_MAX_FANOUT environmental variable. ",
            flags = Flags.Design)

        max_leaf_entries = Attribute("maxLeafEntries",
            "Sets the CCNR_BTREE_MAX_LEAF_ENTRIES environmental variable. ",
            flags = Flags.Design)

        max_node_bytes = Attribute("maxNodeBytes",
            "Sets the CCNR_BTREE_MAX_NODE_BYTES environmental variable. ",
            flags = Flags.Design)

        max_node_pool = Attribute("maxNodePool",
            "Sets the CCNR_BTREE_MAX_NODE_POOL environmental variable. ",
            flags = Flags.Design)

        content_cache = Attribute("contentCache",
            "Sets the CCNR_CONTENT_CACHE environmental variable. ",
            flags = Flags.Design)

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
            flags = Flags.Design)

        directory = Attribute("directory",
            "Sets the CCNR_DIRECTORY environmental variable. ",
            flags = Flags.Design)

        global_prefix = Attribute("globalPrefix",
            "Sets the CCNR_GLOBAL_PREFIX environmental variable. ",
            flags = Flags.Design)

        listen_on = Attribute("listenOn",
            "Sets the CCNR_LISTEN_ON environmental variable. ",
            flags = Flags.Design)

        min_send_bufsize = Attribute("minSendBufsize",
            "Sets the CCNR_MIN_SEND_BUFSIZE environmental variable. ",
            flags = Flags.Design)

        proto = Attribute("proto",
            "Sets the CCNR_PROTO environmental variable. ",
            flags = Flags.Design)

        status_port = Attribute("statusPort",
            "Sets the CCNR_STATUS_PORT environmental variable. ",
            flags = Flags.Design)

        start_write_scope_limit = Attribute("startWriteScopeLimit",
            "Sets the CCNR_START_WRITE_SCOPE_LIMIT environmental variable. ",
            flags = Flags.Design)

        ccns_debug = Attribute("ccnsDebug",
            "Sets the CCNS_DEBUG environmental variable. ",
            flags = Flags.Design)

        ccns_enable = Attribute("ccnsEnable",
            "Sets the CCNS_ENABLE environmental variable. ",
            flags = Flags.Design)

        ccns_faux_error = Attribute("ccnsFauxError",
            "Sets the CCNS_FAUX_ERROR environmental variable. ",
            flags = Flags.Design)

        ccns_heartbeat_micros = Attribute("ccnsHeartBeatMicros",
            "Sets the CCNS_HEART_BEAT_MICROS environmental variable. ",
            flags = Flags.Design)

        ccns_max_compares_busy = Attribute("ccnsMaxComparesBusy",
            "Sets the CCNS_MAX_COMPARES_BUSY environmental variable. ",
            flags = Flags.Design)

        ccns_max_fetch_busy = Attribute("ccnsMaxFetchBusy",
            "Sets the CCNS_MAX_FETCH_BUSY environmental variable. ",
            flags = Flags.Design)

        ccns_node_fetch_lifetime = Attribute("ccnsNodeFetchLifetime",
            "Sets the CCNS_NODE_FETCH_LIFETIME environmental variable. ",
            flags = Flags.Design)

        ccns_note_err = Attribute("ccnsNoteErr",
            "Sets the CCNS_NOTE_ERR environmental variable. ",
            flags = Flags.Design)

        ccns_repo_store = Attribute("ccnsRepoStore",
            "Sets the CCNS_REPO_STORE environmental variable. ",
            flags = Flags.Design)

        ccns_root_advise_fresh = Attribute("ccnsRootAdviseFresh",
            "Sets the CCNS_ROOT_ADVISE_FRESH environmental variable. ",
            flags = Flags.Design)

        ccns_root_advise_lifetime = Attribute("ccnsRootAdviseLifetime",
            "Sets the CCNS_ROOT_ADVISE_LIFETIME environmental variable. ",
            flags = Flags.Design)

        ccns_stable_enabled = Attribute("ccnsStableEnabled",
            "Sets the CCNS_STABLE_ENABLED environmental variable. ",
            flags = Flags.Design)

        ccns_sync_scope = Attribute("ccnsSyncScope",
            "Sets the CCNS_SYNC_SCOPE environmental variable. ",
            flags = Flags.Design)

        repo_file = Attribute("repoFile1",
            "The Repository uses $CCNR_DIRECTORY/repoFile1 for "
            "persistent storage of CCN Content Objects",
            flags = Flags.Design)

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

    def _instantiate_object(self):
        if not self.get("binary"):
            self.set("binary", "ccnr")

        if not self.get("environment"):
            self.set("environment", self._environment)
       
        repoFile1 = self.get("repoFile1")
        if repoFile1:
            env = "CCNR_DIRECTORY=/REPO/" 
            environment = self.get("environment")
            if environment:
                env += ";" + environment
            self.set("environment", env)
            self.set("files", "%s=/REPO/repoFile1" % repoFile1) 

        super(LinuxNS3DceCCNR, self)._instantiate_object()

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

        env = ";".join(map(lambda k: "%s=%s" % (envs.get(k), str(self.get(k))), 
            [k for k in envs.keys() if self.get(k)]))

        return env


