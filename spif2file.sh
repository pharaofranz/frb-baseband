#!/bin/bash

experiment=$1
station=$2
scan=$3
nif=$4
mode=$5
skip=${6:-0}
length=${7:-9999}  #in seconds
scanname=${8:-${scan}}
flipped=${9:-0} # recipes assume LO is below sky freq, if LO above sky freq LSB and USB are flipped
vbs_fs_dir=${10:-"${HOME}/vbs_data/${experiment}/"}
outdir1=${11:-"/scratch0/${USER}/${experiment}"}
outdir2=${12:-"/scratch1/${USER}/${experiment}"}
online=${13:-0}

linkdir="/tmp/${USER}/${experiment}/${scanname}"

mode=${mode^^} # set all upper case
directs="${outdir1} ${outdir2} ${linkdir}"
for dir in $directs;do
    if ! [ -d ${dir} ];then
	mkdir -p ${dir}
	if [[ $? -eq 1 ]];then
	    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Could not create non-existend directory ${dir}. Aborting."
	    exit 1
	fi
    fi
done

bitspersample=2
if [[ ${mode} == 'VDIF_8000-4096-32-2' ]];then
    frames_per_second=64000
    recipe="64>[16,17,48,49][0,1,32,33][18,19,50,51][2,3,34,35][20,21,52,53][4,5,36,37][22,23,54,55][6,7,38,39][24,25,56,57][8,9,40,41][26,27,58,59][10,11,42,43][28,29,60,61][12,13,44,45][30,31,62,63][14,15,46,47]:0-15"
#
elif [[ ${mode} == 'VDIF_8000-2048-32-2' ]];then
    frames_per_second=32000
    recipe="64>[16,17,48,49][0,1,32,33][18,19,50,51][2,3,34,35][20,21,52,53][4,5,36,37][22,23,54,55][6,7,38,39][24,25,56,57][8,9,40,41][26,27,58,59][10,11,42,43][28,29,60,61][12,13,44,45][30,31,62,63][14,15,46,47]:0-15"
#
elif [[ ${mode} == 'VDIF_8000-2048-16-2' ]];then
    frames_per_second=32000
    recipe="32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
#
elif [[ ${mode} == 'VDIF_8000-1024-16-2' ]];then
    frames_per_second=16000
    #recipe="32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
    recipe="32>[24,25,16,17][8,9,0,1][26,27,18,19][10,11,2,3][28,29,20,21][12,13,4,5][30,31,22,23][14,15,6,7]:0-7"
#
elif [[ ${mode} == 'VDIF_1000-1024-16-2' ]];then
    frames_per_second=128000
    #recipe="32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
    recipe="32>[24,25,16,17][8,9,0,1][26,27,18,19][10,11,2,3][28,29,20,21][12,13,4,5][30,31,22,23][14,15,6,7]:0-7"
#
elif [[ ${mode} == 'VDIF_8000-1024-8-2' ]];then
    frames_per_second=16000
    recipe="16>[8,9,12,13][0,1,4,5][10,11,14,15][2,3,6,7]:0-3"
#
elif [[ ${mode} == 'VDIF_8000-1024-16-1' ]];then
    frames_per_second=16000
    recipe="16>[8,12][0,4][9,13][1,5][10,14][2,6][11,15][3,7]:0-7"
    bitspersample=1
#
elif [[ ${mode} == 'VDIF_8000-512-4-2' ]];then
    frames_per_second=8000
    recipe="8>[4,5,6,7][0,1,2,3]:0-1"
    #
elif [[ ${mode} == 'VDIF_8000-16-2-2' ]];then
    frames_per_second=250
    recipe="4>[0,1,2,3]:0"
    #
elif [[ ${mode} == 'VDIF_8000-32-4-2' ]];then
    frames_per_second=500
    recipe="8>[0,1,4,5][2,3,6,7]:0-1"
    #
elif [[ ${mode} == 'VDIF_8000-512-16-2' ]];then
    frames_per_second=8000
    recipe="32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
    #
elif [[ ${mode} == 'MARK5B-1024-16-2' ]];then
    frames_per_second=12800
    recipe="swap_sign_mag+32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
    #
elif [[ ${mode} == 'MARK5B-1024-8-2' ]];then
    frames_per_second=12800
    recipe="swap_sign_mag+16>[8,9,12,13][0,1,4,5][10,11,14,15][2,3,6,7]:0-3"
    #
elif [[ ${mode} == 'MARK5B-2048-16-2' ]];then
    frames_per_second=25600
    recipe="swap_sign_mag+32>[16,17,24,25][0,1,8,9][18,19,26,27][2,3,10,11][20,21,28,29][4,5,12,13][22,23,30,31][6,7,14,15]:0-7"
    #
elif [[ ${mode} == 'MARK5B-2048-32-2' ]];then
    frames_per_second=25600
    recipe="swap_sign_mag+64>[16,17,48,49][0,1,32,33][18,19,50,51][2,3,34,35][20,21,52,53][4,5,36,37][22,23,54,55][6,7,38,39][24,25,56,57][8,9,40,41][26,27,58,59][10,11,42,43][28,29,60,61][12,13,44,45][30,31,62,63][14,15,46,47]:0-15"
    #
else
    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` mode ${mode} not implemented. Aborting."
    exit 1
fi

if [[ ${mode:0:4} == 'VDIF' ]]; then
    payload=${mode:5:4}
    output_payload=${payload}
    input_headersize=32
    input_payload=${payload}

elif [[ ${mode:0:6} == 'MARK5B' ]]; then
    output_payload=10000
    input_headersize=16
    input_payload=10000
else
    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Cannot determine frame sizes from ${mode}. Aborting."
    exit 1
fi

input_framesize=`echo "${input_payload}+${input_headersize}" | bc`

if [[ ${flipped} -gt 0 ]];then
    r=`echo $recipe | cut -d '[' -f1`
    sign=-1
    add=1
    for i in `seq 1 ${nif}`;do
	# odd IFs plus 1, even IFs minus 1
	let field=$i+1 # because field 1 is the word length
	let field=${field}+${add}
	r=${r}[`echo $recipe | cut -d '[' -f${field} | cut -d ']' -f1`]
	add=`echo ${add}*${sign} | bc`
    done
    let field=${nif}+1
    r=${r}`echo $recipe | cut -d ']' -f${field}`
    recipe=${r}
fi
echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Using mode ${mode}."
echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Using recipe ${recipe}"

let nif=${nif}-2 # we actually do a plus 1 below and go in steps of two
# rare case of just one IF...
if [[ ${nif} -lt 0 ]]; then
    nif=0
fi
bytes_per_second=`echo "${input_framesize}*${frames_per_second}" | bc`
bytes_per_minute=`echo "${bytes_per_second}*60" | bc`
vbs_fs_file=${experiment}"_${station}_no0"${scan}
vbs_vdif_file=${experiment}"_${station}_no0"${scanname}
start_frame=`vdif_print_headers ${vbs_fs_dir}/${vbs_fs_file} -n1 | tail -1 | tr "," " " | tr " " "|" | awk -F "|" '{print $5}'`
if [[ ${mode:0:6} == 'MARK5B' ]];then
    start_frame=0
fi
skipbytes=`echo "(${frames_per_second}-${start_frame}-1)*${input_framesize}" | bc`
skipbytes=`echo "${skipbytes}+${bytes_per_second}*${skip}" | bc`
start_byte=${skipbytes}
stop_byte=`echo "${start_byte}+${bytes_per_second}*${length}+16*${input_framesize}" | bc`

runtime=${experiment}_${station}_0${scan}
if [[ ${online} -gt 0 ]];then
    runtime='online'
fi

state=$(cmd2flexbuff "runtime=${runtime};spif2file?" | awk '{print $10}')
while [[ ${state} == 'active' ]];do
    sleep 30
    state=$(cmd2flexbuff "runtime=${runtime};spif2file?" | awk '{print $10}')
done
for i in `seq 0 2 ${nif}`;do
    let ii=$i+1
    if [[ -L ${linkdir}/if_${i} ]]; then
        rm ${linkdir}/if_${i}
    fi
    if [[ -L ${linkdir}/if_${ii} ]]; then
        rm ${linkdir}/if_${ii}
    fi
    let odd_if=$i+1
    let even_if=$ii+1
    echo "ln -s ${outdir1}/${vbs_vdif_file}_IF${odd_if}.vdif ${linkdir}/if_${i}"
    echo "ln -s ${outdir2}/${vbs_vdif_file}_IF${even_if}.vdif ${linkdir}/if_${ii}"
    ln -s ${outdir1}/${vbs_vdif_file}_IF${odd_if}.vdif ${linkdir}/if_${i}
    ln -s ${outdir2}/${vbs_vdif_file}_IF${even_if}.vdif ${linkdir}/if_${ii}
done
cmd2flexbuff \
    "runtime=${runtime}; \
     net_protocol=udpsnor:32000000:32000000:3; \
     spif2file=vdifsize:${output_payload}; \
     mode=${mode}; \
     spif2file=bitspersample:${bitspersample}; \
     spif2file=bitsperchannel:${bitspersample}; \
     spif2file=connect:${vbs_fs_dir}/${vbs_fs_file}:${recipe}=${linkdir}/if_{tag},w; \
     spif2file=on:${start_byte}:${stop_byte} "
echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Splitting job for ${vbs_fs_file} submitted, waiting 30s."
sleep 30
state=$(cmd2flexbuff "runtime=${runtime};spif2file?" | awk '{print $10}')
while [[ ${state} == 'active' ]];do
    sleep 10
    state=$(cmd2flexbuff "runtime=${runtime};spif2file?" | awk '{print $10}')
done
# delete the runtime to make jive5ab disconnect from the input file such that we can unmount the directory if needed
cmd2flexbuff "runtime=${runtime}:delete"
