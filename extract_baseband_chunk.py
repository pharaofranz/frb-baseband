#!/usr/bin/env python3

import argparse
from astropy.time import Time
import os
import subprocess
import numpy as np


def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('-m', '--mjds', nargs='+', type=float, required=True,
                         help='List of MJDs around which data should be extracted')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr',
                                  'ir', 'ib', 'mc', 'nt', 'ur', 'bd', 'sv'],
                         help='REQUIRED. Station name or 2-letter code of dish to be worked on.')
    general.add_argument('-n', '--nsec', type=float, default=2,
                         help='Number of seconds to be extracted (refers to ' +
                         'this much time before and after the MJD specified, i.e.' +
                         'twice as much as given here is extracted). Default=%(default)s')
    general.add_argument('-e', '--experiment', type=str, required=True,
                         help='Name of the experiment.')
    general.add_argument('-d', '--datarate', type=int, required=True,
                         help='Datarate in MB/s')
    general.add_argument('-o', '--outdir', default=os.getcwd(), type=str,
                         help='Output directory. Default is CWD=%(default)s.')
    general.add_argument('--mountdir', default='/tmp', type=str,
                         help='Base path of where to mount the files via vbs_fs. The '+
                         'script will create a directory with the experiment name '+
                         'under that directory. Default=%(default)s')
    return parser.parse_args()


def get_vdif_info(infiles):
    '''
    Takes a list (or single) of total file paths and returns a dictionary
    with the relevant info about all files.
    '''
    if not isinstance(infiles, list):
        infiles = list(infiles)
    types = np.dtype([('file', 'U100'),
                      ('t0', 'f8'),
                      ('f0', 'i8'),
                      ('frame_size', 'i8'),
                      ('file_size', 'i8'),
                      ('header_size', 'i4')])
    info = np.zeros(len(infiles), dtype=types)
    for i,infile in enumerate(infiles):
        cmd = f"vdif_print_headers -n1 {infile}"
        #print(f'Running {cmd}')
        try:
            output = subprocess.check_output(cmd, shell=True,
                                             universal_newlines=True).split('\n')[1]
            t0, frame0, thread, nchan, invalid, legacy, station, nbit, frame_size = output.split(',')
        except:
            raise ValueError('vdif_print_headers died on given file {0}'.format(infile))
        for c in ['y', 'd', 'h', 'm']:
            t0 = t0.replace(c, ':')
        t0 = t0.replace('s', '').strip()
        legacy = int(legacy.split('=')[1].strip())
        header_size = 16 if legacy == 1 else 32
        info[i] = (infile,
                   Time(t0, format='yday', scale='utc').mjd,
                   int(frame0.split('=')[1].strip()),
                   int(frame_size.split('=')[1].strip()),
                   int(os.path.getsize(infile)),
                   header_size)
    return info


def mount_files(experiment, telescope, mount_dir='/tmp/', checkpath=True):
    '''
    Given an experiment name, will use vbs_fs to mount all scans of
    that experiment into mount_dir. Returns a list of absolute file paths.
    '''
    mountpath = f'{mount_dir}/{experiment}'
    if not os.path.isdir(mountpath):
        os.mkdir(mountpath)
    if checkpath:
        if os.listdir(mountpath):
            prompt = input(f'{mountpath} is not empty, continue with what is there? (y/n):')
            go = True if prompt == 'y' else False
            if go:
                return [f'{mountpath}/{f}' for f in os.listdir(mountpath)]
            else:
                quit(0)
    # mounting all baseband data into mountpath
    mountpath = os.path.abspath(mountpath)
    cmd = f"vbs_fs -I '{experiment}_{telescope}*' {mountpath} -o allow_other -o nonempty"
    print(f'Mounting files via {cmd}')
    try:
        vbs_output = subprocess.check_output(cmd, shell=True)
    except:
        raise ValueError(f'Failed with {vbs_output}')
    return [f'{mountpath}/{f}' for f in os.listdir(mountpath)]


def extract_chunk(info, mjds, outdir, nsec=1, datarate=128):
    '''
    Given the mjds, will extract +- nsec of data around each mjd from the
    file that should contain that mjd. This is using dd which will put the data
    into outdir.
    '''
    datarate *= 1e6
    outdir = os.path.abspath(outdir)
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    mjds.sort()
    mjds_not_found = mjds.copy()
    info.sort(order='t0')
    nsec_org = nsec
    for entry in info:
        infile = entry['file']
        start = entry['t0']
        frame_size = entry['frame_size']
        header_size =  entry['header_size']
        frames_per_second = datarate/(frame_size - header_size)
        start = start + (entry['f0'] * 1./frames_per_second)/86400.
        assert entry['file_size'] % frame_size == 0
        frames_in_file = entry['file_size'] // frame_size
        secs_in_file = (entry['file_size'] - frames_in_file * header_size) / datarate
        stop = start + secs_in_file/86400.
        for mjd in mjds:
            if (mjd > start) and (mjd < stop):
                print(f'MJD {mjd} is at {(mjd-start)*86400:.3f} seconds into {infile}')
                mjds_not_found.remove(mjd)
                while (mjd - nsec/86400.) < start:
                    print(mjd - nsec/86400., start)
                    nsec -= 0.1
                    print(f'Shortening time range from beginning to {nsec}')
                while (mjd + nsec/86400.) > stop:
                    nsec -= 0.1
                    print(f'Shortening time range from end to {nsec}')
                if nsec <= 0:
                    raise ValueError(f'Chosen MJD {mjd} too close to the edge of the file.')
                frames_to_skip = int((mjd - start - nsec/86400.) * 86400. * frames_per_second)
                frames_to_extract = int(2 * nsec * frames_per_second)
                fname = infile.split('/')[-1]
                cmd = f'dd if={infile} of={outdir}/{fname}_{mjd:.8f}_plus-minus_{nsec:.1f}_seconds bs={frame_size} skip={frames_to_skip} count={frames_to_extract}'
                print(f'Running {cmd}')
                output = subprocess.check_output(cmd, shell=True)
                # bring nsec back to orignal value in case it was modified
                nsec = nsec_org
        # we don't need to search the mjds that we already found in the next outer loop again.
        mjds = mjds_not_found.copy()
    return mjds


def cleanup(mountdir):
    '''
    Unmounts all files in mountdir.
    '''
    mountdir = os.path.abspath(mountdir)
    cmd = f"fusermount -u {mountdir}"
    output = subprocess.check_output(cmd, shell=True)
    return


if __name__ == "__main__":
    args = options()
    file_list = mount_files(args.experiment, args.telescope, args.mountdir)
    info = get_vdif_info(file_list)
    missing = extract_chunk(info, args.mjds, outdir=args.outdir, nsec=args.nsec, datarate=args.datarate)
    cleanup(f'{args.mountdir}/{args.experiment}')
    if missing:
        print(f'\n Found no matching files for {missing}.\n')
