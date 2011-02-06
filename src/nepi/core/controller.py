#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4

#TODO: DEF ERRORCODES
#TODO: DEF PROTOCOL

class Testbed(object):
    def __init__(self):
        self._testbeds = dict()

    def create_testbed(self, guid, testbed_id, config, access_config = None):
        # TODO: proxy
        # guid: guid of the associated backend
        self._testbeds[guid] = testbed

    def destroy_testbed(self, guid):
        tesbed = self._testbeds[guid]
        tesbed.shutdown()
        del self._testbeds[guid]

    def forward(self, guid, instruction):
        #TODO:
        pass

    def forward_batch(self, guid, batch):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def status(self):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

