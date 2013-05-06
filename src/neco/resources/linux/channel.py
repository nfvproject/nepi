from neco.execution.attribute import Attribute, Flags
from neco.execution.resource import ResourceManager, clsinit, ResourceState
from neco.resources.linux.node import LinuxNode

import collections
import logging
import os
import random
import re
import tempfile
import time
import threading

@clsinit
class LinuxChannel(ResourceManager):
    _rtype = "LinuxChannel"

    def __init__(self, ec, guid):
        super(LinuxChannel, self).__init__(ec, guid)
        self._logger = logging.getLogger("LinuxChannel")

    def log_message(self, msg):
        return " guid %d - %s " % (self.guid, msg)

    def valid_connection(self, guid):
        # TODO: Validate!
        return True
