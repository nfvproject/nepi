
import logging
import weakref

from nepi.util.guid import GuidGenerator

class EventTypes(object):
    START   = "start"
    STOP    = "stop"
    SET     = "set"
    COMMAND = "command"


class BoxState(object):
    FAILED = 0
    NOTEXIST = 1
    NEW = 2
    CREATED = 3
    STARTED = 4
    RUNNING = 5
    FINISHED = 6
    STOPPED = 7
    SHUTDOWN = 8


class ConditionTypes(object):
    DELAY       = "delay"
    WAIT_EVENTS = "wait_events"
    WAIT_VALUES = "wait_values"
    WAIT_STATES = "wait_states"


class EventType(object):
    def __init__(self, owner, type, state, multi = False):
        self._type = type
        self._state = state
        # Can support multiple instances of event
        self._multi = multi
        self._owner = weakref.ref(owner)
        self._owner()._types_idx[type] = []
       
        self._logger = logging.getLogger("nepi.design.events")

    def on(self, condition, value = "", event_id = None):
        if not self._multi:
            if len(self._owner()._types_idx[self._type]) > 0:
                self._logger.error("An event of type %s already exists.",
                         self._type)
                return None
        return self._owner().add_event(self._type, value, condition, event_id)

    def at(self, date, value = ""):
        conditions = dict({ConditionTypes.DELAY: date})
        return self.on(conditions, value)
       
    def after(self, guids, value = ""):
        wait_states = []
        guids = guids if isinstance(guids, list) else [guids]
        for guid in guids:
            wait_states.append((guid, "==", self._state))
        conditions = dict({ConditionTypes.WAIT_STATES: wait_states})
        return self.on(conditions, value)


class EventsMapProxy(object):
    def __init__(self, owner):
        self._owner = weakref.ref(owner)
    
    def __getattr__(self, name):
        return self._owner()._event_types[name]

    def __setattr__(self, name, value):
        if name != "_owner":
            raise RuntimeError("Can't override event type")
        super(EventsMapProxy, self).__setattr__(name, value)


class EventsMap(object):
    def __init__(self):
        super(EventsMap, self).__init__()
        self.__init()

    def __init(self):
        self._eguid_generator = GuidGenerator()
        self._event_types = dict()
        self._types_idx = dict()
        self._events = dict()
        self._e = EventsMapProxy(self)

        self._add_event_type(EventTypes.START, BoxState.STARTED)
        self._add_event_type(EventTypes.STOP, BoxState.STOPPED)
        self._add_event_type(EventTypes.SET, BoxState.STARTED, multi = True)
        self._add_event_type(EventTypes.COMMAND, BoxState.STARTED)

    @property
    def events(self):
        return self._events.values()

    @property
    def e(self):
        return self._e

    def add_event(self, type, value, conditions, event_id = None):
        eid = None if not event_id else event_id[1]
        event_id = (self.guid, self._eguid_generator.next(eid))
        self._events[event_id] = (event_id, type, value, conditions)
        self._types_idx[type].append(event_id)
        return event_id

    def delete_event(self, event_id):
        (event_id, type, value, conditions) = self._events[event_id]
        del self._events[event_id]
        self._types_idx[type].remove(event_id)

    def _add_event_type(self, type, state, multi = False):
        et = EventType(self, type, state, multi)
        self._event_types[type] = et

    def clone_events(self, other):
        self.__init()

