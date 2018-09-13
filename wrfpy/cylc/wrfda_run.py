#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from wrfpy.wrfda import wrfda
from wrfpy.bumpskin import *
from wrfpy.scale import wrfda_interpolate
from wrfpy.config import config
import shutil

class dataAssimilation(config):
    '''
    Data assimilation helper class
    '''
    def __init__(self, datestring):
        config.__init__(self)
        datestart = utils.convert_cylc_time(datestring)
        # initialize WRFDA object
        WRFDA = wrfda(datestart)
        WRFDA.prepare_updatebc(datestart)
        # update lower boundary conditions
        for domain in range(1, WRFDA.max_dom+1):
            WRFDA.updatebc_run(domain)  # run da_updatebc.exe
        # copy radar data into WRFDA workdir if available
        try:
            radarFile = self.config['filesystem']['radar_filepath']
            radarTarget = os.path.join(self.config['filesystem']['work_dir'],
                                    'wrfda', 'd01', 'ob.radar')
            shutil.copyfile(radarFile, radarTarget)
        except (KeyError, IOError):
            pass
        # prepare for running da_wrfvar.exe
        WRFDA.prepare_wrfda()
        # run da_wrfvar.exe
        WRFDA.wrfvar_run(1)
        # interpolate rural variables from wrfda
        wrfda_interpolate(itype='rural')
        try:
            urbanData = self.config['options_urbantemps']['urban_stations']
        except KeyError:
            pass
        if urbanData:
            bskin =  bumpskin(urbanData, dstationtypes=['davis', 'vp2', 'vantage'])
        # update URBPARM.TBL with anthropogenic heat factors
        try:
            urbparmFile = self.config['options_wrf']['urbparm.tbl']
        except KeyError:
            pass
        if urbparmFile:
            urbparm(datestart, urbparmFile)
        # update lateral boundary conditions
        WRFDA.prepare_updatebc_type('lateral', datestart, 1)
        WRFDA.updatebc_run(1)
        # copy files over to WRF run_dir
        WRFDA.wrfda_post(datestart)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call dataAssimilation class
    dataAssimilation(args.datestring)
