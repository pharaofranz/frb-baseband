# Possible edits before installing the pipeline
The file base2fil.sh is the wrapper script around all the rest. This is also where all of the
different I/O-directories can be set with default values. This is not strictly required as
all of these directories can also be set via the config script at run time (see frb.conf for a
description of all the possible parameters and their meaning). The variables of interest and their
default values are the following:  

workdir_odd_base=/scratch0/${USER}/   # vdif files are split into subbands by jive5ab, odd IFs go here  
workdir_even_base=/scratch1/${USER}/  # even IFs go here; can be the same as $workdir_odd_base  
outdir_base=/data1/${USER}/           # final downsampled filterbank file goes here  
fifodir_base=/tmp/${USER}/            # the pipeline works with fifos to limit I/O. Leaving as is should work  
vbsdir_base=${HOME}/vbs_data/         # baseband data is mounted here with vbs_fs. Should work as is.  


# Installing the pipeline
There is a very simple Makefile that you can edit according to your needs.
All this will do is to copy the essential scripts to a destination of your choosing and turn the
script into executibles. 

# Required edits before running the pipeline

## Environment variables
Part of the pipeline is that jive5ab does some corner turning. For things to work you need to
set two environment variables:  
FLEXIP -- that's the IP address of the machine where jive5ab is running  
FLEXPORT -- the communication port that particular jive5ab instance is listening on  

## DSPSR
1. In the top level directory of dspsr, create the file backends.list. It needs to contain
(at least) the following in one line:  
sigproc fits vdif
2. Modify the file ./Kernel/Classes/OutputFile.C  You'll need to change line 69 from:  
int oflag = O_WRONLY | O_CREAT | O_TRUNC | O_EXCL;  
to  
int oflag = O_WRONLY | O_CREAT | O_TRUNC;
3. Build dspsr
4. In case digifil complains that "Your ipol (1) was >= npol (1)" you may need to rewind dspsr and psrchive to
an earlier commit, namely for dspsr to commit b68528e15e8 and, to be on the safe side, you'd also need rewind
your psrchive to commit 79ed5c0821. Then go through steps 2 and 3 again (first rebuild psrchive).

## TEMPO2
Most of the regular EVN stations are not known to tempo2. For dspsr to be able to properly fold
the filterbanks you may want to add the following lines to ./T2runtime/observatory/observatories.dat. If
your station is not listed here, check out the locations.dat file of your distribution of sched.  
 3370965.909    711466.197      5349664.194      ONSALA85            On85  
 3370605.7800   711917.7251     5349830.9156     ONSALA60            On60  
 3370605.7800   711917.7251     5349830.9156     OTT-E               OTT-E  
 3638558.5100   1221969.7200    5077036.7600     TORUN               Tr  
 3183649.314    1276902.989     5359264.710      IRBENE              Ir  
 3183295.000    1276276.000     5359611.000      IRBENE16            Ib  
 2730173.6472   1562442.7975    5529969.1556     Svetloe             Sv  
 -838201.1031   3865751.5547    4987670.8919     Badary              Bd  
 4461369.6718   919597.1349     4449559.3995     Medicina            Mc  
 4934562.8175   1321201.5528    3806484.7555     Noto                Nt  
 3828445.659    445223.600000   5064921.5677     WSRT                wsrt  
