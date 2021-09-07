#!/bin/bash

helpmsg() {
    message='''
    \n
    This script takes a config file as input -- check out frb.conf that was shipped with this repo. \n
    \n
    Essentially, this script takes baseband data (i.e. raw voltages) stored on a Flexbuff in VDIF format \n
    and converts those data to channelised filterbank files. It can generate either Stokes I, full polarisation \n
    filterbanks or single polarisation data. Note that the script assumes circular polarisation as is common in \n
    VLBI recordings.\n
    \n
    In case you have FETCH installed that is running with a rabbitmq-queue, then the filterbanks will we sent off\n
    to that queue. I.e., this script can be used as an end-to-end pipeline to search for millisecond-duration \n
    bright bursts such as giant pulses from pulsars or FRBs.\n
    \n
    In case you observed a known pulsar then the data will be folded and a diagnostic plot will be generated.\n
    ''' 
    echo -e $message
}

pwait() {
    # helper to parallelize jobs
    while [ $(jobs -p | wc -l) -ge $1 ]; do
        sleep 0.33
    done
}

run_process_vdif() {
    # assumes that the IFs passed to the function are all of the same sideband
    # and increase in frequency by 2 x BW
    scanname=$1
    ifs=$2
    source=$3
    experiment=$4
    st=$5
    freqEdge=$6
    bw=$7
    sideband=$8
    nchan=$9
    nsec=${10}
    start=${11}
    station=${12}
    njobs=${13}
    skip=${14}
    workdir=${15}
    pol=${16}
    nthreads=${17}
    tscrunch=${18}
    fifodir=${19}
    nbit=${20}
    bandstep=`echo $bw+$bw | bc`

    for i in ${ifs};do
        process_vdif ${source} ${workdir}/${experiment}_${st}_no0${scanname}_IF${i}.vdif  \
                     -f $freqEdge -b ${bw} -${sideband} --nchan $nchan --nsec $nsec --start $start \
                     --force -t ${station} --pol ${pol} --nthreads ${nthreads} --tscrunch ${tscrunch} \
		     --fil_out_dir ${fifodir} --nbit=${nbit} & sleep 0.2
        pwait $njobs
        freqEdge=`echo $freqEdge+$bandstep | bc`
    done
}

check_progs() {
    progs='process_vdif spif2file cmd2flexbuff setfifo bc vdif_print_headers splice digifil'
    for prog in $progs; do
	which $prog
	if [[ $? -eq 1 ]];then
	    echo "Could not find ${prog} in your PATH. Aborting."
	    exit 1
	fi
    done
}

check_vars() {
    if [[ -z ${FLEXIP} ]] || [[ -z ${FLEXPORT} ]];then
	echo "You need to set environment variables FLEXIP and FLEXPORT."
	echo "FLEXIP is the IP address of the machine where jive5ab is running."
	echo "FLEXPORT is the port that instance of jive5ab is listening on."
	exit 1
    fi
}
	   

compare_size() {
    # takes a list of files and compares their sizes
    # the list is something like files='f1 f2 f3...fn'
    files=$1
    msg "comparing sizes btw ${files}"
    s=0
    diff=1
    counter=0
    while [[ $diff -eq 1 ]];do
        diff=0
        for f in $files;do
            size=`ls -l ${f} | cut -d ' ' -f 5`
            if ! [[ $size -eq $s ]];then
                #echo "size = $size"
                #echo "s = $s"
                diff=1
            fi
            s=$size
        done
        sleep 1
        let counter=${counter}+1
        if [[ $counter -eq 90 ]];then
            msg "file sizes still not the same, aborting..."
            return 1;
        fi
    done
    msg "Seems fine, final size is $size"
}
submit_fetch() {
    # argument $1 points at the filterbank file
    # argument $2 points at the flag file -- can be empty.
     /home/franz/.conda/envs/fetch/bin/python /home/franz/software/src/greenburst/pika_send.py -q "stage01_queue" -m "${1} ${2}"
}
msg() {
    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` ${1}"
}

get_frame_size(){
    frame_size=`vdif_print_headers ${1} -n1 | tail -1 | cut -d '=' -f9`
    echo ${frame_size}
}

get_header_size(){
    l=`vdif_print_headers ${1} -n1 | tail -1 | cut -d ',' -f6`
    if [[ ${l} -eq 'legacy = 0' ]]; then
	echo 32
    elif [[ ${l} -eq 'legacy = 1' ]]; then
	echo 16
    else
	msg "Unknown legacy parameter: ${l}. Aborting."
	exit 1
    fi
}

get_station_code(){
    stations='onsala85 onsala60 srt wsrt effelsberg torun irbene irbene16 medicina noto urumqi badary svetloe'
    sts=(o8 o6 sr wb ef tr ir ib mc nt ur bd sv)
    station=$1
    station=${station,,} # set all to lower case
    c=0
    st=''
    for sta in ${stations};do 
	if [[ ${sta} == ${station} ]];then
	    st=${sts[c]}
	    break
	fi
	let c+=1
    done
    if [[ -z "$st" ]]; then
	echo "Station ${station} not known."
	echo "Options are: (${stations})"
	return 1
    fi
    echo $st
}

if [[ $1 == '-h' ]] || [[ -z "$1" ]];then
    helpmsg
    exit 0
fi

check_progs
check_vars

# intiate some default vars

workdir_odd_base=/scratch0/${USER}/   #  vdif files expected to be here
workdir_even_base=/scratch1/${USER}/
outdir_base=/data1/${USER}/           # final downsampled filterbank file goes here
fifodir_base=/tmp/${USER}/
vbsdir_base=${HOME}/vbs_data/    # baseband data is mounted here.
start=0 #

pol=2           # if set to 2 will create stokes I 
                # if set to either 0 or 1 will process only one polarisation
digifil_nthreads=1 # speeds up the creation of the filterbanks but you lose sensitivity...
flipIF=0
njobs_parallel=20
submit2fetch=0  # if equal to zero will not submit the filterbanks to fetch
nbit=8          # bit depth of fitlerbanks. Can be 2, 8, 16, -32. -32 is floating point 32 bit
isMark5b=0      # by default we assume the raw data are VDIF data, if this set will assume Mark5B recordings
keepVDIF=0      # by default split VDIF files are deleted to save space on disk, if set will keep those data
flagFile=''     # optionally, a flag file can be passed

# load other vars from config file, params above will be overwritten if they are in the config file
source ${1}
if [[ $? -eq 1 ]];then
    helpmsg
    exit 1
fi

# run parse_vex.py with input from ${1}
# parse_vex.py takes config files and appends necessary info.
# then we source that new input file.
# in case of multiple freq setups for same source and station run
# several times from here

workdir_odd=${workdir_odd_base}/${experiment}   #  vdif files expected to be here
workdir_even=${workdir_even_base}/${experiment}
outdir=${outdir_base}/${experiment}           # final downsampled filterbank file goes here
fifodir=${fifodir_base}/fifos/
vbsdir=${vbsdir_base}/${experiment}    # baseband data is mounted here.

# nothing to change below this line
datarate=`echo $bw*$nif*8 | bc | cut -d '.' -f1` # bw in MHz, 8 = 2pol*2bitsamples*2nyquist
nbbc=`echo ${nif}*2 | bc | cut -d '.' -f1`

freqUSB_0=`echo ${freqLSB_0}+${bw} | bc`  # central frequency of lowest USB channel (typically IF2)
st=`get_station_code ${station}`
if [[ $? -eq 1 ]];then
    echo $st
    exit 1
fi

let max_odd=${nif}-1
ifs_odd=`seq 1 2 ${max_odd}`
ifs_even=`seq 2 2 ${nif}`

if ! [ -d ${workdir_odd} ];then
    mkdir -p ${workdir_odd}
fi
if ! [ -d ${workdir_even} ];then
    mkdir -p ${workdir_even}
fi
if ! [ -d ${outdir} ];then
    mkdir -p ${outdir}
fi
if ! [ -d ${vbsdir} ];then
    mkdir -p ${vbsdir}
fi
if ! [ -d ${fifodir} ];then
    mkdir -p ${fifodir}
fi
n_baseband_files=`ls -l ${vbsdir} | wc -l`
if [ ${n_baseband_files} -eq 1 ];then
    msg "${vbsdir} is empty."
    msg "Mounting files for ${experiment} into ${vbsdir}"
    echo " Running vbs_fs -n 8 -I \"${experiment}*\" ${vbsdir}" -o allow_other
    vbs_fs -n 8 -I "${experiment}*" ${vbsdir} -o allow_other
    sleep 3
    n_baseband_files=`ls -l ${vbsdir} | wc -l`
    if [ ${n_baseband_files} -eq 1 ];then
	msg "Something went wrong, still have no files in ${vbsdir}."
	echo "Aborting..."
	exit 1
    fi
fi
msg "There are ${n_baseband_files} baseband files in ${vbsdir}"


if [ ${isMark5b} -eq 0 ];then
    test_file=`ls ${vbsdir}/*_${st}_* | head -1`
    msg "getting bytes_per_frame from ${test_file}"
    frame_size=`get_frame_size ${vbsdir}/${test_file}`
    headersize=`get_header_size ${vbsdir}/${test_file}`
    bytes_per_frame=`echo ${frame_size}-${headersize} | bc` 
    mode="VDIF_${bytes_per_frame}-${datarate}-${nbbc}-2"
else
    msg "Assuming mark5b data with a payload of 10000 bytes per frame and a 16 byte header."
    mode="MARK5B-${datarate}-${nbbc}-2"
fi

msg "will use ${mode}"

scancounter=-1
for scan in "${scans[@]}";do
    let scancounter=${scancounter}+1
    skip=${skips[${scancounter}]}
    length=${lengths[${scancounter}]}
    scanname=${scannames[${scancounter}]}
    # make sure scan and scanname is a 3-digit-number with leading zeros
    scan=`printf "%03g" ${scan}`
    scanname=`printf "%03g" ${scanname}`
    vdif_files=""
    splice_list=''
    for i in `seq 1 2 ${nif}`;do
        # odd IFs first
        vdifnme=${workdir_odd}/${experiment}_${st}_no0${scanname}_IF${i}.vdif
        vdif_files=${vdif_files}${vdifnme}" "
        if [ ! -f ${vdifnme} ];then
            msg "Splitting the raw data."
            #spif2file ${experiment} ${st} ${scan} ${nif} ${mode} ${skip} ${length} ${scanname} \
	    #	${flipIF} ${vbsdir} ${workdir_odd} ${workdir_even}
            /home/franz/git/frb-baseband/spif2file.sh ${experiment} ${st} ${scan} ${nif} ${mode} ${skip} ${length} ${scanname} \
		      ${flipIF} ${vbsdir} ${workdir_odd} ${workdir_even}
    	if [[ $? -eq 1 ]];then
    	    exit 1
    	fi
            msg "splitting is done, waiting 5s for the disks to catch up"
            sleep 5
        fi
        filfifo=${fifodir}/`basename ${vdifnme}`_pol${pol}.fil
        mkfifo ${filfifo}
        splice_list=${filfifo}' '${splice_list}
        # then even IFs
        let n=$i+1
        vdifnme=${workdir_even}/${experiment}_${st}_no0${scanname}_IF${n}.vdif
        vdif_files=${vdif_files}${vdifnme}" "
        if [ ! -f ${vdifnme} ];then
            msg "Splitting the raw data for even IFs."
            #spif2file ${experiment} ${st} ${scan} ${nif} ${mode} ${skip} ${length} ${scanname} \
	#	      ${flipIF} ${vbsdir} ${workdir_odd} ${workdir_even}
            /home/franz/git/frb-baseband/spif2file.sh ${experiment} ${st} ${scan} ${nif} ${mode} ${skip} ${length} ${scanname} \
		      ${flipIF} ${vbsdir} ${workdir_odd} ${workdir_even}
    	if [[ $? -eq 1 ]];then
    	    exit 1
    	fi
            msg "splitting is done, waiting 5s for the disks to catch up"
            sleep 5
        fi
        filfifo=${fifodir}/`basename ${vdifnme}`_pol${pol}.fil
        mkfifo ${filfifo}
        splice_list=${filfifo}' '${splice_list}
    done

    let njobs_splice=${njobs_parallel} #${nif}+1 # 1 extra for splice, another for digfil

    compare_size "${vdif_files}"
    if [[ $? -eq 1 ]];then
        exit 1
    fi
    file_size=`ls -l ${vdifnme} | cut -d ' ' -f 5`

    frame_size_split=`get_frame_size ${vdifnme}`
    headersize_split=`get_header_size ${vdifnme}`

    bytes_per_frame_split=`echo ${frame_size_split}-${headersize_split} | bc`
    
    frames_per_second=`echo ${datarate}*1000000/8/${bytes_per_frame_split} | bc | cut -d '.' -f1`
    frames_per_second_per_band=`echo ${frames_per_second}/${nif} | bc | cut -d '.' -f1`
    nsec=`echo "${file_size}/${frame_size_split}/${frames_per_second_per_band}" | bc`

    run_process_vdif $scanname "$ifs_odd" "$target" $experiment $st $freqLSB_0 $bw l $nchan $nsec $start \
                     $station $njobs_splice $skip $workdir_odd $pol $digifil_nthreads $tscrunch ${fifodir} \
		     $nbit
    # even IFs (i.e. USB)
    run_process_vdif $scanname "$ifs_even" "$target" $experiment $st $freqUSB_0 $bw u $nchan $nsec $start \
                     $station $njobs_splice $skip $workdir_even $pol $digifil_nthreads $tscrunch ${fifodir} \
		     $nbit

    filfile=${experiment}_${st}_no0${scanname}_IFall_vdif_pol${pol}.fil
    # increase the fifo buffer size to speed things up, but wait till splice is running first
    sleep 2 && for filfifo in ${splice_list}; do \
        setfifo ${filfifo} 1048576; \
        sleep 0.2;done && msg "Changed fifo sizes successfuly." &
    if [[ $submit2fetch -ne 0 ]]; then
	if [[ $keepVDIF -eq 0 ]]; then
	    splice ${splice_list} > ${outdir}/${filfile} && \
		rm -rf ${workdir_even}/${experiment}_${st}_no0${scanname}_IF*.vdif \
		   ${workdir_odd}/${experiment}_${st}_no0${scanname}_IF*.vdif && \
		submit_fetch ${outdir}/${filfile} ${flagFile} && \
		msg "Submitted ${outdir}/${filfile} ${flagFile} to fetch" && \
		for filfifo in ${splice_list};do rm -rf $filfifo; done && \
		msg "Fifos removed" &
	else
	    splice ${splice_list} > ${outdir}/${filfile} && \
		submit_fetch ${outdir}/${filfile} ${flagFile} && \
		msg "Submitted ${outdir}/${filfile} ${flagFile} to fetch" && \
		for filfifo in ${splice_list};do rm -rf $filfifo; done && \
		msg "Fifos removed" &
	fi
    else
	if [[ $keepVDIF -eq 0 ]]; then
	    splice ${splice_list} > ${outdir}/${filfile} && \
		rm -rf ${workdir_even}/${experiment}_${st}_no0${scanname}_IF*.vdif \
		   ${workdir_odd}/${experiment}_${st}_no0${scanname}_IF*.vdif && \
		for filfifo in ${splice_list};do rm -rf $filfifo; done && \
		msg "Fifos removed" &
	else
	    splice ${splice_list} > ${outdir}/${filfile} && \
		for filfifo in ${splice_list};do rm -rf $filfifo; done && \
		msg "Fifos removed" &
	fi
    fi
    sleep 5
    pwait $njobs_splice
done # end scans
wait < <(jobs -p)

# in the current setup ${target} might contain Ra and Dec; remove that first and also remove
# all whitespaces
target=`echo ${target} | cut -d '-' -f1 | sed 's/ *$//'`

# psrcat below will not throw an error on BSGR because it starts with B...
# hence we exit here in case we are dealing with BSGR.
if [[ ${target} == 'BSGR' ]];then
    exit 0
fi

# in case we look at a pulsar fold it and create a plot
psrcat -e ${target} > ${target}.psrcat.par
if [ $? -eq 0 ];then
    counter=-1
    for scan in "${scans[@]}";do
	let counter=${counter}+1
	scanname=${scannames[${counter}]}
	scan=`printf "%03g" ${scan}`
	scanname=`printf "%03g" ${scanname}`
        filfile=${experiment}_${st}_no0${scanname}_IFall_vdif_pol${pol}.fil
        dspsr -E ${target}.psrcat.par -L 10 -A -k ${station} -d1 ${outdir}/${filfile} -O ${outdir}/${filfile} -t 8
        psrplot -pF -D /CPS -c x:unit=s ${outdir}/${filfile}.ar -j dedisperse,tscrunch,pscrunch,"fscrunch 128"
        mv pgplot.ps ${outdir}/${filfile}.ps
    done
fi
