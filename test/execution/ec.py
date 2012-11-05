#!/usr/bin/env python

from neco.execution.ec import ExperimentController 
from neco.execution.tasks import TaskStatus

import datetime
import unittest

class ExecuteControllersTestCase(unittest.TestCase):
    def test_schedule_print(self):
        def myfunc(ec_weakref):
            result = id(ec_weakref())
            return (TaskStatus.SUCCESS, result)

        try:
            ec = ExperimentController()

            tid = ec.schedule("0s", myfunc)
            status = None
            while status != TaskStatus.SUCCESS:
                (status, result) = ec.task_info(tid)

            self.assertEquals(id(ec), result)
        finally:
            ec.terminate()

    def test_schedule_date(self):
        def get_time(ec_weakref):
            timestamp = datetime.datetime.now() 
            return (TaskStatus.SUCCESS, timestamp)

        try:
            ec = ExperimentController()

            schedule_time = datetime.datetime.now()
            
            tid = ec.schedule("4s", get_time)
            status = None
            while status != TaskStatus.SUCCESS:
                (status, execution_time) = ec.task_info(tid)

            delta = execution_time - schedule_time
            self.assertTrue(delta > datetime.timedelta(seconds=4))
            self.assertTrue(delta < datetime.timedelta(seconds=5))

        finally:
            ec.terminate()


if __name__ == '__main__':
    unittest.main()

