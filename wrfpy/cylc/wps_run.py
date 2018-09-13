#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy.wps import wps
from wrfpy import utils
from dateutil.relativedelta import relativedelta

def wps_run():
    '''
    Initialize WPS timestep
    '''
    WPS = wps()  # initialize object
    WPS._run_geogrid()
    WPS._run_ungrib()
    WPS._run_metgrid()


def main():
    '''
    Main function to run wps
    '''
    wps_run()


if __name__=="__main__":
    wps_run()
