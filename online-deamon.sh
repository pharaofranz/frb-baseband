#!/bin/bash

# - this script should be sitting there and watch the state of, say, a file that gets updated every now and then
# - if it gets updated, i.e. a line is appended, it will check how many jobs are already running on the system
# - if the threshold is exceeded, it will wait for a while, then check again
# - once sufficient CPU slots are available, it will submit the job
# - it may happen that the file gets updated while we're waiting for enough slots to be come available
# - then we'll have to add that job to the 'queue'
# - we should probably write this in python...
# - or maybe not
#   - https://stackoverflow.com/questions/3430330/best-way-to-make-a-shell-script-daemon#10908325
#   - http://www.faqs.org/faqs/unix-faq/programmer/faq/
# - not sure, maybe a full deamon is overkill? Could just have script that runs in a tmux pane somewhere. And have that start up via tmuxinator

joblist=${1:-/tmp/joblist.txt}
maxjobs=${2:-38}

if ! [ -f ${joblist} ];then
    touch ${joblist}
fi

# check what's in the list from the start
nlines_start=$(wc -l $joblist | cut -d ' ' -f1)

# create an array for the jobs to be processed
declare -a jobarray

# we check for new entries to the joblist-file every 10s. If there's a new entry
# we add it to our array;
# at the same time we check how many jobs are running and submit the jobs in case there
# are enough slots.
while true; do
    nlines=$(wc -l ${joblist} | cut -d ' ' -f1)
    n_new_jobs=$(echo "${nlines}-${nlines_start}" | bc -l)
    if [ ${n_new_jobs} -gt 0 ];then
        nlines_start=${nlines}
        for i in `seq ${n_new_jobs} -1 1`;do
            # entries below contains both the config file and the number of IFs
            linenum=$(echo "${nlines}-${i}+1" | bc -l)
            jobarray[${#jobarray[@]}]=$(sed "${linenum}q;d" ${joblist})
        done
    fi
    job=${jobarray[0]}
    if ! [ -n "$job" ];then
        echo 'no jobs but '
        echo "we see $(ps -ef | grep digifil | grep -v /bin/sh | wc -l) jobs running"
        sleep 10
        continue
    fi
    config_file=$(cut -d ' ' -f1 <<< ${job})
    n_subbands=$(cut -d ' ' -f2 <<< ${job})
    njobs_running=$(ps -ef | grep digifil | grep -v /bin/sh | wc -l)
    if [ $(echo "${n_subbands}+1+${njobs_running}" | bc -l) -lt ${maxjobs} ];then
        #submit the job
        echo "submitting ${config_file}"
        base2fil ${config_file}
        # drop that first entry from the array
        jobarray=( "${jobarray[@]:1}" )
    fi
    sleep 10
done
