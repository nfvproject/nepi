#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core import metadata

class VersionedMetadataInfo(metadata.VersionedMetadataInfo):
    @property
    def connector_types(self):
        from connection_metadata_v3_9 import connector_types
        return connector_types

    @property
    def connections(self):
        from connection_metadata_v3_9 import connections
        return connections

    @property
    def attributes(self):
        from attributes_metadata_v3_9 import attributes
        return attributes

    @property
    def traces(self):
        from traces_metadata_v3_9 import traces
        return traces

    @property
    def create_order(self):
        from factories_metadata_v3_9 import factories_order
        return factories_order

    @property
    def configure_order(self):
        from factories_metadata_v3_9 import factories_order
        return factories_order

    @property
    def factories_info(self):
        from factories_metadata_v3_9 import factories_info
        return factories_info

    @property
    def testbed_attributes(self):
        from attributes_metadata_v3_9 import testbed_attributes
        return testbed_attributes

