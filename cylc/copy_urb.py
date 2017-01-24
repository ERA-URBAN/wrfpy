#!/usr/bin/env python

import argparse
import datetime
import time
import utils
from wrfpy.config import config
import os
#from urb import urb

class copy_urb(config):
    ''''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    def __init__(self, datestring, interval):
        config.__init__(self)
        dt = utils.convert_cylc_time2(datestring)
        prevtime = dt - datetime.timedelta(hours=interval)
        wrfout_time = datetime.datetime.strftime(prevtime, '%Y-%m-%d_%H:%M:%S')
        max_dom = utils.get_max_dom()
        rundir = self.config['filesystem']['wrf_run_dir']
        for dom in range(1,max_dom+1):
            outfile = os.path.join(rundir, 'wrfout_d0' + str(dom) + '_' + wrfout_time)
            infile = os.path.join(rundir, 'wrfinput_d0' + str(dom))
            os.system('/home/haren/cylc-suites/forecast/bin/copy_urb_init.sh ' + outfile + ' ' + infile)        

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('interval', metavar='I', type=int,
                        help='interval between runs')
    # parse arguments
    args = parser.parse_args()
    # call main
    copy_urb(args.datestring, args.interval)    
