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
# Author: Lucia Guevgeozian <lucia.guevgeozian_odizzio@inria.fr>

from test_utils import skipIfNotPythonVersion

import datetime
import unittest

def _get_total_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6

class TimeFuncTestCase(unittest.TestCase):

    @skipIfNotPythonVersion
    def test_total_seconds(self):
        date = datetime.timedelta(2, 468, 506260)
        seconds1 = _get_total_seconds(date)
        seconds2 = date.total_seconds()

        self.assertEquals(seconds1, seconds2)


if __name__ == '__main__':
    unittest.main()


