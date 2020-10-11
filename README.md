[![GitHub license](https://img.shields.io/github/license/pharaofranz/frb-baseband)](https://github.com/pharaofranz/frb-baseband/blob/master/LICENSE)

# frb-baseband

This is a collection of scripts to convert raw baseband data stored as VDIF on a local fluxbeff to filterbank
format.

Dependencies: jive5ab, sigproc, DSPSR

The pipeline itself requires a config file (see FRB.conf for an example). The config file can be created
automatically using create_config.py. This requires a vex file as used in regular VLBI observations.