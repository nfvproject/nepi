#!/bin/bash
## Run instructions:
## cd ~/repos/nepi/src/benchmark
## PYTHONPATH=$PYTHONPATH:~/repos/nepi/src/ bash scalability/run_benchmark.sh


## SCALABILTY 
#### NS3

run0=2
runn=2
nodes=(1 2) 
apps=(1 2) 
threads=(1 2)  

mkdir -p logs

# Change number of nodes [1, 10, 30, 100, 500] (apps = 1, threads = 20)
for n in "${nodes[@]}"; do
    for a in "${apps[@]}"; do
        for t in "${threads[@]}"; do
            for i in $(seq $run0 $runn); do
                echo "Number of nodes = $n. Number of apps = $a. Number of threads = $t. Run $i."
                echo "NEPI_LOGLEVEL=debug python scalability/ns3.py -n $n -a $a -t $t -r $i -H "localhost" > logs/nodes$n.apps$a.threads$t.runs$i.out 2>&1"
                NEPI_LOGLEVEL=debug python scalability/ns3.py -n $n -a $a -t $t -r $i -H "localhost" > logs/nodes$n.apps$a.threads$t.runs$i.out 2>&1
                if [ $? != 0 ]; then
                    echo "Problem with node $n app $a thread $t execution the $i time"
                fi
            done
        done
    done
done

