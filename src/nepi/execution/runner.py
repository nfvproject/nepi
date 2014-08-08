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

from nepi.execution.ec import ExperimentController

import math
import numpy
import os
import tempfile
import time

class ExperimentRunner(object):
    """ The ExperimentRunner entity is reponsible of
    re-running an experiment described by an ExperimentController 
    multiple time.

    """
    def __init__(self):
        super(ExperimentRunner, self).__init__()
    
    def run(self, ec, min_runs = 1, max_runs = -1, wait_time = 0, 
            wait_guids = [], compute_metric_callback = None, 
            evaluate_convergence_callback = None ):
        """ Re-runs a same experiment multiple times

        :param ec: Experiment description of experiment to run
        :type ec: ExperimentController

        :param min_runs: Minimum number of repetitions for experiment
        :type min_runs: int

        :param max_runs: Maximum number of repetitions for experiment
        :type max_runs: int

        :param wait_time: Time to wait in seconds between invoking
            ec.deploy() and ec.release()
        :type wait_time: float

        :param wait_guids: List of guids to pass to ec.wait_finished
            after invoking ec.deploy()
        :type wait_guids: list 

        :param compute_metric_callback: function to invoke after each 
            experiment run, to compute an experiment metric. 
            It will be invoked with the ec and the run count as arguments,
            and it must return a numeric value for the computed metric:

                metric = compute_metric_callback(ec, run)
            
        :type compute_metric_callback: function 

        :param evaluate_convergence_callback: function to evaluate whether the 
            collected metric samples have converged and the experiment runner
            can stop. It will be invoked with the ec, the run count and the
            list of collected metric samples as argument, and it must return
            either True or False:

                stop = evaluate_convergence_callback(ec, run, metrics)

            If stop is True, then the runner will exit.
            
        :type evaluate_convergence_callback: function 

        """

        if (not max_runs or max_runs < 0) and not compute_metric_callback:
            msg = "Undefined STOP condition, set stop_callback or max_runs"
            raise RuntimeError, msg

        if compute_metric_callback and not evaluate_convergence_callback:
            evaluate_convergence_callback = self.evaluate_normal_convergence
            ec.logger.info(" Treating data as normal to evaluate convergence. "
                    "Experiment will stop when the standard error with 95% "
                    "confidence interval is >= 5% of the mean of the collected samples ")
        
        # Force persistence of experiment controller
        ec._persist = True

        dirpath = tempfile.mkdtemp()
        filepath = ec.save(dirpath)

        samples = []
        run = 0
        while True: 
            run += 1

            ec = self.run_experiment(filepath, wait_time, wait_guids)
            
            ec.logger.info(" RUN %d \n" % run)

            if run >= min_runs and max_runs > -1 and run >= max_runs :
                break

            if compute_metric_callback:
                metric = compute_metric_callback(ec, run)
                if metric is not None:
                    samples.append(metric)

                    if run >= min_runs and evaluate_convergence_callback:
                        if evaluate_convergence_callback(ec, run, samples):
                            break
            del ec

        return run

    def evaluate_normal_convergence(self, ec, run, samples):
        if len(samples) == 0:
            msg = "0 samples collected"
            raise RuntimeError, msg
        
        x = numpy.array(samples)
        n = len(samples)
        std = x.std()
        se = std / math.sqrt(n)
        m = x.mean()
        se95 = se * 2
        
        ec.logger.info(" RUN %d - SAMPLES %d MEAN %.2f STD %.2f SE95%% %.2f \n" % (
            run, n, m, std, se95 ) )

        return m * 0.05 >= se95

    def run_experiment(self, filepath, wait_time, wait_guids): 
        ec = ExperimentController.load(filepath)

        ec.deploy()

        ec.wait_finished(wait_guids)
        time.sleep(wait_time)

        ec.release()

        return ec


