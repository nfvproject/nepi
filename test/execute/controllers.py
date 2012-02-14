#!/usr/bin/env python

from nepi.design import create_provider
from nepi.execute import create_ec, EventStatus 
import time
import unittest

class ExecuteControllersTestCase(unittest.TestCase):
    def experiment_description(self):
        provider = create_provider(modnames = ["mock"])
        exp = provider.create("Experiment", label = "exp")
        mocki = provider.create("mock::MockInstance", container = exp, 
                label = "mocki")
        
        node1 = provider.create("mock::Node", container = mocki, 
                label = "node1", boolAttr = True)
        iface1 = provider.create("mock::Interface", container = mocki, 
                label = "iface1")
        addr1 = iface1.add_address(address = "192.168.0.1")
        node1.c.devs.connect(iface1.c.node)

        node2 = provider.create("mock::Node", container = mocki,
                label = "node2", boolAttr = True)
        iface2 = provider.create("mock::Interface", container = mocki, 
                label = "iface2")
        addr2 = iface2.add_address(address = "192.168.0.2")
        node2.c.devs.connect(iface2.c.node)

        iface1.c.peer.connect(iface2.c.peer)

        trace = provider.create("mock::Trace", container = mocki,
                label = "trace", stringAttr = "lala")
        node1.c.traces.connect(trace.c.node)

        app = provider.create("mock::Application", container = mocki,
                label = "app", start = "10s")
        app.c.node.connect(node1.c.apps)

        return exp

    def test_schedule_poll_cancel(self):
        exp = self.experiment_description()
        xml = exp.xml

        ec = create_ec(xml)
        ec.run(modnames = ["mock"])

        try:
            node1 = exp.box("node1")

            # shcedule now
            eid = ec.get(node1.guid, "boolAttr")
            while ec.poll(eid) == EventStatus.PENDING:
                time.sleep(0.01)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            result = ec.result(eid)
            removed = ec.remove(eid)
            self.assertTrue(removed == True)
            status = ec.poll(eid)
            # After getting the result back, the event should have been eraised
            # and status should be None
            self.assertTrue(status == None)

            # schedule for delay 1s
            eid = ec.get(node1.guid, "boolAttr", date = "1s")
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.PENDING)
            time.sleep(1.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)

            # schedule and cancel
            eid = ec.get(node1.guid, "boolAttr", date = "3s")
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.PENDING)
            time.sleep(1)
            removed = ec.cancel(eid)
            self.assertTrue(removed == True)
            status = ec.poll(eid)
            self.assertTrue(status == None)

        except:
            pass

        ec.shutdown()

if __name__ == '__main__':
    unittest.main()

