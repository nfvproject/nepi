#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
from nepi.util import validation
from nepi.util.constants import ApplicationStatus as AS, TestbedStatus as TS, TIME_NOW, DeploymentConfiguration as DC
from nepi.util.parser._xml import XmlExperimentParser
import sys
import re
import threading
import ConfigParser
import os
import collections
import functools
import time
import logging
logging.basicConfig()

ATTRIBUTE_PATTERN_BASE = re.compile(r"\{#\[(?P<label>[-a-zA-Z0-9._]*)\](?P<expr>(?P<component>\.addr\[[0-9]+\]|\.route\[[0-9]+\]|\.trace\[[-a-zA-Z0-9._]+\])?.\[(?P<attribute>[-a-zA-Z0-9._]*)\])#}")
ATTRIBUTE_PATTERN_GUID_SUB = r"{#[%(guid)s]%(expr)s#}"
COMPONENT_PATTERN = re.compile(r"(?P<kind>[a-z]*)\[(?P<index>.*)\]")

def _undefer(deferred):
    if hasattr(deferred, '_get'):
        return deferred._get()
    else:
        return deferred


class TestbedController(object):
    def __init__(self, testbed_id, testbed_version):
        self._testbed_id = testbed_id
        self._testbed_version = testbed_version

    @property
    def testbed_id(self):
        return self._testbed_id

    @property
    def testbed_version(self):
        return self._testbed_version

    @property
    def guids(self):
        raise NotImplementedError

    def defer_configure(self, name, value):
        """Instructs setting a configuartion attribute for the testbed instance"""
        raise NotImplementedError

    def defer_create(self, guid, factory_id):
        """Instructs creation of element """
        raise NotImplementedError

    def defer_create_set(self, guid, name, value):
        """Instructs setting an initial attribute on an element"""
        raise NotImplementedError

    def defer_factory_set(self, guid, name, value):
        """Instructs setting an attribute on a factory"""
        raise NotImplementedError

    def defer_connect(self, guid1, connector_type_name1, guid2, 
            connector_type_name2): 
        """Instructs creation of a connection between the given connectors"""
        raise NotImplementedError

    def defer_cross_connect(self, 
            guid, connector_type_name,
            cross_guid, cross_testbed_guid,
            cross_testbed_id, cross_factory_id,
            cross_connector_type_name):
        """
        Instructs creation of a connection between the given connectors 
        of different testbed instances
        """
        raise NotImplementedError

    def defer_add_trace(self, guid, trace_id):
        """Instructs the addition of a trace"""
        raise NotImplementedError

    def defer_add_address(self, guid, address, netprefix, broadcast): 
        """Instructs the addition of an address"""
        raise NotImplementedError

    def defer_add_route(self, guid, destination, netprefix, nexthop, metric = 0):
        """Instructs the addition of a route"""
        raise NotImplementedError

    def do_setup(self):
        """After do_setup the testbed initial configuration is done"""
        raise NotImplementedError

    def do_create(self):
        """
        After do_create all instructed elements are created and 
        attributes setted
        """
        raise NotImplementedError

    def do_connect_init(self):
        """
        After do_connect_init all internal connections between testbed elements
        are initiated
        """
        raise NotImplementedError

    def do_connect_compl(self):
        """
        After do_connect all internal connections between testbed elements
        are completed
        """
        raise NotImplementedError

    def do_preconfigure(self):
        """
        Done just before resolving netrefs, after connection, before cross connections,
        useful for early stages of configuration, for setting up stuff that might be
        required for netref resolution.
        """
        raise NotImplementedError

    def do_configure(self):
        """After do_configure elements are configured"""
        raise NotImplementedError

    def do_prestart(self):
        """Before do_start elements are prestart-configured"""
        raise NotImplementedError

    def do_cross_connect_init(self, cross_data):
        """
        After do_cross_connect_init initiation of all external connections 
        between different testbed elements is performed
        """
        raise NotImplementedError

    def do_cross_connect_compl(self, cross_data):
        """
        After do_cross_connect_compl completion of all external connections 
        between different testbed elements is performed
        """
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def recover(self):
        """
        On testbed recovery (if recovery is a supported policy), the controller
        instance will be re-created and the following sequence invoked:
        
            do_setup
            defer_X - programming the testbed with persisted execution values
                (not design values). Execution values (ExecImmutable attributes)
                should be enough to recreate the testbed's state.
            *recover*
            <cross-connection methods>
            
        Start will not be called, and after cross connection invocations,
        the testbed is supposed to be fully functional again.
        """
        raise NotImplementedError

    def set(self, guid, name, value, time = TIME_NOW):
        raise NotImplementedError

    def get(self, guid, name, time = TIME_NOW):
        raise NotImplementedError
    
    def get_route(self, guid, index, attribute):
        """
        Params:
            
            guid: guid of box to query
            index: number of routing entry to fetch
            attribute: one of Destination, NextHop, NetPrefix
        """
        raise NotImplementedError

    def get_address(self, guid, index, attribute='Address'):
        """
        Params:
            
            guid: guid of box to query
            index: number of inteface to select
            attribute: one of Address, NetPrefix, Broadcast
        """
        raise NotImplementedError

    def get_attribute_list(self, guid, filter_flags = None, exclude = False):
        raise NotImplementedError

    def get_factory_id(self, guid):
        raise NotImplementedError

    def action(self, time, guid, action):
        raise NotImplementedError

    def status(self, guid):
        raise NotImplementedError
    
    def testbed_status(self):
        raise NotImplementedError

    def trace(self, guid, trace_id, attribute='value'):
        raise NotImplementedError

    def traces_info(self):
        """ dictionary of dictionaries:
            traces_info = dict({
                guid = dict({
                    trace_id = dict({
                            host = host,
                            filepath = filepath,
                            filesize = size in bytes,
                        })
                })
            })"""
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

class ExperimentController(object):
    def __init__(self, experiment_xml, root_dir):
        self._experiment_design_xml = experiment_xml
        self._experiment_execute_xml = None
        self._testbeds = dict()
        self._deployment_config = dict()
        self._netrefs = collections.defaultdict(set)
        self._testbed_netrefs = collections.defaultdict(set)
        self._cross_data = dict()
        self._root_dir = root_dir
        self._netreffed_testbeds = set()
        self._guids_in_testbed_cache = dict()
        self._failed_testbeds = set()
        self._started_time = None
        self._stopped_time = None
        self._testbed_order = []
      
        self._logger = logging.getLogger('nepi.core.execute')
        level = logging.ERROR
        if os.environ.get("NEPI_CONTROLLER_LOGLEVEL", 
                DC.ERROR_LEVEL) == DC.DEBUG_LEVEL:
            level = logging.DEBUG
        self._logger.setLevel(level)
 
        if experiment_xml is None and root_dir is not None:
            # Recover
            self.load_experiment_xml()
            self.load_execute_xml()
        else:
            self.persist_experiment_xml()

    @property
    def experiment_design_xml(self):
        return self._experiment_design_xml

    @property
    def experiment_execute_xml(self):
        return self._experiment_execute_xml

    @property
    def started_time(self):
        return self._started_time

    @property
    def stopped_time(self):
        return self._stopped_time

    @property
    def guids(self):
        guids = list()
        for testbed_guid in self._testbeds.keys():
            _guids = self._guids_in_testbed(testbed_guid)
            if _guids:
                guids.extend(_guids)
        return guids

    def persist_experiment_xml(self):
        xml_path = os.path.join(self._root_dir, "experiment-design.xml")
        f = open(xml_path, "w")
        f.write(self._experiment_design_xml)
        f.close()

    def persist_execute_xml(self):
        xml_path = os.path.join(self._root_dir, "experiment-execute.xml")
        f = open(xml_path, "w")
        f.write(self._experiment_execute_xml)
        f.close()

    def load_experiment_xml(self):
        xml_path = os.path.join(self._root_dir, "experiment-design.xml")
        f = open(xml_path, "r")
        self._experiment_design_xml = f.read()
        f.close()

    def load_execute_xml(self):
        xml_path = os.path.join(self._root_dir, "experiment-execute.xml")
        f = open(xml_path, "r")
        self._experiment_execute_xml = f.read()
        f.close()

    def trace(self, guid, trace_id, attribute='value'):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.trace(guid, trace_id, attribute)
        raise RuntimeError("No element exists with guid %d" % guid)    

    def traces_info(self):
        traces_info = dict()
        for guid, testbed in self._testbeds.iteritems():
            tinfo = testbed.traces_info()
            if tinfo:
                traces_info[guid] = testbed.traces_info()
        return traces_info

    @staticmethod
    def _parallel(callables):
        excs = []
        def wrap(callable):
            def wrapped(*p, **kw):
                try:
                    callable(*p, **kw)
                except:
                    logging.exception("Exception occurred in asynchronous thread:")
                    excs.append(sys.exc_info())
            try:
                wrapped = functools.wraps(callable)(wrapped)
            except:
                # functools.partial not wrappable
                pass
            return wrapped
        threads = [ threading.Thread(target=wrap(callable)) for callable in callables ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for exc in excs:
            eTyp, eVal, eLoc = exc
            raise eTyp, eVal, eLoc

    def start(self):
        self._started_time = time.time() 
        self._start()

    def _start(self, recover = False):
        parser = XmlExperimentParser()
        
        if recover:
            xml = self._experiment_execute_xml
        else:
            xml = self._experiment_design_xml
        data = parser.from_xml_to_data(xml)

        # instantiate testbed controllers
        to_recover, to_restart = self._init_testbed_controllers(data, recover)
        all_restart = set(to_restart)
        
        if not recover:
            # persist testbed connection data, for potential recovery
            self._persist_testbed_proxies()
        else:
            # recover recoverable controllers
            for guid in to_recover:
                try:
                    self._testbeds[guid].do_setup()
                    self._testbeds[guid].recover()
                except:
                    self._logger.exception("During recovery of testbed %s", guid)
                    
                    # Mark failed
                    self._failed_testbeds.add(guid)
    
        def steps_to_configure(self, allowed_guids):
            # perform setup in parallel for all test beds,
            # wait for all threads to finish

            self._logger.debug("ExperimentController: Starting parallel do_setup")
            self._parallel([testbed.do_setup 
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])
       
            # perform create-connect in parallel, wait
            # (internal connections only)
            self._logger.debug("ExperimentController: Starting parallel do_create")
            self._parallel([testbed.do_create
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._logger.debug("ExperimentController: Starting parallel do_connect_init")
            self._parallel([testbed.do_connect_init
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._logger.debug("ExperimentController: Starting parallel do_connect_fin")
            self._parallel([testbed.do_connect_compl
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._logger.debug("ExperimentController: Starting parallel do_preconfigure")
            self._parallel([testbed.do_preconfigure
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])
            self._clear_caches()
            
            # Store testbed order
            self._testbed_order.append(allowed_guids)

        steps_to_configure(self, to_restart)

        if self._netreffed_testbeds:
            self._logger.debug("ExperimentController: Resolving netreffed testbeds")
            # initally resolve netrefs
            self.do_netrefs(data, fail_if_undefined=False)
            
            # rinse and repeat, for netreffed testbeds
            netreffed_testbeds = set(self._netreffed_testbeds)

            to_recover, to_restart = self._init_testbed_controllers(data, recover)
            all_restart.update(to_restart)
            
            if not recover:
                # persist testbed connection data, for potential recovery
                self._persist_testbed_proxies()
            else:
                # recover recoverable controllers
                for guid in to_recover:
                    try:
                        self._testbeds[guid].do_setup()
                        self._testbeds[guid].recover()
                    except:
                        self._logger.exception("During recovery of testbed %s", guid)

                        # Mark failed
                        self._failed_testbeds.add(guid)

            # configure dependant testbeds
            steps_to_configure(self, to_restart)
        
        all_restart = [ self._testbeds[guid] for guid in all_restart ]
            
        # final netref step, fail if anything's left unresolved
        self._logger.debug("ExperimentController: Resolving do_netrefs")
        self.do_netrefs(data, fail_if_undefined=False)
       
        # Only now, that netref dependencies have been solve, it is safe to
        # program cross_connections
        self._logger.debug("ExperimentController: Programming testbed cross-connections")
        self._program_testbed_cross_connections(data)
 
        # perform do_configure in parallel for al testbeds
        # (it's internal configuration for each)
        self._logger.debug("ExperimentController: Starting parallel do_configure")
        self._parallel([testbed.do_configure
                        for testbed in all_restart])

        self._clear_caches()

        #print >>sys.stderr, "DO IT"
        #import time
        #time.sleep(60)
        
        # cross-connect (cannot be done in parallel)
        self._logger.debug("ExperimentController: Starting cross-connect")
        for guid, testbed in self._testbeds.iteritems():
            cross_data = self._get_cross_data(guid)
            testbed.do_cross_connect_init(cross_data)
        for guid, testbed in self._testbeds.iteritems():
            cross_data = self._get_cross_data(guid)
            testbed.do_cross_connect_compl(cross_data)
       
        self._clear_caches()

        # Last chance to configure (parallel on all testbeds)
        self._logger.debug("ExperimentController: Starting parallel do_prestart")
        self._parallel([testbed.do_prestart
                        for testbed in all_restart])

        # final netref step, fail if anything's left unresolved
        self.do_netrefs(data, fail_if_undefined=True)
 
        self._clear_caches()
        
        if not recover:
            # update execution xml with execution-specific values
            # TODO: BUG! BUggy code! cant stand all serializing all attribute values (ej: tun_key which is non ascci)"
            self._update_execute_xml()
            self.persist_execute_xml()

        # start experiment (parallel start on all testbeds)
        self._logger.debug("ExperimentController: Starting parallel do_start")
        self._parallel([testbed.start
                        for testbed in all_restart])

        self._clear_caches()

    def _clear_caches(self):
        # Cleaning cache for safety.
        self._guids_in_testbed_cache = dict()

    def _persist_testbed_proxies(self):
        TRANSIENT = (DC.RECOVER,)
        
        # persist access configuration for all testbeds, so that
        # recovery mode can reconnect to them if it becomes necessary
        conf = ConfigParser.RawConfigParser()
        for testbed_guid, testbed_config in self._deployment_config.iteritems():
            testbed_guid = str(testbed_guid)
            conf.add_section(testbed_guid)
            for attr in testbed_config.get_attribute_list():
                if attr not in TRANSIENT:
                    value = testbed_config.get_attribute_value(attr)
                    if value is not None:
                        conf.set(testbed_guid, attr, value)
        
        f = open(os.path.join(self._root_dir, 'deployment_config.ini'), 'w')
        conf.write(f)
        f.close()
    
    def _load_testbed_proxies(self):
        TYPEMAP = {
            Attribute.STRING : 'get',
            Attribute.BOOL : 'getboolean',
            Attribute.ENUM : 'get',
            Attribute.DOUBLE : 'getfloat',
            Attribute.INTEGER : 'getint',
        }
        
        TRANSIENT = (DC.RECOVER,)
        
        # deferred import because proxy needs
        # our class definitions to define proxies
        import nepi.util.proxy as proxy
        
        conf = ConfigParser.RawConfigParser()
        conf.read(os.path.join(self._root_dir, 'deployment_config.ini'))
        for testbed_guid in conf.sections():
            testbed_config = proxy.AccessConfiguration()
            testbed_guid = str(testbed_guid)
            for attr in testbed_config.get_attribute_list():
                if attr not in TRANSIENT:
                    getter = getattr(conf, TYPEMAP.get(
                        testbed_config.get_attribute_type(attr),
                        'get') )
                    try:
                        value = getter(testbed_guid, attr)
                        testbed_config.set_attribute_value(attr, value)
                    except ConfigParser.NoOptionError:
                        # Leave default
                        pass
    
    def _unpersist_testbed_proxies(self):
        try:
            os.remove(os.path.join(self._root_dir, 'deployment_config.ini'))
        except:
            # Just print exceptions, this is just cleanup
            self._logger.exception("Loading testbed configuration")

    def _update_execute_xml(self):
        # For all testbeds,
        #   For all elements in testbed,
        #       - gather immutable execute-readable attribuets lists
        #         asynchronously
        # Generate new design description from design xml
        # (Wait for attributes lists - implicit syncpoint)
        # For all testbeds,
        #   For all elements in testbed,
        #       - gather all immutable execute-readable attribute
        #         values, asynchronously
        # (Wait for attribute values - implicit syncpoint)
        # For all testbeds,
        #   For all elements in testbed,
        #       - inject non-None values into new design
        # Generate execute xml from new design

        attribute_lists = dict(
            (testbed_guid, collections.defaultdict(dict))
            for testbed_guid in self._testbeds
        )
        
        for testbed_guid, testbed in self._testbeds.iteritems():
            guids = self._guids_in_testbed(testbed_guid)
            for guid in guids:
                attribute_lists[testbed_guid][guid] = \
                    testbed.get_attribute_list_deferred(guid, Attribute.ExecImmutable)
        
        parser = XmlExperimentParser()
        execute_data = parser.from_xml_to_data(self._experiment_design_xml)

        attribute_values = dict(
            (testbed_guid, collections.defaultdict(dict))
            for testbed_guid in self._testbeds
        )
        
        for testbed_guid, testbed_attribute_lists in attribute_lists.iteritems():
            testbed = self._testbeds[testbed_guid]
            for guid, attribute_list in testbed_attribute_lists.iteritems():
                attribute_list = _undefer(attribute_list)
                attribute_values[testbed_guid][guid] = dict(
                    (attribute, testbed.get_deferred(guid, attribute))
                    for attribute in attribute_list
                )
        
        for testbed_guid, testbed_attribute_values in attribute_values.iteritems():
            for guid, attribute_values in testbed_attribute_values.iteritems():
                for attribute, value in attribute_values.iteritems():
                    value = _undefer(value)
                    if value is not None:
                        execute_data.add_attribute_data(guid, attribute, value)
        
        self._experiment_execute_xml = parser.to_xml(data=execute_data)

    def stop(self):
       for testbed in self._testbeds.values():
           testbed.stop()
       self._unpersist_testbed_proxies()
       self._stopped_time = time.time() 
   
    def recover(self):
        # reload perviously persisted testbed access configurations
        self._failed_testbeds.clear()
        self._load_testbed_proxies()

        # re-program testbeds that need recovery
        self._start(recover = True)

    def is_finished(self, guid):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.status(guid) == AS.STATUS_FINISHED
        raise RuntimeError("No element exists with guid %d" % guid)    
    
    def _testbed_recovery_policy(self, guid, data = None):
        if data is None:
            parser = XmlExperimentParser()
            data = parser.from_xml_to_data(self._experiment_design_xml)
        
        return data.get_attribute_data(guid, DC.RECOVERY_POLICY)

    def status(self, guid):
        if guid in self._testbeds:
            # guid is a testbed
            # report testbed status
            if guid in self._failed_testbeds:
                return TS.STATUS_FAILED
            else:
                try:
                    return self._testbeds[guid].status()
                except:
                    return TS.STATUS_UNRESPONSIVE
        else:
            # guid is an element
            testbed = self._testbed_for_guid(guid)
            if testbed is not None:
                return testbed.status(guid)
            else:
                return AS.STATUS_UNDETERMINED

    def set(self, guid, name, value, time = TIME_NOW):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            testbed.set(guid, name, value, time)
        else:
            raise RuntimeError("No element exists with guid %d" % guid)    

    def get(self, guid, name, time = TIME_NOW):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.get(guid, name, time)
        raise RuntimeError("No element exists with guid %d" % guid)    

    def get_deferred(self, guid, name, time = TIME_NOW):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.get_deferred(guid, name, time)
        raise RuntimeError("No element exists with guid %d" % guid)    

    def get_factory_id(self, guid):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.get_factory_id(guid)
        raise RuntimeError("No element exists with guid %d" % guid)    

    def get_testbed_id(self, guid):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.testbed_id
        raise RuntimeError("No element exists with guid %d" % guid)    

    def get_testbed_version(self, guid):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.testbed_version
        raise RuntimeError("No element exists with guid %d" % guid)    

    def shutdown(self):
        exceptions = list()
        ordered_testbeds = set()

        def shutdown_testbed(guid):
            try:
                testbed = self._testbeds[guid]
                ordered_testbeds.add(guid)
                testbed.shutdown()
            except:
                exceptions.append(sys.exc_info())
                
        self._logger.debug("ExperimentController: Starting parallel shutdown")
        
        for testbed_guids in reversed(self._testbed_order):
            testbed_guids = set(testbed_guids) - ordered_testbeds
            self._logger.debug("ExperimentController: Shutting down %r", testbed_guids)
            self._parallel([functools.partial(shutdown_testbed, guid)
                            for guid in testbed_guids])
        remaining_guids = set(self._testbeds) - ordered_testbeds
        if remaining_guids:
            self._logger.debug("ExperimentController: Shutted down %r", ordered_testbeds)
            self._logger.debug("ExperimentController: Shutting down %r", remaining_guids)
            self._parallel([functools.partial(shutdown_testbed, guid)
                            for guid in remaining_guids])
            
        for exc_info in exceptions:
            raise exc_info[0], exc_info[1], exc_info[2]

    def _testbed_for_guid(self, guid):
        for testbed_guid in self._testbeds.keys():
            if guid in self._guids_in_testbed(testbed_guid):
                if testbed_guid in self._failed_testbeds:
                    return None
                return self._testbeds[testbed_guid]
        return None

    def _guids_in_testbed(self, testbed_guid):
        if testbed_guid not in self._testbeds:
            return set()
        if testbed_guid not in self._guids_in_testbed_cache:
            self._guids_in_testbed_cache[testbed_guid] = \
                set(self._testbeds[testbed_guid].guids)
        return self._guids_in_testbed_cache[testbed_guid]

    @staticmethod
    def _netref_component_split(component):
        match = COMPONENT_PATTERN.match(component)
        if match:
            return match.group("kind"), match.group("index")
        else:
            return component, None

    _NETREF_COMPONENT_GETTERS = {
        'addr':
            lambda testbed, guid, index, name: 
                testbed.get_address(guid, int(index), name),
        'route' :
            lambda testbed, guid, index, name: 
                testbed.get_route(guid, int(index), name),
        'trace' :
            lambda testbed, guid, index, name: 
                testbed.trace(guid, index, attribute = name),
        '' : 
            lambda testbed, guid, index, name: 
                testbed.get(guid, name),
    }
    
    def resolve_netref_value(self, value, failval = None):
        rv = failval
        while True:
            for match in ATTRIBUTE_PATTERN_BASE.finditer(value):
                label = match.group("label")
                if label.startswith('GUID-'):
                    ref_guid = int(label[5:])
                    if ref_guid:
                        expr = match.group("expr")
                        component = (match.group("component") or "")[1:] # skip the dot
                        attribute = match.group("attribute")
                        
                        # split compound components into component kind and index
                        # eg: 'addr[0]' -> ('addr', '0')
                        component, component_index = self._netref_component_split(component)

                        # find object and resolve expression
                        for ref_testbed_guid, ref_testbed in self._testbeds.iteritems():
                            if component not in self._NETREF_COMPONENT_GETTERS:
                                raise ValueError, "Malformed netref: %r - unknown component" % (expr,)
                            elif ref_guid not in self._guids_in_testbed(ref_testbed_guid):
                                pass
                            else:
                                ref_value = self._NETREF_COMPONENT_GETTERS[component](
                                    ref_testbed, ref_guid, component_index, attribute)
                                if ref_value:
                                    value = rv = value.replace(match.group(), ref_value)
                                    break
                        else:
                            # unresolvable netref
                            return failval
                        break
            else:
                break
        return rv
    
    def do_netrefs(self, data, fail_if_undefined = False):
        # element netrefs
        for (testbed_guid, guid), attrs in self._netrefs.items():
            testbed = self._testbeds.get(testbed_guid)
            if testbed is not None:
                for name in set(attrs):
                    value = testbed.get(guid, name)
                    if isinstance(value, basestring):
                        ref_value = self.resolve_netref_value(value)
                        if ref_value is not None:
                            testbed.set(guid, name, ref_value)
                            attrs.remove(name)
                        elif fail_if_undefined:
                            raise ValueError, "Unresolvable netref in: %r=%r" % (name,value,)
                if not attrs:
                    del self._netrefs[(testbed_guid, guid)]
        
        # testbed netrefs
        for testbed_guid, attrs in self._testbed_netrefs.items():
            tb_data = dict(data.get_attribute_data(testbed_guid))
            if data:
                for name in set(attrs):
                    value = tb_data.get(name)
                    if isinstance(value, basestring):
                        ref_value = self.resolve_netref_value(value)
                        if ref_value is not None:
                            data.set_attribute_data(testbed_guid, name, ref_value)
                            attrs.remove(name)
                        elif fail_if_undefined:
                            raise ValueError, "Unresolvable netref in: %r" % (value,)
                if not attrs:
                    del self._testbed_netrefs[testbed_guid]
        

    def _init_testbed_controllers(self, data, recover = False):
        blacklist_testbeds = set(self._testbeds)
        element_guids = list()
        label_guids = dict()
        data_guids = data.guids
        to_recover = set()
        to_restart = set()

        # gather label associations
        for guid in data_guids:
            if not data.is_testbed_data(guid):
                (testbed_guid, factory_id) = data.get_box_data(guid)
                label = data.get_attribute_data(guid, "label")
                if label is not None:
                    if label in label_guids:
                        raise RuntimeError, "Label %r is not unique" % (label,)
                    label_guids[label] = guid

        # create testbed controllers
        for guid in data_guids:
            if data.is_testbed_data(guid):
                if guid not in self._testbeds:
                    try:
                        self._create_testbed_controller(
                            guid, data, element_guids, recover)
                        if recover:
                            # Already programmed
                            blacklist_testbeds.add(guid)
                        else:
                            to_restart.add(guid)
                    except:
                        if recover:
                            policy = self._testbed_recovery_policy(guid, data=data)
                            if policy == DC.POLICY_RECOVER:
                                self._create_testbed_controller(
                                    guid, data, element_guids, False)
                                to_recover.add(guid)
                            elif policy == DC.POLICY_RESTART:
                                self._create_testbed_controller(
                                    guid, data, element_guids, False)
                                to_restart.add(guid)
                            else:
                                # Mark failed
                                self._failed_testbeds.add(guid)
                        else:
                            raise
        
        # queue programmable elements
        #  - that have not been programmed already (blacklist_testbeds)
        #  - including recovered or restarted testbeds
        #  - but those that have no unresolved netrefs
        for guid in data_guids:
            if not data.is_testbed_data(guid):
                (testbed_guid, factory_id) = data.get_box_data(guid)
                if testbed_guid not in blacklist_testbeds:
                    element_guids.append(guid)

        # replace references to elements labels for its guid
        self._resolve_labels(data, data_guids, label_guids)
    
        # program testbed controllers
        if element_guids:
            self._program_testbed_controllers(element_guids, data)
        
        return to_recover, to_restart

    def _resolve_labels(self, data, data_guids, label_guids):
        netrefs = self._netrefs
        testbed_netrefs = self._testbed_netrefs
        for guid in data_guids:
            for name, value in data.get_attribute_data(guid):
                if isinstance(value, basestring):
                    while True:
                        for match in ATTRIBUTE_PATTERN_BASE.finditer(value):
                            label = match.group("label")
                            if not label.startswith('GUID-'):
                                ref_guid = label_guids.get(label)
                                if ref_guid is not None:
                                    value = value.replace(
                                        match.group(),
                                        ATTRIBUTE_PATTERN_GUID_SUB % dict(
                                            guid = 'GUID-%d' % (ref_guid,),
                                            expr = match.group("expr"),
                                            label = label)
                                    )
                                    data.set_attribute_data(guid, name, value)
                                    
                                    # memorize which guid-attribute pairs require
                                    # postprocessing, to avoid excessive controller-testbed
                                    # communication at configuration time
                                    # (which could require high-latency network I/O)
                                    if not data.is_testbed_data(guid):
                                        (testbed_guid, factory_id) = data.get_box_data(guid)
                                        netrefs[(testbed_guid, guid)].add(name)
                                    else:
                                        testbed_netrefs[guid].add(name)
                                    
                                    break
                        else:
                            break

    def _create_testbed_controller(self, guid, data, element_guids, recover):
        (testbed_id, testbed_version) = data.get_testbed_data(guid)
        deployment_config = self._deployment_config.get(guid)
        
        # deferred import because proxy needs
        # our class definitions to define proxies
        import nepi.util.proxy as proxy
        
        if deployment_config is None:
            # need to create one
            deployment_config = proxy.AccessConfiguration()
            
            for (name, value) in data.get_attribute_data(guid):
                if value is not None and deployment_config.has_attribute(name):
                    # if any deployment config attribute has a netref, we can't
                    # create this controller yet
                    if isinstance(value, basestring) and ATTRIBUTE_PATTERN_BASE.search(value):
                        # remember to re-issue this one
                        self._netreffed_testbeds.add(guid)
                        return
                    
                    # copy deployment config attribute
                    deployment_config.set_attribute_value(name, value)
            
            # commit config
            self._deployment_config[guid] = deployment_config
        
        if deployment_config is not None:
            # force recovery mode 
            deployment_config.set_attribute_value("recover",recover)
        
        testbed = proxy.create_testbed_controller(testbed_id, testbed_version,
                deployment_config)
        for (name, value) in data.get_attribute_data(guid):
            testbed.defer_configure(name, value)
        self._testbeds[guid] = testbed
        if guid in self._netreffed_testbeds:
            self._netreffed_testbeds.remove(guid)

    def _program_testbed_controllers(self, element_guids, data):
        def resolve_create_netref(data, guid, name, value): 
            # Try to resolve create-time netrefs, if possible
            if isinstance(value, basestring) and ATTRIBUTE_PATTERN_BASE.search(value):
                try:
                    nuvalue = self.resolve_netref_value(value)
                except:
                    # Any trouble means we're not in shape to resolve the netref yet
                    nuvalue = None
                if nuvalue is not None:
                    # Only if we succeed we remove the netref deferral entry
                    value = nuvalue
                    data.set_attribute_data(guid, name, value)
                    if (testbed_guid, guid) in self._netrefs:
                        self._netrefs[(testbed_guid, guid)].discard(name)
            return value

        for guid in element_guids:
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds.get(testbed_guid)
            if testbed is not None:
                # create
                testbed.defer_create(guid, factory_id)
                # set attributes
                for (name, value) in data.get_attribute_data(guid):
                    value = resolve_create_netref(data, guid, name, value)
                    testbed.defer_create_set(guid, name, value)

        for guid in element_guids:
            (testbed_guid, factory_id) = data.get_box_data(guid)
            testbed = self._testbeds.get(testbed_guid)
            if testbed is not None:
                # traces
                for trace_id in data.get_trace_data(guid):
                    testbed.defer_add_trace(guid, trace_id)
                # addresses
                for (address, netprefix, broadcast) in data.get_address_data(guid):
                    if address != None:
                        testbed.defer_add_address(guid, address, netprefix, 
                                broadcast)
                # routes
                for (destination, netprefix, nexthop, metric) in data.get_route_data(guid):
                    testbed.defer_add_route(guid, destination, netprefix, nexthop, metric)
                # store connections data
                for (connector_type_name, other_guid, other_connector_type_name) \
                        in data.get_connection_data(guid):
                    (other_testbed_guid, other_factory_id) = data.get_box_data(
                            other_guid)
                    if testbed_guid == other_testbed_guid:
                        # each testbed should take care of enforcing internal
                        # connection simmetry, so each connection is only
                        # added in one direction
                        testbed.defer_connect(guid, connector_type_name, 
                                other_guid, other_connector_type_name)

    def _program_testbed_cross_connections(self, data):
        data_guids = data.guids
        for guid in data_guids: 
            if not data.is_testbed_data(guid):
                (testbed_guid, factory_id) = data.get_box_data(guid)
                testbed = self._testbeds.get(testbed_guid)
                if testbed is not None:
                    for (connector_type_name, cross_guid, cross_connector_type_name) \
                            in data.get_connection_data(guid):
                        (testbed_guid, factory_id) = data.get_box_data(guid)
                        (cross_testbed_guid, cross_factory_id) = data.get_box_data(
                                cross_guid)
                        if testbed_guid != cross_testbed_guid:
                            cross_testbed = self._testbeds[cross_testbed_guid]
                            cross_testbed_id = cross_testbed.testbed_id
                            testbed.defer_cross_connect(guid, connector_type_name, cross_guid, 
                                    cross_testbed_guid, cross_testbed_id, cross_factory_id, 
                                    cross_connector_type_name)
                            # save cross data for later
                            self._logger.debug("ExperimentController: adding cross_connection data tbd=%d:guid=%d - tbd=%d:guid=%d" % \
                                    (testbed_guid, guid, cross_testbed_guid, cross_guid))
                            self._add_crossdata(testbed_guid, guid, cross_testbed_guid,
                                    cross_guid)

    def _add_crossdata(self, testbed_guid, guid, cross_testbed_guid, cross_guid):
        if testbed_guid not in self._cross_data:
            self._cross_data[testbed_guid] = dict()
        if cross_testbed_guid not in self._cross_data[testbed_guid]:
            self._cross_data[testbed_guid][cross_testbed_guid] = set()
        self._cross_data[testbed_guid][cross_testbed_guid].add(cross_guid)

    def _get_cross_data(self, testbed_guid):
        cross_data = dict()
        if not testbed_guid in self._cross_data:
            return cross_data

        # fetch attribute lists in one batch
        attribute_lists = dict()
        for cross_testbed_guid, guid_list in \
                self._cross_data[testbed_guid].iteritems():
            cross_testbed = self._testbeds[cross_testbed_guid]
            for cross_guid in guid_list:
                attribute_lists[(cross_testbed_guid, cross_guid)] = \
                    cross_testbed.get_attribute_list_deferred(cross_guid)

        # fetch attribute values in another batch
        for cross_testbed_guid, guid_list in \
                self._cross_data[testbed_guid].iteritems():
            cross_data[cross_testbed_guid] = dict()
            cross_testbed = self._testbeds[cross_testbed_guid]
            for cross_guid in guid_list:
                elem_cross_data = dict(
                    _guid = cross_guid,
                    _testbed_guid = cross_testbed_guid,
                    _testbed_id = cross_testbed.testbed_id,
                    _testbed_version = cross_testbed.testbed_version)
                cross_data[cross_testbed_guid][cross_guid] = elem_cross_data
                attribute_list = attribute_lists[(cross_testbed_guid,cross_guid)]
                for attr_name in attribute_list:
                    attr_value = cross_testbed.get_deferred(cross_guid, attr_name)
                    elem_cross_data[attr_name] = attr_value
        
        # undefer all values - we'll have to serialize them probably later
        for cross_testbed_guid, testbed_cross_data in cross_data.iteritems():
            for cross_guid, elem_cross_data in testbed_cross_data.iteritems():
                for attr_name, attr_value in elem_cross_data.iteritems():
                    elem_cross_data[attr_name] = _undefer(attr_value)
        
        return cross_data

class ExperimentSuite(object):
    def __init__(self, experiment_xml, access_config, repetitions = None,
            duration = None, wait_guids = None):
        self._experiment_xml = experiment_xml
        self._access_config = access_config
        self._controllers = dict()
        self._access_configs = dict()
        self._repetitions = 1 if not repetitions else repetitions
        self._duration = duration
        self._wait_guids = wait_guids
        self._current = None
        self._status = TS.STATUS_ZERO
        self._thread = None

    @property
    def current(self):
        return self._current

    @property
    def status(self):
        return self._status

    @property
    def is_finished(self):
        return self._status == TS.STATUS_STOPPED

    @property
    def access_configurations(self):
        return self._access_configs.values()

    def start(self):
        self._status  = TS.STATUS_STARTED
        self._thread = threading.Thread(target = self._run_experiment_suite)
        self._thread.start()

    def shutdown(self):
        if self._thread:
            self._thread.join()
            self._thread = None
        for controller in self._controllers.values():
            controller.shutdown()

    def get_current_access_config(self):
        return self._access_configs[self._current]

    def _run_experiment_suite(self):
        for i in xrange[0, self.repetitions]:
            self._current = i
            self._run_one_experiment()
        self._status  = TS.STATUS_STOPPED

    def _run_one_experiment(self):
        access_config = proxy.AccessConfiguration()
        for attr in self._access_config.attributes:
            access_config.set_attribute_value(attr.name, attr.value)
        access_config.set_attribute_value(DC.DEPLOYMENT_MODE, DC.MODE_DAEMON)
        root_dir = "%s_%d" % (
                access_config.get_attribute_value(DC.ROOT_DIRECTORY), 
                self._current)
        access_config.set_attribute_value(DC.ROOT_DIRECTORY, root_dir)
        controller = proxy.create_experiment_controller(self._experiment_xml,
                access_config)
        self._access_configs[self._current] = access_config
        self._controllers[self._current] = controller
        controller.start()
        started_at = time.time()
        # wait until all specified guids have finished execution
        if self._wait_guids:
            while all(itertools.imap(controller.is_finished, self._wait_guids)):
                time.sleep(0.5)
        # wait until the minimum experiment duration time has elapsed 
        if self._duration:
            while (time.time() - started_at) < self._duration:
                time.sleep(0.5)
        controller.stop()

