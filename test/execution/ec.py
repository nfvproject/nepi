#!/usr/bin/env python
#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>


from nepi.execution.ec import ExperimentController, ECState 
from nepi.execution.scheduler import TaskStatus

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

