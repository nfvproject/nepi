
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
from nepi.design.events import BoxState as ResourceState
from nepi.design.events import ConditionType, EventType, make_condition
from nepi.util.parallel import ParallelRun

class EventStatus:
    SUCCESS = 0
    FAIL = 1
    RETRY = 2
    PENDING = 3
    INVALID = 4

_default_delay = "0.1s"

_strf = "%Y%m%d%H%M%S%f"
_reabs = re.compile("^\d{20}$")
_rerel = re.compile("^(?P<time>\d+(.\d+)?)(?P<units>h|m|s|ms|us)$")

def strfnow():
    return datetime.datetime.now().strftime(_strf)

def strfdiff(str1, str2):
    # Time difference in seconds without ignoring miliseconds
    d1 = datetime.datetime.strptime(str1, _strf)
    d2 = datetime.datetime.strptime(str2, _strf)
    diff = d1 - d2
    ddays = diff.days * 86400
    dus = round(diff.microseconds * 1.0e-06, 1) # PFFFFFF!! it seems condition.wait doesn't support arbitrary float numbers well!!
    ret = ddays + diff.seconds + dus
    
    # Avoid to saturate the procesor, if delay is 0 lets add 0.001
    # Also, the larger the delay is, the more stable the scheduling system
    # will behave. If the delay period is too short, and there are many
    # events around waiting for other events, chances are that the events are 
    # going to be rescheduled many times before the conditions are satisfied,
    # aftecting processing times
    return (ret or 0.001)

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

class Event(object):
    def __init__(self, callback, args):
        super(Event, self).__init__()
        self._callback = callback
        self._args = args
        # kwargs represent additional arguments than might be required
        # to execute an event. These arguments can be added by another
        # event once the initial execution of thisevent has been delayed
        # due to this missing information
        self.kwargs = dict()
        self.status = EventStatus.PENDING
        self.result = None

    @property
    def callback(self):
        return self._callback

    @property
    def args(self):
        return self._args

class EventWrapper(Event):
    def __init__(self, callback, event, conditions, ec):
        super(EventWrapper, self).__init__(callback, [])
        self._event = event
        self._conditions = conditions
        self._ec = ec

    def _done(self):
        # Invalidate current wrapper event in the pend_wapper_events list
        self._ec._pend_wrapper_events[self._event] = None
       
        # re-schedule original event immediately
        self._ec._do_schedule_event(self._event, pending = False, **self._conditions)
        return (EventStatus.SUCCESS, "")

class WaitEventsEventWrapper(EventWrapper):
    def __init__(self, event, wait_eids, conditions, ec):
        callback = self._wait_events_callback
        super(WaitEventsEventWrapper, self).__init__(callback, event, conditions, ec)
        self._wait_events = [self._ec._pend_events[eid] for eid in wait_eids]

    def next_date(self):
        # It is possible that the event(s) for which we need to wait for
        # are wrapped as other events, so we need to take this into account 
        
        events = [self._ec._pend_wrapper_events[event] \
                if event in self._ec._pend_wrapper_events else event \
                for event in self._wait_events]

        # peek[0] == date
        max_date = max(self._ec._scheduler.peek(e)[0] for e in events)
        
        # We need to return a bigger date than the maximum scheduled date. 
        # To achieve this we just sum 1 to the max_date
        return "" if not max_date else  str(int(max_date) + 1)

    def _wait_events_callback(self):
        # Check if there are still events to wait for
        wait_events = [e for e in self._wait_events \
                if e.status in [EventStatus.RETRY, EventStatus.PENDING]]
        
        if wait_events:
            # re-schedule event in a date posterior to the last event
            date = self.next_date()
            result = dict({ConditionType.DATE: date})
            return (EventStatus.RETRY, result)

        return self._done() 

class WaitValuesEventWrapper(EventWrapper):
    def __init__(self, event, wait_values, conditions, ec):
        callback = self._wait_values_callback
        super(WaitValuesEventWrapper, self).__init__(callback, event, conditions, ec)
        self._wait_values = wait_values

    def _wait_values_callback(self):
        for key, (guid, attr, oper, value) in self._wait_values.iteritems():
            if key not in self._event.kwargs:
                state = self._ec.state(guid)
                # we asume the resource will we created in the future.
                # for now we need to wait.
                if state == ResourceState.NOTEXIST:
                    return (EventStatus.RETRY, "")

                # try to get the value 
                (status, result) = self._ec._tc_get(guid, attr, None, None)
                if status != EventStatus.SUCCESS:
                    return (status, result)
                
                # If the condition is not satisfied we need to wait until it is
                if ( oper and not eval("'%s' %s '%s'" % (result, oper, value))):
                    return (EventStatus.RETRY, "")
                   
                self._event.kwargs[key] = result

        return self._done() 

class WaitStatesEventWrapper(EventWrapper):
    def __init__(self, event, wait_states, conditions, ec):
        callback = self._wait_states_callback
        super(WaitStatesEventWrapper, self).__init__(callback, event, conditions, ec)
        self._wait_states = wait_states

    def _wait_states_callback(self):
        for (guid, oper, state) in self._wait_states:
            rstate = self._ec.state(guid)
            # If the condition is not satisfied we need to wait until it is
            if ( not eval(str(rstate) + " " + oper + " " + state) ):
                return (EventStatus.RETRY, "")
        
        return self._done() 


class HeapScheduler(object):
    def __init__(self):
        super(HeapScheduler, self).__init__()
        self._events = list() 
        self._event_idx = dict()
        self._eid = itertools.count(1)
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

    def peek(self, event):
        try:
            return self._event_idx[event]
        except:
            return (None, None, None)

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
    def container_guid(self):
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

        self._start_time = None
        self._stop_time = None

        # Initial experiment description (ED)
        self._original_ed_xml = "original_experiment_description.xml"
        self._save_ed(self._original_ed_xml, ed_xml)
         
        # Incremental runtime ED - Only events are added to the original ED
        #   allowing to reproduce every thing that happend during the experiment
        self._incremental_ed_xml = "incremental_experiment_description.xml"
        self._save_ed(self._incremental_ed_xml, ed_xml)
       
        # Instant runtime ED - Provide a picture of the current state of the experiment
        self._instant_ed_xml = "instant_experiment_description.xml"
        self._save_ed(self._instant_ed_xml, ed_xml)

        # Box provider
        self._provider = None
        # Experiment box - It will be used to keep track of the changes
        #   on the experiment attributes during runtime, allowing to
        #   persist the runtime ED to xml
        self._exp = None

        # Incremental experiment box - It will be used to keep track of all
        #   executed events (incremental changes), allowing to reproduce the
        #   experiment execution
        self._oexp = None
        
        # Experiment controller (EC) state
        self._state = ResourceState.NEW

        # Testbed controller (TC) classes - They will be used to instatiate
        #   the TCs
        self._tc_classes = dict()
        
        # Resources
        self._resources = dict()
        
        # Scheduler
        self._scheduler = HeapScheduler()

        # Event processing thread
        self._proc_thread = threading.Thread(target=self._process_events)
        self._proc_cond = threading.Condition()
        # Flag to signal to stop processing events
        self._proc_stop = False

        # Pending events - The initial eid associated to an event is 
        #   added to the pending event list, allowing to query the 
        #   status of the event
        self._pend_events = dict()
        self._pend_wrapper_events = dict()
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
    def instant_ed_xml(self):
        path = os.path.join(self._root_dir, self._instant_ed_xml)
        return self._load_ed(path)

    @property
    def incremental_ed_xml(self):
        path = os.path.join(self._root_dir, self._incremental_ed_xml)
        return self._load_ed(path)

    @property
    def start_time(self):
        return self._start_time

    @property
    def stop_time(self):
        return self._stop_time

    def poll(self, eid):
        return self._poll_pending_event(eid)

    def result(self, eid):
        return self._result_pending_event(eid)

    def remove(self, eid):
        return self._remove_pending_event(eid)

    def list_events(self):
        return self._list_pending_events()

    def run(self, modnames = None):
        self._load_testbed_controllers(modnames)
        self._provider = create_provider(modnames)
        # Orchestrate experiment by translating the experiment
        # description into scheduled events
        self._orchestrate()
        
        # Start event-processing thread
        self._start_time = strfnow()
        self._proc_thread.start()

    def state(self, guid = None):
        if guid == None:
            return self._state
        else:
            rc = self._resources.get(guid)
            if not rc: 
                return ResourceState.NOTEXIST
            # Once the resource is started, it is 
            # the TC who holds the real current state 
            if rc.state == ResourceState.STARTED:
                return rc.tc.state(guid) 
            return rc.state

    def clean_events(self, eids, **conditions):
        pending = False
        callback = self._clean_events
        args = [eids]
        # The scheduled event has as condition wait_events = [eids], because it
        # needs to wait until all events are done before erasing them
        return self._schedule_event(callback, args, pending, 
                wait_events = eids)

    def flush(self, pending = True, **conditions):
        callback = self._flush
        args = []
        
        return self._schedule_event(callback, args, pending, **conditions)

    def recover(self, guid = None):
        # TODO! 
        pass

    def shutdown_now(self):
        return self._shutdown(None, None)

    def shutdown(self, guid = None, pending = True, track = True, **conditions):
        if guid == None:
            callback = self._shutdown
        else:
            callback = self._tc_shutdown

        args = [track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def create(self, guid, box_id, container_guid, controller_guid, box_tags,
            attributes, pending = True, track = True, **conditions):
        # We need to create the new resource first
        rc = Resource(guid, box_id, container_guid, controller_guid, box_tags)
        self._resources[guid] = rc

        if tags.TC in box_tags:
            callback = self._create
        else:
            callback = self._tc_create
        
        args = [guid, attributes, track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, pending = True,  track = True, **conditions):
        callback = self._tc_connect
        args = [guid, connector, other_guid, other_box_id, other_connector,
                track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def postconnect(self, guid, connector, other_guid, other_box_id, 
            other_connector, pending = True, track = True, **conditions):
        callback = self._tc_postconnect
        args = [guid, connector, other_guid, other_box_id, other_connector,
                track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def start(self, guid, pending = True, track = True, **conditions):
        callback = self._tc_start
        args = [guid, track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def stop_now(self):
        return self._stop()

    def stop(self, guid = None, pending = True, track = True, **conditions):
        if guid == None:
            callback = self._stop
        else:
            callback = self._tc_stop

        args = [guid, track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def set(self, guid, attr, value, pending = True, track = True, **conditions):
        callback = self._tc_set
        args = [guid, attr, value, track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)
    
    def get(self, guid, attr, pending = True, track = True, **conditions):
        callback = self._tc_get
        args = [guid, attr, track, conditions]
        return self._schedule_event(callback, args, pending, **conditions)
 
    def command(self, guid, command, pending = True, track = True, **conditions):
        callback = self._tc_command
        args = [guid, command, cck, onditions]
        return self._schedule_event(callback, args, pending, **conditions)

    def set_graphical_info(self, guid, x, y, height, width, hidden, 
            pending = True, **conditions):
        callback = self._set_graphical_info
        args = [guid, x, y, height, width, hidden]
        return self._schedule_event(callback, args, pending, **conditions)

    @property
    def _tcs(self):
        return [ rc for rc in self._resources.values() \
                if tags.TC in rc.tags ]

    def _stop(self, track, conditions, **kwargs):
        state = self.state()
        if state < ResourceState.STARTED:
            self._logger.debug("_stop(): FAIL, wrong state %d for EC" % (state))
            return (EventStatus.FAIL, "")

        status = EventStatus.SUCCESS
        result = ""
        if state == ResourceState.STARTED:
            # Stop all TCs
            for tc in self._tcs:
                (status, result) = self._tc_stop(tc.guid, None, None)
                if status != EventStatus.SUCCESS:
                    return (status, result)
 
            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                self._oexp.e.stop.on(conditions)
       
            self.__stop()
        return (status, result)

    def __stop(self):
        self._stop_time = strfnow()
        self._state = ResourceState.STOPPED

    def _tc_stop(self, guid, track, conditions, **kwargs):
        state = self.state(guid)
        if state < ResourceState.STARTED:
            self._logger.debug("_tc_stop(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        status = EventStatus.SUCCESS
        result = ""

        if state in [ResourceState.STARTED, ResourceState.RUNNING]:
            rc = self._resources.get(guid)
            (status, result) = rc.tc.stop(guid, **kwargs)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.STOPPED

                # Track event
                if track:
                    conditions = self._make_conditions(conditions)
                    box = self._oexp.box(guid)
                    box.e.stop.on(conditions)
               
        return (status, result)

    def _tc_start(self, guid, track, conditions, **kwargs):
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
        (status, result) = rc.tc.start(guid, **kwargs)
        if status == EventStatus.SUCCESS:
            rc.state = ResourceState.STARTED

            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                box = self._oexp.box(guid)
                box.e.start.on(conditions)

        return (status, result)

    def _shutdown(self, track, conditions, **kwargs):
        status = EventStatus.SUCCESS
        result = ""
        
        # Shutdown all TCs
        for tc in self._tcs:
            (status, result) = self._tc_shutdown(tc.guid, None, None)
            if status != EventStatus.SUCCESS:
                return (status, result)

        # Track event
        if track:
            conditions = self._make_conditions(conditions)
            self._oexp.e.shutdown.on(conditions)

        self._proc_stop = True
        self._proc_cond.acquire()
        self._proc_cond.notify()
        self._proc_cond.release()
        if self._proc_thread.is_alive():
           self._proc_thread.join()
        return (status, result)

    def _tc_shutdown(self, guid, track, conditions, **kwargs):
        state = self.state(guid)
        status = EventStatus.SUCCESS
        result = ""

        rc = self._resources.get(guid)
        if state >= ResourceState.CREATED and state < ResourceState.SHUTDOWN:
            (status, result) = rc.tc.shutdown(**kwargs)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.SHUTDOWN
        elif state == ResourceState.NEW:
            rc.state = ResourceState.SHUTDOWN

        if status == EventStatus.SUCCESS:
            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                box = self._oexp.box(guid)
                box.e.shutdown.on(conditions)

        return (status, result)

    def _create(self, guid, attributes, track, conditions, **kwargs):
        state = self.state(guid)
        if state != ResourceState.NEW:
            self._logger.debug("_create(): FAIL, wrong state %d for TC guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        rc = self._resources.get(guid)
        tcrc_guid = rc.controller_guid
        tcrc = self._resources.get(rc.controller_guid)
        
        # Nested testbed case
        if tcrc_guid and not (tcrc and tcrc.tc):
            # The parent TC is not yet created. We need to delay the event.
            self._logger.debug("_create(): RETRY, nested TC guid(%d). Waiting for TC guid(%d) to become ready." % (guid, tcrc_guid))
            return (EventStatus.RETRY, "")
     
        tc_class = self._tc_classes.get(rc.box_id)
        tc = tc_class(guid, attributes)
        rc.tc = tc
        rc.state = ResourceState.CREATED

        # We now need to add the created box to the experiment design
        container = self._exp
        if rc.container_guid:
            container = self._exp.box(rc.container_guid)
        self._provider.create(rc.box_id, guid = guid, container = container,
                **attributes)

        # Track event
        if track:
            conditions = self._make_conditions(conditions)

            # If this event resulted in the creation of a new box, this box
            # need to be added in the self._oexp too
            if not self._oexp.box(guid):
                container = self._oexp.box(rc.container_guid)
                self._provider.create(rc.box_id, guid = guid, container = container,
                        **attributes)
     
            box = self._oexp.box(guid)
            box.e.create.on(conditions)
     
        return (EventStatus.SUCCESS, "")

    def _tc_create(self, guid, attributes, track, conditions, **kwargs):
        state = self.state(guid)
        if state != ResourceState.NEW:
            self._logger.debug("_tc_create(): FAIL, Wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")

        rc = self._resources.get(guid)
        tcrc_guid = rc.controller_guid
        tcrc = self._resources.get(rc.controller_guid)

        if not tcrc or not tcrc.tc:
            # The TC is not yet created. We need to delay the event
            self._logger.debug("_tc_create(): RETRY, waiting for TC guid(%d) to become ready for guid(%d)" % (tcrc_guid, guid))
            return (EventStatus.RETRY, "")
        else:
            rc.tc = tcrc.tc

        status = EventStatus.SUCCESS
        # Containers are dummy components and should not be created in the TCs       
        if tags.CONTAINER not in rc.tags:
            (status, result) = rc.tc.create(guid, rc.box_id, attributes, **kwargs)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.CREATED 

        if status == EventStatus.SUCCESS:
            # We now need to add the created box to the experiment design 
            container = self._exp
            if rc.container_guid:
                container = self._exp.box(rc.container_guid)
            self._provider.create(rc.box_id, guid = guid, container = container,
                    **attributes)
     
            # Track event
            if track:
                conditions = self._make_conditions(conditions)

                # If this event resulted in the creation of a new box, this box
                # need to be added in the self._oexp too
                if not self._oexp.box(guid):
                    container = self._oexp.box(rc.container_guid)
                    self._provider.create(rc.box_id, guid = guid, container = container,
                            **attributes)
        
                box = self._oexp.box(guid)
                box.e.create.on(conditions)

        return (status, result)

    def _tc_connect(self, guid, connector, other_guid, other_box_id, 
            other_connector, track, conditions, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_connect(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
         
        other_state = self.state(other_guid)
        if other_state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_connect(): FAIL, wrong state %d for guid(%d)" % (
                    other_state, other_guid))
            return (EventStatus.FAIL, "")
        
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_connect(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")
 
        if other_state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_connect(): RETRY,  wrong state %d for guid(%d)" % (
                    other_state, other_guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.connect(guid, connector, other_guid, 
                other_box_id, other_connector, **kwargs)

        if status == EventStatus.SUCCESS:
            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                args = (connector, other_guid, other_box_id, other_connector)
                box = self._oexp.box(guid)
                box.e.connect.on(conditions, args)

        return (status, result)

    def _tc_postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, track, conditions, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_postconnect(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        other_state = self.state(other_guid)
        if other_state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_postconnect(): FAIL, wrong state %d for guid(%d)" % (
                    other_state, other_guid))
            return (EventStatus.FAIL, "")
        
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_postconnect(): RETRY,  wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        if other_state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_postconnect(): RETRY,  wrong state %d for guid(%d)" % (
                    other_state, other_guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.postconnect(guid, connector, other_guid,
                other_box_id, other_connector, **kwargs)

        if status == EventStatus.SUCCESS:
            # We now need to connect the boxes in the experiment design
            box = self._exp.box(guid)
            other_box = self._exp.box(other_guid)
            conn = getattr(box.c, connector)
            other_conn = getattr(other_box.c, other_connector)
            conn.connect(other_conn)

        return (status, result)

    def _tc_get(self, guid, attr, track, conditions, **kwargs): 
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_get(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_get(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        # Track event
        if track:
            conditions = self._make_conditions(conditions)
            args = (attr)
            box = self._oexp.box(guid)
            box.e.get.on(conditions, args)

        rc = self._resources.get(guid)
        (status, result) = rc.tc.get(guid, attr, **kwargs)

        if status == EventStatus.SUCCESS:
            # We take the opportunity to update the local box value, 
            # in case it changed on the TC side
            box = self._exp.box(guid)
            attr = getattr(box.a, attr)
            attr.value = result

        return (status, result)

    def _tc_set(self, guid, name, value, track, conditions, **kwargs): 
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_get(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_get(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.set(guid, name, value, **kwargs)

        if status == EventStatus.SUCCESS:
            # We need to update the local box attribute value
            box = self._exp.box(guid)
            attr = getattr(box.a, name)
            attr.value = value

            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                args = (name, value)
                box = self._oexp.box(guid)
                box.e.set.on(conditions, args)

        return (status, result)

    def _tc_command(self, guid, command, track, conditions, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_command(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_command(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.command(guid, comand, **kwargs)
 
        if status == EventStatus.SUCCESS:
            # Track event
            if track:
                conditions = self._make_conditions(conditions)
                args = (command)
                box = self._oexp.box(guid)
                box.e.command.on(conditions, args)
           
        return (status, result)

    def _set_graphical_info(self, guid, x, y, height, width, hidden):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_set_graphical_info(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state < ResourceState.CREATED:
            self._logger.debug("_set_graphical_info(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        box = self._exp.box(guid)
        box.graphical_info.x = x
        box.graphical_info.y = y
        box.graphical_info.height = height
        box.graphical_info.width = width
        box.graphical_info.hidden = hidden
        return (EventStatus.SUCCESS, "")

    def _clean_events(self, eids):
        for eid in eids:
            self.remove(eid)
        return (EventStatus.SUCCESS, "")

    def _flush(self):
        """ Persists runtime experiment description to file """
        ed_xml = self._exp.xml
        self._save_ed(self._instant_ed_xml, ed_xml)

        ed_xml = self._oexp.xml
        self._save_ed(self._incremental_ed_xml, ed_xml)
        return (EventStatus.SUCCESS, "")

    def _orchestration_done(self):
        self._state = ResourceState.STARTED
        return (EventStatus.SUCCESS, "")
 
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

    def _orchestrate(self):
        def walk_create(box, start_boxes, post_events, pending_events):
            if tags.EXPERIMENT not in box.tags:
                controller_guid = box.controller.guid if box.controller else None
                container_guid = box.container.guid if box.container else None
                attrs = dict((attr_name, getattr(box.a, attr_name).value) \
                        for attr_name in box.attributes if \
                        getattr(box.a, attr_name).value is not None)
                            
                # Delete all events from the self._oexp box to make sure that
                # original events will not appear twice
                events = list(box.events)
                box.delete_all_events()

                # Schedule the events created during design
                start_scheduled = False
                create_scheduled = False
                scheduled_conns = dict()
                for (event_id, type, args, conditions) in events:
                    if type == EventType.START:
                        eid = self.start(box.guid, **conditions)
                        start_scheduled = True
                    elif type == EventType.STOP:
                        eid = self.stop(box.guid, **conditions)
                    elif type == EventType.SHUTDOWN:
                        eid = self.shutdown(box.guid, **conditions)
                    elif type == EventType.CREATE:
                        eid = eid_create = self.create(box.guid, box.box_id, container_guid,
                                controller_guid, box.tags, attrs, **conditions)
                        create_scheduled = True
                    elif type == EventType.SET:
                        (name, value) = args
                        eid = self.set(box.guid, name, value, **conditions)
                    elif type == EventType.GET:
                        (name) = args
                        eid = self.get(box.guid, name, **conditions)
                    elif type == EventType.COMMANDS:
                        (command) = args
                        eid = self.command(box.guid, command, **conditions)
                    elif type == EventType.CONNECTION:
                        (connector, other_guid, other_box_id, other_connector) = args
                        eid = self.connect(box.guid, connector, other_guid, other_box_id, 
                            other_connector, **conditions)
                        scheduled_cons[args] = eid
                    else:
                        continue

                    # switch the eid in the event pending list for the
                    # eid (event_id) generated during design
                    event = self._pend_events[eid]
                    self._pend_lock.acquire()
                    del self._pend_events[eid]
                    self._pend_events[event_id] = event
                    self._pend_lock.release()

                # Schedule create
                if not create_scheduled:
                    eid_create = self.create(box.guid, box.box_id, container_guid,
                            controller_guid, box.tags, attrs, track = False)
                    pending_events.append(eid_create)

                # Schedule set graphical info
                gi = box.graphical_info
                eid_gi = self.set_graphical_info(box.guid, gi.x, gi.y,
                        gi.height, gi.width, gi.hidden) 
                pending_events.append(eid_gi)

                # Schedule connect & postconnect
                for conn in box.connections:
                    (b, c_name, other_b, other_c_name) = conn

                    if conn in scheduled_conns:
                        eid_conn = scheduled_conns[conn]
                    else:
                        eid_conn = self.connect(b.guid, c_name, other_b.guid,
                                other_b.box_id, other_c_name, track = False)
                        pending_events.append(eid_conn)

                    eid_post = self.postconnect(b.guid, c_name, other_b.guid, 
                            other_b.box_id, other_c_name, track = False,
                            wait_events = [eid_conn])
                    pending_events.append(eid_post)
                    post_events.append(eid_post)

                if not start_scheduled:
                    start_boxes.append(box)

            for b in box.boxes:
                walk_create(b, start_boxes, post_events, pending_events)

        def schedule_start(start_boxes, post_events):
            for box in start_boxes:
                start_eid = self.start(box.guid, pending = False, track = False)

        xml = self.original_ed_xml

        self._exp = self._provider.create("Experiment")
        if not xml:
            self._oexp = self._provider.from_xml(self._exp.xml)
            self._state = ResourceState.STARTED
        else:
            # By default, only after all boxes are created and connected they 
            # can be started. 'start_boxes' keeps track of all the boxes whose 
            # default start behavior has not been modifiyed by the user, by 
            # defining a special start event
            start_boxes = []
            # eids of all post_connect events. These are going to be the 
            # wait_events for the 'start' events with default behavior
            post_events = []
            # pending events that need to be removed from the pending list
            # when orchestration is finished.
            # We don't add the start events eids to the pending_events array
            # because the experiment should be marked as STARTED when
            # all resources are connected, and not when all resources are 
            # STARTED. Some resources could only start in the middle of the 
            # experiment exceution.
            pending_events = []

            self._oexp = self._provider.from_xml(xml)
            walk_create(self._oexp, start_boxes, post_events, pending_events)
            schedule_start(start_boxes, post_events)

            # Persist runtime experiment description once all events have
            # been executed
            flush_eid = self.flush(wait_events = pending_events)
            pending_events.append(flush_eid)

            # set state to STARTED once all epnding events are executed
            start_eid = self._schedule_event(self._orchestration_done, [], 
                    wait_events = pending_events)
            pending_events.append(start_eid)
 
            # Schedule to clean pending events
            self.clean_events(pending_events)

    def _process_events(self):
        runner = ParallelRun(maxthreads = 20)
        runner.start()

        try:
            while not self._proc_stop:
                self._proc_cond.acquire()
                if self._scheduler.is_empty: 
                    self._proc_cond.wait()
                (date, eid, event) = self._scheduler.next()
                self._proc_cond.release()

                #print "EVENT", eid, date, id(event) if event else "None", event.callback.func_name if event else "None", event._event.callback.func_name if event and hasattr(event, "_event") else "None", id(event._event) if event and hasattr(event, "_event") else "None"

                if event:
                    # If date is in the future, thread needs to wait
                    # until time elapse or until another event is scheduled
                    now = strfnow()
                    if now < date:
                        # Re-schedule event at same date
                        eid = self._do_schedule_event(event, pending = False, date = date)
                        # Caluclate time difference in seconds
                        timeout = strfdiff(date, now)
                        # Sleep until time elapsed or the scheduling of a new
                        # event awakes the condition
                        self._proc_cond.acquire()
                        self._proc_cond.wait(timeout)
                        self._proc_cond.release()
                    else:
                        # Process events in parallel
                        runner.put(self._execute_event, event)
        except:  
            self._state = ResourceState.FAILED 
            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while processing events in the EC: %s" % err)
 
        #runner.join()

    def _schedule_event(self, callback, args, pending = True, **conditions):
        event = Event(callback, args)
        return self._do_schedule_event(event, pending, **conditions)

    def _do_schedule_event(self, event, pending = True, **conditions):
        # In case there are conditions (Ex: events to wait for), a wrapper event
        # will be created and scheduled instead of the original event.
        # The wrapper event will verify the required condition, and only when this
        # condition is satisfied, it will schedule the original event
        initial_event = event
        wrapper_event = None
        date = None

        if conditions:
            (event, date, failed) = self._resolve_conditions(initial_event, **conditions)
            wrapper_event = event

            if failed:
                # Condition could not be resolved. Event can't be scheduled
                return None

        self._proc_cond.acquire()
        (date, eid, event) = self._scheduler.schedule(event, date)
        self._proc_cond.notify()
        self._proc_cond.release()

        # The initial event will be added to the pending events list,
        # instead of the wrapper event. We want the user to be able to 
        # query the status of the right event
        if pending:
            self._add_pending_event(eid, initial_event, wrapper_event)

        return eid

    def _remove_event(self, event):
        self._proc_cond.acquire()
        self._scheduler.remove(event)
        self._proc_cond.release()

    def _execute_event(self, event):
        try:
            (status, result) = event.callback(*event.args, **event.kwargs)
            event.status = status
            event.result = result

            if status == EventStatus.RETRY:
                conditions = result or dict({'date': _default_delay})
                eid = self._do_schedule_event(event, pending = False, **conditions)
        except:
            # If an exception occurs while executing the callback, the
            # event should be marked as FAILED
            event.status = EventStatus.FAIL

            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while executing event: %s" % err)
 
    def _resolve_conditions(self, event, **conditions):
        failed = True
        ddate = None

        if ConditionType.DATE in conditions:
            # We invoke make_condition because we need a uniform representation
            # of the conditions. They can be provided as a Condition object, 
            # a string condition, or a formatted condition, we need a Condition object.
            condition = make_condition(ConditionType.DATE, 
                    conditions[ConditionType.DATE])
            ddate = condition.condition
            failed = False
        
        if ConditionType.WAIT_EVENTS in conditions:
            condition = make_condition(ConditionType.WAIT_EVENTS, 
                    conditions[ConditionType.WAIT_EVENTS])
            del conditions[ConditionType.WAIT_EVENTS]
            wait_eids = condition.condition
            event = WaitEventsEventWrapper(event, wait_eids, conditions, self)
            ddate = event.next_date()
            failed = False
         
        if ConditionType.WAIT_VALUES in conditions:
            condition = make_condition(ConditionType.WAIT_VALUES, 
                    conditions[ConditionType.WAIT_VALUES])
            del conditions[ConditionType.WAIT_VALUES]
            wait_values = condition.condition
            event = WaitValuesEventWrapper(event, wait_values, conditions, self)
            failed = False
          
        if ConditionType.WAIT_STATES in conditions:
            condition = make_condition(ConditionType.WAIT_STATES, 
                    conditions[ConditionType.WAIT_STATES])
            del conditions[ConditionType.WAIT_STATES]
            wait_states = condition.condition
            event = WaitStatesEventWrapper(event, wait_states, conditions, self)
            failed = False
        
        return (event, ddate, failed)

    def _add_pending_event(self, eid, event, wrapper_event = None):
        self._pend_lock.acquire()
        self._pend_events[eid] = event
        if wrapper_event:
            self._pend_wrapper_events[event] = wrapper_event
        self._pend_lock.release()

    def _remove_pending_event(self, eid):
        event = self._pend_events.get(eid)
        
        wrapper_event = None
        if event in self._pend_wrapper_events:
            wrapper_event = self._pend_wrapper_events[event]

        if event: 
            self._pend_lock.acquire()
            del self._pend_events[eid]
            if wrapper_event:
                del self._pend_wrapper_events[event]
            self._pend_lock.release()

            self._remove_event(event)
            if wrapper_event:
                self._remove_event(wrapper_event)
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

    def _list_pending_events(self):
        return self._pend_events.keys()

    def _load_testbed_controllers(self, modnames = None):
        if modnames == None:
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

    def _make_conditions(self, conditions):
        if not conditions:
            now = strfnow()
            start = self._start_time
            delay = "%.2fs" % strfdiff(now, start)
            conditions = dict({ConditionType.DATE: delay})
        return conditions


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
        return self._start_time

    @property
    def stop_time(self):
        return self._stop_time

    def state(self, guid):
        raise NotImplementedError

    def recover(self):
        raise NotImplementedError

    def shutdown(self, **kwargs):
        raise NotImplementedError

    def create(self, guid, box_id, container_guid, controller_guid, 
            attributes, **kwargs):
        raise NotImplementedError

    def connect(self, guid, connector, other_guid, other_box_id, 
            other_connector, **kwargs):
        raise NotImplementedError

    def postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs): 
        raise NotImplementedError

    def start(self, guid, **kwargs):
        raise NotImplementedError

    def stop(self, guid, **kwargs):
        raise NotImplementedError

    def set(self, guid, attr, value, **kwargs):
        raise NotImplementedError

    def get(self, guid, attr, **kwargs):
        raise NotImplementedError

    def command(self, guid, command, **kwargs):
        raise NotImplementedError


def create_ec(xml, root_dir = "/tmp", debug = False):
    return ExperimentController(xml, root_dir, debug)

