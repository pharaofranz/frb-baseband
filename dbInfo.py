#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np


def options():
    parser = argparse.ArgumentParser(
        description='''
        given a pickle file as created with addVex2db.py we query that pandas
        data frame for either of:\n
        a) total time spent with a particular dish (i.e. on any source)
        b) total time spent with a particular dish on a specific source
        c) total time spent on a particular source with overlap between dishes
        d) total time spent on a particular source without overlap between dishes
        e) all of the above but for a certain experiment or several experiments
        f) overlap between a list of stations''')
    general = parser.add_argument_group()
    general.add_argument('-i', '--dbfile', type=str,
                         help='Pickle (pandas dataframe) file that contains all the info.')
    general.add_argument('-s', '--source', type=str, default=None,
                         help='Source for which the available scans are to be displayed.')
    general.add_argument('-t', '--telescopes', default=None, nargs='+', type=str,
                         help='Station name or 2-letter code of dish(es) to be checked.')
    general.add_argument('-e', '--experiments', default=None, nargs='+', type=str,
                         help='Name(s) of experiment(s) to check.')
    general.add_argument('-v', '--verbose', action='store_true',
                         help='if set will print a bit more info, including the names of experiments that had data.')
    general.add_argument('--mjd_min', default=None, type=float,
                         help='Only entries after mjd_min will be considered. Can be combined with mjd_max.')
    general.add_argument('--mjd_max', default=None, type=float,
                         help='Only entries before mjd_max will be considered. Can be combined with mjd_min.')
    general.add_argument('--freq_min', default=None, type=float,
                         help='Only entries above freq_min MHz will be considered. Can be combined with freq_max.')
    general.add_argument('--freq_max', default=None, type=float,
                         help='Only entries below freq_max MHz will be considered. Can be combined with freq_min.')
    return parser.parse_args()


choices = ['o8', 'o6', 'sr', 'wb', 'ef', 'tr',
           'ir', 'ib', 'mc', 'nt', 'onsala85', 'onsala60', 'srt',
           'wsrt', 'effelsberg', 'torun', 'irbene', 'irbene16',
           'medicina', 'noto'],


# function which can take overlap into account between scans
# taken from Mark Snelders
def merge(times):
    """ Function which reduces the overlap between a list of tuples
    Example [(1, 3), (2, 4), (7, 8)] ---> [(1, 4), (7, 8)]
    Use: unique_times = list(merge(times)) """
    saved = list(times[0])
    for st, en in sorted([sorted(t) for t in times]):
        if st <= saved[1]:
            saved[1] = max(saved[1], en)
        else:
            yield tuple(saved)
            saved[0] = st
            saved[1] = en
    yield tuple(saved)


def main(args):
    df = pd.read_pickle(args.dbfile)
    stations = args.telescopes
    source = args.source
    exps = args.experiments
    mjd_min = args.mjd_min
    mjd_max = args.mjd_max
    freq_min = args.freq_min
    freq_max = args.freq_max

    revert_stations_to_none = True
    if stations is not None:
        revert_stations_to_none = False
        df = df[(df.station.isin(stations))]
        if df.empty:
            print(f'No data for stations {stations}.')
            quit(1)
    if source is not None:
        df = df[(df.source == source)]
        if df.empty:
            print(f'No data for source {source}.')
            quit(1)
            #return df.length_sec.sum() - df.missing_sec.sum()
    if mjd_min is not None:
        df = df[(df.t_startMJD >= mjd_min)]
        if df.empty:
            print(f'No data after {mjd_min}.')
            quit(1)
    if mjd_max is not None:
        df = df[(df.t_startMJD <= mjd_max)]
        if df.empty:
            print(f'No data before {mjd_max}.')
            quit(1)
    if freq_max is not None:
        df = df[(df.RefFreq_MHz <= freq_max)]
        if df.empty:
            print(f'No data below {freq_max} MHz.')
            quit(1)
    if freq_min is not None:
        df = df[(df.RefFreq_MHz >= freq_min)]
        if df.empty:
            print(f'No data above {freq_min} MHz.')
            quit(1)
    totalT = 0
    T_onSource = 0
    T_onSource_noOverlap = 0
    exp_list = []

    # we go through all experiments and scans, using the range between
    # the lowest t_startMJD and the largest t_startMJD+length_sec(t_startMJD);
    # we disgard any scans that are followed by a gap lasting longer than two hours
    # since we assume those were just dummy scans
    # TODO: what if there are several parts that are all more than two hours apart?
    if exps is None:
        # case e)
        exps = df.experiment.unique()
    for exp in exps:
        ddf = df[(df.experiment == exp)].sort_values(by='t_startMJD')
        if ddf.empty:
            print(f'No data for experiment {exp}, skipping.')
            continue
        if stations is None:
            stations = ddf.station.unique()
            revert_stations_to_none = True
        ddf = ddf[(ddf.station.isin(stations))]
        if ddf.empty:
            print(f'Station(s) {stations} not in experiment {exp}. Skipping.')
            continue
        starts = np.array(ddf.t_startMJD)
        if len(starts) <= 2:
            print(f'Only {len(starts)} scans in experiment {exp}. Assuming these are dummy scans and skipping.')
            if revert_stations_to_none is True:
                stations = None
            continue
        # we compute the time diff between start times and disgard those
        # that are followed by a gap lasting more than 2 hours
        exp_list.append(exp)
        mask = np.diff(starts, append=starts[-1])*24. < 2.
        start_mjds = np.array(starts[mask])
        end_mjds = np.array(start_mjds + ddf.length_sec[mask] / 86400)
        totalT += (end_mjds[-1]-start_mjds[0])
        T_onSource += ddf.length_sec[mask].sum() - ddf.missing_sec[mask].sum()
        # now taking overlap out
        times = [(x, y) for x, y in zip(start_mjds, end_mjds)]
        times_red = list(merge(times))
        for i in range(len(times_red)):
            s, e = times_red[i][0], times_red[i][1]
            T_onSource_noOverlap += (e-s)

        if revert_stations_to_none is True:
            stations = None
    if args.verbose:
        print(f'Found data in experiments {exp_list}')
    print(f'I get {totalT * 24:.2f}hrs of telescope time')
    print(f'I get {T_onSource / 3600:.2f}hrs on source in total.')
    print(f'I get {T_onSource_noOverlap * 24:.2f}hrs on source taking overlap out.')


if __name__ == "__main__":
    args = options()
    main(args)
