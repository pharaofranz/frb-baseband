#!/usr/bin/env python3
# This script calculates the number of channels per IF, the time resolution,
# downsampling factor and number of jobs. It then creates a config file which it
# also submits as a job to base2fil.sh.

import os
import re
import dm_utils as dm
from subprocess import check_output
import argparse

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr', \
                                  'ir', 'ib', 'mc', 'nt', 'ur', 'bd', 'sv'],
                         help='REQUIRED. 2-letter code of dish to be searched.')
    general.add_argument('-s', '--source', type=str, required=True,
                         help='REQUIRED. Source name for which data are to be analysed.')
    general.add_argument('-S', '--scannum', type=str, required=True,
                         help='REQUIRED. The scan number to be analyzed.')
    general.add_argument('-f', '--fref', type=float, required=True,
                         help='REQUIRED. The lowest reference frequency in MHz.')
    general.add_argument('-I', '--IF', type=float, required=True,
                         help='REQUIRED. The IF (both upper and lower included) in MHz.')
    general.add_argument('-n', '--nIF', type=int, required=True,
                         help='REQUIRED. Number of IFs.')
    general.add_argument('-v', '--vex', type=str, required=True,
                         help='REQUIRED. Vex file of the experiment (absolute path).')
    general.add_argument('-e', '--expname', type=str, required=False, default=None,
                         help='Only needed if experiment name is different from vex file name.')
    general.add_argument('-j', '--joblist', type=str, default='/tmp/joblist.txt',
                         help='File to which jobs, i.e. config files, will be appended. '+
                         'Those will be picked up by online-deamon.sh (needs to be started separately.)')
    return parser.parse_args()


def main(args):
    TotalSlots = 38 # Total number of job slots.
    ConfigDir = "/home/oper/frb_processing/configs/"
    FlagDir = "/data1/franz/fetch/Standard/"
    VexFile = args.vex
    ExpName = args.expname if args.expname is not None else (os.path.basename(args.vex)).split('.')[0]
    j = 6 # 2 to the power of j = wanted time resolution (or the lowest value for the system). In us.

    TelName = args.telescope
    SourceName = args.source
    ScanNbr = args.scannum
    f = args.fref
    IF = args.IF
    NbrOfIF = float(args.nIF)

    DM = dm.get_dm(SourceName)
    if DM is not None:			# Check if calibrator scan or target source.
        f_min = (f-IF)/1000            	# In GHz.
        BW = NbrOfIF*IF

        if dm.isPulsar == False:
            t_res = 2**j			# Wanted time resolution in us.
            RBW = t_res*f_min**3/(8.3*DM)	# In MHz.
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
            TimePeriod  = re.findall("\d+\.\d+", str(TimePeriod)) # In s.
            T = float(TimePeriod[0])*10**6      # In us.
            t_res = T/NbrOfTimeBins
            i = j                         	# Lowest time resolution value for the system. Then check if it can be higher.
            TestPowerOf2 = False
            while TestPowerOf2 == False:
                n = 2**i
                if t_res == n:
                    TestPowerOf2 = True
                elif t_res < n:
                    t_res = n/2
                    TestPowerOf2 = True
                i += 1

            RBW = t_res*f_min**3/(8.3*DM)	# In MHz.
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
        t_samp = RecordRate*2*ChanPerIF		# Per channel.
        DownSamp = int(t_res/t_samp)
        NbrOfJobs = int(IF+1)
        f_min = int(f_min*1000) 	        # In MHz.
        f_max = int(f_min+BW)

        ConfigFile = ConfigDir + ExpName + "_" + TelName + "_" + SourceName + "_no" + ScanNbr + ".conf"
        FlagFile = FlagDir + TelName + ".flag_" + str(f_min) + "-" + str(f_max) + "MHz_" + str(NbrOfChan_FFT) + "chan"
        CreateConfig = "create_config.py -i " + VexFile + " -s " + SourceName + " -t " + TelName + " -N " + str(int(NbrOfIF+1)) + " -d " + str(DownSamp) + " -n " + str(ChanPerIF) + " -S " + ScanNbr + " -F " + FlagFile + " --online" + " -o " + ConfigFile
        if dm.isPulsar is False:
            CreateConfig += CreateConfig + " --search"
        else:
            CreateConfig += CreateConfig + " --pol 4"
        os.system(CreateConfig)

        check_joblist_exists = f"if ! [ -f {args.joblist} ];then touch {args.joblist};fi"
        os.system(check_joblist_exists)

        SubmitJob = f"echo \"{ConfigFile} {args.nIF}\" >> {args.joblist}"
        os.system(SubmitJob)
    return


if __name__ == "__main__":
    args = options()
    main(args)
