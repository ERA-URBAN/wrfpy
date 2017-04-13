#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
import wrfpy.upp as upp
import os


def main(datestring, interval):
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wrf.__init()
    '''
    dt = utils.convert_cylc_time(datestring)
    postprocess = upp()
    # construct wrfout name for domain 1
    dt_str = dt.strftime('%Y-%m-%d_%H:%M:%S')
    wrfout_name = wrfout_d01_ + dt_str
    wrfout_file = os.path.join(self.config['filesystem']['wrf_run_dir'], wrfout_name)
    start_date = utils.return_validate(postprocess.config['options_general']['date_start'])
    if (start_date == dt):  # very first timestep
      postprocess.run_unipost_file(wrfout_files[0], use_t0=True)
    else:
      postprocess.run_unipost_file(wrfout_files[0], use_t0=False)


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
