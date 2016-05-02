#!/usr/bin/env python

'''
description:    WRF part of wrfpy
license:        APACHE 2.0
author:         Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

from config import config
from datetime import datetime
import glob
import os
import f90nml

class run_wrf(config):
  '''
  run_wrf is a subclass of config  # TODO: use better names
  '''
  def __init__(self, datestart, dateend):
    config.__init__(self)
    # TODO: wrf_run_dir should be flexible if running in UPP mode
    self.wrf_run_dir = self.config['filesystem']['wrf_run_dir']
    self.cleanup_previous_wrf_run()
    self.prepare_wrf_config(datestart, dateend)

  def cleanup_previous_wrf_run(self):
    from utils import silentremove
    '''
    cleanup initial/boundary conditions and namelist from previous WRF run
    '''
    # remove initial conditions (wrfinput files)
    for filename in glob.glob(os.path.join(
      self.config['filesystem']['wrf_run_dir'], 'wrfinput_d*')):
      silentremove(filename)
    # remove lateral boundary conditions (wrfbdy_d01)
    silentremove(os.path.join(self.config['filesystem']['wrf_run_dir'],
                              'wrfbdy_d01'))
    silentremove(os.path.join(self.config['filesystem']['wrf_run_dir'],
                              'namelist.input'))


  def prepare_wrf_config(self, datestart, dateend):
    '''
    Copy over default WRF namelist and modify time_control variables
    '''
    from datetime import datetime
    # check if both datestart and dateend are a datetime instance
    if not all([ isinstance(dt, datetime) for dt in [datestart, dateend] ]):
      raise TypeError("datestart and dateend must be an instance of datetime")
    # namelist.input target
    input_namelist = os.path.join(self.config['filesystem']['wrf_run_dir'],
                                  'namelist.input')
    # read WRF namelist in WRF work_dir
    wrf_nml = f90nml.read(self.config['options_wrf']['namelist.input'])
    # get number of domains
    ndoms = wrf_nml['domains']['max_dom']
    # check if ndoms is an integer and >0
    if not (isinstance(ndoms, int) and ndoms>0):
      raise ValueError("'domains_max_dom' namelist variable should be an " \
                      "integer>0")
    # define dictionary with time control values
    dict = {'time_control:start_year':datestart.year,
            'time_control:start_month':datestart.month,
            'time_control:start_day':datestart.day,
            'time_control:start_hour':datestart.hour,
            'time_control:end_year':dateend.year,
            'time_control:end_month':dateend.month,
            'time_control:end_day':dateend.day,
            'time_control:end_hour':dateend.hour,
            }
    # loop over dictionary and set start/end date parameters
    for el in dict.keys():
      if type(dict[el])!=list:
        wrf_nml[el.split(':')[0]][el.split(':')[1]] = [dict[el]] * ndoms
      else:
        wrf_nml[el.split(':')[0]][el.split(':')[1]] = dict[el] * ndoms
    # write namelist.input
    wrf_nml.write(os.path.join(
      self.config['filesystem']['wrf_run_dir'], 'namelist.input'))


  def run_real(self, j_id=None):
    '''
    run wrf real.exe
    '''
    # check if slurm_real.exe is defined
    if len(self.config['options_slurm']['slurm_real.exe']):
      if j_id:
        mid = "--dependency=afterok:%d" %j_id
        real_command = ['sbatch', mid, self.config['options_slurm']['slurm_real.exe']]
      else:
        real_command = ['sbatch', self.config['options_slurm']['slurm_real.exe']]
      utils.check_file_exists(real_command[-1])
      utils.silentremove(os.path.join(self.wrf_rundir, 'real.exe'))
      os.symlink(os.path.join(self.config['filesystem']['wrf_dir'],'main','real.exe'),
                 os.path.join(self.wrf_rundir, 'real.exe'))
      try:
        res = subprocess.check_output(real_command, cwd=self.wrf_rundir,
                                      stderr=utils.devnull())
        j_id = int(res.split()[-1])  # slurm job-id
      except subprocess.CalledProcessError:
        logger.error('Real failed %s:' %real_command)
        raise  # re-raise exception
      return j_id  # return slurm job-id
    else:  # run locally
      real_command = os.path.join(self.config['filesystem']['wrf_dir'],
                              'main', 'real.exe')
      utils.check_file_exists(real_command)
      try:
        subprocess.check_call(real_command, cwd=self.wrf_rundir,
                              stdout=utils.devnull(), stderr=utils.devnull())
      except subprocess.CalledProcessError:
        logger.error('real.exe failed %s:' %real_command)
        raise  # re-raise exception


  def run_wrf(self, j_id=None):
    '''
    run wrf.exe
    '''
    # check if slurm_wrf.exe is defined
    if len(self.config['options_slurm']['slurm_wrf.exe']):
      if j_id:
        mid = "--dependency=afterok:%d" %j_id
        wrf_command = ['sbatch', mid, self.config['options_slurm']['slurm_wrf.exe']]
      else:
        wrf_command = ['sbatch', self.config['options_slurm']['slurm_wrf.exe']]
      utils.check_file_exists(wrf_command[-1])
      utils.silentremove(os.path.join(self.wrf_rundir, 'wrf.exe'))
      os.symlink(os.path.join(self.config['filesystem']['wrf_dir'],'main','wrf.exe'),
                 os.path.join(self.wrf_rundir, 'wrf.exe'))
      try:
        res = subprocess.check_output(wrf_command, cwd=self.wrf_rundir,
                                      stderr=utils.devnull())
        j_id = int(res.split()[-1])  # slurm job-id
      except subprocess.CalledProcessError:
        logger.error('Wrf failed %s:' %wrf_command)
        raise  # re-raise exception
      return j_id  # return slurm job-id
    else:  # run locally
      wrf_command = os.path.join(self.config['filesystem']['wrf_dir'],
                              'main', 'wrf.exe')
      utils.check_file_exists(wrf_command)
      try:
        subprocess.check_call(wrf_command, cwd=self.wrf_rundir,
                              stdout=utils.devnull(), stderr=utils.devnull())
      except subprocess.CalledProcessError:
        logger.error('wrf.exe failed %s:' %wrf_command)
        raise  # re-raise exception


if __name__=="__main__":
  datestart= datetime(2014,07,16,00)
  dateend = datetime(2014,07,17,00)  
  wrf = run_wrf(datestart, dateend)
  real_jid = wrf.run_real()
