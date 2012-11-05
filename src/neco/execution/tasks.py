
class TaskStatus:
    NEW = 0
    RETRY = 1
    SUCCESS = 2
    FAIL = 3
    RECYCLE = 4

class Task(object):
    def __init__(self, timestamp, callback, args, kwargs):
        self.id = None 
        self.timestamp = timestamp
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.status = TaskStatus.NEW

