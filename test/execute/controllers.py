#!/usr/bin/env python

from nepi.design import create_provider
from nepi.execute import create_ec, EventStatus, Event, ResourceState 
import time
import unittest

def attrs(box):
    return dict((attr_name, getattr(box.a, attr_name).value) \
        for attr_name in box.attributes if \
        getattr(box.a, attr_name).value is not None)

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

    trace1 = provider.create("mock::Trace", container = mocki,
            label = "trace1", stringAttr = "lala")
    node1.c.traces.connect(trace1.c.node)

    trace2 = provider.create("mock::Trace", container = mocki,
            label = "trace2", stringAttr = "lala")
    node2.c.traces.connect(trace2.c.node)

    app1 = provider.create("mock::Application", container = mocki,
            label = "app1", start = "10s")
    app1.c.node.connect(node1.c.apps)

    app2 = provider.create("mock::Application", container = mocki,
            label = "app2", start = "10s")
    app2.c.node.connect(node1.c.apps)

    return exp


class ExecuteControllersTestCase(unittest.TestCase):
    def test_schedule_exception(self):
        # This test has the objective of verifying that errors that occur 
        # while executing an event will not afect the processing of following
        # events
        def error_func():
            raise RuntimeError

        def do_nothing():
            return (EventStatus.SUCCESS, "")

        ec = create_ec("", debug = False)
        ec.run(modnames = [])

        try:
            # An error launched during event execution should not crash the EC
            args = []
            eid = ec._schedule_event(error_func, args)
            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.FAIL)

            # Processing should continue normally after the exception
            eid = ec._schedule_event(do_nothing, args)
            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)

            # There should be no events left in the queue
            self.assertEquals(len(ec._scheduler._events), 0)
            # There should be exactly 2 events scheduled in the past
            nxt = ec._scheduler._eid.next()
            self.assertEquals(nxt, 3)
        finally:
            ec.shutdown_now()

    def test_schedule_date(self):
        # This test has the objective of verifying that events are executed
        # at the correct time they were scheduled on
        def do_nothing():
            return (EventStatus.SUCCESS, "")

        ec = create_ec("", debug = False)
        ec.run(modnames = [])

        try:
            args = []
            # Scheduling an event in 2 seconds. It should not be executed before
            eid = ec._schedule_event(do_nothing, args, date = "2s")
            time.sleep(0.3)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.PENDING)
            time.sleep(1.8)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)

            # There should be no events left in the queue
            self.assertEquals(len(ec._scheduler._events), 0)
            # There should be exactly 2 events scheduled in the past:
            # the original event + the rescheduled event (as the execution
            # date was still in the future)
            nxt = ec._scheduler._eid.next()
            self.assertEquals(nxt, 3)

            # Now, lets try to schedule an event in the future wait, and
            # schedule another earlier event, to verify that the processing
            # thread is correctly correctly
            args = []
            eid1 = ec._schedule_event(do_nothing, args, date = "2s")
            time.sleep(0.4)
            status = ec.poll(eid1)
            self.assertTrue(status == EventStatus.PENDING)
            
            # Even if eid1 was scheduled first, eid2 should be executed first
            eid2 = ec._schedule_event(do_nothing, args)
            time.sleep(0.1)
            status = ec.poll(eid2)
            self.assertTrue(status == EventStatus.SUCCESS)
            status = ec.poll(eid1)
            self.assertTrue(status == EventStatus.PENDING)
            
            # Finally, the original event should be executed
            time.sleep(1.6)
            status = ec.poll(eid1)
            self.assertTrue(status == EventStatus.SUCCESS)
           
            nxt = ec._scheduler._eid.next()
            self.assertEquals(nxt, 8)

        finally:
            ec.shutdown_now()

    def test_schedule_pending(self):
        # This test has the objective of verifying that events marked as
        # 'pending' will be added to the pending events list, and vicerversa 
        def do_nothing():
            return (EventStatus.SUCCESS, "")

        ec = create_ec("", debug = False)
        ec.run(modnames = [])

        try:
            args = []
            # Event is explicitelly not added to the pending events list
            eid = ec._schedule_event(do_nothing, args, pending = False)
            time.sleep(0.3)
            status = ec.poll(eid)
            self.assertTrue(status == None)
            # Verify that pending event list has len == 0
            self.assertEquals(len(ec._pend_events), 0)

            eid = ec._schedule_event(do_nothing, args, pending = True)
            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            # Verify that pending event list has len == 1
            self.assertEquals(len(ec._pend_events), 1)

        finally:
            ec.shutdown_now()

    def test_schedule_creation_order(self):
        # This test has the objective of verifying that basic ordering
        # rules for component creating are respected. (Ex, a child component
        # can never be created before its parent)
        provider = create_provider(modnames = ["mock"])
        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        node = provider.create("mock::Node", container = mocki)

        ec = create_ec("", debug = False)

        try: 
            ec.run(modnames = ["mock"])

            # Validation: node can't be created before it's TC!
            create_node_eid = ec.create(node.guid, node.box_id, 
                    container_guid(node),
                    controller_guid(node),
                    node.tags, 
                    attrs(node))
            time.sleep(0.2)
            # Verify that node_create event is in RETRY status 
            # as execution was delayed by the events itself as 
            # conditions for execution where not yet satisfied
            status = ec.poll(create_node_eid)
            self.assertTrue(status == EventStatus.RETRY)
            # Verify that pending event list has len == 1
            self.assertEquals(len(ec._pend_events), 1)

            create_mock_eid = ec.create(mocki.guid, mocki.box_id, 
                    container_guid(mocki),
                    controller_guid(mocki),
                    mocki.tags, 
                    attrs(mocki))
            time.sleep(0.2)
            status = ec.poll(create_mock_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            status = ec.poll(create_node_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            
            # The pend_events list should only have two entries, even if retries where done
            self.assertEquals(len(ec._pend_events), 2)
            removed = ec.remove(create_node_eid)
            self.assertTrue(removed)
            removed = ec.remove(create_mock_eid)
            self.assertTrue(removed)
            self.assertEquals(len(ec._pend_events), 0)

        finally:
            ec.shutdown_now()

    def test_schedule_wait_events(self):
        # This test has the objective of verifying the 'wait_events'
        # condition
        def do_nothing():
            return (EventStatus.SUCCESS, "")

        ec = create_ec("", debug = False)
        ec.run(modnames = [])

        try:
            args = []
            eid1 = ec._schedule_event(do_nothing, args, date = "2s")
            # The second event is scheduled inmediatelly, but needs to wait
            # until the other event is done.
            eid2 = ec._schedule_event(do_nothing, args, wait_events = [eid1])

            time.sleep(0.2)
            status = ec.poll(eid1)
            self.assertTrue(status == EventStatus.PENDING)
            status = ec.poll(eid2)
            self.assertTrue(status == EventStatus.PENDING)
            
            time.sleep(1.9)
            status = ec.poll(eid1)
            self.assertTrue(status == EventStatus.SUCCESS)
            status = ec.poll(eid2)
            self.assertTrue(status == EventStatus.SUCCESS)
 
            # There should be no events left in the queue
            self.assertEquals(len(ec._scheduler._events), 0)
            # There should be exactly 5 events scheduled in the past.
            # 2 orginal events + 1 reschedule for the 2s delay + the w
            nxt = ec._scheduler._eid.next()
            self.assertEquals(nxt, 5)
        finally:
            ec.shutdown_now()

    def test_schedule_wait_values(self):
        # This test has the objective of verifying the 'wait_values'
        # condition
        def do_nothing(node_guid, **kwargs):
            if "boolAttr" not in kwargs:
                result = dict({
                    "wait_values": "boolAttr:guid(%d).boolAttr == True" % node_guid
                })
                return (EventStatus.RETRY, result)
            return (EventStatus.SUCCESS, "")

        provider = create_provider(modnames = ["mock"])
        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        node = provider.create("mock::Node", container = mocki)

        ec = create_ec("", debug = False)

        try: 
            ec.run(modnames = ["mock"])

            create_mock_eid = ec.create(mocki.guid, mocki.box_id, 
                    container_guid(mocki),
                    controller_guid(mocki),
                    mocki.tags, 
                    attrs(mocki))
            create_node_eid = ec.create(node.guid, node.box_id, 
                    container_guid(node),
                    controller_guid(node),
                    node.tags, 
                    attrs(node))
            
            time.sleep(0.1)
            status = ec.poll(create_node_eid)
            self.assertTrue(status == EventStatus.SUCCESS)
            
            args = [node.guid]
            eid = ec._schedule_event(do_nothing, args)
            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.RETRY)
            
            set_eid = ec.set(node.guid, "boolAttr", True)
            time.sleep(0.1)
            status = ec.poll(set_eid)
            self.assertTrue(status == EventStatus.SUCCESS)

            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)
  
            # There should be no events left in the queue
            self.assertEquals(len(ec._scheduler._events), 0)
          
        finally:
            ec.shutdown_now()

    def test_schedule_wait_states(self):
        # This test has the objective of verifying the 'wait_states'
        # condition
        def do_nothing():
            return (EventStatus.SUCCESS, "")

        provider = create_provider(modnames = ["mock"])
        exp = provider.create("Experiment")
        mocki = provider.create("mock::MockInstance", container = exp)
        node = provider.create("mock::Node", container = mocki)
        app = provider.create("mock::Application", container = mocki)

        ec = create_ec("", debug = False)

        try: 
            ec.run(modnames = ["mock"])
            
            wait = "guid(%d).state == %d" % (app.guid, ResourceState.STARTED)
            eid = ec._schedule_event(do_nothing, [], wait_states = wait)
            time.sleep(0.1)
            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.PENDING)
 
            create_mock_eid = ec.create(mocki.guid, mocki.box_id, 
                    container_guid(mocki),
                    controller_guid(mocki),
                    mocki.tags, 
                    attrs(mocki))
            create_node_eid = ec.create(node.guid, node.box_id, 
                    container_guid(node),
                    controller_guid(node),
                    node.tags, 
                    attrs(node))
            create_app_eid = ec.create(app.guid, app.box_id, 
                    container_guid(app),
                    controller_guid(app),
                    app.tags, 
                    attrs(app))
            start_app_eid = ec.start(app.guid)
            
            time.sleep(0.5)
            status = ec.poll(start_app_eid)
            self.assertTrue(status == EventStatus.SUCCESS)

            status = ec.poll(eid)
            self.assertTrue(status == EventStatus.SUCCESS)
          
        finally:
            ec.shutdown_now()

    def test_orchestration(self):
        exp = experiment_description()
        xml = exp.xml
        ec = create_ec(xml)

        try: 
            ec.run(modnames = ["mock"])

            # Wait until orchestration is finished
            while ec.state() != ResourceState.STARTED:
                # There should be pending events
                self.assertNotEquals(len(ec._pend_events), 0)
                time.sleep(0.1)

            # There should be no pending events in the ec after
            # the experiment is orchestrated
            self.assertEquals(len(ec._pend_events), 0)
 
            # Design & runtime experiments should be the same 
            rxml = ec.incremental_ed_xml
            self.assertEquals(xml, rxml)

            trace = exp.box("trace1")
            set_eid = ec.set(trace.guid, "stringAttr", "lolo")
            time.sleep(0.2)
            get_eid = ec.get(trace.guid, "stringAttr")
            time.sleep(0.2)
            result = ec.result(get_eid)
            self.assertEquals(result, "lolo")

            # Because we didn't flush the changes, the runtime
            # ed should still be the same
            rxml = ec.incremental_ed_xml
            self.assertEquals(xml, rxml)

            eid = ec.flush()
            
            while ec.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)
           
            rxml = ec.incremental_ed_xml
            
            self.assertNotEquals(xml, rxml)

        finally:
            ec.shutdown_now()

    def test_orchestration_with_events(self):
        exp = experiment_description()
        
        app1 = exp.box("app1")
        app2 = exp.box("app2")
        start_eid1 = app1.e.start.at("1s")
        start_eid2 = app2.e.start.after(app1.guid)
         
        trace1 = exp.box("trace1")
        args = ('stringAttr', 'pepe')
        conditions = dict({'wait_states': [(app2.guid, '==', ResourceState.STARTED)]})
        set_eid1 = trace1.e.set.on(conditions, args)

        node1 = exp.box("node1")
        set_eid2 = node1.e.set.at("3s", "boolAttr", False)
        
        args = ('stringAttr', 'lolo')
        conditions = dict({'wait_events': [set_eid2]})
        set_eid3 = trace1.e.set.on(conditions, args)
         
        trace2 = exp.box("trace2")
        args = ('stringAttr', 'wiiiiiiiiiii')
        conditions = dict({'wait_values': dict({"val": (trace1.guid, "stringAttr", '==', "lolo")})})
        set_eid4 = trace2.e.set.on(conditions, args)

        xml = exp.xml
        ec = create_ec(xml)

        try: 
            ec.run(modnames = ["mock"])

            # Wait until orchestration is finished
            while ec.state() != ResourceState.STARTED:
                # There should be pending events
                self.assertNotEquals(len(ec._pend_events), 0)
                time.sleep(0.1)

            # The design events should still be pending 
            self.assertTrue(len(ec._pend_events) >= 6)

            status = ec.poll(start_eid1)
            self.assertTrue(status != EventStatus.SUCCESS)

            status = ec.poll(start_eid2)
            self.assertTrue(status != EventStatus.SUCCESS)
 
            time.sleep(1)

            status = ec.poll(start_eid1)
            self.assertTrue(status == EventStatus.SUCCESS)

            while ec.poll(start_eid1) in [EventStatus.PENDING, EventStatus.RETRY]:
                status = ec.poll(set_eid1)
                self.assertTrue(status != EventStatus.SUCCESS)
      
                status = ec.poll(set_eid2)
                self.assertTrue(status != EventStatus.SUCCESS)
       
                status = ec.poll(set_eid3)
                self.assertTrue(status != EventStatus.SUCCESS)
 
                status = ec.poll(set_eid4)
                self.assertTrue(status != EventStatus.SUCCESS)
                
                time.sleep(0.1)
 
            while ec.poll(set_eid1) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)
 
            result = ec.result(set_eid1)
            self.assertEquals(result, "pepe")
 
            time.sleep(2)

            status = ec.poll(set_eid2)
            self.assertTrue(status == EventStatus.SUCCESS)
  
            result = ec.result(set_eid2)
            self.assertEquals(result, False)

            time.sleep(0.2)

            status = ec.poll(set_eid3)
            self.assertTrue(status == EventStatus.SUCCESS)
  
            result = ec.result(set_eid3)
            self.assertEquals(result, "lolo")
 
            while ec.poll(set_eid4) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)

            result = ec.result(set_eid4)
            self.assertEquals(result, 'wiiiiiiiiiii')

            for eid in ec.list_events():
                while ec.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                    time.sleep(0.1)
             
            eid = ec.flush()
            
            while ec.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)
           
            # Design & runtime experiments should be the same now that all 
            # events were executed
            rxml = ec.incremental_ed_xml

            self.assertEquals(xml, rxml)

        finally:
            ec.shutdown_now()

    def test_repeatability(self):
        rxml = ""

        exp = experiment_description()
        xml = exp.xml
        ec = create_ec(xml)

        try: 
            ec.run(modnames = ["mock"])

            # Wait until orchestration is finished
            while ec.state() != ResourceState.STARTED:
                # There should be pending events
                self.assertNotEquals(len(ec._pend_events), 0)
                time.sleep(0.1)

            trace = exp.box("trace1")
            set_eid = ec.set(trace.guid, "stringAttr", "lolo")
            while ec.poll(set_eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)
           
            eid = ec.flush()
            while ec.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)

            rxml = ec.incremental_ed_xml

        finally:
            ec.shutdown_now()

        ec2 = create_ec(rxml)

        try: 
            ec2.run(modnames = ["mock"])

            for eid in ec2.list_events():
                while ec2.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                    time.sleep(0.1)
               
            eid = ec2.flush()
            while ec2.poll(eid) in [EventStatus.PENDING, EventStatus.RETRY]:
                time.sleep(0.1)

            rxml2 = ec2.incremental_ed_xml
            
        finally:
            ec2.shutdown_now()

        self.assertEquals(rxml, rxml2)


if __name__ == '__main__':
    unittest.main()

