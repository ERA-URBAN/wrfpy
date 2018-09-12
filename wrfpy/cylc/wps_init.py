#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy.wps import wps
from wrfpy import utils


def wps_init(datestart, dateend):
    '''
    Initialize WPS timestep
    '''
    WPS = wps()  # initialize object
    WPS._initialize(datestart, dateend)


def main(datestring, interval):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    dt = utils.convert_cylc_time(datestring)
    wps_init(dt, dt + datetime.timedelta(hours=interval))


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize WPS step.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('interval', metavar='I', type=int,
			help='Time interval in hours')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring, args.interval)    
