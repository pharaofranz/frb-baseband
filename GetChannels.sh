#!/bin/bash

read -p "Enter source name: " SourceName 
read -p "Enter experiment name: " ExpName
#read -p "Enter telescope initials: " TeleName 

obs=$(obsinfo.py -i "$ExpName".vex -s $SourceName --setup -t o8)
#obs=$(obsinfo.py -i "$ExpName".vex -s $SourceName --setup -t TeleName)

var1=$(echo $obs | grep -oP '(?<=fref).*?(?=MHz)')
flow=$(echo ${var1##*=})

var2=$(echo $obs | grep -oP '(?<=Bandwidth/IF).*(?=MHz)')
IF=$(echo ${var2##*=})

var3=$(echo $obs |  grep -oP '(?<=Number).*(?=recording)')
NbrIF=$(echo ${var3##*=})

python3 CalcChannels.py $SourceName $flow $IF $NbrIF


#obsinfo.py -i "$ScanName".vex -s SourceName --setup -t o8 > TempList
#grep "=" TempList > TempList
#flow=$(awk '$1 == fref { print $3 }' TempList)

#obsinfo.py -i "$ScanName".vex -s SourceName --setup -t o8 | grep "=" > TempList
#flow=$(awk '$1 == fref { print $3 }' TempList2)
