# -*- coding: utf-8 -*-

from constants import TESTBED_ID, TESTBED_VERSION
from nepi.core import testbed_impl
from nepi.util.constants import TIME_NOW

from nepi.testbeds.omf.omf_api import OmfAPI

import logging
import os
import time

class TestbedController(testbed_impl.TestbedController):
    def __init__(self):
        super(TestbedController, self).__init__(TESTBED_ID, TESTBED_VERSION)
        self._home = None
        self._api = None
        self._logger = logging.getLogger('nepi.testbeds.omf')
 
    def do_setup(self):
        debug = self._attributes.get_attribute_value("enableDebug")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # create home
        self._home = self._attributes.get_attribute_value("homeDirectory")
        home = os.path.normpath(self._home)
        if not os.path.exists(home):
            os.makedirs(home, 0755)

        # initialize OMF xmpp client
        slice = self._attributes.get_attribute_value("xmppSlice")
        host = self._attributes.get_attribute_value("xmppHost")
        port = self._attributes.get_attribute_value("xmppPort")
        password = self._attributes.get_attribute_value("xmppPassword")

        self._api = OmfAPI(slice, host, port, password)
 
        super(TestbedController, self).do_setup()

    @property
    def api(self):
        return self._api

    def set(self, guid, name, value, time = TIME_NOW):
        super(TestbedController, self).set(guid, name, value, time)
        element = self._elements[guid]
        if element:
            try:
                setattr(element, name, value)
            except:
                # We ignore these errors while recovering.
                # Some attributes are immutable, and setting
                # them is necessary (to recover the state), but
                # some are not (they throw an exception).
                if not self.recovering:
                    raise

    def get(self, guid, name, time = TIME_NOW):
        value = super(TestbedController, self).get(guid, name, time)
        element = self._elements.get(guid)
        try:
            return getattr(element, name)
        except (KeyError, AttributeError):
            return value

    def shutdown(self):
        if self.api: 
            self.api.disconnect()

