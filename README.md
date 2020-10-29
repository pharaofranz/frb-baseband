[![GitHub license](https://img.shields.io/github/license/pharaofranz/frb-baseband)](https://github.com/pharaofranz/frb-baseband/blob/master/LICENSE)

# frb-baseband

This is a collection of scripts to convert raw baseband data stored as VDIF on a local fluxbeff to filterbank
format.

Dependencies: [jive5ab](https://github.com/jive-vlbi/jive5ab), [SIGPROC](https://github.com/pharaofranz/sigproc)(slightly modified version), [psrcat](https://www.atnf.csiro.au/research/pulsar/psrcat/download.html), [PSRCHIVE](http://psrchive.sourceforge.net/download.shtml), [DSPSR](http://dspsr.sourceforge.net/download.shtml), [SFXC](https://github.com/aardk/sfxc)

The pipeline itself requires a config file (see FRB.conf for an example). The config file can be created
automatically using create_config. This requires a vex file as used in regular VLBI observations.