#!/bin/bash
# This script takes the experiment name from the field system as input and checks
# if it is related to a FRB/pulsar experiment and that it is not a VLBI experiment?
# If so, then it checks the name of the current scan and outputs it to online_process.sh. 

ExpName=$(lognm) # Check how to do this
if [ ${ExpName:0:1} == "p" ]; then
    if [ ${ExpName:1:1} != "r" ]; then
        NewScan=$(inject_snap -w "mk5=scan_set?") # Determine the scan name
        ScanName=$(cut -f3 -d":" <<< $NewScan)
        ssh oper@ebur "/home/cecilia/Documents/frb-baseband/online_process.sh ${ScanName}"
    fi
fi
