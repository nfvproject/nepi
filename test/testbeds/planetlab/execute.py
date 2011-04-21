#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.util.constants import STATUS_FINISHED
from nepi.testbeds import netns
import os
import shutil
import tempfile
import test_util
import time
import unittest

class NetnsExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

