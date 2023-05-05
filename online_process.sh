#!/bin/bash
# This script takes a scan name as input and then outputs the experiment name, 
# telescope name, scan number, source name, lowest reference frequency, IF 
# and number of IFs to submit_job.py, which then submits the job.

# I guess the scan name should come from Rave each time a new scan is finished?
# Maybe it's enough if the script checks for a new input every 15.5 min? Or should 
# it check every 30 s? submit_job needs to check with jive5ab if it's ready? Or put
# on queue. 

# read -p "Enter experiment name: " ExpName 
# TotalNbrOfScans=$(grep -o "scan No" "$ExpName".vex | wc -l)
# for ((i=1; i<=$TotalNbrOfScans; i++)) # Or maybe use while-loop instead
#do
# Gets scan name from Rave
ScanName=$(echo pr272a_o8_no0002)
echo "Scan name: " $ScanName 
ExpName=$(echo ${ScanName/_*/})
TelName=$(cut -f2 -d"_" <<< $ScanName)
ScanNbr=$(echo ${ScanName##*_} | grep -o -E "[0-9]+")

SourceName=$(obsinfo.py -i "$ExpName".vex -t $TelName -S $ScanNbr | tr -s ' ' ',' | csvcut -c 'source' | sed -n '2 p') 
echo "Source name: " $SourceName

FreqInfo=$(obsinfo.py -i "$ExpName".vex -s $SourceName --setup -t $TelName)

var1=$(echo $FreqInfo | grep -oP '(?<=fref).*?(?=MHz)')
flow=$(echo ${var1##*=})

var2=$(echo $FreqInfo | grep -oP '(?<=Bandwidth/IF).*(?=MHz)')
IF=$(echo ${var2##*=})

var3=$(echo $FreqInfo |  grep -oP '(?<=Number).*(?=recording)')
NbrIF=$(echo ${var3##*=})

python3 submit_job.py $ExpName $TelName $ScanNbr $SourceName $flow $IF $NbrIF
#done

# Reference scan: pr272a_o8_no0062
# Pulsar scan: pr272a_ef_no0032
