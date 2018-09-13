#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from wrfpy.config import config
from pynetcdf2littler.wrapper_littler import wrapper_littler
from dateutil.relativedelta import relativedelta
import os
import glob
import shutil


class copySynop(config):
    ''''
    Example script how to copy output files from e.g.
    prepare_synop.py or combine_synop.py if there are 
    different synop input files for e.g. different days/months
    '''
    def __init__(self, args):
        config.__init__(self)
        obsDir = self.config['filesystem']['obs_dir']
        obsFilename = self.config['filesystem']['obs_filename']
        outputFile = os.path.join(obsDir, obsFilename) 
        dt = utils.convert_cylc_time(args.datestring)
        # startdate
        dt1 = datetime.datetime(dt.year, dt.month, 1)
        dt1s = dt1.strftime('%Y%m%d')  # convert to string
        inputdir = os.path.join(args.inputdir, dt1s)
        inputFile = os.path.join(inputdir, args.inputfile)
        # remove existing file
        utils.silentremove(outputFile)
        # copy inputfile to location specified in config.json
        shutil.copyfile(inputFile, outputFile)  


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('-d', '--inputdir', help='inputdir',
                        required=False, default=os.getcwd())
    parser.add_argument('-i', '--inputfile', help='name of inputfile',
                        required=True)
    # parse arguments
    args = parser.parse_args()
    # call main
    copySynop(args)
