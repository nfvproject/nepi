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


import datetime
import re

_strf = "%Y%m%d%H%M%S%f"
_reabs = re.compile("^\d{20}$")
_rerel = re.compile("^(?P<time>\d+(.\d+)?)(?P<units>h|m|s|ms|us)$")

# Work around to fix "ImportError: Failed to import _strptime because the import lock is held by another thread."
datetime.datetime.strptime("20120807124732894211", _strf)

def strfnow():
    """ Current date """
    return datetime.datetime.now().strftime(_strf)

def strfdiff(str1, str2):
    # Time difference in seconds without ignoring miliseconds
    d1 = datetime.datetime.strptime(str1, _strf)
    d2 = datetime.datetime.strptime(str2, _strf)
    diff = d1 - d2
    ddays = diff.days * 86400
    dus = round(diff.microseconds * 1.0e-06, 2) 
    ret = ddays + diff.seconds + dus
    # delay must be > 0
    return (ret or 0.001)

def strfvalid(date):
    """ User defined date to scheduler date 
    
    :param date : user define date matchin the pattern _strf 
    :type date : date 

    """
    if not date:
        return strfnow()
    if _reabs.match(date):
        return date
    m = _rerel.match(date)
    if m:
        time = float(m.groupdict()['time'])
        units = m.groupdict()['units']
        if units == 'h':
            delta = datetime.timedelta(hours = time) 
        elif units == 'm':
            delta = datetime.timedelta(minutes = time) 
        elif units == 's':
            delta = datetime.timedelta(seconds = time) 
        elif units == 'ms':
            delta = datetime.timedelta(microseconds = (time*1000)) 
        else:
            delta = datetime.timedelta(microseconds = time) 
        now = datetime.datetime.now()
        d = now + delta
        return d.strftime(_strf)
    return None

