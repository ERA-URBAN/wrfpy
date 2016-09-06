#!/usr/bin/env python

import argparse
import datetime
import time
import utils
from wrfda import wrfda

def updatebc_init(datestart):
    '''
    Initialize WPS timestep
    '''
    WRFDA = wrfda()  # initialize object
    WRFDA.prepare_updatebc(datestart)
    for domain in range(1, WRFDA.max_dom+1):
      WRFDA.updatebc_run(domain)  # run da_updatebc.exe
    WRFDA.prepare_wrfda()  # prepare for running da_wrfvar.exe
    for domain in range(1, WRFDA.max_dom+1):
      WRFDA.wrfvar_run(domain)  # run da_wrfvar.exe
    WRFDA.prepare_updatebc_type('lateral', datestart, 1)  # prepare for updating lateral bc
    WRFDA.updatebc_run(1)  # run da_updatebc.exe
    WRFDA.wrfda_post()  # copy files over to WRF run_dir

def main(datestring):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    dt = utils.convert_cylc_time2(datestring)
    updatebc_init(dt)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    main(args.datestring)    
