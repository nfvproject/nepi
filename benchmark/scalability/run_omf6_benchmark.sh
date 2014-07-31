#!/bin/bash
## Run instructions:
## cd /home/wlab18/Documents/Nepi/neco/nepi/src
## PYTHONPATH=$PYTHONPATH:/home/wlab18/Documents/Nepi/neco/nepi/src bash scalability/run_omf6_benchmark.sh


## SCALABILTY 
#### OMF6

run0=1
runn=10
nodes=(1 10 30 5) 
apps=(1 10 50)
threads=(1 10 50)
delay="0.5"

hosts=("G1" "D1" "E1" "H1" "I2" "E2" "G2" "H2" "D2" "F2" "G3" "D3" "L3" "I3" "B3" "E3"
"E4" "D4" "I4" "C4" "K4" "H4" "J4" "G4" "F4" "H5" "B5" "J5" "F5" "I5" "K6" "G6" "H6" "J6" "D6" "C6" "I6" "M18" "M20")

mkdir -p logs

# Change number of nodes, apps, threads
for n in "${nodes[@]}"; do
    for a in "${apps[@]}"; do
        for t in "${threads[@]}"; do
            for i in $(seq $run0 $runn); do
                for h in "${hosts[@]}"; do
                    host="zotac"$h".wilab2.ilabt.iminds.be"
                    echo $host
                    ssh jtribino@$host "sudo killall ruby ; sudo service omf_rc start > /dev/null"
                done
                echo "Number of nodes = $n. Number of apps = $a. Number of threads = $t. Run $i."
                echo "NEPI_LOGLEVEL=info python scalability/omf6.py -n $n -a $a -t $t -d $delay -r $i > logs/scheddelay$delay.nodes$n.apps$a.threads$t.runs$i.out 2>&1"
                NEPI_LOGLEVEL=info python scalability/omf6.py -n $n -a $a -t $t -d $delay -r $i > logs/omf6.scheddelay$delay.nodes$n.apps$a.threads$t.runs$i.out 2>&1
                if [ $? != 0 ]; then
                    echo "Problem with node $n app $a thread $t execution the $i time"
                fi
            done
        done
    done
done






