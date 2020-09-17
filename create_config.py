#!/usr/bin/env python3
import argparse
from astropy.time import Time
import os
import pandas as pd

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('vexfile', type=str,
                         help='vexfile used for the experiment. Script will ' \
                         'create a pandas dataframe that contains the info '\
                         'from the SCHED section in the vexfile. The dataframe ' \
                         'will be created (and looked for) in the directory where ' \
                         'where the vexfile lives. It will be named <vexfile>.df.')
    general.add_argument('-s', '--source', type=str, required=True,
                         help='REQUIRED. Source for which data are to be analysed.')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr', \
                                  'onsala85', 'onsala60', 'srt',\
                                  'wsrt', 'effelsberg', 'torun'],
                         help='REQUIRED. Station name or 2-letter code of dish to be searched.')
    general.add_argument('-S', '--scans', nargs='+', default=None, type=int,
                         help='Optional list of scans to be searched. By default will ' \
                         'return all scans. Scan numbers with or without leading zeros.')
    general.add_argument('-n', '--nchan', type=int, default=128,
                         help='Number of channels per subband (i.e. per IF). Default=%(default)s')
    general.add_argument('-d', '--downsamp', type=int, default=1,
                         help='Downsampling factor for final filterbanks. Default '\
                         'is no downsampling.')
    general.add_argument('-o', '--outfile', type=str, default=None,
                         help='Name of the output config file. Per default will be ' \
                         'created in current working directory and will be named ' \
                         '<experiment>_<station>_<source>.conf[_<mode>], where ' \
                         '_<mode> will only be appended in case there a multiple '\
                         'frequency setups.')
    general.add_argument('-T', '--template', type=str, default=None,
                         help='Template config file that contains parameters beyond '\
                         'those taken care of here. Existing parameters that this '\
                         'script takes care of will be overwritten.')
    
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

def getFreq(vexdic, station, mode):
    '''
    Returns the reference frequency, bandwidth, and number of IFs for station in mode.
    '''
    lines = vexdic['MODE']
    station = fixStationName(station).capitalize()
    mode = mode.upper()
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

def getExperimentName(vexdic):
    '''
    Returns the name of the experiment as defined in the vexfile.
    '''
    lines = vexdic['EXPER']
    start_lineNums = [i for i,line in enumerate(lines) if line.startswith('def')]
    stop_lineNums = [i for i,line in enumerate(lines) if line.startswith('enddef')]
    if len(start_lineNums) > 1:
        raise RunError(f'Found more than one experiment name in vexfile. Not sure how to deal with this...')
    for lineNum in range(start_lineNums[0]+1,stop_lineNums[0]):
        line = lines[lineNum]
        if 'exper_name' in line:
            experiment = line.split('=')[1].strip().replace(';','')
            break
    return experiment

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
    station = fixStationName(station).capitalize()
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
        skip_secs.append(skip_sec-1 if skip_sec > 0 else skip_sec)
        start_scans.append(f'{scan:03d}')
    scanNames = [f'{scan:03d}' for scan in list(ddf.scanNo.values)]
    if not len(start_scans) == len(skip_secs) == len(scan_lengths) == len(scanNames):
        raise RunError('Not the same number of scans, seconds to skip and scan lengths.')
    return start_scans, skip_secs, scan_lengths, scanNames
    
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

def writeConfig(outfile, experiment, source, station,
                ra, dec, fref, bw, nIF, nchan, downsamp,
                scans, skips, lengths,
                scanNames, template=None):
    templ = []
    if not template == None:
        if not os.path.exists(template):
            raise InputError(f'The supplied template file {template} does not exist.')
        f = open(template, 'r')
        templ = f.readlines()
        f.close()
        params = ['experiment', 'target', 'scans', 'skips',
                  'lenghts', 'freqLSB_0', 'bw', 'nif',
                  'nchan', 'tscrunch', 'station']
        # we overwrite existing parameters
        delLines = [i for param in params for i,line in enumerate(templ) if param in line]
        templ = [line for i,line in enumerate(templ) if i not in delLines]
    scans = list2BashArray(scans)
    skips = list2BashArray(skips)
    lengths = list2BashArray(lengths)
    scanNames = list2BashArray(scanNames)
    station = fixStationName(station, short=False)
    templ.append(f'experiment={experiment}\n')
    templ.append(f'target=\"{source} --ra {ra} --dec {dec}\"\n')
    templ.append(f'station={station}\n')
    templ.append(f'scans={scans}\n')
    templ.append(f'skips={skips}\n')
    templ.append(f'lengths={lengths}\n')
    templ.append(f'scannames={scanNames}\n')
    templ.append(f'freqLSB_0={fref-bw/2}\n')
    templ.append(f'bw={bw}\n')
    templ.append(f'nif={nIF}\n')
    templ.append(f'nchan={nchan}\n')
    templ.append(f'tscrunch={downsamp}\n')
    with open(outfile, 'w') as f:
        for line in templ:
            f.write(line)
    return
    
    
def list2BashArray(l):
    '''
    Takes a regular list and turns it into a bash array for scripting.
    '''
    if not isinstance(l, list):
        try:
            l = list(l)
        except:
            raise InputError(f'Supplied object cannot be turned into a list. l={l}.')
    array = '( '
    for i in l:
        array = f'{array}{i} '
    array = f'{array})'
    return array

def fixStationName(station, short=True):
    '''
    Returns the 2-letter station code for station if short=True, else the 
    long version that is TEMPO2-compliant.
    '''
    station = station.lower()
    longnames = ['onsala85', 'onsala60', 'srt', 'wsrt', 'effelsberg', 'torun']
    shortnames = ['o8', 'o6', 'sr', 'wb', 'ef', 'tr']
    if not (station in longnames) and not (station in shortnames):
        raise InputError(f'Station {station} not recognized. ' \
                         f'Must be any of {longnames} or {shortnames}')
    if len(station) > 2:
        return shortnames[longnames.index(station)] if short else station
    else:
        return station if short else longnames[shortnames.index(station)]
    
def main(args):
    vexfile = os.path.abspath(args.vexfile)
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
    experiment = getExperimentName(vex)
    print(f'Found experiment {experiment}.')
    fmodes = list(df.fmode.unique())
    print(f'There are {len(fmodes)} frequency modes: {fmodes}')
    source = args.source.replace('_D','').upper()
    station = args.telescope
    nchan = args.nchan
    downsamp = args.downsamp
    outfile = args.outfile
    template = args.template
    ra, dec = getSourceCoords(vex, source)
    if outfile == None:
        outdir = os.getcwd()
        outfile = f'{outdir}/{experiment}_{station}_{source}.conf'
    first=True
    for i,fmode in enumerate(fmodes):
        if len(fmodes) > 1:
            if first:
                outfile = f'{outfile}_{fmode}'
                first = False
            else:
                outfile = outfile.replace(fmodes[i-1], fmode)
        try:
            fref, bw, nIF = getFreq(vex, station, fmode)
        except:
            print(f'No setup for station {station} in mode {fmode}.')
            continue
        try:
            scans, skips, lengths, scanNames = getScanList(df, source,
                                                           station, fmode,
                                                           scans=args.scans)
        except:
            print(f'Found no data for {source} for {station} in {fmode}.')
        try:
            writeConfig(outfile, experiment, source, station, ra, dec,
                        fref, bw, nIF, nchan, downsamp, scans, skips, lengths,
                        scanNames, template)
            print(f'Successfully written {outfile}.')
        except:
            print(f'Could not create config file for {source} observed with {station} in {fmode}.')
    return
        
        
if __name__ == "__main__":
    args = options()
    main(args)
    
