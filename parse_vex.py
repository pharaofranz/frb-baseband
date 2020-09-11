#!/usr/bin/env python3
import argparse
import pandas as pd
from astropy.time import Time

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('vexfile', type=str,
                         help='vexfile used for the experiment')
    general.add_argument('-s', '--source', type=str, required=True,
                         help='Source for which data are to be analysed.')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         help='2-letter Station code of dish to be searched.')
    general.add_argument('-S', '--scans', type=str, nargs='+',
                         help='Optional list of scans to be searched. By default will ' \
                         'return all scans.')
    return parser.parse_args()


def vex2dic(vexfile):
    '''
    Opens the vexfile, strip()'s it, removes all commented lines and returns a dictionary
    whose keys are the differnt sections and their lines are the entries.
    '''
    try:
        f = open(vexfile, 'r')
    except:
        raise InputError(f'Something is wrong with your {vexfile}')
    vex = f.readlines()
    f.close()
    VEX = {}
    vex = [l.strip() for l in vex]
    vex = [l for l in vex if not l.startswith('*')]
    section_starts = [i for i,l in enumerate(vex) if l.startswith('$')]
    for i,line_num in enumerate(section_starts):
        key = vex[line_num].replace('$', '').replace(';','')
        try:
            VEX[key] = vex[line_num+1:section_starts[i+1]]
        except:
            VEX[key] = vex[line_num+1:]
    return VEX

def get_freq(vexdic, station, mode):
    '''
    Returns the reference frequency, bandwidth, and number of IFs for station in mode.
    '''
    
    return f_ref, bw, n_if

def sched2df(vexdic):
    '''
    Takes a dictionary with key 'SCHED' that contains all lines from the 'SCHED' section.
    Returns a pandas dataframe with all the scans and their info.
    '''
    lines = vexdic['SCHED']
    scans = pd.DataFrame(columns=['scanNo', 't_startMJD', 'length_sec',
                                  'missing_sec', 'mode', 'source', 'station'])
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('scan')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('endscan')]
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        scanNo = lines[start_lineNum].replace('scan No0', '').replace(';','')
        for lineNum in range(start_lineNum+1,stop_lineNum):
            line = lines[lineNum]
            if line.startswith('start'):
                start, mode, source, _ = line.split(';')
                start = start.split('=')[1].strip()\
                                           .replace('y',':')\
                                           .replace('d',':')\
                                           .replace('h',':')\
                                           .replace('m',':')\
                                           .replace('s','')
                start = Time(start, format='yday', scale='utc').mjd
                mode = mode.split('=')[1].strip()
                source = source.split('=')[1].strip()\
                                             .replace('_D','')
            elif line.startswith('station'):
                station, missing_sec, length_sec = line.split(':')[:3]
                station = station.split('=')[1].strip()
                missing_sec = int(missing_sec.split(' s')[0].strip())
                length_sec = int(length_sec.split(' s')[0].strip())
                scans = scans.append({'scanNo': scanNo, 't_startMJD': start,\
                                      'length_sec': length_sec, 'missing_sec': missing_sec,\
                                      'mode': mode, 'source': source,
                                      'station': station}, ignore_index=True)
            else:
                continue
    return scans

def get_times(vexfile, scans):
    '''
    
    '''


    
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


if __name__ == "__main__":
    args = options()
