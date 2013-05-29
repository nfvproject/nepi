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
import os
import traceback

LOGLEVEL = os.environ.get("NEPI_LOGLEVEL", "INFO").upper()
LOGLEVEL = getattr(logging, LOGLEVEL)
#FORMAT = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
FORMAT = "%(asctime)s %(name)s %(levelname)-4s %(message)s"

# NEPI_LOG variable contains space separated components 
# on which logging should be enabled
LOG = os.environ.get("NEPI_LOG", "ALL").upper()

if LOG != 'ALL':
    # Set by default loglevel to error
    logging.basicConfig(format = FORMAT, level = logging.ERROR)

    # Set logging level to that defined by the user
    # only for the enabled components
    for component in LOG.split(" "):
        try:
           log = logging.getLogger(component)
           log.setLevel(LOGLEVEL)
        except:
            err = traceback.format_exc()
            print "ERROR ", err
else:
    # Set the logging level defined by the user for all
    # components
    logging.basicConfig(format = FORMAT, level = LOGLEVEL)

