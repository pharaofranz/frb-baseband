[![GitHub license](https://img.shields.io/github/license/pharaofranz/frb-baseband)](https://github.com/pharaofranz/frb-baseband/blob/master/LICENSE)

# frb-baseband

This is a collection of scripts to convert raw baseband data stored as VDIF on a local fluxbeff to filterbank
format.

Dependencies: [jive5ab](https://github.com/jive-vlbi/jive5ab), [SIGPROC](https://github.com/pharaofranz/sigproc)(slightly modified version), [psrcat](https://www.atnf.csiro.au/research/pulsar/psrcat/download.html), [PSRCHIVE](http://psrchive.sourceforge.net/download.shtml), [DSPSR](http://dspsr.sourceforge.net/download.shtml), [SFXC](https://github.com/aardk/sfxc)

The pipeline itself (base2fil.sh) requires a config file (see FRB.conf for an example). The config file can be created
automatically using create_config. This requires a vex file as used in regular VLBI observations.

Essentially, this script takes baseband data (i.e. raw voltages) stored on a Flexbuff in VDIF format and converts those data to channelised filterbank files. It can generate either Stokes I, full polarisation filterbanks or single polarisation data. Note that the script assumes circular polarisation as is common in VLBI recordings.

In case you have FETCH installed that is running with a rabbitmq-queue, then the filterbanks will we sent off to that queue. I.e., this script can be used as an end-to-end pipeline to search for millisecond-duration bright bursts such as giant pulses from pulsars or FRBs.

In case you observed a known pulsar then the data will be folded and a diagnostic plot will be generated.