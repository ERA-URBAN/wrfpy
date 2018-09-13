#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from wrfpy.wrfda import wrfda

def obsproc_run(datestart):
    '''
    Initialize WPS timestep
    '''
    WRFDA = wrfda(datestart)  # initialize object
    WRFDA.obsproc_run()


def main(datestring):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    dt = utils.convert_cylc_time(datestring)
    obsproc_run(dt)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring)    
