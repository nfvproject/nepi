
import datetime
import itertools
import heapq
import threading
import time
import logging

from nepi.design import tags
from nepi.design.boxes import create_provider
from nepi.util.parallel import ParallelRun

class ResourceState:
    NEW = 0
    FAILED = 1
    CREATED = 2
    CONFIGURED = 3
    CONNECTED = 4
    STARTED = 5
    STOPPED = 6
    SHUTDOWN = 7

class EventStatus:
    SUCCESS = 0
    FAIL = 1
    RETRY = 2

_strf = "%Y%m%d%H%M%S%f"

def strfnow():
    return datetime.datetime.now().strftime(_strf)

def strfdiff(str1, str2):
    d1 = datetime.strptime(str1, _strf)
    d2 = datetime.strptime(str2, _strf)

    # convert to unix timestamp
    ds1 = time.mktime(d1.timetuple())
    ds2 = time.mktime(d2.timetuple())

    return ds2-ds1

class Event(object):
    def __init__(self, callback, args):
        self._callback = callback
        self._args = args

    @property
    def callback(self):
        return self._callback

    @property
    def args(self):
        return self._args

class HeapScheduler(object):
    def __init__(self):
        self._events = list() 
        self._event_idx = dict()
        self._evid = itertools.count()
        self._empty = True

    @property
    def is_empty(self):
        return self._empty

    def schedule(self, event, date = None):
        if not date:
            date = strfnow() 
        # re-schedule event
        if event in self._event_idx:
            self.remove(event)
        evid = next(self._evid)
        entry = [date, evid, event]
        self._event_idx[event] = entry
        heapq.heappush(self._events, entry)
        self._empty = False

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
               date, evid, event = heapq.heappop(self._events)
               if event:
                  del self._event_idx[event]
                  return (event, date)
            except IndexError:
                # heap empty
                pass
        self._empty = True
        return (None, None)

class Resource(object):
    def __init__(self, guid, box_id, parent_guid, testbed_guid):
        self._guid = guid
        self._box_id = box_id
        self._parent_guid = parent_guid
        self._testbed_guid = testbed_guid
        self.state = ResourceState.NEW
        self.tc = None

class ExperimentController(object):
    def __init__(self, xml):
        self._design_xml = xml
        # runtime-xml
        self._xml = None
        self._testbed_controllers = dict()
        self._start_time = None
        self._stop_time = None
        # flag indicating that user stoped experiment
        self._stopped = True

        # resources
        self._resources = dict()
        # scheduler
        self._scheduler = HeapScheduler()
        # event processing thread
        self._thread = threading.Thread(target=self._process_events)
        self._cond = threading.Condition()
        # stop event processing
        self._stop = False

        # Logging
        self._logger = logging.getLogger("nepi.execute.ec")

    @property
    def design_xml(self):
        return self._design_xml

    @property
    def xml(self):
        return self._xml

    @property
    def start_time(self):
        return self._started_time

    @property
    def stop_time(self):
        return self._stopped_time

    def create(self, guid, box_id, parent_guid, testbed_guid, attributes,
            date = None, condition = None):
        # create new resource
        rc = Resource(guid, box_id, parent_guid, testbed_guid)
        self._resources[guid] = rc
        
        # schedule create
        callback = self._create
        args = [guid, box_id, parent_guid, testbed_guid, attributes]
        event = Event(callback, args)
        self._schedule_event(event, date)

    def tc_create(self, guid, box_id, parent_guid, testbed_guid, attributes,
            date = None, condition = None):
        # create new resource
        rc = Resource(guid, box_id, parent_guid, testbed_guid)
        self._resources[guid] = rc

        # schedule create
        callback = self._tc_create 
        args = [guid, box_id, parent_guid, testbed_guid, attributes]
        event = Event(callback, args)
        self._schedule_event(event, date)

    def connect(self, guid, connector, other_guid, other_connector, 
            date = None, condition = None):
        pass

    def postconnect(self, guid, connector, other_guid, other_connector, 
            date = None, condition = None):
        pass

    def start(self, guid, date = None, condition = None):
        pass

    def stop(self, guid = None, date = None, condition = None):
        if guid == None:
            self._stop_time = strfnow()
            self._stoppped = True
            # TODO: STOP ALL TESTBEDS!!
        else:
           pass

    def run(self, mods = None):
        self._start_time = strfnow()
        self._thread.start()
        # process XML experiment description, and schedule events
        self._process_xml(mods)

    def shutdown(self):
        self._stop = True
        # TODO: SHUTDOWN ALL TESTBEDS !!
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        self._thread.join()

    def recover(self):
        pass

    def status(self, guid = None):
        pass

    def set(self, guid, condition):
        pass
    
    def get(self):
        pass

    def _create(self, guid, box_id, parent_guid, testbed_guid, attributes):
        # TODO!
        self._logger.error("created %s.guid(%d) %d %d - %s" % (box_id, guid, parent_guid, testbed_guid, str(attributes)))
        return EventStatus.SUCCESS

    def _tc_create(self, guid, box_id, parent_guid, testbed_guid, attributes):
        # TODO!
        self._logger.error("TC created %s.guid(%d) %d %d - %s" % (box_id, guid, parent_guid, testbed_guid, str(attributes)))
        return EventStatus.SUCCESS

    def _process_xml(self, mods = None):
        def walk_create(box):
            if not [t for t in box.tags if t in [tags.EXPERIMENT, tags.CONTAINER]]:
                controller_guid = box.controller.guid if box.controller else None
                container_guid = box.container.guid if box.container else None
                attrs = dict((attr_name, getattr(box.a, attr_name)) for attr_name in box.attributes)
                if tags.CONTROLLER in box.tags:
                    self.tc_create(box.guid, box.box_id, container_guid, 
                        controller_guid, attrs)
                else:
                    self.create(box.guid, box.box_id, container_guid, 
                        controller_guid, attrs)

            for b in box.boxes:
                walk_create(b)

        provider = create_provider(mods)
        exp = provider.from_xml(self._design_xml)
        walk_create(exp)

    def _schedule_event(self, event, date = None):
        self._cond.acquire()
        self._scheduler.schedule(event, date)
        self._cond.notify()
        self._cond.release()

    def _process_events(self):
        sync_limit = 20
        runner = ParallelRun(maxthreads = sync_limit / 2)
        runner.start()
        count = 1

        while not self._stop:
            self._cond.acquire()
            if self._scheduler.is_empty: 
                self._cond.wait()
            (event, date) = self._scheduler.next()
            self._cond.release()

            if event:
                # If date is in the future, thread needs to wait
                # until time elapse or until another event is scheduled
                now = strfnow()
                if now < date:
                    # reeschedule event at same date
                    self._schedule_event(event, date)
                    # difference in seconds
                    timeout = strfdiff(date, now) 
                    self._cond.acquire()
                    self._cond.wait(timeout)
                    self._cond.release()
                else:
                    # process events in parallel
                    runner.put(self._execute_event, event)

            if count == sync_limit:
                count == 0
                runner.sync()
            count +=1 
                
        runner.sync()
        runner.join()

    def _remove_event(self, event):
        self._cond.acquire()
        self._scheduler.remove(event)
        self._cond.release()

    def _execute_event(self, event):
        ret = event.callback(*event.args)
        if ret == EventStatus.RETRY:
            self._schedule_event(event)
        else: # FAIL or SUCCESS
            self._remove_event(event) 
            if ret == EventStatus.FAIL:
                self._logger.error("Event failure: %s(%s)" % (event.callback, event.args))


def create_ec(xml):
    return ExperimentController(xml)

