#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from pynetcdf2littler.wrapper_littler import wrapper_littler
from dateutil.relativedelta import relativedelta
import os
import glob
import fileinput

def main(args):
    '''
    Example script to combine different output files
    from the prepare_synop.py script
    '''
    dt = utils.convert_cylc_time(args.datestring)
    # startdate
    dt1 = datetime.datetime(dt.year, dt.month, 1)
    dt1s = dt1.strftime('%Y%m%d')  # convert to string
    outputdir = os.path.join(args.outputdir, dt1s)
    filenames = glob.glob(os.path.join(outputdir, '*'))
    outputfile = args.outputfile
    if filenames:
        with open(os.path.join
                  (outputdir, outputfile), 'w') as fout:
            for line in fileinput.input(filenames):
                fout.write(line)
    else:
        with open(outputfile, 'a'):
            os.utime(outputfile, None)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('-d', '--outputdir', help='outputdir',
                        required=False, default=os.getcwd())
    parser.add_argument('-o', '--outputfile', help='name of outputfile',
                        required=True)
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args)
