#!/usr/bin/env python3

import argparse
from astropy.time import Time
from extract_baseband_chunk import get_vdif_info, mount_files, cleanup


def options():
    parser = argparse.ArgumentParser(
        description='Given a (list of) MJD, this script will figure out how '+
        'many seconds into a certain VDIF scan this MJD appears. It assumes'+
        'you have a VBS file system and requires vdif_print_header from SFXC.')
    general = parser.add_argument_group()
    general.add_argument('-m', '--mjds', nargs='+', type=float, required=True,
                         help='List of MJDs for which we want to know the scan '+
                         'and number of seconds since start of that scan')
    general.add_argument('-t', '--telescope', type=str, required=True,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr',
                                  'ir', 'ib', 'mc', 'nt', 'ur', 'bd', 'sv'],
                         help='REQUIRED. Station name or 2-letter code of dish to be worked on.')
    general.add_argument('-e', '--experiment', type=str, required=True,
                         help='Name of the experiment.')
    general.add_argument('-d', '--datarate', type=int, required=True,
                         help='Datarate in MB/s')
    general.add_argument('--mountdir', default='/tmp', type=str,
                         help='Base path of where to mount the files via vbs_fs. The '+
                         'script will create a directory with the experiment name '+
                         'under that directory. Default=%(default)s')
    return parser.parse_args()


def get_secs(info, mjds, datarate=128):
    '''
    Given the mjds, will print how many seconds after the start time of a
    particular VDIF file this corresponds to. Will also print the yday-format
    of that particular MJD.
    '''
    datarate *= 1e6
    mjds.sort()
    mjds_not_found = mjds.copy()
    info.sort(order='t0')
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
                print(f"{mjd} is {Time(mjd, format='mjd', scale='utc').yday} in yday.\n")
                mjds_not_found.remove(mjd)
        # we don't need to search the mjds that we already found in the next outer loop again.
        mjds = mjds_not_found.copy()
    return mjds


if __name__ == "__main__":
    args = options()
    file_list = mount_files(args.experiment, args.telescope, args.mountdir)
    info = get_vdif_info(file_list)
    missing = get_secs(info, args.mjds, datarate=args.datarate)
    cleanup(f'{args.mountdir}/{args.experiment}')
    if missing:
        print(f'\n Found no matching files for {missing}.\n')
