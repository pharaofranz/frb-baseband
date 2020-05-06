#!/bin/bash

pwait() {
    # helper to parallelize jobs
    while [ $(jobs -p | wc -l) -ge $1 ]; do
        sleep 0.33
    done
}

run_process_vdif() {
    # assumes that the IFs passed to the function are all of the same sideband
    # and increase in frequency by 2 x BW
    scan=$1
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
    chunk=${14}
    workdir=${15}
    pol=${16}
    nthreads=${17}
    tscrunch=${18}
    fifodir=${19}
    bandstep=`echo $bw+$bw | bc`

    for i in ${ifs};do
        ~/git/my_all/python/process_vdif.py ${source} ${workdir}/${experiment}_${st}_no0${scan}_IF${i}_s${chunk}.vdif  \
                                            -f $freqEdge -b ${bw} -${sideband} --nchan $nchan --nsec $nsec --start $start \
                                            --force -t ${station} --pol ${pol} --nthreads ${nthreads} --tscrunch ${tscrunch} --fil_out_dir ${fifodir} & sleep 0.2
        pwait $njobs
        freqEdge=`echo $freqEdge+$bandstep | bc`
    done
}

compare_size() {
    # takes a list of files and compares their sizes
    # the list is something like files='f1 f2 f3...fn'
    files=$1
    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` comparing sizes btw ${files}"
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
        sleep 5
        let counter=${counter}+1
        if [[ $counter -eq 30 ]];then
            echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` file sizes still not the same, aborting..."
            return 1;
        fi
    done
    echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Seems fine, final size is $size"
}
submit_fetch() {
     /home/franz/software/src/anaconda3/envs/osoFRBsearch/bin/python /home/franz/software/src/greenburst/pika_send.py -q "stage01_queue" -m ${1}
}
####
# Onsala, magnetar obs
####
scans=`seq -f "%03g" 6 28` # SGR1935, 15 min
#scans='001'  # B1933+16, 10min

#source="R3 --ra 01:58:00.7495 --dec 65:43:00.3185"
#source="R2 --ra 04:22:39.0 --dec 73:40:06.00"
source="SGR1935 --ra 19:34:55.68 --dec 21:53:48.2"

#source="B0531+21"
#source="B0329+54"
#source="B0355+54"
#source="B1933+16"

chunks='1'         # relevant only for PRECISE runs (one file contains 4 scans, cal - target - cal - target, in that case chunks='1 3')
freqLSB_0=1275.49  # central frequency of lowest LSB channel (typically IF1)
freqUSB_0=1307.49  # central frequency of lowest USB channel (typically IF2)
bw=32.0            # bandwidth per IF
#station='SRT'
#st='sr'
station='Onsala85'  # relevant for folding data (station code for tempo2)
st='o8_2g'          # relevant for bit map used by jive5ab (see spif2file.vlbish)
experiment='pr999e'
workdir_odd='/scratch0/franz/'${experiment}   #  vdif files expected to be here
workdir_even='/scratch1/franz/'${experiment}
outdir='/data1/franz/'${experiment}           # final downsampled filterbank file goes here
fifodir='/tmp/franz/fifos/'
start=0 #
cal_length1=0   # length of first cal-scan
cal_length2=0   # length of second cal-scan
tgt_length1=898 # length of first target scan
tgt_length2=0   # length of second target scan

nchan=256       # number of channels in filterbank
nif=8           # number of subbands in the data, 16 at OSO at 4G recording, 8 at Tr or Sr at 2G recording
pol=2           # if set to 2 will create stokes I 
                # if set to either 0 or 1 will process only one polarisation
tscrunch=8      # downsampling factor for digil (final filterbank)
digifil_nthreads=1 # speeds up the creation of the filterbanks but you lose sensitivity...

# below relevant for number of seconds in vdif data
frame_size=8016        # in bytes
frames_per_second=4000 # 4000 for 4G recording at OSO = 64000 / 16 IFs
                       # 4000 also for 2G recording at SRT = 32000 / 8 IFs

# nothing to change below this line
# fiddling around with 'st'-variable. $sts is only used in submission to bogar
# to enable different bitmaps for the same station (e.g. Tr at L- or at C-band)
# we need the first two letters on from $st as defined above for file names
sts=$st
st=${sts:0:2}
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
#if ! [ -d ${tmpdir} ];then
#    mkdir -p ${tmpdir}
#fi
if ! [ -d ${fifodir} ];then
    mkdir -p ${fifodir}
fi
for scan in $scans;do
    for chunk in ${chunks};do
        vdif_files=""
        splice_list=''
        for i in `seq 1 2 ${nif}`;do
            # odd IFs first
            vdifnme=${workdir_odd}/${experiment}_${st}_no0${scan}_IF${i}_s${chunk}.vdif
            vdif_files=${vdif_files}${vdifnme}" "
            if [ ! -f ${vdifnme} ];then
                echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Splitting the VDIF on Bogar."
                /home/franz/scripts/spif2file_2chunk.vlbish ${experiment} ${sts} ${scan} ${chunk} ${cal_length1} ${cal_length2} ${tgt_length1} ${tgt_length2} ${nif}
                echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` splitting is done, waiting 30s for the disks to catch up"
                sleep 30
            fi
            #filfifo=${vdifnme}_pol${pol}.fil
	    filfifo=${fifodir}/`basename ${vdifnme}`_pol${pol}.fil
            mkfifo ${filfifo}
            splice_list=${filfifo}' '${splice_list}
            # then even IFs
            let n=$i+1
            vdifnme=${workdir_even}/${experiment}_${st}_no0${scan}_IF${n}_s${chunk}.vdif
            vdif_files=${vdif_files}${vdifnme}" "
            if [ ! -f ${vdifnme} ];then
                echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Splitting the VDIF on Bogar for even IFs."
                /home/franz/scripts/spif2file_2chunk.vlbish ${experiment} ${sts} ${scan} ${chunk} ${cal_length1} ${cal_length2} ${tgt_length1} ${tgt_length2} ${nif}
                echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` splitting is done, waiting 30s for the disks to catch up"
                sleep 30
            fi
            #filfifo=${vdifnme}_pol${pol}.fil
	    filfifo=${fifodir}/`basename ${vdifnme}`_pol${pol}.fil
            mkfifo ${filfifo}
            splice_list=${filfifo}' '${splice_list}
        done

    let njobs_splice=18 #${nif}+1 # 1 extra for splice, another for digfil

    compare_size "${vdif_files}"
    if [[ $? -eq 1 ]];then
        exit 1
    fi
    file_size=`ls -l ${vdifnme} | cut -d ' ' -f 5`
    nsec=`echo "${file_size}/${frame_size}/${frames_per_second}" | bc`
    run_process_vdif $scan "$ifs_odd" "$source" $experiment $st $freqLSB_0 $bw l $nchan $nsec $start \
                      $station $njobs_splice $chunk $workdir_odd $pol $digifil_nthreads $tscrunch ${fifodir}
    # even IFs (i.e. USB)
    run_process_vdif $scan "$ifs_even" "$source" $experiment $st $freqUSB_0 $bw u $nchan $nsec $start \
                      $station $njobs_splice $chunk $workdir_even $pol $digifil_nthreads $tscrunch ${fifodir}

    filfile=${experiment}_${st}_no0${scan}_IFall_s${chunk}_vdif_pol${pol}.fil
    # increase the fifo buffer size to speed things up, but wait till splice is running first
    sleep 2 && for filfifo in ${splice_list}; do \
        /home/franz/scripts/setfifo.perl ${filfifo} 1048576; \
        sleep 0.2;done && echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Changed fifo sizes successfuly." &
    splice ${splice_list} > ${outdir}/${filfile} && \
        rm ${workdir_even}/${experiment}_${st}_no0${scan}_IF*_s${chunk}.vdif \
           ${workdir_odd}/${experiment}_${st}_no0${scan}_IF*_s${chunk}.vdif && \
        submit_fetch ${outdir}/${filfile} && \
        echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Submitted ${outdir}/${filfile} to fetch" && \
        for filfifo in ${splice_list};do rm $filfifo; done && \
        echo "`date +%d'-'%m'-'%y' '%H':'%M':'%S` Fifos removed" &
    sleep 30
done # end chunks
done # end scans
wait < <(jobs -p)
# in case we look at a pulsar fold it and create a plot
psrcat -e ${source} > ${source}.psrcat.par
if [ $? -eq 0 ];then
    for scan in $scans;do
        for chunk in ${chunks};do
            filfile=${experiment}_${st}_no0${scan}_IFall_s${chunk}_vdif_pol${pol}.fil
            dspsr -E ${source}.psrcat.par -L 10 -A -k ${station} -d1 ${outdir}/${filfile} -O ${outdir}/${filfile} -t 8
            psrplot -pF -D /CPS -c x:unit=s ${outdir}/${filfile}.ar -j dedisperse,tscrunch,pscrunch,"fscrunch 128"
            mv pgplot.ps ${outdir}/${filfile}.ps
        done
    done
fi
