
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
        
        # Runtime ED
        self._runtime_ed_xml = "runtime_experiment_description.xml"
        self._save_ed(self._runtime_ed_xml, ed_xml)

        # Box provider
        self._provider = None
        # Experiment design box - It will be used to keep track of the
        #   changes on the experiment design during runtime, allowing
        #   to persist the runtime ED to xml
        self._exp_box = None
        
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

    def clean_events(self, eids, date = None):
        pending = False
        callback = self._clean_events
        args = [eids]
        # The scheduled event has as condition wait_events = [eids], because it
        # needs to wait until all events are done before erasing them
        return self._schedule_event(callback, args, date, pending, 
                wait_events = eids)

    def flush(self, date = None, pending = True, **conditions):
        callback = self._flush
        args = []
        
        return self._schedule_event(callback, args, date, pending, **conditions)

    def recover(self, guid = None):
        # TODO! 
        pass

    def shutdown_now(self):
        return self._shutdown()

    def shutdown(self, guid = None, date = None, pending = True, **conditions):
        if guid == None:
            callback = self._shutdown
        else:
            callback = self._tc_shutdown
        args = []
        
        return self._schedule_event(callback, args, date, pending, **conditions)

    def create(self, guid, box_id, container_guid, controller_guid, box_tags,
            attributes, date = None, pending = True, **conditions):
        # We need to create the new resource first
        rc = Resource(guid, box_id, container_guid, controller_guid, box_tags)
        self._resources[guid] = rc

        if tags.TC in box_tags:
            callback = self._create
        else:
            callback = self._tc_create
        
        args = [guid, attributes]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, date = None, pending = True, **conditions):
        callback = self._tc_connect
        args = [guid, connector, other_guid, other_box_id, other_connector]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def postconnect(self, guid, connector, other_guid, other_box_id, 
            other_connector, date = None, pending = True, **conditions):
        callback = self._tc_postconnect
        args = [guid, connector, other_guid, other_box_id, other_connector]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def start(self, guid, date = None, pending = True, **conditions):
        callback = self._tc_start
        args = [guid]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def stop_now(self):
        return self._stop()

    def stop(self, guid = None, date = None, pending = True, **conditions):
        if guid == None:
            callback = self._stop
        else:
            callback = self._tc_stop
        args = [guid]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def set(self, guid, attr, value, date = None, pending = True, **conditions):
        callback = self._tc_set
        args = [guid, attr, value]
        return self._schedule_event(callback, args, date, pending, **conditions)
    
    def get(self, guid, attr, date = None, pending = True, **conditions):
        callback = self._tc_get
        args = [guid, attr]
        return self._schedule_event(callback, args, date, pending, **conditions)
 
    def command(self, guid, command, date = None, pending = True, **conditions):
        callback = self._tc_command
        args = [guid, command]
        return self._schedule_event(callback, args, date, pending, **conditions)

    def set_graphical_info(self, guid, x, y, height, width, hidden, 
            date = None, pending = True, **conditions):
        callback = self._set_graphical_info
        args = [guid, x, y, height, width, hidden]
        return self._schedule_event(callback, args, date, pending, **conditions)

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

        self._proc_stop = True
        self._proc_cond.acquire()
        self._proc_cond.notify()
        self._proc_cond.release()
        if self._proc_thread.is_alive():
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
        container = self._exp_box
        if rc.container_guid:
            container = self._exp_box.box(rc.container_guid)
        self._provider.create(rc.box_id, guid = guid, container = container,
                **attributes)

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
            # The TC is not yet created. We need to delay the event
            self._logger.debug("_tc_create(): RETRY, waiting for TC guid(%d) to become ready for guid(%d)" % (tcrc_guid, guid))
            return (EventStatus.RETRY, "")
        else:
            rc.tc = tcrc.tc

        status = EventStatus.SUCCESS
        # Containers are dummy components and should not be created in the TCs       
        if tags.CONTAINER not in rc.tags:
            (status, result) = rc.tc.create(guid, rc.box_id, attributes)
            if status == EventStatus.SUCCESS:
                rc.state = ResourceState.CREATED 

        if status == EventStatus.SUCCESS:
            # We now need to add the created box to the experiment design 
            container = self._exp_box
            if rc.container_guid:
                container = self._exp_box.box(rc.container_guid)
            self._provider.create(rc.box_id, guid = guid, container = container,
                    **attributes)

        return (status, result)

    def _tc_connect(self, guid, connector, other_guid, other_box_id, 
            other_connector, **kwargs):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.STOPPED, ResourceState.FINISHED,
                ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_connect(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state not in [ResourceState.CREATED, ResourceState.STARTED, ResourceState.RUNNING]:
            self._logger.debug("_tc_connect(): RETRY, wrong state %d for guid(%d)" % (state, guid))
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

        if status == EventStatus.SUCCESS:
            # We now need to connect the boxes in the experiment design
            box = self._exp_box.box(guid)
            other_box = self._exp_box.box(other_guid)
            conn = getattr(box.c, connector)
            other_conn = getattr(other_box.c, other_connector)
            conn.connect(other_conn)

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

        if status == EventStatus.SUCCESS:
            # We take the opportunity to update the local box value, 
            # in case it changed on the TC side
            box = self._exp_box.box(guid)
            attr = getattr(box.a, attr)
            attr.value = result

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

        if status == EventStatus.SUCCESS:
            # We need to update the local box attribute value
            box = self._exp_box.box(guid)
            attr = getattr(box.a, attr)
            attr.value = value

        return (status, result)

    def _tc_command(self, guid, command): 
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_tc_command(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state in [ResourceState.NOTEXIST, ResourceState.NEW]:
            self._logger.debug("_tc_command(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        rc = self._resources.get(guid)
        (status, result) = rc.tc.command(guid, comand)
        
        return (status, result)

    def _set_graphical_info(self, guid, x, y, height, width, hidden):
        state = self.state(guid)
        if state in [ResourceState.FAILED, ResourceState.SHUTDOWN]:
            self._logger.debug("_set_graphical_info(): FAIL, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.FAIL, "")
        
        if state < ResourceState.CREATED:
            self._logger.debug("_set_graphical_info(): RETRY, wrong state %d for guid(%d)" % (state, guid))
            return (EventStatus.RETRY, "")

        box = self._exp_box.box(guid)
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
        ed_xml = self._exp_box.xml
        self._save_ed(self._runtime_ed_xml, ed_xml)
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

                # Schedule create
                eid_create = self.create(box.guid, box.box_id, container_guid,
                        controller_guid, box.tags, attrs)
                pending_events.append(eid_create)

                # Schedule set graphical info
                gi = box.graphical_info
                eid_gi = self.set_graphical_info(box.guid, gi.x, gi.y,
                        gi.height, gi.width, gi.hidden, 
                        wait_events = [eid_create])
                pending_events.append(eid_gi)

                # Schedule connect & postconnect
                for conn in box.connections:
                    (b, c_name, other_b, other_c_name) = conn

                    eid_conn = self.connect(b.guid, c_name, other_b.guid,
                            other_b.box_id, other_c_name, 
                            wait_events = [eid_create])
                    pending_events.append(eid_conn)

                    eid_post = self.postconnect(b.guid, c_name, other_b.guid, 
                            other_b.box_id, other_c_name,
                            wait_events = [eid_conn])
                    pending_events.append(eid_post)
                    post_events.append(eid_post)

                # Schedule the events created during design
                start_scheduled = False
                for (event_id, type, args, conditions) in box.events:
                    if type == EventType.START:
                        eid = self.start(box.guid, **conditions)
                        start_scheduled = True
                    elif type == EventType.STOP:
                        eid = self.stop(box.guid, **conditions)
                    elif type == EventType.SET:
                        (name, value) = args
                        eid = self.set(box.guid, name, value, **conditions)
                    elif type == EventType.COMMANDS:
                        (name, value) = args
                        eid = self.commans(box.guid, command, **conditions)
                    else:
                        continue

                    # switch the eid for the event_id in the event pending list
                    event = self._pend_events[eid]
                    self._remove_pending_event(eid)
                    self._add_pending_event(event_id, event)

                if not start_scheduled:
                    start_boxes.append(box)

            for b in box.boxes:
                walk_create(b, start_boxes, post_events, pending_events)

        def schedule_start(start_boxes, post_events):
            for box in start_boxes:
                start_eid = self.start(box.guid, pending = False)

        xml = self.original_ed_xml

        if not xml:
            self._exp_box = self._provider.create("Experiment")
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

            self._exp_box = self._provider.from_xml(xml)
            walk_create(self._exp_box, start_boxes, post_events, pending_events)
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

                #print "EVENT", date, eid, event.callback if event else "NONE", id(event) if event else "None"

                if event:
                    # If date is in the future, thread needs to wait
                    # until time elapse or until another event is scheduled
                    now = strfnow()
                    if now < date:
                        # Re-schedule event at same date
                        eid = self.__schedule_event(event, date, pending = False)
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

    def _schedule_event(self, callback, args, date = None, pending = True, 
            **conditions):
        event = Event(callback, args)
        return self.__schedule_event(event, date, pending, **conditions)

    def __schedule_event(self, event, date = None, pending = True, 
            **conditions):
        # In case there are conditions (Ex: events to wait for), a wrapper event
        # will be created and scheduled instead of the original event.
        # The wrapper event will verify the required condition, and only when this
        # condition is satisfied, it will schedule the original event
        initial_event = event
        if conditions:
            (event, date, failed) = self._resolve_conditions(initial_event, date, **conditions)

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
            self._add_pending_event(eid, initial_event)

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
                conditions = result or dict({'delay': _default_delay})
                eid = self.__schedule_event(event, pending = False, **conditions)
        except:
            # If an exception occurs while executing the callback, the
            # event should be marked as FAILED
            event.status = EventStatus.FAIL

            import traceback
            err = traceback.format_exc()
            self._logger.error("Error while executing event: %s" % err)
 
    def _resolve_conditions(self, event, date, **conditions):
        if ConditionType.DELAY in conditions:
            # We invoke make_condition because we need a uniform representation
            # of the conditions. They can be provided as a Condition object, 
            # a string condition, or a formatted condition, we need a Condition object.
            condition = make_condition(ConditionType.DELAY, 
                    conditions[ConditionType.DELAY])
            date = condition.condition
            return (event, date, False)
        
        if ConditionType.WAIT_EVENTS in conditions:
            condition = make_condition(ConditionType.WAIT_EVENTS, 
                    conditions[ConditionType.WAIT_EVENTS])
            del conditions[ConditionType.WAIT_EVENTS]
            wait_eids = condition.condition
            (new_event, date) = self._wait_events_wrapper(event, wait_eids, date, **conditions)
            return (new_event, date, False)
         
        if ConditionType.WAIT_VALUES in conditions:
            condition = make_condition(ConditionType.WAIT_VALUES, 
                    conditions[ConditionType.WAIT_VALUES])
            del conditions[ConditionType.WAIT_VALUES]
            wait_values = condition.condition
            (new_event, date) = self._wait_values_wrapper(event, wait_values, date, **conditions)
            return (new_event, date, False)
          
        if ConditionType.WAIT_STATES in conditions:
            condition = make_condition(ConditionType.WAIT_STATES, 
                    conditions[ConditionType.WAIT_STATES])
            del conditions[ConditionType.WAIT_STATES]
            wait_states = condition.condition
            (new_event, date) = self._wait_states_wrapper(event, wait_states, date, **conditions)
            return (new_event, date, False)
        
        return (event, date, True)
    
    def _wait_events_wrapper(self, event, wait_eids, date, **conditions):
        def _max_date(wait_events):
            # peek[0] == date
            max_date = max(self._scheduler.peek(e)[0] for e in wait_events)
            # It is possible that the event(s) for which we need to wait for
            # are wrapped as other events. In that case, we will not be able
            # to find those event(s) in the self._scheduler, because we don't 
            # know their 'eid(s)', and then we will not be able to find the max
            # scheduled date. The only alternative left will be to return ""
            # (which means, schedule as soon as possible)
            # If the event(s) we need to wait for are not wrapped, we can get
            # their dates, and in this case we will need to return a bigger date
            # than the maximum scheduled date. To achieve this we just sum 1 
            # to the max_date
            return "" if not max_date else  str(int(max_date) + 1)

        def _wait_events_wrapper_event(event, wait_events, conditions):
            # Check if there are still events to wait for
            wait_events = [e for e in wait_events \
                    if e.status in [EventStatus.RETRY, EventStatus.PENDING]]
            if wait_events:
                # re-schedule event in a date posterior to the last event
                date = _max_date(wait_events)
                result = dict({ConditionType.DELAY: date})
                return (EventStatus.RETRY, result)
            
            # re-schedule original event immediately
            self.__schedule_event(event, pending = False, **conditions)
            return (EventStatus.SUCCESS, "")

        wait_events = [self._pend_events[eid] for eid in wait_eids]
        date = _max_date(wait_events)
        
        callback = _wait_events_wrapper_event
        args = [event, wait_events, conditions]
        new_event = Event(callback, args)
        return (new_event, date)
       
    def _wait_values_wrapper(self, event, wait_values, date, **conditions):
        def _wait_values_wrapper_event(event, wait_values, conditions):
            for key, (guid, attr, oper, value) in wait_values.iteritems():
                if key not in event.kwargs:
                    state = self.state(guid)
                    # we asume the resource will we created in the future.
                    # for now we need to wait.
                    if state == ResourceState.NOTEXIST:
                        return (EventStatus.RETRY, "")

                    # try to get the value 
                    (status, result) = self._tc_get(guid, attr)
                    if status != EventStatus.SUCCESS:
                        return (status, result)
                    # If the condition is not satosfied we need to wait until it is
                    if ( oper and not eval(str(result) + " " + oper + " " + value) ):
                        return (EventStatus.RETRY, "")
                       
                    event.kwargs[key] = result

            # re-schedule original event immediately
            self.__schedule_event(event, pending = False, **conditions)
            return (EventStatus.SUCCESS, "")

        # require attributes to put in event.kwargs
        callback = _wait_values_wrapper_event
        args = [event, wait_values, conditions]
        new_event = Event(callback, args)
        return (new_event, date)

    def _wait_states_wrapper(self, event, wait_states, date, **conditions):
        def _wait_states_wrapper_event(event, wait_states, conditions):
            for (guid, oper, state) in wait_states:
                rstate = self.state(guid)
                # If the condition is not satisfied we need to wait until it is
                if ( not eval(str(rstate) + " " + oper + " " + state) ):
                    return (EventStatus.RETRY, "")
 
            # re-schedule original event immediately
            self.__schedule_event(event, pending = False, **conditions)
            return (EventStatus.SUCCESS, "")

        callback = _wait_states_wrapper_event
        args = [event, wait_states, conditions]
        new_event = Event(callback, args)
        return (new_event, date)

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

    def command(self, guid, command):
        raise NotImplementedError


def create_ec(xml, root_dir = "/tmp", debug = False):
    return ExperimentController(xml, root_dir, debug)

