class TraceAttr:
    ALL = 'all'
    STREAM = 'stream'
    PATH = 'path'
    SIZE = 'size'

class Trace(object):
    def __init__(self, name, help):
        self._name = name
        self._help = help
        self.enabled = False

    @property
    def name(self):
        return self._name

    @property
    def help(self):
        return self._help

