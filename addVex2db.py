#!/usr/bin/env python3
import argparse
from astropy.time import Time
import os
import pandas as pd
from create_config import vex2dic, getExperimentName

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('vexfile', type=str,
                         help='Vexfile used for the experiment. Script will ' \
                         'add to or create pandas dataframe that contains the info '\
                         'from the SCHED section in the vexfile.')
    general.add_argument('-f', '--db_file', type=str, default=os.environ['VEXDB'],
                         help='Name of pandas dataframe file. Expected to be a pickle file. '\
                         'If the file exists entries will be added; if it does not exists will '\
                         'will create a new file. Defaults to environmen variable VEXDB; i.e. '
                         'default=%(default)s')
    general.add_argument('--replace', action='store_true',
                         help='If set will replace all entries for a given experiment with those in '\
                         'the supplied vexfile.(Assumption is that experiment name in vexfile exists '\
                         'already in dataframe).')
    general.add_argument('--debug', action='store_true',
                         help='If set will raise errors to explain what went wrong instead '\
                         'of just saying that something did not work.')
    return parser.parse_args()


def getFreq(vexdic, station, mode):
    '''
    Returns the reference frequency, bandwidth, and number of IFs for station in mode.
    '''
    lines = vexdic['MODE']
    station = station.capitalize()
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('def')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('enddef')]
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        if mode in lines[start_lineNum]:
            for lineNum in range(start_lineNum+1,stop_lineNum):
                line = lines[lineNum]
                if ('FREQ' in line) and (station in line):
                    f_info = line.split('=')[1].strip().split('MHz')
                    f_ref = float(f_info[0])
                    n_if, bw = f_info[1].split('x')
                    n_if = str(int(n_if) // 2)
                    bw = float(bw)
                    break
            break
    try:
        return f_ref, bw, n_if
    except:
        raise RunError(f'Could not determine Frequency setup for {station} in {mode}.')

    
def sched2df(vexdic):
    '''
    Takes a dictionary with key 'SCHED' that contains all lines from the 'SCHED' section.
    Returns a pandas dataframe with all the scans and their info.
    '''
    experiment = getExperimentName(vexdic)
    lines = vexdic['SCHED']
    scans = pd.DataFrame(columns=['experiment','scanNo', 't_startMJD', 'gap2previous_sec', 'length_sec',
                                  'missing_sec', 'fmode', 'source', 'station', 'RefFreq_MHz', 'BW_MHz', 'n_IF'])
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('scan')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('endscan')]
    first_scan = True
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        scanNo = int(lines[start_lineNum].replace('scan No', '').replace(';',''))
        first_station = True
        for lineNum in range(start_lineNum+1,stop_lineNum):
            line = lines[lineNum]
            # parameters can be either all in one line or one per line
            # but always separated by ';' and ending on ';'
            entries = line.split(';')
            for entry in entries:
                if 'start' in entry:
                    start = entry.split('=')[1].strip()\
                                               .replace('y',':')\
                                               .replace('d',':')\
                                               .replace('h',':')\
                                               .replace('m',':')\
                                               .replace('s','')
                    start = Time(start, format='yday', scale='utc').mjd
                    if first_scan:
                        gap2previous = 0
                    else:
                        gap2previous = int((start - previous_stop) * 86400)
                elif 'mode' in entry:
                    mode = entry.split('=')[1].strip()
                elif 'source' in entry:
                    source = entry.split('=')[1].strip()\
                                                 .replace('_D','')
                elif 'station' in entry:
                    station, missing_sec, length_sec = entry.split(':')[:3]
                    station = station.split('=')[1].strip()
                    missing_sec = int(missing_sec.split(' s')[0].strip())
                    length_sec = int(length_sec.split(' s')[0].strip())
                    if first_station:
                        first_station = False
                    else:
                        if not length_tmp == length_sec:
                            print(f'\nWARNING: Not all stations have the same scan length in scanNo {scanNo}.\n')
                    length_tmp = length_sec
                    f_ref, bw, n_if = getFreq(vexdic, station, mode)
                    scans = scans.append({'experiment': experiment, 'scanNo': scanNo, 't_startMJD': start,\
                                          'gap2previous_sec': gap2previous, \
                                          'length_sec': length_sec, 'missing_sec': missing_sec,\
                                          'fmode': mode, 'source': source,
                                          'station': station, 'RefFreq_MHz': f_ref, 'BW_MHz': bw,\
                                          'n_IF': n_if}, ignore_index=True)
                else:
                    continue

        previous_stop = start + length_sec / 86400.
        first_scan = False
    return scans
    
class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class RunError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message

    
def main(args):
    vexfile = os.path.abspath(args.vexfile)
    vex = vex2dic(vexfile)
    df_file = os.path.abspath(args.db_file)
    if not os.path.exists(df_file):
        df = sched2df(vex)
        df.to_pickle(df_file)
    else:
        df = pd.read_pickle(df_file)
        # first check if experiment is already in the dataframe
        exp = getExperimentName(vex)
        if exp in df.experiment.unique():
            if args.replace:
                print(f'Will replace all entries for experiment {exp} with entries from '\
                      f'supplied {vexfile}.')
                df = df.loc[(df.experiment != exp)]
            else:
                raise InputError(f'Experiment {exp} already in the database. Use flag --replace '\
                                 'to replace the existing entry.')
        df = pd.concat([df, sched2df(vex)])
        df.to_pickle(df_file)
    return
        
        
if __name__ == "__main__":
    args = options()
    main(args)
    
