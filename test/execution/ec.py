#!/usr/bin/env python

from neco.execution.ec import ExperimentController, ECState 
from neco.execution.scheduler import TaskStatus

import datetime
import time
import unittest

class ExecuteControllersTestCase(unittest.TestCase):
    def test_schedule_print(self):
        def myfunc():
            return 'hola!' 

        ec = ExperimentController()
    
        tid = ec.schedule("0s", myfunc, track=True)
        
        while True:
            task = ec.get_task(tid)
            if task.status != TaskStatus.NEW:
                break

            time.sleep(1)

        self.assertEquals('hola!', task.result)

        ec.shutdown()

    def test_schedule_date(self):
        def get_time():
            return datetime.datetime.now() 

        ec = ExperimentController()

        schedule_time = datetime.datetime.now()
        
        tid = ec.schedule("4s", get_time, track=True)

        while True:
            task = ec.get_task(tid)
            if task.status != TaskStatus.NEW:
                break

            time.sleep(1)

        execution_time = task.result
        delta = execution_time - schedule_time
        self.assertTrue(delta > datetime.timedelta(seconds=4))
        self.assertTrue(delta < datetime.timedelta(seconds=5))

        ec.shutdown()

    def test_schedule_exception(self):
        def raise_error():
            raise RuntimeError, "the error"

        ec = ExperimentController()
        ec.schedule("2s", raise_error)

        while ec.ecstate not in [ECState.FAILED, ECState.TERMINATED]:
           time.sleep(1)
        
        self.assertEquals(ec.ecstate, ECState.FAILED)
        ec.shutdown()


if __name__ == '__main__':
    unittest.main()

