#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy.wrf import run_wrf
from wrfpy import utils


def main(datestring, interval):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wrf.__init() and initialize()
    '''
    dt = utils.convert_cylc_time(datestring)
    WRF = run_wrf()
    WRF.initialize(dt, dt + datetime.timedelta(hours=interval))

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize WRF step.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('interval', metavar='I', type=int,
			help='Time interval in hours')
   # parse arguments
    args = parser.parse_args()
   # call main
    main(args.datestring, args.interval)   
