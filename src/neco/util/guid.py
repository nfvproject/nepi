# FIXME: This class is not thread-safe. 
# Should it be made thread-safe?
class GuidGenerator(object):
    def __init__(self):
        self._guids = list()

    def next(self, guid = None):
        if guid != None:
            return guid
        else:
            last_guid = 0 if len(self._guids) == 0 else self._guids[-1]
            guid = last_guid + 1 
        self._guids.append(guid)
        self._guids.sort()
        return guid

