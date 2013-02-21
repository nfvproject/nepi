import logging
import weakref

class Resource(object):
    def __init__(self, ec, guid):
        self._guid = guid
        self._ec = weakref.ref(ec)

        # Logging
        loglevel = "debug"
        self._logger = logging.getLogger("neco.execution.Resource.%s" % 
            self.guid)
        self._logger.setLevel(getattr(logging, loglevel.upper()))

    @property
    def guid(self):
        return self._guid

    @property
    def ec(self):
        return self._ec()


