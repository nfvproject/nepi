#!/bin/bash

## SCALABILTY 
#### NS3

runs=2
nodes=(1 10) 
apps=(1 10) 
threads=(1 10)  

# Change number of nodes [1, 10, 30, 100, 500] (apps = 1, threads = 20)
for n in $nodes; do
    for a in $apps; do
        for t in $threads; do
            for i in $(seq 2 $runs); do
                echo "Number of nodes = $n. Number of apps = $a. Number of threads = $t. Run $i."
                NEPI_LOGLEVEL=debug python ./scalability/ns3.py -n $n -a $a -t $t -r $i -H "localhost" > nodes$n.apps$a.threads$t.runs$i.out 2>&1
                if [ $? != 0 ]; then
                    echo "Problem with node $n app $a thread $t execution the $i time"
                fi
            done
        done
    done
done

