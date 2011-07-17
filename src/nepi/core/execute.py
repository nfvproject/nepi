#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import Attribute, AttributesMap
from nepi.util import validation
from nepi.util.constants import ApplicationStatus as AS, TIME_NOW
from nepi.util.parser._xml import XmlExperimentParser
import sys
import re
import threading
import ConfigParser
import os
import collections
import functools

ATTRIBUTE_PATTERN_BASE = re.compile(r"\{#\[(?P<label>[-a-zA-Z0-9._]*)\](?P<expr>(?P<component>\.addr\[[0-9]+\]|\.route\[[0-9]+\]|\.trace\[[0-9]+\])?.\[(?P<attribute>[-a-zA-Z0-9._]*)\])#}")
ATTRIBUTE_PATTERN_GUID_SUB = r"{#[%(guid)s]%(expr)s#}"
COMPONENT_PATTERN = re.compile(r"(?P<kind>[a-z]*)\[(?P<index>.*)\]")

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

        self.persist_experiment_xml()

    @property
    def experiment_design_xml(self):
        return self._experiment_design_xml

    @property
    def experiment_execute_xml(self):
        return self._experiment_execute_xml

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
            @functools.wraps(callable)
            def wrapped(*p, **kw):
                try:
                    callable(*p, **kw)
                except:
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    excs.append(sys.exc_info())
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
        parser = XmlExperimentParser()
        data = parser.from_xml_to_data(self._experiment_design_xml)

        # instantiate testbed controllers
        self._init_testbed_controllers(data)
        
        # persist testbed connection data, for potential recovery
        self._persist_testbed_proxies()
        
        def steps_to_configure(self, allowed_guids):
            # perform setup in parallel for all test beds,
            # wait for all threads to finish
            self._parallel([testbed.do_setup 
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])
       
            # perform create-connect in parallel, wait
            # (internal connections only)
            self._parallel([testbed.do_create
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._parallel([testbed.do_connect_init
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._parallel([testbed.do_connect_compl
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])

            self._parallel([testbed.do_preconfigure
                            for guid,testbed in self._testbeds.iteritems()
                            if guid in allowed_guids])
            self._clear_caches()

        steps_to_configure(self, self._testbeds)

        if self._netreffed_testbeds:
            # initally resolve netrefs
            self.do_netrefs(data, fail_if_undefined=False)
            
            # rinse and repeat, for netreffed testbeds
            netreffed_testbeds = set(self._netreffed_testbeds)

            self._init_testbed_controllers(data)
            
            # persist testbed connection data, for potential recovery
            self._persist_testbed_proxies()

            # configure dependant testbeds
            steps_to_configure(self, netreffed_testbeds)
            
        # final netref step, fail if anything's left unresolved
        self.do_netrefs(data, fail_if_undefined=True)
        
        # perform do_configure in parallel for al testbeds
        # (it's internal configuration for each)
        self._parallel([testbed.do_configure
                        for testbed in self._testbeds.itervalues()])

        self._clear_caches()

        #print >>sys.stderr, "DO IT"
        #import time
        #time.sleep(60)
        
        # cross-connect (cannot be done in parallel)
        for guid, testbed in self._testbeds.iteritems():
            cross_data = self._get_cross_data(guid)
            testbed.do_cross_connect_init(cross_data)
        for guid, testbed in self._testbeds.iteritems():
            cross_data = self._get_cross_data(guid)
            testbed.do_cross_connect_compl(cross_data)
       
        self._clear_caches()

        # Last chance to configure (parallel on all testbeds)
        self._parallel([testbed.do_prestart
                        for testbed in self._testbeds.itervalues()])

        self._clear_caches()
        
        # update execution xml with execution-specific values
        self._update_execute_xml()
        self.persist_execute_xml()

        # start experiment (parallel start on all testbeds)
        self._parallel([testbed.start
                        for testbed in self._testbeds.itervalues()])

        self._clear_caches()

    def _clear_caches(self):
        # Cleaning cache for safety.
        self._guids_in_testbed_cache = dict()

    def _persist_testbed_proxies(self):
        TRANSIENT = ('Recover',)
        
        # persist access configuration for all testbeds, so that
        # recovery mode can reconnect to them if it becomes necessary
        conf = ConfigParser.RawConfigParser()
        for testbed_guid, testbed_config in self._deployment_config.iteritems():
            testbed_guid = str(testbed_guid)
            conf.add_section(testbed_guid)
            for attr in testbed_config.get_attribute_list():
                if attr not in TRANSIENT:
                    conf.set(testbed_guid, attr, 
                        testbed_config.get_attribute_value(attr))
        
        f = open(os.path.join(self._root_dir, 'deployment_config.ini'), 'w')
        conf.write(f)
        f.close()
    
    def _load_testbed_proxies(self):
        TYPEMAP = {
            STRING : 'get',
            INTEGER : 'getint',
            FLOAT : 'getfloat',
            BOOLEAN : 'getboolean',
        }
        
        # deferred import because proxy needs
        # our class definitions to define proxies
        import nepi.util.proxy as proxy
        
        conf = ConfigParser.RawConfigParser()
        conf.read(os.path.join(self._root_dir, 'deployment_config.ini'))
        for testbed_guid in conf.sections():
            testbed_config = proxy.AccessConfiguration()
            for attr in conf.options(testbed_guid):
                testbed_config.set_attribute_value(attr, 
                    conf.get(testbed_guid, attr) )
                
            testbed_guid = str(testbed_guid)
            conf.add_section(testbed_guid)
            for attr in testbed_config.get_attribute_list():
                if attr not in TRANSIENT:
                    getter = getattr(conf, TYPEMAP.get(
                        testbed_config.get_attribute_type(attr),
                        'get') )
                    testbed_config.set_attribute_value(
                        testbed_guid, attr, getter(attr))
    
    def _unpersist_testbed_proxies(self):
        try:
            os.remove(os.path.join(self._root_dir, 'deployment_config.ini'))
        except:
            # Just print exceptions, this is just cleanup
            import traceback
            ######## BUG ##########
            #BUG: If the next line is uncomented pyQt explodes when shutting down the experiment !!!!!!!!
            #traceback.print_exc(file=sys.stderr)

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

        def undefer(deferred):
            if hasattr(deferred, '_get'):
                return deferred._get()
            else:
                return deferred
        
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
                attribute_list = undefer(attribute_list)
                attribute_values[testbed_guid][guid] = dict(
                    (attribute, testbed.get_deferred(guid, attribute))
                    for attribute in attribute_list
                )
        
        for testbed_guid, testbed_attribute_values in attribute_values.iteritems():
            for guid, attribute_values in testbed_attribute_values.iteritems():
                for attribute, value in attribute_values.iteritems():
                    value = undefer(value)
                    if value is not None:
                        execute_data.add_attribute_data(guid, attribute, value)
        
        self._experiment_execute_xml = parser.to_xml(data=execute_data)

    def stop(self):
       for testbed in self._testbeds.values():
           testbed.stop()
       self._unpersist_testbed_proxies()
   
    def recover(self):
        # reload perviously persisted testbed access configurations
        self._load_testbed_proxies()
        
        # recreate testbed proxies by reconnecting only
        self._init_testbed_controllers(recover = True)
        
        # another time, for netrefs
        self._init_testbed_controllers(recover = True)

    def is_finished(self, guid):
        testbed = self._testbed_for_guid(guid)
        if testbed != None:
            return testbed.status(guid) == AS.STATUS_FINISHED
        raise RuntimeError("No element exists with guid %d" % guid)    

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
        for testbed in self._testbeds.values():
            try:
                testbed.shutdown()
            except:
                exceptions.append(sys.exc_info())
        for exc_info in exceptions:
            raise exc_info[0], exc_info[1], exc_info[2]

    def _testbed_for_guid(self, guid):
        for testbed_guid in self._testbeds.keys():
            if guid in self._guids_in_testbed(testbed_guid):
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
                testbed.trace(guid, index, name),
        '' : 
            lambda testbed, guid, index, name: 
                testbed.get(guid, name),
    }
    
    def resolve_netref_value(self, value, failval = None):
        match = ATTRIBUTE_PATTERN_BASE.search(value)
        if match:
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
                                return value.replace(match.group(), ref_value)
        # couldn't find value
        return failval
    
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

        # create testbed controllers
        for guid in data_guids:
            if data.is_testbed_data(guid):
                if guid not in self._testbeds:
                    self._create_testbed_controller(guid, data, element_guids,
                            recover)
            else:
                (testbed_guid, factory_id) = data.get_box_data(guid)
                if testbed_guid not in blacklist_testbeds:
                    element_guids.append(guid)
                    label = data.get_attribute_data(guid, "label")
                    if label is not None:
                        if label in label_guids:
                            raise RuntimeError, "Label %r is not unique" % (label,)
                        label_guids[label] = guid

        # replace references to elements labels for its guid
        self._resolve_labels(data, data_guids, label_guids)
    
        # program testbed controllers
        if not recover:
            self._program_testbed_controllers(element_guids, data)

    def _resolve_labels(self, data, data_guids, label_guids):
        netrefs = self._netrefs
        testbed_netrefs = self._testbed_netrefs
        for guid in data_guids:
            for name, value in data.get_attribute_data(guid):
                if isinstance(value, basestring):
                    match = ATTRIBUTE_PATTERN_BASE.search(value)
                    if match:
                        label = match.group("label")
                        if not label.startswith('GUID-'):
                            ref_guid = label_guids.get(label)
                            if ref_guid is not None:
                                value = ATTRIBUTE_PATTERN_BASE.sub(
                                    ATTRIBUTE_PATTERN_GUID_SUB % dict(
                                        guid = 'GUID-%d' % (ref_guid,),
                                        expr = match.group("expr"),
                                        label = label), 
                                    value)
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
        deferred = dict()

        def add_deferred_testbed(deferred, testbed_guid):
            if not testbed_guid in deferred:
                deferred[testbed_guid] = dict()
                deferred[testbed_guid]["connections"] = set()
                deferred[testbed_guid]["cross_connections"] = set()

        def add_deferred_connection(deferred, data, guid, connector_type_name,
                other_guid, other_connector_type_name):

            (testbed_guid, factory_id) = data.get_box_data(guid)
            (other_testbed_guid, other_factory_id) = data.get_box_data(
                    other_guid)
            testbed = self._testbeds[testbed_guid]
            testbed_id = testbed.testbed_id
            add_deferred_testbed(deferred, testbed_guid)

            if testbed_guid == other_testbed_guid:
                # each testbed should take care of enforcing internal
                # connection simmetry, so each connection is only
                # added in one direction
                c = (guid, connector_type_name, other_guid,
                        other_connector_type_name)
                deferred[testbed_guid]["connections"].add(c)
            else:
                # the controller takes care of cross_connection simmetry
                # so cross_connections are added in both directions
                other_testbed = self._testbeds[other_testbed_guid]
                other_testbed_id = other_testbed.testbed_id
                add_deferred_testbed(deferred, other_testbed_guid)
                c1 = (testbed_guid, testbed_id, guid, factory_id,
                        connector_type_name, other_testbed_guid,
                        other_testbed_id, other_guid, other_factory_id,
                        other_connector_type_name)
                c2 = (other_testbed_guid, other_testbed_id, other_guid, 
                        other_factory_id, other_connector_type_name,
                        testbed_guid, testbed_id, guid, factory_id,
                        connector_type_name)
                deferred[testbed_guid]["cross_connections"].add(c1)
                deferred[other_testbed_guid]["cross_connections"].add(c2)

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
            # create
            testbed.defer_create(guid, factory_id)
            # set attributes
            for (name, value) in data.get_attribute_data(guid):
                value = resolve_create_netref(data, guid, name, value)
                testbed.defer_create_set(guid, name, value)
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
                add_deferred_connection(deferred, data, guid,
                        connector_type_name, other_guid,
                        other_connector_type_name)

        # connections        
        for testbed_guid, data in deferred.iteritems():
            testbed = self._testbeds.get(testbed_guid)
            for (guid, connector_type_name, other_guid,
                    other_connector_type_name) in data["connections"]:
                testbed.defer_connect(guid, connector_type_name, 
                        other_guid, other_connector_type_name)
            for (testbed_guid, testbed_id, guid, factory_id,
                        connector_type_name, other_testbed_guid,
                        other_testbed_id, other_guid, other_factory_id,
                        other_connector_type_name) in data["cross_connections"]:
                testbed.defer_cross_connect(guid, connector_type_name, other_guid, 
                        other_testbed_guid, other_testbed_id, other_factory_id, 
                        other_connector_type_name)
                # save cross data for later
                self._add_crossdata(testbed_guid, guid, other_testbed_guid,
                        other_guid)

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
                attribute_list = cross_testbed.get_attribute_list(cross_guid)
                for attr_name in attribute_list:
                    attr_value = cross_testbed.get_deferred(cross_guid, attr_name)
                    elem_cross_data[attr_name] = attr_value
        return cross_data
    
