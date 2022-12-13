#!/usr/bin/env python3
from astropy.time import Time
import argparse
import astropy.units as u
import glob
import os


def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    general.add_argument('-p', '--path', type=str, default=os.getcwd(),
                         help='Path to png files. Default=CWD.')
    general.add_argument('-b', '--prefix', type=str, default='',
                         help='Optional prefix to png files. Default="".')
    general.add_argument('-m', '--mid', type=str, default='cand_tstart',
                         help='Optional character string in png file names. Default=%(default)s.')
    general.add_argument('-t', '--type', type=str, default='png',
                         choices=['png', 'jpg', 'eps', 'pdf'],
                         help='File types to glob on. Default=%(default)s')
    general.add_argument('-d', '--dish', type=str, default='ef',
                         choices=['o8', 'o6', 'sr', 'wb', 'ef', 'tr', \
                                  'ir', 'ib', 'mc', 'nt', 'ur', 'bd', 'sv', 'zc'],
                         help='2-letter station code. Default=%(default)s.')
    general.add_argument('-f', '--full', action='store_true',
                         help='If set will store all of scan, MJD, DM, and S/N. Otherwise just a string of MJDs.')
    general.add_argument('-o', '--outfile', type=str, default=f'{os.getcwd()}/fetch_imgs_parsed.txt',
                         help='Output file. Default=%(default)s.')

    return parser.parse_args()


#txtfile = '/home/pharao/tmp/pr249a_img_names.txt'
#parsed = '/home/pharao/tmp/pr249a_img_names_parsed.txt'
#txtfile = '/home/pharao/tmp/pr247a_img_names.txt'
#parsed = '/home/pharao/tmp/pr247a_img_names_parsed.txt'

def main(args):
    imgs = glob.glob(f'{args.path}/{args.prefix}*{args.mid}*.{args.type}')
    with open(args.outfile, 'w') as f:
        first = True
        for img in imgs:
            img = img.strip()
            if args.full:
                scan = img.split(f'{args.dish}_no0')[1].split('_')[0]
            tstart = float(img.split('tstart_')[1].split('_')[0])
            tcand = float(img.split('tcand_')[1].split('_')[0])
            dm = round(float(img.split('dm_')[1].split('_')[0]), 1)
            snr = round(float(img.split('snr_')[1].split('.png')[0]), 1)
            mjd = (Time(tstart, format="mjd", scale="utc") + tcand*u.s).mjd
            if args.full:
                f.write(f'{scan}: {mjd:.12f} {dm} {snr}\n')
            else:
                f.write(f'{mjd:.12f}') if first else f.write(f',{mjd:.12f}')
            first = False
        f.write('\n')
if __name__ == "__main__":
    args = options()
    main(args)
