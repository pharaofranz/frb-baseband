#!/usr/bin/env python3
import argparse
import subprocess
import os, stat
import string
import random


def options():
    parser = argparse.ArgumentParser()
    general = parser.add_argument_group('General info about the data.')
    digifil = parser.add_argument_group('Input to digifil.')
    prepdata = parser.add_argument_group('Input to prepdata/prepsubband')
    general.add_argument('psrname', type=str,
                         help='The B- or J-name of the target. If not a known pulsar must ' +
                         'also supply ra and dec.')
    general.add_argument('filename', type=str,
                         help='name of the raw vdif file')
    general.add_argument('-f', '--freq', type=float, default=1608.0,
                         help='CENTRAL frequency in MHz of the data. ' +
                        'Default=%(default)s MHz')
    general.add_argument('--ra', type=str, default=None,
                         help='RA of source -- required if psrname is not a known pulsar. '+
                         'Format: hh:mm:ss.ss.')
    general.add_argument('--dec', type=str, default=None,
                         help='Dec of source -- required if psrname is not a known pulsar. '+
                         'Format: dd:mm:ss.ss.')
    general.add_argument('-b', '--bw', type=float, default=16.0,
                         help='Bandwidth of the scan. Default=%(default)s MHz')
    general.add_argument('-u', '--usb', action='store_true',
                         help='If set assumes upper side band.' +
                         'Either -u or -l MUST be set. NO defaults.')
    general.add_argument('-l', '--lsb', action='store_true',
                         help='If set assumes lower side band.' +
                         'Either -u or -l MUST be set. NO defaults.')
    general.add_argument('-t', '--telescope', type=str, default='ONSALA85',
                         help='Telescope used. Must match one known to ' +
                         ' tempo/tempo2. Default=%(default)s')
    general.add_argument('--use_tmp', action='store_true',
                         help='If set will put all intermediate files in /tmp')
    general.add_argument('--hdr_only', action='store_true',
                         help='If set will create only the hdr files needed for dsprs/digifil.')
    digifil.add_argument('--fil_out_dir', type=str, default=None,
                         help='sets the directory where filterbank files will be written to. '+
                         'Default=/same/dir/as/input/vdif_file')
    digifil.add_argument('--nchan', type=int, default=512,
                         help='Number of channels per subband. ' +
                         'Default=%(default)s.')
    digifil.add_argument('--nsec', type=float, default=120,
                         help='Numer of seconds to process. ' +
                         'Default=%(default)s.')
    digifil.add_argument('--start', type=float, default=1,
                         help='Process as of so many seconds into the file.' +
                         'Default=%(default)s.')
    digifil.add_argument('--force', action='store_true',
                         help='If set will delete a pre-existing filterband file '+
                         'of the same name.')
    digifil.add_argument('--pol', type=int, default=2, choices=[0, 1, 2, 3, 4],
                         help='Determines which "channel" of the vdif file to process. '+
                         'Currently dspsr understands only 2-channel VDIF, where each chan '+
                         'is thought to be a polaristaion. If set to 2 will process both '+
                         'creating stokes I. If set to 3 get (PP+QQ)^2, if 4 get full '+
                         'polarisation, i.e. PP,QQ,PQ,QP. '
                         'Default=%(default)s.', )
    digifil.add_argument('--twobit', action='store_true',
                         help='If set will spit out 2bit filterbank instead of 8bit.')
    digifil.add_argument('--tscrunch', type=int, default=1,
                         help='Donwsampling factor, digifils -t parameter. '+
                         'Default=%(default)s.')
    digifil.add_argument('--nthreads', type=int, default=1,
                         help='Number of threads to use per instance of digifil. '+
                         'Default=%(default)s.')
    prepdata.add_argument('--do_prepdata', action='store_true',
                          help='If set will run prepdata or prepsubband on filterbank files')
    prepdata.add_argument('--ncpus', type=int, default=1,
                          help='Number of cpus to use. Only affects whether ' +
                          'prepdata (ncpus=1) or prepsubband (ncpus>1) is used.'+
                          'Default=%(default)s.')
    prepdata.add_argument('--dm', type=float, default=None,
                          help='Dispersion measure to use. Default is that which psrcat provides.')
    prepdata.add_argument('--nozerodm', action='store_false',
                          help='if set will not add -zerodm to prepdata/prepsubband commands.')
    prepdata.add_argument('--clip', type=int, default=5,
                          help='S/N above which to clip data in prepdata/prepsubband.'+
                          'Set to 0 to do no clipping.'+
                          'Default=%(default)s.')
    prepdata.add_argument('--dm2', type=float, default=0.0,
                          help='If set will run prepsubband instead of prepdata and go through '+
                          'a the range of DMs defined by dm and dm2 in steps of dmstep.'+
                          'Default is to do no range but one DM only.')
    prepdata.add_argument('--dmstep', type=float, default=1.0,
                          help='The stepsize in the DM search if both dm and dm2 are set.'+
                          'Default=%(default)s.')
    return parser.parse_args()


def psr_info(psr):
    cmd = "psrcat -c 'raj decj dm' -o short -nohead -nonumber {0}".format(psr)
    try:
        ra, dec, dm = subprocess.check_output(cmd, shell=True).split()
    except:
        raise RunError('psrcat died on given source {0}'.format(psr))
    return ra.decode(), dec.decode(), float(dm)


def id_generator(size=20, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

def make_hdr(psr, freq, filename, pol=2, usb=True, ra=None, dec=None,
             bw=16.0, telescope='ONSALA85', tmp=False):
    if not usb:
        bw *= -1
    pre = '/tmp/' if tmp else os.path.dirname(filename)  # os.getcwd()
    if ra is None or dec is None:
        ra, dec, dm = psr_info(psr)
    template = 'HDR_VERSION 0.1\n' +\
               'TELESCOPE  {0}\n'  +\
               'SOURCE     {1}\n'  +\
               'RA         {2}\n'  +\
               'DEC        {3}\n'  +\
               'FREQ       {4}\n'  +\
               'BW         {5}\n'  +\
               'DATAFILE   {6}\n'  +\
               'INSTRUMENT VDIF\n' +\
               'MODE       PSR\n' +\
               'BASIS      Circular\n' +\
               ''
    hdrfile = '{0}/{1}_pol{2}.hdr'.format(pre, os.path.basename(filename), pol)
    with open(hdrfile, 'w') as f:
        f.write(template.format(telescope, psr, ra, dec,
                                freq, bw, filename))
    return hdrfile


def run_digifil(hdr, fil_out_dir=None, start=1, nsecs=120, nchan=128, overwrite=False, pol=2, twobit=False, tscrunch=1, nthreads=1, dm=0.0, coherent=False):
    filterbankfile = hdr.replace('.hdr', '.fil')
    if fil_out_dir is not None:
        filterbankfile = '{0}/{1}'.format(fil_out_dir, os.path.basename(filterbankfile))
    if os.path.exists(filterbankfile):
        if overwrite:
            if not stat.S_ISFIFO(os.stat(filterbankfile).st_mode):
                os.remove(filterbankfile)
        else:
            raise InputError('Filterbankfile {0} exists already. '.format(filterbankfile) +
                             'Delete first or set --force to overwrite')
    nbit = 2 if twobit else 8
    if tscrunch > 1:
        cmd = 'digifil -cont -c -b{4} -S{0} -T{1} -2 -D 0.0 -t {6} -o {2} {3} -threads {5}'.format(
            start, nsecs, filterbankfile, hdr, nbit, nthreads, tscrunch)
    else:
        cmd = 'digifil -cont -c -b{4} -S{0} -T{1} -2 -D 0.0 -o {2} {3} -threads {5}'.format(
            start, nsecs, filterbankfile, hdr, nbit, nthreads)
    leakage_factor = 512 if nchan <= 128 else 2*nchan
    if pol < 2:
        cmd = '{0} -P{1} -F{2}:{3}'.format(cmd, pol, nchan, leakage_factor)
    else:
        if pol == 2:
            # get Stokes I, i.e. PP+QQ
            cmd = '{0} -d1 -F{1}:{2}'.format(cmd, nchan, leakage_factor)
        elif pol == 4:
            # full pol, PP,QQ,PQ,QP
            cmd = '{0} -d4 -F{1}:{2}'.format(cmd, nchan, leakage_factor)
        elif pol == 3:
            # (PP+QQ)^2
            cmd = '{0} -d3 -F{1}:{2}'.format(cmd, nchan, leakage_factor)
        else:
            raise InputError(f'pol = {pol} not implemented. Choices are 0, 1, 2, 3, 4')
    if dm > 0.0:
        cmd = '{0} -D {1}'.format(cmd, dm)
        if coherent:
            cmd = '{0} -F{1}:D'.format(cmd, nchan)
    print('running {0}'.format(cmd))
    try:
        id = id_generator()
        errfile_nme = '/tmp/digifil.{0}'.format(id)
        errfile = open(errfile_nme, 'w')
        id = id_generator()
        outfile_nme = '/tmp/digifil.{0}'.format(id)
        outfile = open(outfile_nme, 'w')
        subprocess.check_call(cmd, shell=True, stdout=outfile,
                              stderr=errfile)
    except subprocess.CalledProcessError:
        with open(outfile, 'r') as f:
            stdout = f.readlines()
        with open(errfile, 'r') as f:
            stderr = f.readlines()
        raise RunError(f'Digifil died. \n stdout reports \n {stdout} \n stderr reports \n {stderr}')
    return filterbankfile


def prepdata(filterbankfile, dm1, zerodm=True, clip=5,
             dm2=0, dmstep=1.0, ncpus=1):
    '''
    Runs either prepdata or prepsubband depending on whether more than
    one CPU are specified of if a dm-range is given.
    '''
    if dm2 > 0.0:
        if dm2 < dm1:
            raise InputError('DM2 must be larger than DM1.')
        numdms = int((dm2-dm1) // dmstep + 1)
        cmd = 'prepsubband -lodm {0} -numdms {1} -dmstep {2}'.format(dm1, numdms, dmstep)
        outfile = filterbankfile.replace('.fil', '')
    else:
        cmd = 'prepdata -dm {0}'.format(dm1)
        outfile = filterbankfile.replace('.fil', '_dm{0}'.format(dm1))

    cmd = '{0} -filterbank -noweights -noscales -nobary -ncpus {1}'.format(cmd, ncpus)
    if zerodm:
        cmd = '{0} -zerodm '.format(cmd)
    if clip > 0:
        cmd = '{0} -clip {1} '.format(cmd, clip)
    cmd = '{0} -o {1} {2}'.format(cmd, outfile, filterbankfile)
    print('running {0}'.format(cmd))
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
        raise RunError('Prepdata died.')
    return

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
    if not args.usb and not args.lsb:
        raise InputError('You MUST supply either -l OR -u ' +
                         'to specify if data are LSB or USB')
    if args.usb and args.lsb:
        raise InputError('You MUST supply either -l OR -u ' +
                         'not both.')
    usb = True if args.usb else False
    hdr = make_hdr(args.psrname, args.freq, args.filename, usb=usb,
                   bw=args.bw, telescope=args.telescope, tmp=args.use_tmp,
                   ra=args.ra, dec=args.dec, pol=args.pol)
    if args.hdr_only:
        print("Not creating filterbanks. Hdr files done.")
        quit(0)
    filterbankfile = run_digifil(hdr, args.fil_out_dir, args.start, args.nsec, args.nchan,
                                 overwrite=args.force, pol=args.pol,
                                 twobit=args.twobit, tscrunch=args.tscrunch,
                                 nthreads=args.nthreads)
    if args.do_prepdata:
        if args.dm is not None:
            dm1 = args.dm
        else:
            dm1 = psr_info(args.psrname)[2]
        prepdata(filterbankfile, dm1, zerodm=args.nozerodm, clip=args.clip,
                 dm2=args.dm2, dmstep=args.dmstep, ncpus=args.ncpus)
