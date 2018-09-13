#!/usr/bin/env python

'''
description:    WRF part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

from wrfpy.config import config
from wrfpy import utils
import f90nml
import os
import shutil
import argparse
import collections
import subprocess
import time

class retry_wrf(config):
  '''
  change namelist timestep in rundir
  '''
  def __init__(self):
    config.__init__(self)  # load config
    self.wrf_run_dir = self.config['filesystem']['wrf_run_dir']
    self._cli_parser()
    self.define_retry_values()
    self.load_nml()
    self.change_namelist()
    self.write_namelist()
    self.run_wrf()

  def _cli_parser(self):
    '''
    parse command line arguments
    '''
    parser = argparse.ArgumentParser(
      description='WRF retry script',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('datestring', metavar='N', type=str,
                        help='Date-time string from cylc suite')
    parser.add_argument('retrynumber', metavar='M', type=int,
                        help='cylc retry number')
    args = parser.parse_args()
    self.retry_number = args.retrynumber
    self.dt = utils.convert_cylc_time(args.datestring)

  def load_nml(self):
    '''
    load namelist in wrf rundir
    '''
    self.wrf_nml = f90nml.read(os.path.join(self.wrf_run_dir,
                                            'namelist.input'))

  def define_retry_values(self):
    '''
    define retry values
    '''
    # empty nested dictionary
    self.retry_values = collections.defaultdict(dict)
    # define retry steps
    self.retry_values[1]['time_step'] = 10
    self.retry_values[1]['parent_time_step_ratio'] = [1, 5, 5]
    self.retry_values[2]['time_step'] = 8
    self.retry_values[2]['parent_time_step_ratio'] = [1, 5, 5]
    self.retry_values[3]['time_step'] = 12
    self.retry_values[3]['parent_time_step_ratio'] = [1, 6, 6]
    self.retry_values[4]['time_step'] = 6
    self.retry_values[4]['parent_time_step_ratio'] = [1, 5, 5]


  def change_namelist(self):
    if self.retry_number in [1,2,3,4]:
      self.wrf_nml['domains']['parent_time_step_ratio'
        ] = self.retry_values[self.retry_number]['parent_time_step_ratio']
      self.wrf_nml['domains']['time_step'
        ] = self.retry_values[self.retry_number]['time_step']
    elif self.retry_number > 4:
      print('falling back to no data assimilation')
      for dom in [1, 2, 3]:
        # construct wrfout name for domain 1
        dt_str = self.dt.strftime('%Y-%m-%d_%H:%M:%S')
        wrfvar_input = 'wrfvar_input_d0' + str(dom) + '_' + dt_str
        # remove wrfinput file with data assimilation
        os.remove(os.path.join(self.wrf_run_dir, 'wrfinput_d0' + str(dom)))
        # copy wrfinput file without data assimilation as fallback
        shutil.copyfile(os.path.join(self.wrf_run_dir, wrfvar_input),
                        os.path.join(self.wrf_run_dir, 'wrfinput_d0' + str(dom)))

  def write_namelist(self):
    '''
    write changed namelist to disk
    '''
    # remove backup file if exists
    try:
      os.remove(os.path.join(self.wrf_run_dir, 'namelist.input.bak'))
    except OSError:
      pass
    # copy file to backup file
    shutil.copyfile(os.path.join(self.wrf_run_dir, 'namelist.input'),
                    os.path.join(self.wrf_run_dir, 'namelist.input.bak'))
    # remove original namelist
    os.remove(os.path.join(self.wrf_run_dir, 'namelist.input'))
    # write new namelist
    self.wrf_nml.write(os.path.join(self.wrf_run_dir,
                                    'namelist.input'))

  def run_wrf(self):
    '''
    run wrf
    '''
    j_id = None
    if len(self.config['options_slurm']['slurm_wrf.exe']):
      # run using slurm
      if j_id:
        mid = "--dependency=afterok:%d" %j_id
        wrf_command = ['sbatch', mid, self.config['options_slurm']['slurm_wrf.exe']]
      else:
        wrf_command = ['sbatch', self.config['options_slurm']['slurm_wrf.exe']]
      utils.check_file_exists(wrf_command[-1])
      try:
        res = subprocess.check_output(wrf_command, cwd=self.wrf_run_dir,
                                      stderr=utils.devnull())
        j_id = int(res.split()[-1])  # slurm job-id
      except subprocess.CalledProcessError:
        #logger.error('WRF failed %s:' %wrf_command)
        raise  # re-raise exception
      utils.waitJobToFinish(j_id)
    else:
      # run locally
      subprocess.check_call(os.path.join(self.wrf_run_dir, 'wrf.exe'), cwd=self.wrf_run_dir,
                            stdout=utils.devnull(), stderr=utils.devnull())

if __name__=="__main__":
  retry_wrf()
