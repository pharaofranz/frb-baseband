#!/bin/bash

# Directory for vex files. Has to match what's in start_online_process.sh on FS
VexDir=/home/oper/frb_processing/vex/

# Generates a help message.
case $1 in
 -[h?] | --help)
    cat <<-____HALP
        Usage: ${0##*/} [ --help ]
        This script takes a scan name as input and then outputs the experiment name,
        telescope name, source name, scan number, lowest reference frequency, IF and
        number of IFs to submit_job.py, which then submits the job. The script also
        checks if a pandas dataframe already exists, so the path to the vex-file
        directory needs to be added (in the beginning of the script).
____HALP
        exit 0;;
esac


ScanName=$1
ExpName=$(echo ${ScanName/_*/})
TelName=$(cut -f2 -d"_" <<< $ScanName)
ScanNbr=$(echo ${ScanName##*_} | grep -o -E "[0-9]+")

VexFile="$VexDir/$ExpName".vex
if test -f "$VexFile".df; then # Checks if a pandas dataframe already exist. If it does, it will be removed.
    rm "$VexFile".df
fi

SourceName=$(obsinfo.py -i $VexFile -t $TelName -S $ScanNbr | tr -s ' ' ',' | csvcut -c 'source' | sed -n '2 p')
FreqInfo=$(obsinfo.py -i $VexFile -s $SourceName --setup -t $TelName)

var1=$(echo $FreqInfo | grep -oP '(?<=fref).*?(?=MHz)')
fref=$(echo ${var1##*=})

var2=$(echo $FreqInfo | grep -oP '(?<=Bandwidth/IF).*(?=MHz)')
IF=$(echo ${var2##*=})

var3=$(echo $FreqInfo |  grep -oP '(?<=Number).*(?=recording)')
NbrOfIF=$(echo ${var3##*=})

submit_job.py -t $TelName -s $SourceName -S $ScanNbr -f $fref -I $IF -n $NbrOfIF -v $VexFile
