#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.decription import AF_INET
from nepi.testbeds import netns

instance = netns.TestbedInstance(None)

instance.create(2, "Node", [])
instance.create(3, "Node", [])
instance.create(4, "NodeInterface", [])
instance.create_set(4, "up", True)
instance.connect(2, "devs", 4, "node")
instance.add_adddress(4, AF_INET, "10.0.0.1", None, None)
instance.create(5, "NodeInterface", [])
instance.create_set(5, "up", True)
instance.connect(3, "devs", 5, "node")
instance.add_adddress(5, AF_INET, "10.0.0.2", None, None)
instance.create(6, "Switch", [])
instance.create_set(6, "up", True)
instance.connect(4, "switch", 6, "devs")
instance.connect(5, "switch", 6, "devs")
instance.create(7, "Application", [])
instance.create_set(7, "command", "ping -qc10 10.0.0.2")
instance.connect(7, "node", 2, "apps")

instance.do_create()
instance.do_connect()
instance.do_configure()
instance.start()
import time
time.sleep(5)
instance.stop()

