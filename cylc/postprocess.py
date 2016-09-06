#!/usr/bin/env python

import argparse
import datetime
import time
import utils
from config import config
import os
import errno
#from urb import urb

class postprocess(config):
    ''''
    Main function to initialize WPS timestep:
      - converts cylc timestring to datetime object
      - calls wps_init()
    '''
    def __init__(self, datestring):
        config.__init__(self)
        dt = utils.convert_cylc_time2(datestring)
        wrfout_time = datetime.datetime.strftime(dt, '%Y-%m-%d_%H:%M:%S')
        max_dom = utils.get_max_dom()
        rundir = self.config['filesystem']['wrf_run_dir']
        archivedir = self.config['filesystem']['archive_dir']
        for dom in range(1,max_dom+1):
            wrfout = os.path.join(rundir, 'wrfout_d0' + str(dom) + '_' + wrfout_time)
            archived = os.path.join(archivedir, 'wrfout_d0' + str(dom) + '_' + wrfout_time)
            os.system('nc3tonc4 ' + wrfout + ' ' + archived)
            plot_archive = os.path.join(archivedir, 'plot', wrfout_time)
	    utils._create_directory(plot_archive)
            #utils._create_directory(os.path.join(plot_archive, trim))
	    os.system('ncl /home/haren/cylc-suites/forecast/bin/wrf_Surface3.ncl inputfile=' + r'\"' + archived + r'\" outputfile=\"' + plot_archive + r'/surface_d0' + str(dom) + '.png' + r'\"')
	    #iname = 'surface_d0' + str(dom) + '.png')
            #os.system('convert ' + os.path.join(plot_archive, iname) + ' -fuzz 1% -trim +repage ' + os.path.join(plot_archive, 'trim', iname))
        plot_latest = os.path.join(archivedir, 'plot', 'latest')
        try:
	    os.symlink(plot_archive, plot_latest)
        except OSError, e:
            if e.errno == errno.EEXIST:
                 os.remove(plot_latest)
                 os.symlink(plot_archive, plot_latest)
  
if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Initialize obsproc.')
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    # parse arguments
    args = parser.parse_args()
    # call main
    postprocess(args.datestring)    
