
import logging
import re
import weakref

from nepi.util.guid import GuidGenerator

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


class ConditionType(object):
    DATE       = "date"
    WAIT_EVENTS = "wait_events"
    WAIT_VALUES = "wait_values"
    WAIT_STATES = "wait_states"

class Condition(object):
    def __init__(self, type, condition):
        super(Condition, self).__init__()
        self._type = type
        if isinstance(condition, str):
            condition = self._condition_from_string(condition)
        self._condition = condition

    @property
    def type(self):
        return self._type

    @property
    def condition(self):
        return self._condition

    @property
    def strcondition(self):
        """ Condition in string format """
        return self._condition_to_string(self._condition)

    def _condition_from_string(self, strcondition):
        raise NotImplementedError

    def _condition_to_string(self, condition):
        raise NotImplementedError

class DateCondition(Condition):
    def __init__(self, delay):
        type = ConditionType.DATE
        super(DateCondition, self).__init__(type, delay)
 
    def _condition_from_string(self, strcondition):
        return strcondition

    def _condition_to_string(self, condition):
        return condition

class WaitEventsCondition(Condition):
    def __init__(self, eids):
        type = ConditionType.WAIT_EVENTS
        super(WaitEventsCondition, self).__init__(type, eids)
 
    def _condition_from_string(self, strcondition):
        def toeid(seid):
            # The eid can be either a int or a int tuple
            if seid[0] != '(':
                return int(seid)
            return tuple(map(int, seid[1:-1].split(",")))
        return map(toeid, strcondition.split("|"))

    def _condition_to_string(self, condition):
        return "|".join(map(str, condition))

class WaitValuesCondition(Condition):
    _revalues = re.compile("(?P<key>[a-zA-Z_-]+):guid\((?P<guid>\d+)\)\.(?P<attr>[a-zA-Z_-]+)( ?(?P<oper>(\=\=|\!\=|\>|\>\=|\<|\<\=)) ?(?P<value>[0-9a-zA-Z_-]+))?")
    
    def __init__(self, wait_values):
        type = ConditionType.WAIT_VALUES
        super(WaitValuesCondition, self).__init__(type, wait_values)
 
    def _condition_from_string(self, strcondition):
        values = dict()
        wait_values = strcondition.split(",")
        for arg in wait_values:
            m = self._revalues.match(arg)
            key = m.groupdict()['key'] 
            guid = int( m.groupdict()['guid'])
            attr = m.groupdict()['attr']
            oper = m.groupdict()['oper']
            value = m.groupdict()['value']
            values[key] = (guid, attr, oper, value)

        return values

    def _condition_to_string(self, condition):
        wait_values = []
        for key, (guid, attr, oper, value) in condition.iteritems():
            arg = "%s:guid(%d).%s" % (key, guid, attr)
            if oper and value:
                arg = "%s %s %s" % (arg, oper, value) 
            wait_values.append(arg)

        return ",".join(wait_values)

class WaitStatesCondition(Condition):
    _restates = re.compile("guid\((?P<guid>\d+)\)\.state ?(?P<oper>(\=\=|\!\=|\>|\>\=|\<|\<\=)) ?(?P<state>[0-8])")
    
    def __init__(self, wait_states):
        type = ConditionType.WAIT_STATES
        super(WaitStatesCondition, self).__init__(type, wait_states)
 
    def _condition_from_string(self, strcondition):
        states = []
        wait_states = strcondition.split(",")
        for arg in wait_states:
            m = self._restates.match(arg)
            guid = int(m.groupdict()['guid'])
            oper = m.groupdict()['oper']
            state = m.groupdict()['state']
            states.append((guid, oper, state))

        return states

    def _condition_to_string(self, condition):
        wait_states = []
        for (guid, oper, state) in condition:
            arg = "guid(%d).state %s %s" % (guid, oper, state)
            wait_states.append(arg)

        return ",".join(wait_states)

def make_condition(type, condition):
    if isinstance(condition, Condition):
        return condition

    if type == ConditionType.DATE:
        return DateCondition(condition)
    if type == ConditionType.WAIT_EVENTS:
        return WaitEventsCondition(condition)
    if type == ConditionType.WAIT_VALUES:
        return WaitValuesCondition(condition)
    if type == ConditionType.WAIT_STATES:
        return WaitStatesCondition(condition)

    return None 

class EventType(object):
    CREATE = "create"
    CONNECT = "connect"
    START   = "start"
    STOP    = "stop"
    SET     = "set"
    GET     = "get"
    COMMAND = "command"
    SHUTDOWN = "shutdown"

class Event(object):
    def __init__(self, owner, type, multi = False):
        super(Event, self).__init__()
        self._type = type
        # Can support multiple instances of event
        self._multi = multi
        self._owner = weakref.ref(owner)
        self._owner()._types_idx[type] = []
       
        self._logger = logging.getLogger("nepi.design.events")

    @property
    def type(self):
        return self._type

    def on(self, conditions, args = (), event_id = None):
        if not self._multi:
            if len(self._owner()._types_idx[self._type]) > 0:
                self._logger.error(" An event of type '%s' already exists.",
                         self._type)
                return None
            
        for type, condition in conditions.iteritems():
            condition = make_condition(type, condition)
            if not condition:
                self._logger.error(" Invalid condition type '%s'.", type)
            conditions[type] = condition

        return self._owner().add_event(self._type, conditions, args, event_id)

    def at(self, date, *args):
        conditions = dict({ConditionType.DATE: date})
        return self.on(conditions, args)

    def after(self, state, guids, *args):
        wait_states = []
        guids = guids if isinstance(guids, list) else [guids]
        for guid in guids:
            wait_states.append((guid, "==", state))
        conditions = dict({ConditionType.WAIT_STATES: wait_states})
        return self.on(conditions, args)
      
class StateEvent(Event):
    def __init__(self, owner, type, state, multi = False):
        super(StateEvent, self).__init__(owner, type, multi)
        self._state = state
 
    def at(self, date):
        return super(StateEvent, self).at(date)

    def after(self, guids, state = None):
        state = state or self._state
        return super(StateEvent, self).after(state, guids)

class StartEvent(StateEvent):
    def __init__(self, owner):
        type = EventType.START  
        state = BoxState.STARTED
        super(StartEvent, self).__init__(owner, type, state)

class StopEvent(StateEvent):
    def __init__(self, owner):
        type = EventType.STOP 
        state = BoxState.STOPPED
        super(StopEvent, self).__init__(owner, type, state)

class CreateEvent(StateEvent):
    def __init__(self, owner):
        type = EventType.CREATE
        state = BoxState.CREATED
        super(CreateEvent, self).__init__(owner, type, state)

class ShutdownEvent(StateEvent):
    def __init__(self, owner):
        type = EventType.SHUTDOWN
        state = BoxState.SHUTDOWN
        super(ShutdownEvent, self).__init__(owner, type, state)

class ConnectEvent(Event):
    def __init__(self, owner):
        type = EventType.CONNECT
        super(ConnectEvent, self).__init__(owner, type, multi = True)
 
    def at(self, date, guid, connector, other_guid, other_box_id, other_connector):
        return super(ConnectEvent, self).at(date, guid, connector, other_guid,
                other_box_id, other_connector)

class SetEvent(Event):
    def __init__(self, owner):
        type = EventType.SET 
        super(SetEvent, self).__init__(owner, type, multi = True)
 
    def at(self, date, name, value):
        return super(SetEvent, self).at(date, name, value)
 
class GetEvent(Event):
    def __init__(self, owner):
        type = EventType.GET 
        super(GetEvent, self).__init__(owner, type, multi = True)
 
    def at(self, date, name):
        return super(GetEvent, self).at(date, name)
      
class CommandEvent(Event):
    def __init__(self, owner):
        type = EventType.COMMAND  
        super(CommandEvent, self).__init__(owner, type, multi = True)
 
    def at(self, date, command):
        return super(CommnadEvent, self).at(date, command)


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

        self._add_event(StartEvent(self))
        self._add_event(StopEvent(self))
        self._add_event(SetEvent(self))
        self._add_event(GetEvent(self))
        self._add_event(CommandEvent(self))
        self._add_event(ShutdownEvent(self))
        self._add_event(CreateEvent(self))
        self._add_event(ConnectEvent(self))

    @property
    def events(self):
        return self._events.values()

    @property
    def e(self):
        return self._e

    def add_event(self, type, conditions, args, event_id = None):
        eid = None if not event_id else event_id[1]
        event_id = (self.guid, self._eguid_generator.next(eid))
        self._events[event_id] = (event_id, type, args, conditions)
        self._types_idx[type].append(event_id)
        return event_id

    def delete_event(self, event_id):
        (event_id, type, args, conditions) = self._events[event_id]
        del self._events[event_id]
        self._types_idx[type].remove(event_id)

    def delete_all_events(self):
        self._eguid_generator = GuidGenerator()
        for (event_id, type, args, conditions) in self._events.values():
            del self._events[event_id]
            self._types_idx[type].remove(event_id)

    def _add_event(self, event):
        self._event_types[event.type] = event

    def clone_events(self, other):
        self.__init()

