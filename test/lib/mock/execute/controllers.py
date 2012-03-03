
import logging
import weakref 

from nepi.execute import controllers
from mock.design.boxes import TESTBED, TRACE, NODE

class MockObject(object):
    def __init__(self, guid, box_id, attributes, tc):
        super(MockObject, self).__init__()
        self._attributes = attributes
        self._guid = guid
        self._box_id = box_id
        self._tc = tc
        self.state = controllers.ResourceState.CREATED

    @property
    def tc(self):
        return self._tc()

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        return (controllers.EventStatus.SUCCESS, "")

    def postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        return (controllers.EventStatus.SUCCESS, "")

    def start(self, guid):
        return (controllers.EventStatus.SUCCESS, "")

    def stop(self, guid):
        return (controllers.EventStatus.SUCCESS, "")

    def get(self, attr):
         if not attr in self._attributes:
            self.tc._logger.debug("get(%d, %s): FAIL, no such attribute " % 
                    (self._guid, attr))
            return (controllers.EventStatus.FAIL, "")
         value = self._attributes[attr]
         self.tc._logger.debug("get(%d, %s) = %s : SUCCESS " % 
                    (self._guid, attr, str(value)))
         return (controllers.EventStatus.SUCCESS, value)

    def set(self, attr, value):
        if not attr in self._attributes:
            self.tc._logger.debug("set(%d, %s, %s): FAIL, no such attribute " % 
                    (self._guid, attr, str(value)))
            return (controllers.EventStatus.FAIL, "")
        self._attributes[attr] = value
        self.tc._logger.debug("set(%d, %s, %s): SUCCESS " % 
                    (self._guid, attr, str(value)))
        return (controllers.EventStatus.SUCCESS, value)


class Trace(MockObject):
    def __init__(self, guid, box_id, attributes, tc):
        super(Trace, self).__init__(guid, box_id, attributes, tc)

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        self.tc._logger.debug("connect(): SUCCESS")
        return (controllers.EventStatus.SUCCESS, "")


class TestbedController(controllers.TestbedController):
    def __init__(self, guid, attributes):
        super(TestbedController, self).__init__(guid, attributes)
        self._objects = dict()

        self._logger = logging.getLogger("nepi.execute.tc.mock")
        log_level = attributes.get('logLevel')
        if log_level == "Debug":
            level = logging.DEBUG
            self._logger.setLevel(level)
 
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
        self._state = controllers.ResourceState.SHUTDOWN
        self._logger.debug("shutdown(): SUCCESS")
        return (controllers.EventStatus.SUCCESS, "")

    def create(self, guid, box_id, attributes):
        tc = weakref.ref(self)
        if box_id == TRACE:
            obj = Trace(guid, box_id, attributes, tc)
        else:
            obj = MockObject(guid, box_id, attributes, tc)
        self._objects[guid] = obj
        self._logger.debug("create(%d, %s, %s): SUCCESS " % (guid, box_id, str(attributes)))
        return (controllers.EventStatus.SUCCESS, "")

    def connect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        obj = self._objects.get(guid)
        if not obj:
            self._logger.debug("connect(%d, %s, %d, %s): FAIL, no such object " % 
                    (guid, connector, other_guid, other_connector))
            return (controllers.EventStatus.FAIL, "")
        
        return obj.connect(guid, connector, other_guid, other_box_id, 
                other_connector, **kwargs)

    def postconnect(self, guid, connector, other_guid, other_box_id,
            other_connector, **kwargs):
        obj = self._objects.get(guid)
        if not obj:
            self._logger.debug("postconnect(%d, %s, %d, %s): FAIL, no such object " % 
                    (guid, connector, other_guid, other_connector))
            return (controllers.EventStatus.FAIL, "")

        return obj.postconnect(guid, connector, other_guid, other_box_id,
            other_connector, **kwargs)

    def start(self, guid):
        if guid == self.guid:
            self._state = controllers.ResourceState.STARTED
 
        obj = self._objects.get(guid)
        if not obj:
            self._logger.debug("start(%d): FAIL, no such object " % guid )
            return (controllers.EventStatus.FAIL, "")
        return obj.start(guid)

    def stop(self, guid):
        if guid == self.guid:
            self._state = controllers.ResourceState.STOPPED
        self._logger.debug("stop(%d): SUCCESS " % (guid))
  
        obj = self._objects.get(guid)
        if not obj:
            self._logger.debug("stop(%d): FAIL, no such object " % guid )
            return (controllers.EventStatus.FAIL, "")
        return obj.stop(guid)

    def set(self, guid, attr, value):
        obj = self._objects.get(guid)
        if not obj: 
            self._logger.debug("set(%d): FAIL, no such object " % (guid))
            return (controllers.EventStatus.FAIL, "")
        return obj.set(attr, value)

    def get(self, guid, attr):
        obj = self._objects.get(guid)
        if not obj: 
            self._logger.debug("get(%d): FAIL, no such object " % (guid))
            return (controllers.EventStatus.FAIL, "")
        return obj.get(attr)


TC_CLASS = TestbedController
TC_BOX_ID = TESTBED


