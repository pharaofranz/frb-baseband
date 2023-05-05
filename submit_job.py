#!/usr/bin/env python3
# This script calculates the number of channels per IF, the time resolution
# and downsampling factor. It then creates a config file which it also submits
# as a job to base2fil.sh.

import sys
import os
#from dm_utils import get_dm
import dm_utils as dm

ExpName = sys.argv[1]
TelName = sys.argv[2]
ScanNbr = sys.argv[3]
SourceName = sys.argv[4]
f = float(sys.argv[5])               # In MHz
IF = float(sys.argv[6])              # In MHz
NbrOfIF = float(sys.argv[7])

DM = dm.get_dm(SourceName)

if DM is not None:
   # if 'error' in response:
     #   isPulsar = 1
    f_min = (f-IF)/1000              # In GHz    
    t_res = 64                       # Wanted time resolution in us
    BW = NbrOfIF*IF 
    RBW = t_res*f_min**3/(8.3*DM)    # In MHz
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
       if NbrOfChan < n:
          NbrOfChan_FFT = n
          break
       elif NbrOfChan == n:
          NbrOfChan_FFT = n
          break
       elif i == 13 and NbrOfChan > n:
          NbrOfChan_FFT = n
          break
    
    ChanPerIF = int(NbrOfChan_FFT/NbrOfIF)
    RecordRate = 1/(2*IF)
    t_samp = RecordRate*2*ChanPerIF    # Per channel
    DownSamp = int(t_res/t_samp)
    
    print("#channels/IF: ", ChanPerIF)
    print("Sampling time: ", t_samp)
    print("Downsampling factor: ", DownSamp)
    
    NbrOfJobs = int(IF+1)
    f_min = int(f_min*1000) 	   # In MHz
    f_max = int(f_min+BW)
    VexFile = ExpName + ".vex"
    ConfigFile = ExpName + "_" + TelName + "_" + SourceName + "_no" + str(ScanNbr) + ".conf"
    PathToFlag = "/data1/franz/fetch/Standard/" + TelName + ".flag_" + str(f_min) + "-" + str(f_max) + "MHz_" + str(NbrOfChan_FFT) + "chan"
    dir = "/home/cecilia/Documents/frb-baseband/"
    CreateConfig = dir + "create_config.py -i " + VexFile + " -s " + SourceName + " -t " + TelName + " -N " + str(NbrOfJobs) + " -d " + str(DownSamp) + " -n " + str(ChanPerIF) + " -S " + str(ScanNbr) + " -F " + PathToFlag + " --online" + " -o " + ConfigFile
   
    if dm.isPulsar == False:
        CreateConfig += CreateConfig + " --search"
    else:
        CreateConfig += CreateConfig + " --pol 4"

    print(CreateConfig)
    os.system(CreateConfig)

    SubmitJob = dir + "base2fil.sh " + ConfigFile
    #print(SubmitJob)
    #os.system(SubmitJob)
