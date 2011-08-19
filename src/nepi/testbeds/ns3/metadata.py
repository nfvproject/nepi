#!/usr/bin/env python
# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import metadata
from nepi.util.constants import DeploymentConfiguration as DC

supported_recovery_policies = [
        DC.POLICY_FAIL,
        DC.POLICY_RESTART,
    ]

class MetadataInfo(metadata.MetadataInfo):
    @property
    def connector_types(self):
        from connection_metadata import connector_types
        return connector_types

    @property
    def connections(self):
        from connection_metadata import connections
        return connections

    @property
    def attributes(self):
        from attributes_metadata import attributes
        return attributes

    @property
    def traces(self):
        from traces_metadata import traces
        return traces

    @property
    def create_order(self):
        from factories_metadata import factories_order
        return factories_order

    @property
    def configure_order(self):
        from factories_metadata import factories_order
        return factories_order

    @property
    def factories_info(self):
        from factories_metadata import factories_info
        return factories_info

    @property
    def testbed_attributes(self):
        from attributes_metadata import testbed_attributes
        return testbed_attributes

    @property
    def testbed_id(self):
        return TESTBED_ID

    @property
    def testbed_version(self):
        return TESTBED_VERSION

    @property
    def supported_recovery_policies(self):
        return supported_recovery_policies


