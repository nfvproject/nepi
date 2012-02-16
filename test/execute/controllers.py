#!/usr/bin/env python

from nepi.design import create_provider
from nepi.execute import create_ec, EventStatus 
import time
import unittest

def attrs(box):
    return dict((attr_name, getattr(box.a, attr_name).value) \
        for attr_name in box.attributes)

def controller_guid(box):
    return box.controller.guid if box.controller else None

def container_guid(box):
    return box.container.guid if box.container else None

def experiment_description():
    provider = create_provider(modnames = ["mock"])
    exp = provider.create("Experiment", label = "exp")
    mocki = provider.create("mock::MockInstance", container = exp, 
            label = "mocki")
    #mocki.a.logLevel.value = "Debug"
    
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


class ExecuteControllersTestCase(unittest.TestCase):
    def test_schedule_creation_order(self):
        provider = create_provider(modnames = ["mock"])
        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        node = provider.create("mock::Node", container = mocki)

        ec = create_ec("", debug = False)

        try: 
            ec.run(modnames = ["mock"])

            # validation: node can't be created before it's TC!
            create_node_eid = ec.create(node.guid, node.box_id, 
                    container_guid(node),
                    controller_guid(node),
                    node.tags, 
                    attrs(node))
            time.sleep(0.5)
            status = ec.poll(create_node_eid)
            self.assertTrue(status == EventStatus.RETRY)
            create_mock_eid = ec.create(mocki.guid, mocki.box_id, 
                    container_guid(mocki),
                    controller_guid(mocki),
                    mocki.tags, 
                    attrs(mocki))
            time.sleep(0.5)
            status = ec.poll(create_mock_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            status = ec.poll(create_node_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            
            # the pend_events list should only have two entries, even if retries where done
            self.assertEquals(len(ec._pend_events), 2)
            removed = ec.remove(create_node_eid)
            self.assertTrue(removed)
            removed = ec.remove(create_mock_eid)
            self.assertTrue(removed)
            self.assertEquals(len(ec._pend_events), 0)

        except:
            raise
        finally:
            ec.shutdown()

    def test_schedule_wait_events(self):
        exp = experiment_description()
        # get the xml experiment description
        xml = exp.xml

        ec = create_ec(xml)

        try: 
            ec.run(modnames = ["mock"])
            trace1 = exp.box("trace")

            # validation: get should be performed after set
            set_eid = ec.set(trace1.guid, "stringAttr", "new value", date = "3s")
            get_eid = ec.get(trace1.guid, "stringAttr", wait_events = [set_eid])
            status = ec.poll(get_eid)
            self.assertTrue(status == EventStatus.PENDING)
            time.sleep(2)
            status = ec.poll(get_eid)
            self.assertTrue(status == EventStatus.PENDING)
            time.sleep(1.1)
            status = ec.poll(get_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            result = ec.result(get_eid)
            self.assertEquals(result, "new value")
            removed = ec.remove(get_eid)
            self.assertTrue(removed)
            removed = ec.remove(set_eid)
            self.assertTrue(removed)
            
            # validation: wait on unexistent events should not break everything
            get_eid = ec.get(trace1.guid, "stringAttr", wait_events = [set_eid])
            while ec.poll(get_eid) in [EventStatus.RETRY, EventStatus.PENDING]:
                time.sleep(0.01)
            status = ec.poll(get_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            result = ec.result(get_eid)
            self.assertEquals(result, "new value")

        except:
            raise
        finally:
            ec.shutdown()

    def test_schedule_poll_cancel(self):
        exp = experiment_description()
        # get the xml experiment description
        xml = exp.xml

        ec = create_ec(xml)

        try: 
            ec.run(modnames = ["mock"])
            trace1 = exp.box("trace")

            # shcedule get
            eid = ec.get(trace1.guid, "stringAttr")
            while ec.poll(eid) in [EventStatus.RETRY, EventStatus.PENDING]:
                time.sleep(0.01)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            result = ec.result(eid)
            self.assertEquals(result, "lala")
            removed = ec.remove(eid)
            self.assertTrue(removed)
            status = ec.poll(eid)
            # After getting the result back, the event should have been eraised
            # and status should be None
            self.assertTrue(status == None)

            # shcedule set
            eid = ec.set(trace1.guid, "stringAttr", "lolo")
            while ec.poll(eid) in [EventStatus.RETRY, EventStatus.PENDING]:
                time.sleep(0.01)
            ec.remove(eid)
            # verify that the value was set correctly
            eid = ec.get(trace1.guid, "stringAttr")
            while ec.poll(eid) in [EventStatus.RETRY, EventStatus.PENDING]:
                time.sleep(0.01)
            result = ec.result(eid)
            self.assertEquals(result, "lolo")
            ec.remove(eid)
            
            node1 = exp.box("node1")
            
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
            removed = ec.remove(eid)
            self.assertTrue(removed)
            status = ec.poll(eid)
            self.assertTrue(status == None)

            # poll on nonexistent event id should not break things
            eid = 1000000000000
            status = ec.poll(eid)
            self.assertTrue(status == None)
            result = ec.result(eid)
            self.assertTrue(result == None)
            removed = ec.remove(eid)
            self.assertFalse(removed)

        except:
            raise
        finally:
            ec.shutdown()


if __name__ == '__main__':
    unittest.main()

