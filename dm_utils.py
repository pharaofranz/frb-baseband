#!/usr/bin/env python3

from subprocess import PIPE, Popen, check_output
import sys

isPulsar = False

# Until I figure out how to send a message around that contains several arguments
# I hardcode the FRB DMs here and have a function for pulsars below
def get_dm(src):
    global isPulsar
    FRB_DMs = {	'BSGR': 332.7,
                'F19': 1202.0,
                'FRB180301': 517.0,
                'FRB190417': 1379.0,
                'FRB190520': 1202.0,
                'FRB190608': 338.7,
                'FRB210117': 730.0,
                'FRB210320': 384.8,
                'FRB210407': 1785.3,
                'FRB210807': 251.9,
                'FRB211127': 234.83,
                'FRB211212': 206.0,
                'FRB220105': 583.0,
                'FRB190714A': 504.1,
                'FRB20200120': 88.0,
                'FRB20180901A': 517.0,
                'FRB20180915A': 371,
                'FRB20181030E': 159,
                'FRB20181224E': 580.7,
                'FRB20181226B': 288,
                'FRB20190103C': 1349,
                'FRB20190111A': 173.1,
                'FRB20190118A': 225,
                'FRB20190122C': 690,
                'FRB20190124C': 302.5,
                'FRB20190202A': 306,
                'FRB20190518C': 444,
                'FRB20190915D': 488.7,
                'FRB20191013D': 523.6,
                'FRB20200223B': 202.3,
                'FRB20201114A': 323.2,
                'FRB20220912A': 220,
                'LS63': 241.0,
                'LSI61': 241.0,
                'LSI63': 241.0,
                'M81': 88.0,
                'M81R': 88.0,
                'NR1': 277.0,
                'NR2': 187.0,
                'NR3': 764.0,
                'NR4': 183.0,
                'NR5': 443.0,
                'NR6': 597.0,
                'NR7': 251.0,
                'R2': 190.0,
                'R3': 349.7,
                'R4': 103.0,
                'R5': 450.0,
                'R6': 363.5,
                'R7': 444.0,
                'R8': 1281.5,
                'R9': 309.6,
                'R10': 424.9,
                'R11': 460.2,
                'R12': 578.9,
                'R13': 552.7,
                'R14': 301.7,
                'R15': 195.8,
                'R16': 394.2,
                'R17': 223.7,
                'R18': 1379.0,
                'R19': 490.0,
                'R21': 714.0,
                'R24': 400.0,
                'R25': 222.0,
                'R34': 325.0,
                'R47': 365.0,
                'R48': 625.0,
                'R54': 220.0,
                'R65': 1705.0,
                'R67': 413.0,
                'R68': 415.0,
                'R70': 290.0,
                'R74': 510.0,
                'R180301': 517.0,
                'R190520': 1202.0,
                'R200120': 88.0,
                'R200616': 977.90,
                'R220912': 220,
                'SGR': 332.7,
                'SGR1935': 332.7,
    }
    try:
        return FRB_DMs[src]
    except KeyError:
        try:
            cmd = "psrcat -c 'dm' -o short -nohead -nonumber {0}".format(src)
            dm = check_output(cmd, shell=True)
            isPulsar = True
            return float(dm)
        except:
            return None
    except:
        return None


def get_src(fil_file):
    cmd = f'header {fil_file}'
    fil_header = check_output(cmd, shell=True).decode("utf-8").splitlines()
    for line in fil_header:
        if 'Source Name' in line:
            src = line.split(':')[1].strip()
            break
    return src


def get_nchan(fil_file):
    cmd = f'header {fil_file}'
    fil_header = check_output(cmd, shell=True).decode("utf-8").splitlines()
    for line in fil_header:
        if 'Number of channels' in line:
            nchan = line.split(':')[1].strip()
            break
    return int(nchan)
