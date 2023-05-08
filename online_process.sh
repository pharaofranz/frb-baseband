#!/bin/bash
# This script takes a scan name as input and then outputs the experiment name, 
# telescope name, scan number, source name, lowest reference frequency, IF 
# and number of IFs to submit_job.py, which then submits the job.

# A script on the field system calls this script for every new scan.
# Then this script, or submit_job.py, checks with jive5ab if it's ready to take on a new 
# job? Maybe by putting it on queue? Then it's probably best if submit_job.py handles it. 

ScanName=$1
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


# Reference scan: pr272a_o8_no0062
# Pulsar scan: pr272a_ef_no0032
# Time resolution over 100 us: pr235a_ef_no0003
# pr275a_ef_no0137
