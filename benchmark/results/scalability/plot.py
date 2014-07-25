#import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('GTK') 
import matplotlib.pyplot as plt
import numpy as np

data = dict()

f = open("dummy_scalability1.out", "r")
for l in f:
    if l.startswith("time|"):
        continue
    rows = l.split("|")
    node_count = int(rows[11])
    app_count = int(rows[12])
    
    # Compute number of rms (1 dev per node)
    rm_count = node_count*2 + app_count*node_count + 1

    thread_count = int(rows[13])

    ttd = int(rows[14])
    ttr = int(rows[15])
    ttrel = int(rows[16])

    # Compute total duration of experiment in seconds
    duration = (ttd + ttr + ttrel) / 1000.0
    
    if not thread_count in data:
        data[thread_count] = dict()
    if not rm_count in data[thread_count]:
        data[thread_count][rm_count] = list()

    data[thread_count][rm_count].append(duration)
   
f.close()

## compute mean and standard deviation of the data

#plt.gca().set_color_cycle(['red', 'green', 'blue', 'yellow', 'orange'])
colors = ['red', 'green', 'blue', 'orange']
i = 0

for thread_count, rm_info in data.iteritems():
    x = []
    y = []
    emin = []
    emax = []
    legends = []

    for rm_count in sorted(rm_info.keys()):
        durations = rm_info[rm_count]

        samples = np.array(durations)
        m = samples.mean()
        min = samples.min()
        max = samples.max()

        x.append(rm_count)
        y.append(m)
        emin.append(min)
        emax.append(max)

    # plot
    legends.append(thread_count)
    color = colors[i]

    plt.plot(x, y, marker= 'o', linestyle='-', color=color, 
            label="%d threads" % thread_count)
    plt.plot(x, emax, marker= '+', linestyle='', color=color)
    plt.plot(x, emin, marker= '_', linestyle='', color=color)

    i += 1

    """
    x = sorted(rm_info.keys())
    print x
    samples = []

    for rm_count in x:
        samples.append(rm_info[rm_count])

    plt.boxplot(samples, positions=x)
    legends.append(thread_count)
    """

plt.xlabel('# Resources')
#plt.gca().set_xscale('log')

plt.ylabel('Duration (second)')
#plt.gca().set_yscale('log')

plt.legend(loc='upper left')
plt.show()

