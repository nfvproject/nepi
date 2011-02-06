# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4

class Experiment(object):
    def __init__(self):
        self._backends = dict()

    def add_backend(self, backend):
        self._backends[backend.guid] = backend

    def remove_backend(self, backend):
        del self._backends[backend.guid]

    def instructions(self):
        #TODO
        pass

