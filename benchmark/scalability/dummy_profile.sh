#PYTHONPATH=$PYTHONPATH:~/repos/nepi/src NEPI_LOGLEVEL=debug python -m cProfile -s cumulative dummy.py -n 1000 -a 5 -t 1 -r 1 -d 0.5 -o 0 > ../results/scalability/dummy_profiled_$(date -u  '+%Y%m%d%H%M').txt

PYTHONPATH=$PYTHONPATH:~/repos/nepi/src NEPI_LOGLEVEL=debug python -m cProfile -s cumulative dummy.py -n 10 -a 5 -t 1 -r 1 -d 0.5 -o 0 > dummy_profiled.txt
