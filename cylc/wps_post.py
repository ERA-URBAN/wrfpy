#!/usr/bin/env python

import argparse
import datetime
import time
from wrfpy import utils
from wrfpy.config import config
import os
#from urb import urb
import shutil
import glob

class wps_post(config):
    ''''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    def __init__(self):
        config.__init__(self)
        rundir = self.config['filesystem']['wrf_run_dir']
        wpsdir = os.path.join(self.config['filesystem']['work_dir'], 'wps')
        ## wrf run dir
        # cleanup old met_em files
        # create list of files to remove
        #files = [glob.glob(os.path.join(rundir, ext))
        #         for ext in ['met_em*']]
        # flatten list
        #files_flat = [item for sublist in files for item in sublist] 
        # remove files silently
        #[ utils.silentremove(filename) for filename in files_flat ]
        # copy new met_em files
        # create list of files to copy
        files = [glob.glob(os.path.join(wpsdir, ext))
                 for ext in ['met_em*']]
        # flatten list
        files_flat = [item for sublist in files for item in sublist]
        [ shutil.copyfile(filename, os.path.join(rundir, os.path.basename(filename))) for filename in files_flat ]
        ## wps workdir
        # create list of files to remove
        files = [glob.glob(os.path.join(wpsdir, ext))
                 for ext in ['met_em*', 'FILE*', 'PFILE*', 'GRIBFILE*']]
        # flatten list
        files_flat = [item for sublist in files for item in sublist]
        # remove files silently
        [ utils.silentremove(filename) for filename in files_flat ]

if __name__=="__main__":
    wps_post() 
