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

def stformat(sdate):
    """ Constructs a datetime object from a string date with
    format YYYYMMddHHMMSSffff 

    """
    return datetime.datetime.strptime(sdate, _strf).date()

def tsformat(date = None):
    """ Formats a datetime object to a string with format YYYYMMddHHMMSSffff.
    If no date is given, the current date is used.
    
    """
    if not date:
        date = tnow()

    return date.strftime(_strf)

def tnow():
    """ Returns datetime object with the current time """
    return datetime.datetime.now()

def tdiff(date1, date2):
    """ Returns difference ( date1 - date2 ) as a datetime object,
    where date1 and date 2 are datetime objects 
    
    """
    return date1 - date2

def _get_total_seconds(td): 
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6

def tdiffsec(date1, date2):
    """ Returns the date difference ( date1 - date2 ) in seconds,
    where date1 and date 2 are datetime objects 
    
    """
    diff = tdiff(date1, date2)
    return _get_total_seconds(diff)

def stabsformat(sdate, dbase = None):
    """ Constructs a datetime object from a string date.
    The string date can be expressed as an absolute date
    ( i.e. format YYYYMMddHHMMSSffff ) or as a relative time
    ( e.g. format '5m' or '10s'). 
    If the date is a relative time and the dbase parameter 
    is given (dbase must be datetime object), the returned
    date will be dbase + sdate. If dbase is None, 
    current time will be used instead as base time.

    :param date : string date  
    :type date : date 

    """

    # No date given, return current datetime
    if not sdate:
        return tnow()

    # Absolute date is given
    if _reabs.match(sdate):
        return stformat(sdate)

    # Relative time is given
    m = _rerel.match(sdate)
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
        
        if not dbase:
            dbase = tnow()

        return dbase + delta

    return None

def compute_delay_ms(timestamp2, timestamp1):
    d1 = datetime.datetime.fromtimestamp(float(timestamp1))
    d2 = datetime.datetime.fromtimestamp(float(timestamp2))
    delay = d2 - d1

    # round up resolution - round up to miliseconds
    return delay.total_seconds() * 1000

