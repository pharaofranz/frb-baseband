#!/bin/bash
# This script takes a scan name as input and then outputs the experiment name, 
# telescope name, scan number, source name, lowest reference frequency, IF 
# and number of IFs to submit_job.py, which then submits the job.

ScanName=$1
ExpName=$(echo ${ScanName/_*/})
TelName=$(cut -f2 -d"_" <<< $ScanName)
ScanNbr=$(echo ${ScanName##*_} | grep -o -E "[0-9]+")

SourceName=$(obsinfo.py -i /home/oper/"$ExpName".vex -t $TelName -S $ScanNbr | tr -s ' ' ',' | csvcut -c 'source' | sed -n '2 p') 
FreqInfo=$(obsinfo.py -i /home/oper/"$ExpName".vex -s $SourceName --setup -t $TelName)

var1=$(echo $FreqInfo | grep -oP '(?<=fref).*?(?=MHz)')
f_low=$(echo ${var1##*=})

var2=$(echo $FreqInfo | grep -oP '(?<=Bandwidth/IF).*(?=MHz)')
IF=$(echo ${var2##*=})

var3=$(echo $FreqInfo |  grep -oP '(?<=Number).*(?=recording)')
NbrOfIF=$(echo ${var3##*=})

python3 /home/cecilia/Documents/frb-baseband/submit_job.py $ExpName $TelName $ScanNbr $SourceName $f_low $IF $NbrOfIF
