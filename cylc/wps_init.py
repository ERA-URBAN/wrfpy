#!/usr/bin/env python

import argparse
import datetime
import time
from wps import wps
import utils


def wps_init(datestart, dateend, boundarydir):
    '''
    Initialize WPS timestep
    '''
    WPS = wps(datestart, dateend, boundarydir)  # initialize object
    WPS._initialize()


def main(datestring, interval, boundarydir):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    dt = utils.convert_cylc_time2(datestring)
    wps_init(dt, dt + datetime.timedelta(hours=interval), boundarydir)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize WPS step.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('interval', metavar='I', type=int,
			help='Time interval in hours')
    parser.add_argument('directory', metavar='D', type=str,
                        help='Directory containing boundary files')

    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring, args.interval, args.directory)    
