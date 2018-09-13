#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from pynetcdf2littler.wrapper_littler import wrapper_littler
from dateutil.relativedelta import relativedelta
import os

def main(args):
    '''
    Example script to integrate pynetcdf2littler into CYLC
    '''
    dt = utils.convert_cylc_time(args.datestring)
    # startdate
    dt1 = datetime.datetime(dt.year, dt.month, 1)
    dt1s = dt1.strftime('%Y%m%d')  # convert to string
    dt2 = dt1 + relativedelta(months=1)
    dt2s = dt2.strftime('%Y%m%d')  # convert to string
    outputdir = os.path.join(args.outputdir, dt1s)
    wrapper_littler(args.filelist, args.namelist, outputdir,
                    args.outputfile, dt1s, dt2s)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('-f', '--filelist',
                        help='filelist containing netcdf files',
                        default='wrapper.filelist', required=False)
    parser.add_argument('-n', '--namelist', help='netcdf2littler namelist',
                        required=True)
    parser.add_argument('-d', '--outputdir', help='outputdir',
                        required=False, default=os.getcwd())
    parser.add_argument('-o', '--outputfile', help='name of outputfile',
                        required=False, default='pynetcdf2littler.output')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args)
