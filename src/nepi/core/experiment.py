#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.util.guid import GuidGenerator 
import sys

class ExperimentDescription(object):
    def __init__(self, guid = 0):
        self._guid_generator = GuidGenerator(guid)
        # testbed design instances
        self._testbed_descriptions = dict()
        self._testbed_providers = dict()

    @property
    def xml_description(self):
        raise NotImplementedError

    def add_testbed_description(self, testbed_id, testbed_version):
        testbed_module = self._testbed_module(testbed_id)
        testbed_provider = self._testbed_provider(testbed_id, testbed_version)
        testbed_description = testbed_module.create_description_instance(
                self._guid_generator, testbed_version, testbed_provider)
        guid = testbed_description.guid
        self._testbed_descriptions[guid] = testbed_description
        return testbed_description

    def remove_testbed_description(self, testbed_description):
        guid = testbed_description.guid
        del self._testbed_descriptions[guid]

    def _testbed_module(self, testbed_id):
        mod_name = 'nepi.testbeds.%s' % testbed_id
        if not mod_name in sys.modules:
            __import__(mod_name)
        return sys.modules[mod_name]

    def _testbed_provider(self, testbed_id, testbed_version):
        key = "%s_%s" % (testbed_id, testbed_version)
        if key not in self._testbed_providers:
            testbed_module = self._testbed_module(testbed_id)
            testbed_provider = testbed_module.create_provider(testbed_version)
            self._testbed_providers[key] = testbed_provider
        return self._testbed_providers[key]

