# Calculates the number of channels and downsampling factor.
import sys
import dm_utils as dm

SourceName = sys.argv[1]
f = float(sys.argv[2])          # In MHz
IF = float(sys.argv[3])         # In MHz
NbrOfIF = float(sys.argv[4])

DM = dm.get_dm(SourceName)
f_min = (f-IF)/1000              # In GHz    
Delta_t = 64                     # Wanted time resolution in us
BW = NbrOfIF*IF 
RBW = Delta_t*f_min**3/(8.3*DM)  # In MHz
NbrOfChan = BW/RBW
#print("Check NbrOfChan: ", NbrOfChan)

MaxNbrChan = 2**13
if NbrOfChan > MaxNbrChan:
   Check_t = (BW/MaxNbrChan)*8.3*DM/(f_min**3)
   print("Check time: ", Check_t)
   if Check_t >= 100: 
      Delta_t = 2*Delta_t
      RBW = Delta_t*f_min**3/(8.3*DM) 
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

ChanPerIF = NbrOfChan_FFT/NbrOfIF
RecordRate = 1/(2*IF)
t_samp = RecordRate*2*ChanPerIF   # Per channel
DownSampFactor = Delta_t/t_samp

#print("Calculated #channels: ", NbrOfChan)
#print("Total #channels: ", NbrOfChan_FFT)
print("#channels/IF: ", ChanPerIF)
print("Sampling time: ", t_samp)
print("Downsampling factor: ", DownSampFactor)

