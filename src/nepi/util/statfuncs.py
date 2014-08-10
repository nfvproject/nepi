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

import math
import numpy
from scipy import stats

def compute_mean(sample):
    # TODO: Discard outliers !!!!

    if not sample:
        print " CANNOT COMPUTE STATS for ", sample
        return (0, 0, 0, 0)

    x = numpy.array(sample)

    # sample mean and standard deviation
    n, min_max, mean, var, skew, kurt = stats.describe(x)
    std = math.sqrt(var)

    # for the population mean and std ...
    # mean = x.mean()
    # std = x.std()
    
    # Calculate confidence interval t-distribution
    ## BUG: Use quantil of NORMAL distribution, not t-student quantil distribution
    ci = stats.t.interval(0.95, n-1, loc = mean, scale = std/math.sqrt(n))

    return (mean, std, ci[0], ci[1])

