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

import logging

class Logger(object):
    def __init__(self, logger_component):
        self._logger = logging.getLogger(logger_component)

    def debug(self, msg, out = None, err = None):
        self.log(msg, logging.DEBUG, out, err)

    def error(self, msg, out = None, err = None):
        self.log(msg, logging.ERROR, out, err)

    def warn(self, msg, out = None, err = None):
        self.log(msg, logging.WARNING, out, err)

    def info(self, msg, out = None, err = None):
        self.log(msg, logging.INFO, out, err)

    def log(self, msg, level, out = None, err = None):
        if out:
            msg += " - OUT: %s " % out

        if err:
            msg += " - ERROR: %s " % err

        msg = self.log_message(msg)

        self.logger.log(level, msg)

    def log_message(self, msg):
        return msg

    @property
    def logger(self):
        return self._logger
