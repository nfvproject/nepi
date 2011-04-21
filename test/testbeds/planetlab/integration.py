#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getpass
from nepi.core.design import ExperimentDescription, FactoriesProvider
from nepi.core.execute import ExperimentController
from nepi.util import proxy
import os
import shutil
import tempfile
import test_util
import time
import unittest

class NetnsIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root_dir)

if __name__ == '__main__':
    unittest.main()

