
import datetime
import itertools
import heapq
import logging
import os
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
    INVALID = 4

_strf = "%Y%m%d%H%M%S%f"
_reabs = re.compile("^\d{20}$")
_rerel = re.compile("^(?P<time>\d+(.\d+)?)(?P<units>h|m|s|ms|us)$")

def strfnow():
    return datetime.datetime.now().strftime(_strf)

def strfdiff(str1, str2):
    # time difference in seconds without ignoring miliseconds
    d1 = datetime.datetime.strptime(str1, _strf)
    d2 = datetime.datetime.strptime(str2, _strf)
    diff = d1 - d2
    ddays = diff.days * 86400
    dus = round(diff.microseconds * 1.0e-06, 0) # PFFFFFF!! it seems condition.wait doesn't support arbitrary float numbers well!!
    ret = ddays + diff.seconds + dus
    # avoid to saturate the procesor. if delay is 0 lets add 0.001
    return ret or 0.001

def strfvalid(date):
    if not date:
        return strfnow()
    if _reabs.match(date):
        return date
    m = _rerel.match(date)
    if m:
        time = float(m.groupdict()['time'])
        units = m.groupdict()['units']
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


_retryre = re.compile("^(?P<delay>delay:\d+(.\d+)?(h|m|s|ms|us))$|^(?P<kwargs>kwargs:([0-9a-zA-Z_-]+:guid\(\d+\)\.[0-9a-zA-Z_-]+,)*([0-9a-zA-Z_-]+:guid\(\d+\)\.[0-9a-zA-Z_-]+))$")
_kwargre = re.compile("(?P<key>[a-zA-Z_-]+):guid\((?P<guid>\d+)\)\.(?P<attr>[a-zA-Z_-]+)")

class Event(object):
    DEFAULT_DELAY = "0.1s"

    def __init__(self, callback, args, wait_events = None):
        super(Event, self).__init__()
        self._callback = callback
        self._args = args
        self.kwargs = dict()
        self.status = EventStatus.PENDING
        self.result = None
        # Event need to wait until these events are completed
        # to execute
        self.wait_events = wait_events or []

    @property
    def callback(self):
        return self._callback

    @property
    def args(self):
        return self._args


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
            (date, eid, event) = self._event_idx.pop(event)
            # Mark entry as invalid
            event.status = EventStatus.INVALID
        except:
            pass

    def next(self):
        while self._events:
            try:
                date, eid, event = heapq.heappop(self._events)
                if event.status != EventStatus.INVALID:
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
    def __init__(self, ed_xml, root_dir = "/tmp", debug = False):
        super(ExperimentController, self).__init__()
        # root directory to store files
        self._root_dir = root_dir

        # original experiment description (ED)
        self._original_ed_xml = "original_experiment_description.xml"
        self._save_ed(self._original_ed_xml, ed_xml)
        
        # runtime ED
        self._runtime_ed_xml = "runtime_experiment_description.xml"
        self._save_ed(self._runtime_ed_xml, ed_xml)

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
        if debug:
            level = logging.DEBUG
            self._logger.setLevel(level)
 
    @property
    def original_ed_xml(self):
        path = os.path.join(self._root_dir, self._original_ed_xml)
        return self._load_ed(path)

    @property
    def runtime_ed_xml(self):
        path = os.path.join(self._root_dir, self._runtime_ed_xml)
        return self._load_ed(path)

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

    def shutdown(self, guid = None, date = None, wait_events = None,
            pending = True):
        if guid == None:
            callback = self._shutdown
        else:
            callback = self._tc_shutdown
        args = []
        # schedule shutdown
        return self._schedule_event(callback, args, date, wait_events, pending)

    def create(self, guid, box_id, container_guid, controller_guid, box_tags,
            attributes, date = None, wait_events = None, pending = True):
        # create new resource
        rc = Resource(guid, box_id, container_guid, controller_guid, box_tags)
        self._resources[guid] = rc

        if tags.TC in box_tags:
            callback = self._create
        else:
            callback = self._tc_create
        
        args = [guid, attributes]
        # schedule create
        return self._schedule_event(callback, args, date, wait_events, pending)

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, date = None, wait_events = None, pending = True):
        callback = self._tc_connect
        args = [guid, connector, other_guid, other_box_id, other_connector]
        return self._schedule_event(callback, args, date, wait_events, pending)

    def postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, date = None, wait_events = None, pending = True):
        callback = self._tc_postconnect
        args = [guid, connector, other_guid, other_box_id, other_connector]
        return self._schedule_event(callback, args, date, wait_events, pending)

    def start(self, guid, date = None, wait_events = None, pending = True):
        callback = self._tc_start
        args = [guid]
        return self._schedule_event(callback, args, date, wait_events, pending)

    def stop_now(self):
        return self._stop()

    def stop(self, guid = None, date = None, wait_events = None,
            pending = True):
        if guid == None:
            callback = self._stop
        else:
            callback = self._tc_stop
        args = [guid]
        return self._schedule_event(callback, args, date, wait_events, pending)

    def set(self, guid, attr, value, date = None, wait_events = None,
            pending = True):
        callback = self._tc_set
        args = [guid, attr, value]
        return self._schedule_event(callback, args, date, wait_events, pending)
    
    def get(self, guid, attr, date = None, wait_events = None, pending = True):
        callback = self._tc_get
        args = [guid, attr]
        return self._schedule_event(callback, args, date, wait_events, pending)

    @property
    def _tcs(self):
        return [ rc for rc in self._resources.values() \
                if tags.TC in rc.tags ]

    def _stop(self):
        state = self.state()
        if state < ResourceState.STARTED:
            self._logger.debug("_stop(): FAIL, wrong state %d for EC" % (state))
            return (EventStatus.FAIL, "")

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
            self._logger.debug("_tc_stop(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

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
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_start(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        if state != ResourceState.CREATED:
            self._logger.debug("_tc_start(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

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
            (status, result) = rc.tc.shutdown()
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.SHUTDOWN
        elif state == ResourceState.NEW:
            rc.state = ResourceState.SHUTDOWN

        return (status, result)

    def _create(self, guid, attributes):
        state = self.state(guid)
        if state != ResourceState.NEW:
            self._logger.debug("_create(): FAIL, wrong state %d for TC guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        rc = self._resources.get(guid)
        tcrc_guid = rc.controller_guid
        tcrc = self._resources.get(rc.controller_guid)
        
        # Nested testbed
        if tcrc_guid and not (tcrc and tcrc.tc):
            # The TC is not yet created. We need to delay the event.
            self._logger.debug("_create(): RETRY, nested TC guid(%d). Waiting for TC guid(%d) to become ready." % (guid, tcrc_guid))
            return (EventStatus.RETRY, "")
        
        tc_class = self._tc_classes.get(rc.box_id)
        tc = tc_class(guid, attributes)
        rc.tc = tc
        rc.state = ResourceState.CREATED 

        return (EventStatus.SUCCESS, "")

    def _tc_create(self, guid, attributes):
        state = self.state(guid)
        if state != ResourceState.NEW:
            self._logger.debug("_tc_create(): FAIL, Wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        rc = self._resources.get(guid)
        tcrc_guid = rc.controller_guid
        tcrc = self._resources.get(rc.controller_guid)

        if not tcrc or not tcrc.tc:
            # The TC is not yet created. We need to delay the event.
            self._logger.debug("_tc_create(): RETRY, waiting for TC guid(%d) to become ready for guid(%d)" % (tcrc_guid, guid))
            return (EventStatus.RETRY, "")
        else:
            rc.tc = tcrc.tc

        (status, result) = rc.tc.create(guid, rc.box_id, attributes)
        if status == EventStatus.SUCCESS:
            rc.state = ResourceState.CREATED 
        return (status, result)

    def _tc_connect(self, guid, connector, other_guid, other_box_id, 
            other_connector, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_connect(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_connect(): RETRY,  wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.connect(guid, connector, other_guid, 
                other_box_id, other_connector, **kwargs)
        return (status, result)

    def _tc_postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_postconnect(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_postconnect(): RETRY,  wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.postconnect(guid, connector, other_guid,
                other_box_id, other_connector, **kwargs)
        return (status, result)

    def _tc_get(self, guid, attr): 
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_get(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_get(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.get(guid, attr)
        return (status, result)

    def _tc_set(self, guid, attr, value): 
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_get(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_get(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.set(guid, attr, value)
        return (status, result)

    def _save_ed(self, filename, xml):
        """ Persist experiment description to file """
        path = os.path.join(self._root_dir, filename)
        f = open(path, "w")
        f.write(xml)
        f.close()

    def _load_ed(self, filename):
        """ Load experiment description from file """
        path = os.path.join(self._root_dir, filename)
        f = open(path, "r")
        xml = f.read()
        f.close()
        return xml

    def _orchestrate_ed(self, modnames = None):
        def walk_create(box):
            if not [t for t in box.tags if t in [tags.EXPERIMENT, tags.CONTAINER]]:
                controller_guid = box.controller.guid if box.controller else None
                container_guid = box.container.guid if box.container else None
                attrs = dict((attr_name, getattr(box.a, attr_name).value) \
                        for attr_name in box.attributes)

                # schedule create
                eid_create = self.create(box.guid, box.box_id, container_guid,
                        controller_guid, box.tags, attrs, pending = False)

                # schedule connect
                wait_events = []
                for conn in box.connections:
                    (b, c_name, other_b, other_c_name) = conn

                    eid_conn = self.connect(b.guid, c_name, other_b.guid,
                            other_b.box_id, other_c_name, 
                            wait_events = [eid_create], pending = False)
                    wait_events.append(eid_conn)

                    eid_post = self.postconnect(b.guid, c_name, other_b.guid, 
                            other_b.box_id, other_c_name,
                            wait_events = [eid_conn], pending = False)
                    wait_events.append(eid_post)

                # schedule start
                eid_start = self.start(box.guid, wait_events = wait_events, 
                        pending = False)

            for b in box.boxes:
                walk_create(b)

        provider = create_provider(modnames)
        xml = self.original_ed_xml
        if xml:
            exp = provider.from_xml(xml)
            walk_create(exp)

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
                        self.__schedule_event(event, date, pending = False)
                        # difference in seconds
                        timeout = strfdiff(date, now)
                        self._proc_cond.acquire()
                        self._proc_cond.wait(timeout)
                        self._proc_cond.release()
                    elif [eid for eid in event.wait_events \
                            if self.poll(eid) in [EventStatus.RETRY, EventStatus.PENDING]]:
                        # re-schedule event in a delta of time
                        date = Event.DEFAULT_DELAY 
                        self.__schedule_event(event, date, pending = False)
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

    def _schedule_event(self, callback, args, date = None, wait_events = None,
            pending = True):
        event = Event(callback, args, wait_events)
        return self.__schedule_event(event, date, pending)

    def __schedule_event(self, event, date = None, pending = True):
        self._proc_cond.acquire()
        (date, eid, event) = self._scheduler.schedule(event, date)
        self._proc_cond.notify()
        self._proc_cond.release()

        if pending:
            self._add_pending_event(eid, event)
        return eid

    def _remove_event(self, event):
        self._proc_cond.acquire()
        self._scheduler.remove(event)
        self._proc_cond.release()

    def _execute_event(self, event):
        (status, result) = event.callback(*event.args, **event.kwargs)
        event.status = status
        event.result = result
        
        if status == EventStatus.RETRY:
            # result holds the criterion to determine what to do
            (event, date, status) = self._resolve_retry(event, result)

        # if status is still RETRY
        if status == EventStatus.RETRY:
            self.__schedule_event(event, date, pending = False)

    def _resolve_retry(self, event, result):
        status = EventStatus.RETRY
        date = Event.DEFAULT_DELAY
        if result:
            m = _retryre.match(result)
            if m:
                d = m.groupdict()
                if d['delay']:
                    # take what follows "delay:"
                    date = d['delay'][6:] 
                elif d['kwargs']:
                    # take what follows "kwargs:"
                    skwargs = d['kwargs'][7:]
                    event = self._kwargs_wrapper_event(event, skwargs)
                else:
                    status = EventStatus.FAIL
            else:
                status = EventStatus.FAIL

        return (event, date, status)

    def _kwargs_wrapper_event(self, event, skwargs):
        def _wrapper_event(event, rkwargs):
            for key, (guid, attr) in rkwargs.iteritems():
                if key not in event.kwargs:
                    guid = int(guid)
                    state = self.state(guid)
                    # we asume the resource will we created in the future.
                    # for now we need to wait.
                    if state == ResourceState.NOTEXIST:
                        return (EventStatus.RETRY, "")

                    # try to get the value
                    (status, result) = self._tc_get(guid, attr)
                    if status == EventStatus.SUCCESS:
                        event.kwargs[key] = result
                    else:
                        return (status, result)

            # re-schedule original event immediately
            self.__schedule_event(event, date = None, pending = False)
            return (EventStatus.SUCCESS, "")

        # require attributes to put in event.kwargs
        rkwargs = dict()
        for arg in skwargs.split(","):
            m = _kwargre.match(arg)
            key = m.groupdict()['key'] 
            guid = m.groupdict()['guid']
            attr = m.groupdict()['attr']
            rkwargs[key] = (guid, attr)

        callback = _wrapper_event
        args = [event, rkwargs]
        new_event = Event(callback, args)
        return new_event

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
        if not event:
            return None 

        return event.result

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
    def __init__(self, guid, attributes):
        super(TestbedController, self).__init__()
        self._guid = guid
        self._attributes = attributes
        self._start_time = None
        self._stop_time = None
        # testbed controller (TC) state
        self._state = ResourceState.CREATED

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
        raise NotImplementedError

    def recover(self):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def create(self, guid, box_id, container_guid, controller_guid, attributes):
        raise NotImplementedError

    def connect(self, guid, connector, other_guid, other_box_id, 
            other_connector, **kwargs):
        raise NotImplementedError

    def postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs): 
        raise NotImplementedError

    def start(self, guid):
        raise NotImplementedError

    def stop(self, guid):
        raise NotImplementedError

    def set(self, guid, attr, value):
        raise NotImplementedError

    def get(self, guid, attr):
        raise NotImplementedError


def create_ec(xml, root_dir = "/tmp", debug = False):
    return ExperimentController(xml, root_dir, debug)

