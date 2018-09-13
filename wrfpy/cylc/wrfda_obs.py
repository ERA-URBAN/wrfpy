#!/usr/bin/env python

import argparse
import datetime
import time
import shutil
from wrfpy.readObsTemperature import readObsTemperature
from wrfpy import utils

def main(datestring):
    dt = utils.convert_cylc_time(datestring)
    readObsTemperature(dt, dstationtypes=['davis', 'vp2', 'vantage'])


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring)
