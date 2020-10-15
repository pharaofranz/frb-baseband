#!/usr/bin/env python3
import argparse
from astropy.time import Time
import os
import pandas as pd
from create_config import vex2dic, sched2df, fixStationName

def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('-i', '--vexfile', type=str, required=True,
                         help='REQUIRED. vexfile used for the experiment. If only the vexfile ' \
                         'is supplied will print a summary of the experiment. '\
                         'Running this the first time might take a while as a pandas dataframe is ' \
                         'created from the SCHED section of the vexfile. This dataframe will be '\
                         'written to disk (as pickle file) in the location of the vexfile. ' \
                         'It will be named <vexfile>.df.')
    general.add_argument('-s', '--source', type=str, default=None,
                         help='Source for which the available scans are to be displayed.')
    general.add_argument('-t', '--telescope', type=str, default=None,
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr', \
                                  'ir', 'ib', 'mc', 'nt', 'onsala85', 'onsala60', 'srt',\
                                  'wsrt', 'effelsberg', 'torun', 'irbene', 'irbene16',\
                                  'medicina', 'noto'],
                         help='Station name or 2-letter code of dish to be printed.')
    general.add_argument('-S', '--scans', nargs='+', default=None, type=int,
                         help='Optional list of scans to be looked at. By default will ' \
                         'return all scans. Scan numbers with or without leading zeros.')
    general.add_argument('--sources', action='store_true',
                         help='if set will print all sources observed by telescope (-t has to be set)')
    general.add_argument('--time_spent', action='store_true',
                         help='computes the time on source for each sources obseved by telescope.'\
                         '(-t and --sources need to be set)')
    return parser.parse_args()


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
    if not args.source == None:
        source = args.source.replace('_D','').upper()
    if not args.telescope == None:
        station = fixStationName(args.telescope).capitalize()
    scans = args.scans
    if args.source == args.telescope == args.scans == None:
        stations = list(df.station.unique())
        sources = list(df.source.unique())
        fmodes = list(df.fmode.unique())
        nscans = len(list(df.scanNo.unique()))
        print(f'Found the following stations: {stations}')
        print(f'Found the following sources: {sources}')
        print(f'Found the following frequency setups: {fmodes}')
        print(f'Found a total of {nscans} scans.')
        return
    elif args.source == args.telescope == None: # we print all requested scans
        df = df[(df.scanNo.isin(scans))]
        print(df)
        return
    elif args.source == args.scans == None:  # we print whatever Station station observed
        df = df[(df.station == station)]
        if args.sources:
            if args.time_spent:
                sources = list(df.source.unique())
                times = [df[(df.source == source)]['length_sec'].sum() -
                         df[(df.source == source)]['missing_sec'].sum() for source in sources]
                missing = [df[(df.source == source)]['missing_sec'].sum() for source in sources]
                for source, time, miss in zip(sources, times, missing):
                    print(f'{source}: {time} s = {time/60.:.2f} min = {time/60./60.:.2f} hrs')
                    print(f'Recording but off source: {miss/60./60.:.2f} hrs')
                return
            df = df.source.unique()
        print(df)
        return
    elif args.telescope == args.scans == None: # we print when and who observed Source source
        df = df[(df.source == source)]
        print(df)
        return
    elif args.source == None: # i.e we we have a list of scans for a certain station
        df = df[(df.station == station) & (df.scanNo.isin(scans))]
        print(df)
        return
    elif args.telescope == None: #i.e. we have ask if Source source was observed in Scans scans?
        df = df[(df.source == source) & (df.scanNo.isin(scans))]
        print(df)
        return
    elif args.scans == None: # i.e. ask Station station observed Source source in which scans?
        df = df[(df.source == source) & (df.station == station)]
        print(df)
        return
    else: # all are true
        df = df[(df.source == source) & (df.station == station) & (df.scanNo.isin(scans))]
        print(df)
        return


if __name__ == "__main__":
    args = options()
    main(args)
        
