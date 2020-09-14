#!/usr/bin/env python3
import argparse
from astropy.time import Time
import os
import pandas as pd

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('vexfile', type=str,
                         help='vexfile used for the experiment')
    general.add_argument('-s', '--source', type=str, required=True,
                         help='Source for which data are to be analysed.')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr'],
                         help='2-letter Station code of dish to be searched.')
    general.add_argument('-S', '--scans', nargs='+', default=None,
                         help='Optional list of scans to be searched. By default will ' \
                         'return all scans. Scan numbers without leading zeros please.')
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
    lines = vexdic['MODE']
    station = station.capitalize()
    mode = mode.upper()
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('def')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('enddef')]
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        if mode in lines[start_lineNum]:
            for lineNum in range(start_lineNum+1,stop_lineNum):
                line = lines[lineNum]
                if ('FREQ' in line) and (station in line):
                    f_info = line.split('=')[1].strip().split('MHz')
                    f_ref = f_info[0]
                    n_if, bw = f_info[1].split('x')
                    n_if = str(int(n_if) // 2)
                    break
            break
    try:
        return f_ref, bw, n_if
    except:
        raise RunError(f'Could not determine Frequency setup for {station} in {mode}.')

def getSourceCoords(vexdic, source):
    '''
    Returns the RA and Dec for source.
    '''
    lines = vexdic['SOURCE']
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('def')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('enddef')]
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        if source in lines[start_lineNum]:
            for lineNum in range(start_lineNum+1,stop_lineNum):
                line = lines[lineNum]
                if 'dec' in line:
                    ra, dec = line.split(';')[:2]
                    ra = ra.split('=')[1].strip()
                    dec = dec.split('=')[1].strip()
                    ra = ra.replace('h', ':').replace('m', ':').replace('s', '')
                    dec = dec.replace('d', ':').replace('\'', ':').replace('\"','')
                    break
    try:
        return ra, dec
    except:
        raise RunError(f'Could not get Ra and Dec for {source}.')
    
def sched2df(vexdic):
    '''
    Takes a dictionary with key 'SCHED' that contains all lines from the 'SCHED' section.
    Returns a pandas dataframe with all the scans and their info.
    '''
    lines = vexdic['SCHED']
    scans = pd.DataFrame(columns=['scanNo', 't_startMJD', 'gap2previous_sec', 'length_sec',
                                  'missing_sec', 'fmode', 'source', 'station'])
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('scan')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('endscan')]
    first_scan = True
    for start_lineNum,stop_lineNum in zip(start_lineNums, stop_lineNums):
        scanNo = int(lines[start_lineNum].replace('scan No', '').replace(';',''))
        first_station = True
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
                if first_scan:
                    gap2previous = 0
                else:
                    gap2previous = int((start - previous_stop) * 86400)
            elif line.startswith('station'):
                station, missing_sec, length_sec = line.split(':')[:3]
                station = station.split('=')[1].strip()
                missing_sec = int(missing_sec.split(' s')[0].strip())
                length_sec = int(length_sec.split(' s')[0].strip())
                if first_station:
                    first_station = False
                else:
                    if not length_tmp == length_sec:
                        print(f'\nWARNING: Not all stations have the same scan length in scanNo {scanNo}.\n')
                length_tmp = length_sec
                scans = scans.append({'scanNo': scanNo, 't_startMJD': start,\
                                      'gap2previous_sec': gap2previous, \
                                      'length_sec': length_sec, 'missing_sec': missing_sec,\
                                      'fmode': mode, 'source': source,
                                      'station': station}, ignore_index=True)
            else:
                continue
        previous_stop = start + length_sec / 86400.
        first_scan = False
    return scans

def getScanList(df, source, station, mode, scans=None):
    '''
    For source, station and mode in vexfile, 
    returns three lists: scanNo's, number of seconds to skip 
    at the beginning of the scan, and number of secodns to process.
    '''
    mode = mode.upper()
    station = station.capitalize()
    ddf = df[(df.source == source) &
             (df.fmode == mode) &
             (df.station == station)]
    if scans:
        ddf = ddf[(ddf.scanNo.isin(scans))]
    if ddf.empty:
        raise InputError(f'No data found for station: {station}, mode: {mode}, source: {source}, scans: {scans}.')
    scan_lengths = list(ddf.length_sec)
    skip_secs = []
    start_scans = []
    for scanNo in list(ddf.scanNo.values):
        scan = scanNo
        skip_sec = 0
        while df[(df.scanNo == scan) &
                 (df.station == station)].gap2previous_sec.item() < 10:
            scan -= 1
            skip_sec += df[(df.scanNo == scan) &
                           (df.station == station)].length_sec.item()
        skip_secs.append(skip_sec-1)
        start_scans.append(scan)
    if not len(start_scans) == len(skip_secs) == len(scan_lengths):
        raise RunError('Not the same number of scans, seconds to skip and scan lengths.')
    return start_scans, skip_secs, scan_lengths
    
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
    vexfile = args.vexfile
    vex = vex2dic(vexfile)
    # per default we expect the dataframe to be in the same dir
    # as the vexfile. If it's not there we create it such that
    # we can re-use it again later.
    sched_dir = os.path.dirname(vexfile)
    vexfile_name = os.path.basename(vexfile)
    df_file = f'{sched_dir}/{vexfile_name}.df'
    if not os.path.exists(df_file):
        df = sched2df(vex)
        df.to_pickle(df_file)
    else:
        df = pd.read_pickle(df_file)
    fmodes = list(df.fmode.unique())
    print(f'There are {len(fmodes)} frequency modes: {fmodes}')
    source = args.source.replace('_D','')
    station = args.telescope
    ra, dec = getSourceCoords(vex, args.source)
    for fmode in fmodes:
        try:
            fref, bw, nIF = get_freq(vex, station, fmode)
        except:
            print(f'No setup for station {station} in mode {fmode}.')
            continue
        scans, skips, lengths = getScanList(df, source,
                                            station, fmode,
                                            scans=args.scans)
        
    return
        
        
if __name__ == "__main__":
    args = options()
    main(args)
