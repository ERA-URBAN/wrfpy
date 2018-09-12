#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy.wrf import run_wrf
from wrfpy import utils


def main():
    '''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wrf.__init() and initialize()
    '''
    WRF = run_wrf()
    WRF.run_wrf()

if __name__=="__main__":
    main()
