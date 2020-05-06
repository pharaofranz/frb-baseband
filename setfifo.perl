#!/usr/bin/perl
# usage: name-of-open-fifo size-in-bytes
# http://unix.stackexchange.com/a/353761/119298
use strict;
use Fcntl;
my $fifo = shift @ARGV or die "usage: fifo size";
my $size = shift @ARGV or die "usage: fifo size";
open(FD, $fifo) or die "cannot open";
#printf "old size %d\n",fcntl(\*FD, Fcntl::F_GETPIPE_SZ, 0);
my $new = fcntl(\*FD, Fcntl::F_SETPIPE_SZ, int($size));
die "failed" if $new<$size;
#printf "new size %d\n",$new;
