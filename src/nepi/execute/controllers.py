
import datetime
import itertools
import heapq
import logging
import re
import sys
import threading
import time

from nepi.design import tags
from nepi.design.boxes import create_provider
from nepi.util.parallel import ParallelRun

class ResourceState:
    FAILED = 0
    NOTEXIST = 1
    NEW = 2
    CREATED = 3
    STARTED = 4
    RUNNING = 5
    FINISHED = 6
    STOPPED = 7
    SHUTDOWN = 8

class EventStatus:
    SUCCESS = 0
    FAIL = 1
    RETRY = 2
    PENDING = 3


_strf = "%Y%m%d%H%M%S%f"
_reabs = re.compile("^\d{20}$")
_rerel = re.compile("^(\d+)(h|m|s|ms|us)$")

def strfnow():
    return datetime.datetime.now().strftime(_strf)

def strfdiff(str1, str2):
    d1 = datetime.datetime.strptime(str1, _strf)
    d2 = datetime.datetime.strptime(str2, _strf)

    # convert to unix timestamp
    ds1 = time.mktime(d1.timetuple())
    ds2 = time.mktime(d2.timetuple())
   
    return ds1 - ds2

def strfvalid(date):
    if not date:
        return strfnow()
    if _reabs.match(date):
        return date
    m = _rerel.match(date)
    if m:
        time = int(m.groups()[0])
        units = m.groups()[1]
        if units == 'h':
            delta = datetime.timedelta(hours = time) 
        elif units == 'm':
            delta = datetime.timedelta(minutes = time) 
        elif units == 's':
            delta = datetime.timedelta(seconds = time) 
        elif units == 'ms':
            delta = datetime.timedelta(microseconds = (time*1000)) 
        else:
            delta = datetime.timedelta(microseconds = time) 
        now = datetime.datetime.now()
        d = now + delta
        return d.strftime(_strf)
    return None


class Event(object):
    DEFAULT_DELAY = "0.2s"

    def __init__(self, callback, args, wait_events = None, delay = None):
        super(Event, self).__init__()
        self._callback = callback
        self._args = args
        self.status = EventStatus.PENDING
        self.result = None
        # Event need to wait until these events are completed
        # to execute
        self._wait_events = wait_events or []
        # Time to wait until retry
        self._delay = delay or self.DEFAULT_DELAY

    @property
    def callback(self):
        return self._callback

    @property
    def args(self):
        return self._args
    
    @property
    def delay(self):
        return self._delay

    @property
    def wait_events(self):
        return self._wait_events

    def add_wait_event(self, eid):
        self._wait_events.append(eid)


class HeapScheduler(object):
    def __init__(self):
        super(HeapScheduler, self).__init__()
        self._events = list() 
        self._event_idx = dict()
        self._eid = itertools.count()
        self._empty = True

    @property
    def is_empty(self):
        return self._empty

    def schedule(self, event, date = None):
        # validate date
        date = strfvalid(date)
        if not date:
            return (None, None, None)

        # generate event id
        eid = next(self._eid)
        entry = (date, eid, event)

        # re-schedule event
        if event in self._event_idx:
            self.remove(event)

        self._event_idx[event] = entry
        heapq.heappush(self._events, entry)
        self._empty = False
        return entry

    def remove(self, event):
        try:
            entry = self._event_idx.pop(event)
            # Mark entry as invalid
            entry[-1] = None
        except:
            pass

    def next(self):
        while self._events:
            try:
               date, eid, event = heapq.heappop(self._events)
               if event:
                  del self._event_idx[event]
                  return (date, eid, event)
            except IndexError:
                # heap empty
                pass
        self._empty = True
        return (None, None, None)


class Resource(object):
    def __init__(self, guid, box_id, container_guid, controller_guid, tags):
        super(Resource, self).__init__()
        self._guid = guid
        self._box_id = box_id
        self._container_guid = container_guid
        self._controller_guid = controller_guid
        self._tags = tags
        self.state = ResourceState.NEW
        # Reference to the testbed controller (TC)
        self.tc = None

    @property
    def guid(self):
        return self._guid
        
    @property
    def box_id(self):
        return self._box_id

    @property
    def container_guiid(self):
        return self._container_guid

    @property
    def controller_guid(self):
        return self._controller_guid

    @property
    def tags(self):
        return self._tags


class ExperimentController(object):
    def __init__(self, xml):
        super(ExperimentController, self).__init__()
        # original experiment description (ED)
        self._original_ed_path = "original_experiment_description.xml"
        self._save_ed(self._original_ed_path, xml)
        
        # runtime ED
        self._runtime_ed_path = "runtime_experiment_description.xml"
        self._save_ed(self._runtime_ed_path, xml)

        self._start_time = None
        self._stop_time = None
        # flag indicating that user stoped experiment
        self._stopped = True
        # experiment controller (EC) state
        self._state = ResourceState.NEW

        # testbed controller (TC) classes 
        self._tc_classes = dict()
        # resources
        self._resources = dict()

        # scheduler
        self._scheduler = HeapScheduler()
        # event processing thread
        self._proc_thread = threading.Thread(target=self._process_events)
        self._proc_cond = threading.Condition()
        # stop event processing
        self._stop = False

        # pending events
        self._pend_events = dict()
        self._pend_lock = threading.Lock()

        # Logging
        self._logger = logging.getLogger("nepi.execute.ec")

    @property
    def original_ed(self):
        return self._load_ed(self._original_ed_path)

    @property
    def runtime_ed(self):
        return self._load_ed(self._runtime_ed_path)

    @property
    def start_time(self):
        return self._started_time

    @property
    def stop_time(self):
        return self._stopped_time

    def poll(self, eid):
        return self._poll_pending_event(eid)

    def result(self, eid):
        return self._result_pending_event(eid)

    def remove(self, eid):
        return self._remove_pending_event(eid)

    def cancel(self, eid):
        return self._cancel_pending_event(eid)

    def run(self, modnames = None):
        self._load_testbed_controllers(modnames)
        # start event-processing thread
        self._proc_thread.start()
        # orchestrate experiment description, and schedule events
        self._orchestrate_ed(modnames)
        self._state = ResourceState.STARTED
        self._start_time = strfnow()

    def state(self, guid = None):
        if guid == None:
            return self._state
        else:
            rc = self._resources.get(guid)
            if not rc: 
                return ResourceState.NOTEXIST
            # once the resource is started, it is 
            # the TC to hold the current state 
            if rc.state == ResourceState.STARTED:
                return rc.tc.state(guid) 
            return rc.state

    def recover(self, guid = None):
        # TODO! 
        pass

    def shutdown_now(self):
        return self._shutdown()

    def shutdown(self, guid = None, date = None, wait_events = None):
        if guid == None:
            callback = self._shutdown
        else:
            callback = self._tc_shutdown
        args = []
        # schedule shutdown
        return self._schedule_event(callback, args, date, wait_events)

    def create(self, guid, box_id, container_guid, controller_guid, box_tags,
            attributes, date = None, wait_events = None):
        # create new resource
        rc = Resource(guid, box_id, container_guid, controller_guid, box_tags)
        self._resources[guid] = rc

        if tags.TC in box_tags:
            callback = self._create
        else:
            callback = self._tc_create
        
        args = [guid, attributes]
        # schedule create
        return self._schedule_event(callback, args, date, wait_events)

    def connect(self, guid, connector, other_guid, other_connector, 
            date = None, wait_events = None):
        callback = self._tc_connect
        args = [guid, connector, other_guid, other_connector]
        return self._schedule_event(callback, args, date, wait_events)

    def postconnect(self, guid, connector, other_guid, other_connector, 
            date = None, wait_events = None):
        callback = self._tc_postconnect
        args = [guid, connector, other_guid, other_connector]
        return self._schedule_event(callback, args, date, wait_events)

    def start(self, guid, date = None, wait_events = None):
        callback = self._tc_start
        args = [guid]
        return self._schedule_event(callback, args, date, wait_events)

    def stop_now(self):
        return self._stop()

    def stop(self, guid = None, date = None, wait_events = None):
        if guid == None:
            callback = self._stop
        else:
            callback = self._tc_stop
        args = [guid]
        return self._schedule_event(callback, args, date, wait_events)

    def set(self, guid, attr, value, date = None, wait_events = None):
        callback = self._tc_get
        args = [guid, attr, value]
        return self._schedule_event(callback, args, date, wait_events)
    
    def get(self, guid, attr, date = None, wait_events = None):
        callback = self._tc_get
        args = [guid, attr]
        return self._schedule_event(callback, args, date, wait_events)

    def clean_events(self, wait_events):
        """ Schedule an event that will remove the events from the 
            pending_events list when there are executed. """
        callback = self._clean_events
        args = [wait_events]
        date = None
        return self._schedule_event(callback, args, date, wait_events, "3s")

    @property
    def _tcs(self):
        return [ rc for rc in self._resources.values() \
                if tags.TC in rc.tags ]

    def _stop(self):
        state = self.state()
        if state < ResourceState.STARTED:
           return (EventStatus.FAIL, "Couldn't stop EC. Wrong state %d"
                % (state))

        status = EventStatus.SUCCESS
        result = ""
        if state == ResourceState.STARTED:
            # Stop all TCs
            for tc in self._tcs:
                (status, result) = self._tc_stop(tc.guid)
                if status != EventStatus.SUCCESS:
                    return (status, result)
        
            self.__stop()
        return (status, result)

    def __stop(self):
        self._stop_time = strfnow()
        self._stoppped = True
        self._state = ResourceState.STOPPED

    def _tc_stop(self, guid):
        state = self.state(guid)
        if state < ResourceState.STARTED:
           return (EventStatus.FAIL, "Couldn't stop RC. Wrong state %d for guid(%d)"
                % (state, guid))

        status = EventStatus.SUCCESS
        result = ""

        if state in [ResourceState.STARTED, ResourceState.RUNNING]:
            rc = self._resources.get(guid)
            (status, result) = rc.tc.stop(guid)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.STOPPED

        return (status, result)

    def _tc_start(self, guid):
        state = self.state(guid)
        if state != ResourceState.CREATED:
           return (EventStatus.FAIL, "Couldn't start RC. Wrong state %d for guid(%d)"
                % (state, guid))

        status = EventStatus.SUCCESS
        result = ""

        rc = self._resources.get(guid)
        (status, result) = rc.tc.start(guid)
        if status == EventStatus.SUCCESS:
            rc.state = ResourceState.STARTED

        return (status, result)

    def _shutdown(self):
        status = EventStatus.SUCCESS
        result = ""
        
        # Shutdown all TCs
        for tc in self._tcs:
            (status, result) = self._tc_shutdown(tc.guid)
            if status != EventStatus.SUCCESS:
                return (status, result)

        self._stop = True
        self._proc_cond.acquire()
        self._proc_cond.notify()
        self._proc_cond.release()
        self._proc_thread.join()
        return (status, result)

    def _tc_shutdown(self, guid):
        state = self.state(guid)
        status = EventStatus.SUCCESS
        result = ""

        rc = self._resources.get(guid)
        if state >= ResourceState.CREATED and state < ResourceState.SHUTDOWN:
            (status, result) = rc.tc.shutdown(guid)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.SHUTDOWN
        elif state == ResourceState.NEW:
            rc.state = ResourceState.SHUTDOWN

        return (status, result)

    def _create(self, guid, attributes):
        state = self.state(guid)
        if state != ResourceState.NEW:
           return (EventStatus.FAIL, "Couldn't create TC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        tcrc_guid = rc.controller_guid
        tcrc = self._resources.get(rc.controller_guid)
        
        if tcrc_guid and not tcrc:
            # The TC doesn't exist.
            return (EventStatus.FAIL, "TC for guid(%d) does not exist." % guid)

        # Nested testbed
        if tcrc_guid and not tcrc.tc:
            # The TC is not yet created. We need to delay the event.
            return (EventStatus.RETRY, "0.2s")
        
        tc_class = self._tc_classes.get(rc.box_id)
        tc = tc_class(guid)
        rc.tc = tc
        rc.state = ResourceState.CREATED 

        return (EventStatus.SUCCESS, "")

    def _tc_create(self, guid, attributes):
        state = self.state(guid)
        if state != ResourceState.NEW:
           return (EventStatus.FAIL, "Couldn't create RC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        tcrc = self._resources.get(rc.controller_guid)
            
        if not tcrc:
            # The TC doesn't exist.
            return (EventStatus.FAIL, "TC for guid(%d) does not exist." % guid)

        if not tcrc.tc:
            # The TC is not yet created. We need to delay the event.
            return (EventStatus.RETRY, "0.2s")
        else:
            rc.tc = tcrc.tc

        (status, result) = rc.tc.create(guid, rc.box_id, attributes)
        if status == EventStatus.SUCCESS:
            rc.state = ResourceState.CREATED 
        return (status, result)

    def _tc_connect(self, guid, connector, other_guid, other_connector):
        state = self.state(guid)
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
           return (EventStatus.FAIL, "Couldn't connect RC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        (status, result) = rc.tc.connect(guid, connector, other_guid, other_connector)
        return (status, result)

    def _tc_postconnect(self, guid, connector, other_guid, other_connector):
        state = self.state(guid)
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
           return (EventStatus.FAIL, "Couldn't postconnect RC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        (status, result) = rc.tc.postconnect(guid, connector, other_guid, other_connector)
        return (status, result)

    def _tc_get(self, guid, attr): 
        state = self.state(guid)
        if state in [ResourceState.NOTEXIST, ResourceState.NEW, ResourceState.SHUTDOWN]:
           return (EventStatus.FAIL, "Couldn't get attribute from RC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        (status, result) = rc.tc.get(guid, attr)
        return (status, result)

    def _tc_set(self, guid, attr, value): 
        state = self.state(guid)
        if state in [ResourceState.NOTEXIST, ResourceState.NEW, ResourceState.SHUTDOWN]:
           return (EventStatus.FAIL, "Couldn't set attribute on RC. Wrong state %d for guid(%d)"
                % (state, guid))

        rc = self._resources.get(guid)
        (status, result) = rc.tc.set(guid, attr, value)
        return (status, result)

    def _clean_events(self, events):
        for eid in events:
            self.remove(eid)
        return (EventStatus.SUCCESS, "")

    def _save_ed(self, path, xml):
        """ Persist experiment description to file """
        f = open(path, "w")
        f.write(xml)
        f.close()

    def _load_ed(self, path):
        """ Load experiment description from file """
        f = open(path, "r")
        xml = f.read()
        f.close()
        return xml

    def _orchestrate_ed(self, modnames = None):
        def walk_create(box, pending_events):
            if not [t for t in box.tags if t in [tags.EXPERIMENT, tags.CONTAINER]]:
                controller_guid = box.controller.guid if box.controller else None
                container_guid = box.container.guid if box.container else None
                attrs = dict((attr_name, getattr(box.a, attr_name)) \
                        for attr_name in box.attributes)

                # schedule create
                eid_create = self.create(box.guid, box.box_id, container_guid, 
                        controller_guid, box.tags, attrs)
                pending_events.append(eid_create)

                # schedule connect
                wait_events = []
                for conn in box.connections:
                    (b, c_name, other_b, other_c_name) = conn

                    eid_conn = self.connect(b.guid, c_name, other_b, other_c_name,
                            wait_events = [eid_create])
                    wait_events.append(eid_conn)
                    pending_events.append(eid_conn)

                    eid_post = self.postconnect(b.guid, c_name, other_b, other_c_name,
                            wait_events = [eid_conn])
                    wait_events.append(eid_post)
                    pending_events.append(eid_post)

                # schedule start
                eid_start = self.start(box.guid, wait_events = wait_events)
                pending_events.append(eid_start)

            for b in box.boxes:
                walk_create(b, pending_events)

        pending_events = []
        provider = create_provider(modnames)
        exp = provider.from_xml(self.original_ed)
        walk_create(exp, pending_events)

        self.clean_events(pending_events)

    def _schedule_event(self, callback, args, date = None, 
            wait_events = None, delay = None):
        event = Event(callback, args, wait_events, delay)
        return self.__schedule_event(event, date)

    def __schedule_event(self, event, date = None):
        self._proc_cond.acquire()
        (date, eid, event) = self._scheduler.schedule(event, date)
        self._proc_cond.notify()
        self._proc_cond.release()

        self._add_pending_event(eid, event)
        return eid

    def _process_events(self):
        sync_limit = 20
        runner = ParallelRun(maxthreads = sync_limit / 2)
        runner.start()
        count = 1

        try:
            while not self._stop:
                self._proc_cond.acquire()
                if self._scheduler.is_empty: 
                    self._proc_cond.wait()
                (date, eid, event) = self._scheduler.next()
                self._proc_cond.release()
                
                if event:
                    # If date is in the future, thread needs to wait
                    # until time elapse or until another event is scheduled
                    now = strfnow()
                    if now < date:
                        # re-schedule event at same date
                        self.__schedule_event(event, date)
                        # difference in seconds
                        timeout = strfdiff(date, now)
                        self._proc_cond.acquire()
                        self._proc_cond.wait(timeout)
                        self._proc_cond.release()
                    elif [eid for eid in event.wait_events \
                            if self.poll(eid) == EventStatus.PENDING]:
                        # re-schedule event in 1 second
                        self.__schedule_event(event, event.delay)
                    else:
                        # process events in parallel
                        runner.put(self._execute_event, event)

                if count == sync_limit:
                    count == 0
                    runner.sync()
                count +=1 
        except:  
            self._state = ResourceState.FAILED 
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while processing events in the EC: %s" % err)
 
        #runner.sync()
        #runner.join()

    def _remove_event(self, event):
        self._proc_cond.acquire()
        self._scheduler.remove(event)
        self._proc_cond.release()

    def _execute_event(self, event):
        (status, result) = event.callback(*event.args)
        event.status = status
        event.result = result
        
        if status == EventStatus.RETRY:
            # Results holds the delay
            self.__schedule_event(event, date = result)
        else: # FAIL or SUCCESS
            self._remove_event(event) 
            if status == EventStatus.FAIL:
                self._logger.error("Event failure: %s(%s) - %s" % (event.callback.func_name, event.args, result))

    def _add_pending_event(self, eid, event):
        self._pend_lock.acquire()
        self._pend_events[eid] = event                
        self._pend_lock.release()

    def _remove_pending_event(self, eid):
        event = self._pend_events.get(eid)
        if event: 
            self._pend_lock.acquire()
            del self._pend_events[eid]
            self._pend_lock.release()

            self._remove_event(event)
            return True

        return False

    def _poll_pending_event(self, eid):
        event = self._pend_events.get(eid)
        if not event:
            return None

        return event.status

    def _result_pending_event(self, eid):
        event = self._pend_events.get(eid)
        if not event or event.status == EventStatus.PENDING:
            return None 

        return event.result

    def _cancel_pending_event(self, eid):
        event = self._pend_events.get(eid)
        if event and event.status == EventStatus.PENDING:
            return self._remove_pending_event(eid)

        return False

    def _load_testbed_controllers(self, modnames = None):
        if not modnames:
            import pkgutil
            import nepi.testbeds
            pkgpath = os.path.dirname(nepi.testbeds.__file__)
            modnames = ["nepi.testbeds.%s" % name for _, name, _ in pkgutil.iter_modules([pkgpath])]

        mods = []
        for modname in modnames:
            if modname not in sys.modules:
                __import__(modname)
            mod = sys.modules[modname]
            mods.append(mod)

        for mod in mods:
            self._add_tc(mod.TC_BOX_ID, mod.TC_CLASS)

    def _add_tc(self, box_id, tc_class):
        self._tc_classes[box_id] = tc_class


class TestbedController(object):
    def __init__(self, guid):
        super(TestbedController, self).__init__()
        self._guid = guid
        self._start_time = None
        self._stop_time = None
        # flag indicating that user stoped experiment
        self._stopped = True
        # experiment controller (EC) state
        self._state = ResourceState.NEW

        # objects
        self._objects = dict()

    @property
    def guid(self):
        return self._guid

    @property
    def start_time(self):
        return self._started_time

    @property
    def stop_time(self):
        return self._stopped_time

    def state(self, guid):
        if guid == self.guid:
            return self._state
        else:
            obj = self._objects.get(guid)
            if not obj: 
                return ResourceState.NOTEXIST
            return obj.state

    def recover(self):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def create(self, guid, box_id, container_guid, controller_guid, attributes):
        raise NotImplementedError

    def connect(self, guid, connector, other_guid, other_connector):
        raise NotImplementedError

    def postconnect(self, guid, connector, other_guid, other_connector): 
        raise NotImplementedError

    def start(self, guid = None):
        raise NotImplementedError

    def stop(self, guid = None):
        raise NotImplementedError

    def set(self, guid, attr, value):
        obj = self._objects.get(guid)
        if not obj: 
            return (EventStatus.FAIL, "Object guid(%d) doesn't exist." % guid)
        return obj.set_attr(attr, value)

    def get(self, guid, attr):
        obj = self._objects.get(guid)
        if not obj: 
            return (EventStatus.FAIL, "Object guid(%d) doesn't exist." % guid)
        return obj.get_attr(attr)


def create_ec(xml):
    return ExperimentController(xml)

