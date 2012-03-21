# FIXME: This class is not thread-safe. 
# Should it be made thread-safe?
class GuidGenerator(object):
    def __init__(self):
        self._guids = list()
        self.off = False

    def next(self, guid = None):
        # This mechanism allows to build Factory boxes without worring 
        # about the actual assigned guids. 
        # BoxProvider should always off the guid_generator when building 
        # box factories.
        if self.off:
            return guid

        if guid != None:
            if guid in self._guids:
                raise RuntimeError("guid %d is already assigned" % guid)
        else:
            last_guid = 0 if len(self._guids) == 0 else self._guids[-1]
            guid = last_guid + 1 
        self._guids.append(guid)
        self._guids.sort()
        return guid

