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


from nepi.util.parallel import ParallelRun

import datetime
import unittest

class ParallelRunTestCase(unittest.TestCase):
    def test_run_simple(self):
        runner = ParallelRun(maxthreads = 4)
        runner.start()

        count = [0]

        def inc(count):
            count[0] += 1
        
        for x in xrange(10):
            runner.put(inc, count)

        runner.destroy()

        self.assertEquals(count[0], 10)

    def test_run_interrupt(self):

        def sleep():
            import time
            time.sleep(5)

        startt = datetime.datetime.now()

        runner = ParallelRun(maxthreads = 4)
        runner.start()
       
        for x in xrange(100):
            runner.put(sleep)

        runner.empty()
        runner.destroy()

        endt = datetime.datetime.now()
        time_elapsed = (endt - startt).seconds
        self.assertTrue( time_elapsed < 500)

    def test_run_error(self):
        count = [0]

        def inc(count):
            count[0] += 1
 
        def error():
            raise RuntimeError()

        runner = ParallelRun(maxthreads = 4)
        runner.start()
       
        for x in xrange(4):
            runner.put(inc, count)

        runner.put(error)
       
        runner.destroy()
      
        self.assertEquals(count[0], 4)
        
        self.assertRaises(RuntimeError, runner.sync)

if __name__ == '__main__':
    unittest.main()

