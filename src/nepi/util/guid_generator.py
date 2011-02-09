#!/usr/bin/env python
# -*- coding: utf-8 -*-

class GuidGenerator(object):
    def __init__(self, guid = 0):
        self._last_guid = guid

    def next(self):
        self._last_guid += 1
        return self._last_guid

