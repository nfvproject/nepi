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

from nepi.execution.scheduler import HeapScheduler, Task, TaskStatus
from nepi.util.timefuncs import tnow, stabsformat

import unittest

class SchedulerTestCase(unittest.TestCase):
    def test_task_order(self):
        def first():
            return 1

        def second():
            return 2

        def third():
            return 3

        scheduler = HeapScheduler()
        
        t1 = tnow()
        t2 = stabsformat("2s")
        t3 = stabsformat("3s")
    
        tsk1 = Task(t1, first)
        tsk2 = Task(t2, second)
        tsk3 = Task(t3, third)

        # schedule the tasks in disorder
        scheduler.schedule(tsk2)
        scheduler.schedule(tsk3)
        scheduler.schedule(tsk1)

        # Make sure tasks are retrieved in teh correct order
        tsk = scheduler.next()
        self.assertEquals(tsk.callback(), 1)
        
        tsk = scheduler.next()
        self.assertEquals(tsk.callback(), 2)
        
        tsk = scheduler.next()
        self.assertEquals(tsk.callback(), 3)


if __name__ == '__main__':
    unittest.main()

