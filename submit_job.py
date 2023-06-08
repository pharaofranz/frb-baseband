#!/usr/bin/env python3
# This script calculates the number of channels per IF, the time resolution,
# downsampling factor and number of jobs. It then creates a config file which it 
# also submits as a job to base2fil.sh.

import sys
import os
import re
import dm_utils as dm
from subprocess import check_output

ExpName = sys.argv[1]
TelName = sys.argv[2]
ScanNbr = sys.argv[3]
SourceName = sys.argv[4]
f = float(sys.argv[5])			# In MHz
IF = float(sys.argv[6])			# In MHz
NbrOfIF = float(sys.argv[7])

DM = dm.get_dm(SourceName)
if DM is not None:			# Check if calibrator scan or target source.
    f_min = (f-IF)/1000            	# In GHz    
    BW = NbrOfIF*IF 

    if dm.isPulsar == False:
        t_res = 64			# Wanted time resolution in us
        RBW = t_res*f_min**3/(8.3*DM)	# In MHz
        NbrOfChan = BW/RBW
        
        MaxNbrOfChan = 2**13
        if NbrOfChan > MaxNbrOfChan:
            Check_t = (BW/MaxNbrOfChan)*8.3*DM/(f_min**3)
            if Check_t >= 100: 
                t_res = 2*t_res
                RBW = t_res*f_min**3/(8.3*DM) 
                NbrOfChan = BW/RBW

        for i in range(1,14):
            n = 2**i
            if NbrOfChan < n or NbrOfChan == n or i == 13 and NbrOfChan > n:
                NbrOfChan_FFT = n
                break
        ChanPerIF = int(NbrOfChan_FFT/NbrOfIF)
    else:                                            
        NbrOfTimeBins = 512
        TimePeriod = check_output("psrcat -c 'p0' -o short " + SourceName + " -nohead -nonumber", shell=True) 
        TimePeriod  = re.findall("\d+\.\d+", str(TimePeriod)) # In s
        T = float(TimePeriod[0])*10**6                        # In us 
        t_res = T/NbrOfTimeBins
        i = 6                         		# Since the lowest time resolution is 64 us
        TestPowerOf2 = False
        while TestPowerOf2 == False:
            n = 2**i
            if t_res == n:
                TestPowerOf2 = True
            elif t_res < n:
                t_res = n/2 
                TestPowerOf2 = True
            i += 1

        RBW = t_res*f_min**3/(8.3*DM)		# In MHz
        NbrOfChan = BW/RBW   
        for i in range(1,14):
            n = 2**i
            if NbrOfChan < n or NbrOfChan == n or i == 13 and NbrOfChan > n:
                NbrOfChan_FFT = n
                break       
        ChanPerIF = int(NbrOfChan_FFT/NbrOfIF)
        MinChanPerIF = 32
        if ChanPerIF < MinChanPerIF:
            ChanPerIF = MinChanPerIF
            NbrOfChan_FFT = ChanPerIF*NbrOfIF

    RecordRate = 1/(2*IF)
    t_samp = RecordRate*2*ChanPerIF		# Per channel
    DownSamp = int(t_res/t_samp)  
    NbrOfJobs = int(IF+1)
    f_min = int(f_min*1000) 	       		# In MHz
    f_max = int(f_min+BW)

    PathToCode = "/home/cecilia/Documents/frb-baseband/"
    VexFile = "/home/oper/" + ExpName + ".vex" 
    ConfigFile = "/home/oper/" + ExpName + "_" + TelName + "_" + SourceName + "_no" + str(ScanNbr) + ".conf"
    PathToFlag = "/data1/franz/fetch/Standard/" + TelName + ".flag_" + str(f_min) + "-" + str(f_max) + "MHz_" + str(NbrOfChan_FFT) + "chan"
    CreateConfig = PathToCode + "create_config.py -i " + VexFile + " -s " + SourceName + " -t " + TelName + " -N " + str(NbrOfJobs) + " -d " + str(DownSamp) + " -n " + str(ChanPerIF) + " -S " + str(ScanNbr) + " -F " + PathToFlag + " --online" + " -o " + ConfigFile  
    if dm.isPulsar == False:
        CreateConfig += CreateConfig + " --search"
    else:
        CreateConfig += CreateConfig + " --pol 4"
    os.system(CreateConfig)

    SubmitJob = PathToCode + "base2fil.sh " + ConfigFile
    # Check so there are enough available job slots before submitting the job
    TotalSlots = 60
    MaxBusySlots = int(TotalSlots-(NbrOfIF+1))
    CheckDigifil = "while [ $(ps -ef | grep digifil | grep -v /bin/sh | wc -l) -gt " + str(MaxBusySlots) + " ]; do sleep 30; done"
    os.system(CheckDigifil)
    os.system(SubmitJob)
