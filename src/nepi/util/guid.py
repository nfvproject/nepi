# -*- coding: utf-8 -*-

class GuidGenerator(object):
    def __init__(self):
        self._guids = list()

    def next(self, guid = None):
        if guid != None:
            if guid in self._guids:
                raise RuntimeError("guid %d is already assigned" % guid)
        else:
            last_guid = 0 if len(self._guids) == 0 else self._guids[-1]
            guid = last_guid + 1 
        self._guids.append(guid)
        self._guids.sort()
        return guid

