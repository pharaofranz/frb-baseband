#!/usr/bin/env python3
import argparse
from astropy.time import Time
import os
import pandas as pd
from create_config import vex2dic, getExperimentName, sched2df

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
        df = sched2df(vex, add2db=True)
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
        df = pd.concat([df, sched2df(vex, add2db=True)])
        df.to_pickle(df_file)
    return


if __name__ == "__main__":
    args = options()
    main(args)
