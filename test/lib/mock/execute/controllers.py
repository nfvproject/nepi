
import logging

from nepi.execute import controllers

class MockObject(object):
    def __init__(self, guid, box_id, attributes):
        super(MockObject, self).__init__()
        self._attributes = attributes
        self._guid = guid
        self._box_id = box_id
        self.state = controllers.ResourceState.NEW

    def get_attr(self, attr):
         if not attr in self._attributes:
            return (controllers.EventStatus.FAIL, "Object guid(%d) doesn't have attr %s." % (guid, attr))
         value = self._attributes[attr]
         return (controllers.EventStatus.SUCCESS, value)

    def set_attr(self, attr, value):
        if not attr in self._attributes:
            return (controllers.EventStatus.FAIL, "Object guid(%d) doesn't have attr %s." % (guid, attr))
        self._attributes[attr] = value
        return (controllers.EventStatus.SUCCESS, value)


class TestbedController(controllers.TestbedController):
    def __init__(self, guid):
        super(TestbedController, self).__init__(guid)
        # Logging
        self._logger = logging.getLogger("nepi.execute.tc.mock")

    def recover(self):
        raise NotImplementedError

    def shutdown(self):
        self.state = controllers.ResourceState.SHUTDWON
        self._logger.info("SHUTDOWN")
        return (controllers.EventStatus.SUCCESS, "")

    def create(self, guid, box_id, attributes):
        obj = MockObject(guid, box_id, attributes)
        self._objects[guid] = obj
        self._logger.info("CREATE")
        return (controllers.EventStatus.SUCCESS, "")

    def connect(self, guid, connector, other_guid, other_connector):
        self._logger.info("CONNECT")
        return (controllers.EventStatus.SUCCESS, "")

    def postconnect(self, guid, connector, other_guid, other_connector): 
        self._logger.info("POSTCONNECT")
        return (controllers.EventStatus.SUCCESS, "")

    def start(self, guid = None):
        self._logger.info("START")
        return (controllers.EventStatus.SUCCESS, "")

    def stop(self, guid = None):
        self._logger.info("STOP")
        return (controllers.EventStatus.SUCCESS, "")


TC_CLASS = TestbedController
TC_BOX_ID = "mock::MockInstance"


