#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from wrfpy.upp import upp
from wrfpy.config import config
import os

class run_upp(config):
  ''''
  '''
  def __init__(self, datestring):
    config.__init__(self)
    dt = utils.convert_cylc_time(datestring)
    postprocess = upp()
    # construct wrfout name for domain 1
    dt_str = dt.strftime('%Y-%m-%d_%H:%M:%S')
    wrfout_name = 'wrfout_d01_' + dt_str
    wrfout_file = os.path.join(self.config['filesystem']['wrf_run_dir'], wrfout_name)
    start_date = utils.return_validate(postprocess.config['options_general']['date_start'])
    upp_interval = postprocess.config['options_upp']['upp_interval']
    if (start_date == dt):  # very first timestep
      postprocess.run_unipost_file(wrfout_file, frequency=upp_interval, use_t0=True)
    else:
      postprocess.run_unipost_file(wrfout_file, frequency=upp_interval, use_t0=False)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize WRF step.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    run_upp(args.datestring)   
